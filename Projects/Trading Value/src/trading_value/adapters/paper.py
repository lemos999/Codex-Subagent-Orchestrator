"""Paper trading adapter — live market data, virtual orders.

Connects to Binance Futures via ccxt, feeds real-time 30m bars to the RL agent,
and tracks virtual positions/PnL without risking real money.

Usage:
    PYTHONPATH=src py -3 -m trading_value.adapters.paper
    or
    PYTHONPATH=src py -3 scripts/run_paper.py
"""
from __future__ import annotations

import json
import time
import sys
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field, asdict
from pathlib import Path

import ccxt
import numpy as np
import pandas as pd

from ..core.models import Timeframe
from ..core.indicators import build_all_snapshots


@dataclass
class PaperTrade:
    """Record of a completed paper trade."""
    entry_time: str
    exit_time: str
    side: str  # "LONG" or "SHORT"
    entry_price: float
    exit_price: float
    qty: float
    pnl: float
    pnl_pct: float
    exit_reason: str
    bars_held: int


@dataclass
class PaperState:
    """Current paper trading state."""
    balance: float = 10000.0
    position: int = 0  # -1, 0, 1
    entry_price: float = 0.0
    stop_price: float = 0.0
    position_qty: float = 0.0
    bars_held: int = 0
    entry_time: str = ""
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    peak_balance: float = 10000.0
    max_drawdown: float = 0.0
    trades: list = field(default_factory=list)
    # Execution engine: signal-execution separation
    pending_intent: str = ""      # "LONG", "SHORT", "CLOSE", "REVERSE", ""
    intent_price: float = 0.0     # 30m close price when intent was generated
    intent_atr: float = 0.0       # ATR at intent time
    intent_time: str = ""         # when intent was set
    intent_fills: int = 0         # how many 1-min checks since intent
    # Track A state (with virtual trading)
    track_a: dict = field(default_factory=lambda: {
        "regime": "UNKNOWN", "h1": "UNKNOWN", "m30": "UNKNOWN",
        "mode": "UNKNOWN", "setup": "IDLE", "signal": "waiting",
        "balance": 10000.0, "position": 0, "entry_price": 0.0,
        "stop_price": 0.0, "qty": 0.0, "pnl": 0.0,
        "total_trades": 0, "wins": 0, "losses": 0,
    })


class PaperTrader:
    """Live paper trading engine using RL v4 agent."""

    def __init__(
        self,
        model_path: str = "data/rl_model_v4",
        symbol: str = "ETH/USDT:USDT",
        leverage: int = 10,
        risk_pct: float = 0.0035,
        commission_rate: float = 0.0004,
        state_file: str = "data/paper_state.json",
        log_file: str = "data/paper_log.jsonl",
        time_func=None,
    ):
        self._now = time_func or (lambda: self._now())
        self._is_lstm = model_path and ("_c_" in model_path or "lstm" in model_path.lower())
        if self._is_lstm:
            from sb3_contrib import RecurrentPPO
            self.model = RecurrentPPO.load(model_path)
            self._lstm_states = None
            self._episode_start = np.ones((1,), dtype=bool)
        else:
            from stable_baselines3 import PPO
            self.model = PPO.load(model_path)
        self.symbol = symbol
        self.symbol_short = symbol.replace("/", "").replace(":USDT", "")
        self.leverage = leverage
        self.risk_pct = risk_pct
        self.commission_rate = commission_rate
        self.state_file = Path(state_file)
        self.log_file = Path(log_file)

        # Exchange connection (read-only, no API key needed for public data)
        # Shared singleton to avoid MemoryError when running 6 models
        if not hasattr(PaperTrader, '_shared_exchange'):
            PaperTrader._shared_exchange = ccxt.binance({"options": {"defaultType": "future"}})
            PaperTrader._shared_exchange.load_markets()
        self.exchange = PaperTrader._shared_exchange

        # Load or create state
        self.state = self._load_state()

        # Data buffers
        self.bars_30m: list[dict] = []
        self.bars_1h: list[dict] = []
        self.bars_4h: list[dict] = []

        # Snapshot caches (rebuilt on each cycle)
        self._snapshot_cache: dict[Timeframe, dict] = {}

    def _load_state(self) -> PaperState:
        if self.state_file.exists():
            with open(self.state_file) as f:
                data = json.load(f)
            state = PaperState(**{k: v for k, v in data.items() if k not in ("trades", "track_a")})
            state.trades = [PaperTrade(**t) for t in data.get("trades", [])]
            if "track_a" in data:
                state.track_a = data["track_a"]
            return state
        return PaperState()

    def _save_state(self):
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "balance": self.state.balance,
            "position": self.state.position,
            "entry_price": self.state.entry_price,
            "stop_price": self.state.stop_price,
            "position_qty": self.state.position_qty,
            "bars_held": self.state.bars_held,
            "entry_time": self.state.entry_time,
            "total_trades": self.state.total_trades,
            "wins": self.state.wins,
            "losses": self.state.losses,
            "peak_balance": self.state.peak_balance,
            "max_drawdown": self.state.max_drawdown,
            "trades": [asdict(t) for t in self.state.trades[-100:]],  # keep last 100
            "pending_intent": self.state.pending_intent,
            "intent_price": self.state.intent_price,
            "intent_atr": self.state.intent_atr,
            "intent_time": self.state.intent_time,
            "intent_fills": self.state.intent_fills,
            "track_a": self.state.track_a,
        }
        with open(self.state_file, "w") as f:
            json.dump(data, f, indent=2)

    def _log(self, event: str, details: dict):
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "time": self._now().isoformat(),
            "event": event,
            **details,
        }
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
        print(f"  [{entry['time'][:19]}] {event}: {details}")

    def fetch_history(self, timeframe: str, limit: int = 200) -> pd.DataFrame:
        """Fetch recent OHLCV bars from Binance."""
        ohlcv = self.exchange.fetch_ohlcv(self.symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        return df

    def _evaluate_track_a(self, snapshots):
        """Evaluate Track A (rule-based) with forward cloud + donchian + virtual trading."""
        try:
            from ..core.regime import classify_regime
            from ..core.mode import evaluate_mode
            from ..core.indicators import (
                analyze_forward_cloud, compute_donchian,
            )
            from ..core.setup import select_watch_zones

            ta = self.state.track_a
            for key, default in [("balance", 10000.0), ("position", 0), ("entry_price", 0.0),
                                  ("stop_price", 0.0), ("qty", 0.0), ("pnl", 0.0),
                                  ("total_trades", 0), ("wins", 0), ("losses", 0)]:
                if key not in ta:
                    ta[key] = default

            required = {Timeframe.H4, Timeframe.H1, Timeframe.M30}
            if not required.issubset(snapshots.keys()):
                return

            regime = classify_regime(snapshots)
            mode_result = evaluate_mode(regime)
            snap_30m = snapshots[Timeframe.M30]
            current_price = snap_30m.close
            atr = snap_30m.atr

            ta["regime"] = str(regime.htf.value)
            ta["h1"] = str(regime.h1.value)
            ta["m30"] = str(regime.m30.value)
            ta["mode"] = str(mode_result.mode.value)

            # --- Forward cloud analysis (Ichimoku predictive power) ---
            cloud_analysis = None
            try:
                df_30m = self.fetch_history("30m", 200)
                cloud_analysis = analyze_forward_cloud(df_30m)
                dc_upper, dc_lower, dc_middle = compute_donchian(df_30m, period=48)
                ta["donchian"] = f"U:{dc_upper:.0f} M:{dc_middle:.0f} L:{dc_lower:.0f}"
                ta["cloud_info"] = ""
                if cloud_analysis:
                    direction = "rising" if cloud_analysis.cloud_rising else "falling" if cloud_analysis.cloud_falling else "flat"
                    twist = cloud_analysis.twist_direction if cloud_analysis.twist_detected else "none"
                    ta["cloud_info"] = f"{direction} | thick:{cloud_analysis.future_cloud_thickness_pct:.1f}% | twist:{twist}"
            except Exception:
                dc_upper = dc_lower = dc_middle = 0
                ta["donchian"] = "-"
                ta["cloud_info"] = "-"

            # --- Check existing position ---
            if ta["position"] != 0:
                hit = False
                if ta["position"] == 1 and current_price <= ta["stop_price"]:
                    hit = True
                elif ta["position"] == -1 and current_price >= ta["stop_price"]:
                    hit = True

                # Trailing: if unrealized > 2R, tighten stop
                if not hit and ta["position"] != 0:
                    risk_dist = abs(ta["entry_price"] - ta["stop_price"])
                    if risk_dist > 0:
                        unrealized_r = (current_price - ta["entry_price"]) * ta["position"] / risk_dist
                        if unrealized_r >= 2.0:
                            if ta["position"] == 1:
                                new_stop = ta["entry_price"] + risk_dist
                                if new_stop > ta["stop_price"]:
                                    ta["stop_price"] = new_stop
                            else:
                                new_stop = ta["entry_price"] - risk_dist
                                if new_stop < ta["stop_price"]:
                                    ta["stop_price"] = new_stop

                if hit:
                    raw_pnl = (current_price - ta["entry_price"]) * ta["position"] * ta["qty"]
                    comm = current_price * ta["qty"] * self.commission_rate
                    pnl = raw_pnl - comm
                    ta["balance"] += pnl
                    ta["total_trades"] += 1
                    if pnl > 0:
                        ta["wins"] += 1
                    else:
                        ta["losses"] += 1
                    self._log("TRACK_A_STOP", {"price": current_price, "pnl": round(pnl, 2)})
                    ta["position"] = 0
                    ta["entry_price"] = 0.0
                    ta["stop_price"] = 0.0
                    ta["qty"] = 0.0

            ta["pnl"] = ta["balance"] - 10000.0

            # --- Enhanced mode decision (NEUTRAL에서도 거래 허용) ---
            strategy = None
            enhanced_signal = ""

            if mode_result.mode.value != "MODE_NO_TRADE":
                # Original mode allows trading
                strategy = mode_result.allowed_setups[0] if mode_result.allowed_setups else None
                enhanced_signal = strategy or "NONE"

            elif mode_result.mode.value == "MODE_NO_TRADE" and cloud_analysis and dc_upper > 0:
                # MODE_NO_TRADE but check cloud + donchian for override
                # 1. Cloud twist bullish + price near donchian upper → TREND_LONG
                if cloud_analysis.twist_detected and cloud_analysis.twist_direction == "bullish":
                    if current_price > dc_middle:
                        strategy = "TREND_LONG"
                        enhanced_signal = "CLOUD_TWIST_LONG"

                # 2. Cloud twist bearish + price near donchian lower → REBOUND_SHORT
                elif cloud_analysis.twist_detected and cloud_analysis.twist_direction == "bearish":
                    if current_price < dc_middle:
                        strategy = "REBOUND_SHORT"
                        enhanced_signal = "CLOUD_TWIST_SHORT"

                # 3. Cloud rising + donchian upper breakout → TREND_LONG
                elif cloud_analysis.cloud_rising and current_price >= dc_upper * 0.998:
                    strategy = "TREND_LONG"
                    enhanced_signal = "DC_BREAKOUT_LONG"

                # 4. Cloud falling + donchian lower breakdown → REBOUND_SHORT
                elif cloud_analysis.cloud_falling and current_price <= dc_lower * 1.002:
                    strategy = "REBOUND_SHORT"
                    enhanced_signal = "DC_BREAKDOWN_SHORT"

                # 5. Thin cloud (weak resistance) + price above cloud → TREND_LONG
                elif (cloud_analysis.future_cloud_thickness_pct < 0.5
                      and current_price > cloud_analysis.future_resistance):
                    strategy = "TREND_LONG"
                    enhanced_signal = "THIN_CLOUD_BREAK_LONG"

                if strategy:
                    ta["mode"] = f"ENHANCED_{strategy}"

            if not strategy:
                ta["signal"] = enhanced_signal or "NO_TRADE"
                ta["setup"] = "IDLE"
                return

            ta["signal"] = enhanced_signal or strategy

            # --- Already in position ---
            if ta["position"] != 0:
                ta["setup"] = "HOLDING"
                return

            # --- Entry logic: zone touch OR donchian level ---
            side = 1 if "LONG" in strategy else -1
            entered = False

            # Method 1: Traditional zone touch
            zones = select_watch_zones(strategy, snapshots, atr)
            touched = None
            for z in (zones or []):
                if z.low <= 0 or z.high <= 0:
                    continue
                if z.low <= current_price <= z.high:
                    touched = z
                    break

            if touched:
                if side == 1:
                    stop = touched.low - 0.2 * atr
                else:
                    stop = touched.high + 0.2 * atr
                ta["setup"] = "ZONE_ENTRY"
                entered = True

            # Method 2: Donchian-based entry (if no zone touch)
            elif dc_upper > 0 and not touched:
                if side == 1 and current_price >= dc_upper * 0.998:
                    stop = dc_middle  # donchian middle as stop
                    ta["setup"] = "DC_ENTRY"
                    entered = True
                elif side == -1 and current_price <= dc_lower * 1.002:
                    stop = dc_middle
                    ta["setup"] = "DC_ENTRY"
                    entered = True

            # Method 3: Forward cloud as support/resistance entry
            elif cloud_analysis and not touched:
                if side == 1 and abs(current_price - cloud_analysis.future_support) < atr * 0.5:
                    stop = cloud_analysis.future_support - 0.3 * atr
                    ta["setup"] = "CLOUD_ENTRY"
                    entered = True
                elif side == -1 and abs(current_price - cloud_analysis.future_resistance) < atr * 0.5:
                    stop = cloud_analysis.future_resistance + 0.3 * atr
                    ta["setup"] = "CLOUD_ENTRY"
                    entered = True

            if not entered:
                ta["setup"] = "WAIT"
                return

            # --- Score the entry quality ---
            from ..core.scorer import score_entry
            score = score_entry(
                strategy=strategy, side=side, current_price=current_price,
                snapshots=snapshots, cloud_analysis=cloud_analysis,
                dc_upper=dc_upper, dc_lower=dc_lower, dc_middle=dc_middle,
                zone_touched=(ta["setup"] == "ZONE_ENTRY"),
                recent_wins=ta.get("wins", 0), recent_losses=ta.get("losses", 0),
            )
            ta["score"] = score.total
            ta["score_detail"] = score.details[:80]

            ENTRY_THRESHOLD = 55
            if score.total < ENTRY_THRESHOLD:
                ta["setup"] = f"SCORE_LOW({score.total})"
                return

            # --- RR check ---
            risk_dist = abs(current_price - stop)
            if risk_dist <= 0:
                return
            if side == 1:
                target = dc_upper if dc_upper > current_price else current_price + risk_dist * 2
            else:
                target = dc_lower if dc_lower < current_price else current_price - risk_dist * 2
            rr = abs(target - current_price) / risk_dist
            if rr < 1.5:
                ta["setup"] = "RR_LOW"
                return

            # --- Position sizing ---
            risk_amount = ta["balance"] * 0.001
            qty = (risk_amount / risk_dist) * self.leverage if risk_dist > 0 else 0
            if qty <= 0:
                return

            comm = current_price * qty * self.commission_rate
            ta["balance"] -= comm
            ta["position"] = side
            ta["entry_price"] = current_price
            ta["stop_price"] = stop
            ta["qty"] = qty

            side_str = "LONG" if side == 1 else "SHORT"
            self._log("TRACK_A_OPEN", {
                "side": side_str, "strategy": strategy, "method": ta["setup"],
                "price": round(current_price, 2), "stop": round(stop, 2),
                "qty": round(qty, 4), "regime": ta["regime"],
                "cloud": ta.get("cloud_info", ""),
                "donchian": ta.get("donchian", ""),
            })

        except Exception as e:
            ta["signal"] = f"error: {e}"

    def build_observation(self) -> np.ndarray | None:
        """Build the 33-dim observation vector from live data."""
        from ..core.indicators import analyze_forward_cloud, compute_donchian_series, detect_swings
        from ..core.regime import classify_regime

        try:
            df_30m = self.fetch_history("30m", 200)
            df_1h = self.fetch_history("1h", 200)
            df_4h = self.fetch_history("4h", 200)
        except Exception as e:
            self._log("FETCH_ERROR", {"error": str(e)})
            return None

        # Build snapshots
        data = {Timeframe.M30: df_30m, Timeframe.H1: df_1h, Timeframe.H4: df_4h}
        snapshots = {}
        for tf, df in data.items():
            cache = build_all_snapshots(df, tf)
            if cache:
                last_key = max(cache.keys())
                snapshots[tf] = cache[last_key]

        if Timeframe.M30 not in snapshots:
            return None

        # Evaluate Track A with these snapshots
        self._evaluate_track_a(snapshots)

        # Build obs vector (same encoding as rl_env.py, 33 dims)
        obs = np.full(33, -1.0, dtype=np.float32)

        _CLOUD = {"above": 1.0, "in": 0.0, "below": -1.0}
        _TK = {"bullish": 1.0, "bearish": -1.0}
        _PROF = {"above_va": 1.0, "inside_va": 0.0, "below_va": -1.0}

        # [0-8] Cloud/TK/Profile for H4, H1, M30
        for i, tf in enumerate([Timeframe.H4, Timeframe.H1, Timeframe.M30]):
            if tf in snapshots:
                s = snapshots[tf]
                obs[i * 3] = _CLOUD.get(str(s.cloud_position), 0.0)
                obs[i * 3 + 1] = _TK.get(str(s.tk_state), 0.0)
                obs[i * 3 + 2] = _PROF.get(str(s.profile_bias), 0.0)

        # [9] Position
        obs[9] = float(self.state.position)

        # [10] Unrealized PnL in R units
        if self.state.position != 0 and self.state.entry_price > 0:
            current = snapshots[Timeframe.M30].close
            risk_dist = abs(self.state.entry_price - self.state.stop_price) or 1.0
            unrealized = (current - self.state.entry_price) * self.state.position
            obs[10] = np.clip(unrealized / risk_dist, -5, 5)

        # [11] ATR normalized
        atr = snapshots[Timeframe.M30].atr
        close = snapshots[Timeframe.M30].close
        obs[11] = np.clip(atr / close, 0, 5) if close > 0 else 0.0

        # [12-16] Recent 5 bar returns
        if len(df_30m) >= 6 and atr > 0:
            for j in range(5):
                idx = len(df_30m) - 5 + j
                ret = (df_30m.iloc[idx]["close"] - df_30m.iloc[idx - 1]["close"])
                obs[12 + j] = np.clip(ret / atr, -5, 5)

        # [17] Distance to nearest zone / ATR
        if atr > 0:
            zone_levels = []
            for s in snapshots.values():
                if hasattr(s, 'vah') and s.vah > 0: zone_levels.append(s.vah)
                if hasattr(s, 'val') and s.val > 0: zone_levels.append(s.val)
                if hasattr(s, 'poc') and s.poc > 0: zone_levels.append(s.poc)
            if zone_levels:
                min_dist = min(abs(close - z) for z in zone_levels)
                obs[17] = np.clip(min_dist / atr, 0, 5)

        # [18] Volume ratio
        vol = snapshots[Timeframe.M30].volume
        vol_sma = snapshots[Timeframe.M30].volume_sma_20
        obs[18] = np.clip(vol / vol_sma if vol_sma > 0 else 1.0, 0, 5)

        # [19] Consecutive losses
        obs[19] = min(self.state.losses, 5) / 5.0

        # [20] Time in position
        obs[20] = min(self.state.bars_held, 48) / 48.0

        # [21-24] Regime encoding
        _HTF = {"HTF_BULLISH": 1.0, "HTF_NEUTRAL": 0.0, "HTF_BEARISH": -1.0}
        _H1 = {"H1_BULLISH": 1.0, "H1_NEUTRAL": 0.0, "H1_BEARISH": -1.0}
        _M30 = {"M30_BULLISH": 1.0, "M30_NEUTRAL": 0.0, "M30_BEARISH": -1.0}
        _MODE = {"MODE_TREND_LONG": 1.0, "MODE_PULLBACK_LONG": 0.33,
                 "MODE_REBOUND_SHORT": -0.33, "MODE_NO_TRADE": -1.0}

        if all(tf in snapshots for tf in [Timeframe.H4, Timeframe.H1, Timeframe.M30]):
            regime = classify_regime(snapshots)
            if regime is not None:
                obs[21] = _HTF.get(regime.htf.value, 0.0)
                obs[22] = _H1.get(regime.h1.value, 0.0)
                obs[23] = _M30.get(regime.m30.value, 0.0)
                # Infer mode
                htf, h1, m30 = regime.htf.value, regime.h1.value, regime.m30.value
                if htf == "HTF_BULLISH" and h1 == "H1_BULLISH" and m30 == "M30_BULLISH":
                    obs[24] = _MODE["MODE_TREND_LONG"]
                elif htf == "HTF_BULLISH" and h1 != "H1_BEARISH":
                    obs[24] = _MODE["MODE_PULLBACK_LONG"]
                elif htf == "HTF_BEARISH" and m30 == "M30_BEARISH":
                    obs[24] = _MODE["MODE_REBOUND_SHORT"]
                else:
                    obs[24] = _MODE["MODE_NO_TRADE"]

        # [25-28] Forward cloud twist
        try:
            if len(df_30m) >= 78:
                fca = analyze_forward_cloud(df_30m)
                if fca is not None:
                    if fca.twist_detected:
                        obs[25] = 1.0 if fca.twist_direction == "bullish" else -1.0
                    else:
                        obs[25] = 0.0
                    obs[26] = 1.0 if fca.cloud_rising else (-1.0 if fca.cloud_falling else 0.0)
                    obs[27] = np.clip(fca.future_cloud_thickness_pct, 0, 5)
                    if close > fca.future_resistance:
                        obs[28] = 1.0
                    elif close < fca.future_support:
                        obs[28] = -1.0
                    else:
                        obs[28] = 0.0
        except Exception:
            pass

        # [29-32] Donchian channel + swing features
        try:
            if len(df_30m) >= 20 and atr > 0:
                dc = compute_donchian_series(df_30m, period=20)
                dc_upper = dc["dc_upper"].iloc[-1]
                dc_lower = dc["dc_lower"].iloc[-1]
                dc_range = dc_upper - dc_lower
                if dc_range > 0:
                    obs[29] = np.clip((close - dc_lower) / dc_range, -0.5, 1.5)

            if len(df_30m) >= 5 and atr > 0:
                sh, sl = detect_swings(df_30m, left=2, right=2)
                if sh and sl:
                    nearest_high = sh[-1][1]
                    nearest_low = sl[-1][1]
                    obs[30] = np.clip(abs(close - nearest_high) / atr, 0, 5)
                    obs[31] = np.clip(abs(close - nearest_low) / atr, 0, 5)
                    bars_since = len(df_30m) - 1 - max(sh[-1][0], sl[-1][0])
                    obs[32] = min(bars_since / 48.0, 1.0)
        except Exception:
            pass

        return obs

    def execute_action(self, action: int, current_price: float, atr: float):
        """Execute the agent's action on paper."""
        ACTION_NAMES = {0: "HOLD", 1: "LONG", 2: "SHORT", 3: "CLOSE", 4: "REVERSE"}
        action_name = ACTION_NAMES.get(action, "UNKNOWN")

        if action == 0:  # HOLD
            if self.state.position != 0:
                self.state.bars_held += 1
            return

        if action == 1:  # LONG
            if self.state.position == 0:
                self._open_position(1, current_price, atr)
            return

        if action == 2:  # SHORT
            if self.state.position == 0:
                self._open_position(-1, current_price, atr)
            return

        if action == 3:  # CLOSE
            if self.state.position != 0:
                self._close_position(current_price, "agent_close")
            return

        if action == 4:  # REVERSE
            if self.state.position != 0:
                old_side = self.state.position
                self._close_position(current_price, "reverse")
                self._open_position(-old_side, current_price, atr)
            return

    def _open_position(self, side: int, price: float, atr: float):
        risk_distance = max(atr, price * 0.001)
        stop = price - risk_distance if side == 1 else price + risk_distance
        risk_amount = self.state.balance * self.risk_pct
        qty = (risk_amount / risk_distance) * self.leverage if risk_distance > 0 else 0

        comm = price * qty * self.commission_rate
        self.state.balance -= comm

        self.state.position = side
        self.state.entry_price = price
        self.state.stop_price = stop
        self.state.position_qty = qty
        self.state.bars_held = 0
        self.state.entry_time = self._now().isoformat()

        side_str = "LONG" if side == 1 else "SHORT"
        self._log("OPEN", {
            "side": side_str, "price": price, "stop": round(stop, 2),
            "qty": round(qty, 4), "commission": round(comm, 2),
            "balance": round(self.state.balance, 2),
        })

    def _close_position(self, price: float, reason: str):
        raw_pnl = (price - self.state.entry_price) * self.state.position * self.state.position_qty
        comm = price * self.state.position_qty * self.commission_rate
        pnl = raw_pnl - comm

        self.state.balance += raw_pnl - comm
        if self.state.balance > self.state.peak_balance:
            self.state.peak_balance = self.state.balance
        dd = self.state.peak_balance - self.state.balance
        if dd > self.state.max_drawdown:
            self.state.max_drawdown = dd

        self.state.total_trades += 1
        if pnl > 0:
            self.state.wins += 1
        else:
            self.state.losses += 1

        trade = PaperTrade(
            entry_time=self.state.entry_time,
            exit_time=self._now().isoformat(),
            side="LONG" if self.state.position == 1 else "SHORT",
            entry_price=self.state.entry_price,
            exit_price=price,
            qty=self.state.position_qty,
            pnl=round(pnl, 2),
            pnl_pct=round(pnl / 10000 * 100, 2),
            exit_reason=reason,
            bars_held=self.state.bars_held,
        )
        self.state.trades.append(trade)

        self._log("CLOSE", {
            "reason": reason, "price": price,
            "pnl": round(pnl, 2), "balance": round(self.state.balance, 2),
            "bars_held": self.state.bars_held,
            "win_rate": f"{self.state.wins}/{self.state.total_trades}",
        })

        self.state.position = 0
        self.state.entry_price = 0.0
        self.state.stop_price = 0.0
        self.state.position_qty = 0.0
        self.state.bars_held = 0

    def check_stop_loss(self, high: float, low: float, close: float):
        """Check if stop loss was hit during this bar."""
        if self.state.position == 0:
            return
        if self.state.position == 1 and low <= self.state.stop_price:
            self._close_position(self.state.stop_price, "stop_loss")
        elif self.state.position == -1 and high >= self.state.stop_price:
            self._close_position(self.state.stop_price, "stop_loss")

    def fast_check(self) -> None:
        """1-minute fast monitoring between 30m evaluations.

        Four features:
        1. Pending intent execution: enter at better price (pullback) or timeout
        2. Real-time stop loss: check current price vs stop every minute
        3. Trailing profit lock: if unrealized > 2R, move stop to breakeven+1R
        4. Volatility circuit breaker: if 5m range > 3x ATR, emergency close
        """
        try:
            ticker = self.exchange.fetch_ticker(self.symbol)
            current = ticker["last"]
        except Exception:
            return

        # --- 0. Execute pending intent ---
        if self.state.pending_intent and self.state.position == 0:
            self.state.intent_fills += 1
            signal_price = self.state.intent_price
            atr = self.state.intent_atr or (current * 0.01)
            intent = self.state.pending_intent  # "LONG" or "SHORT"

            # Entry conditions:
            # a) Pullback: price moved favorably by 0.1~0.5 ATR from signal
            # b) Timeout: 15 minutes (15 checks) passed, enter at market
            # c) Adverse move > 1 ATR: cancel intent (opportunity gone)

            if intent == "LONG":
                pullback = signal_price - current  # positive = price dropped = good for long
                adverse = current - signal_price    # positive = price ran away
            else:  # SHORT
                pullback = current - signal_price  # positive = price rose = good for short
                adverse = signal_price - current    # positive = price dropped away

            filled = False
            reason = ""

            if pullback >= atr * 0.1:
                # Good pullback - enter now at better price
                filled = True
                reason = f"pullback ${pullback:+,.1f} ({pullback/atr:.1f}R)"
            elif self.state.intent_fills >= 15:
                # Timeout after 15 minutes - enter at market
                filled = True
                reason = f"timeout 15min (price ${current:,.2f})"
            elif adverse > atr * 1.0:
                # Price moved too far against us - cancel
                self._log("INTENT_CANCEL", {
                    "intent": intent,
                    "signal_price": signal_price,
                    "current": current,
                    "adverse": round(adverse, 2),
                    "reason": "price moved >1R against signal",
                })
                self.state.pending_intent = ""
                self._save_state()
                return

            if filled:
                action = 1 if intent == "LONG" else 2
                self.execute_action(action, current, atr)
                self._log("INTENT_FILL", {
                    "intent": intent,
                    "signal_price": signal_price,
                    "fill_price": current,
                    "improvement": round(pullback, 2),
                    "reason": reason,
                    "position": self.state.position,
                    "balance": round(self.state.balance, 2),
                })
                self.state.pending_intent = ""
                self._save_state()
            return  # don't run stop checks when not in position

        if self.state.position == 0:
            return

        entry = self.state.entry_price
        stop = self.state.stop_price
        side = self.state.position
        risk_dist = abs(entry - stop)
        if risk_dist <= 0:
            return

        # --- 1. Real-time stop check ---
        if side == 1 and current <= stop:
            self._close_position(current, "fast_stop")
            self._save_state()
            return
        if side == -1 and current >= stop:
            self._close_position(current, "fast_stop")
            self._save_state()
            return

        # --- 2. Trailing profit lock ---
        unrealized_r = (current - entry) * side / risk_dist
        if unrealized_r >= 2.0:
            # Move stop to entry + 1R (lock 1R profit)
            if side == 1:
                new_stop = entry + risk_dist
                if new_stop > self.state.stop_price:
                    self.state.stop_price = new_stop
                    self._log("TRAIL", {"new_stop": round(new_stop, 2),
                                        "unrealized_r": round(unrealized_r, 2),
                                        "price": current})
                    self._save_state()
            else:
                new_stop = entry - risk_dist
                if new_stop < self.state.stop_price:
                    self.state.stop_price = new_stop
                    self._log("TRAIL", {"new_stop": round(new_stop, 2),
                                        "unrealized_r": round(unrealized_r, 2),
                                        "price": current})
                    self._save_state()

        # --- 3. Volatility circuit breaker ---
        try:
            ohlcv_5m = self.exchange.fetch_ohlcv(self.symbol, "5m", limit=20)
            if len(ohlcv_5m) >= 15:
                ranges = [c[2] - c[3] for c in ohlcv_5m[-15:]]  # high - low
                avg_range = sum(ranges[:-1]) / len(ranges[:-1])
                last_range = ranges[-1]
                if avg_range > 0 and last_range > avg_range * 3.0:
                    self._log("CIRCUIT_BREAKER", {
                        "last_5m_range": round(last_range, 2),
                        "avg_range": round(avg_range, 2),
                        "ratio": round(last_range / avg_range, 1),
                        "price": current,
                    })
                    self._close_position(current, "circuit_breaker")
                    self._save_state()
        except Exception:
            pass

    def run_once(self) -> bool:
        """Run one 30m evaluation cycle.

        Signal-execution separation:
        - Model generates intent (LONG/SHORT/CLOSE/REVERSE/HOLD)
        - Intent is recorded but NOT immediately executed
        - fast_check() executes at optimal timing within the next 30 minutes
        - HOLD and CLOSE are still executed immediately (no benefit in delaying)
        """
        obs = self.build_observation()
        if obs is None:
            return False

        # Get current price info
        df = self.fetch_history("30m", 5)
        if df.empty:
            return False
        last_bar = df.iloc[-2]  # use completed bar, not current
        current = float(last_bar["close"])
        high = float(last_bar["high"])
        low = float(last_bar["low"])
        atr_approx = float(df["high"].iloc[-10:].max() - df["low"].iloc[-10:].min()) / 5 if len(df) >= 10 else current * 0.01

        # Check stop loss first
        self.check_stop_loss(high, low, current)

        # Get agent action
        if self._is_lstm:
            action, self._lstm_states = self.model.predict(
                obs, state=self._lstm_states,
                episode_start=self._episode_start, deterministic=True)
            self._episode_start = np.zeros((1,), dtype=bool)
        else:
            action, _ = self.model.predict(obs, deterministic=True)
        action = int(action)

        ACTION_NAMES = {0: "HOLD", 1: "LONG", 2: "SHORT", 3: "CLOSE", 4: "REVERSE"}
        action_name = ACTION_NAMES[action]

        # CLOSE/REVERSE on existing position: execute immediately (exit timing matters less)
        if action in (3, 4) and self.state.position != 0:
            self.execute_action(action, current, atr_approx)
            self.state.pending_intent = ""
            self._save_state()
            self._log("CYCLE", {
                "action": action_name, "price": current,
                "position": self.state.position,
                "balance": round(self.state.balance, 2),
                "execution": "immediate",
            })
            return True

        # LONG/SHORT entry: record as pending intent, execute via fast_check
        if action in (1, 2) and self.state.position == 0:
            self.state.pending_intent = action_name
            self.state.intent_price = current
            self.state.intent_atr = atr_approx
            self.state.intent_time = self._now().isoformat()
            self.state.intent_fills = 0
            self._save_state()
            self._log("INTENT", {
                "action": action_name, "signal_price": current,
                "atr": round(atr_approx, 2),
                "message": f"Waiting for better entry (target: pullback within {atr_approx:.0f})",
                "position": self.state.position,
                "balance": round(self.state.balance, 2),
            })
            return True

        # HOLD or no-op
        if action != 0 or self.state.position != 0:
            self._log("CYCLE", {
                "action": action_name, "price": current,
                "position": self.state.position,
                "balance": round(self.state.balance, 2),
            })
        self._save_state()
        return True

    def run_loop(self):
        """Run continuously: 1-minute fast checks + 30-minute full evaluation."""
        print(f"Paper Trading Started")
        print(f"  Symbol: {self.symbol}")
        print(f"  Leverage: {self.leverage}x")
        print(f"  Balance: ${self.state.balance:,.2f}")
        print(f"  Model: rl_model_v4")
        print(f"  Fast check: every 60s (stop/trail/circuit breaker)")
        print(f"  Full eval:  every 30m (RL agent decision)")
        print(f"  State: {self.state_file}")
        print(f"  Log: {self.log_file}")
        print()

        last_30m_eval = None

        while True:
            try:
                now = self._now()

                # --- 30m evaluation: at :00 and :30 ---
                bar_slot = now.minute // 30  # 0 or 1
                slot_key = f"{now.hour}:{bar_slot}"
                if slot_key != last_30m_eval and now.second >= 10:
                    # 30m bar just closed (+10s buffer)
                    print(f"  [{now.strftime('%H:%M:%S')}] 30m eval...")
                    self.run_once()
                    last_30m_eval = slot_key

                # --- 1m fast check ---
                if self.state.position != 0:
                    self.fast_check()

                # Sleep 60 seconds
                time.sleep(60)

            except KeyboardInterrupt:
                print("\nStopping paper trader...")
                self._save_state()
                break
            except Exception as e:
                self._log("ERROR", {"error": str(e)})
                time.sleep(60)

    def status(self) -> str:
        """Print current status."""
        s = self.state
        wr = f"{s.wins}/{s.total_trades} ({s.wins/s.total_trades*100:.0f}%)" if s.total_trades > 0 else "0/0"
        pos = "FLAT" if s.position == 0 else ("LONG" if s.position == 1 else "SHORT")
        lines = [
            f"=== Paper Trading Status ===",
            f"  Balance:  ${s.balance:,.2f} (peak ${s.peak_balance:,.2f})",
            f"  PnL:      ${s.balance - 10000:+,.2f}",
            f"  Position: {pos}" + (f" @ ${s.entry_price:,.2f} (held {s.bars_held} bars)" if s.position != 0 else ""),
            f"  Trades:   {s.total_trades} (W/L: {wr})",
            f"  Max DD:   ${s.max_drawdown:,.2f}",
        ]
        if s.trades:
            last = s.trades[-1]
            lines.append(f"  Last:     {last.side} ${last.pnl:+,.2f} ({last.exit_reason})")
        return "\n".join(lines)


if __name__ == "__main__":
    trader = PaperTrader()
    print(trader.status())
    trader.run_loop()
