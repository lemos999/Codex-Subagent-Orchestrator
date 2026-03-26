"""FVG (Fair Value Gap) rule-based paper trader.

Implements the Day Trading FVG strategy for crypto:
- 15m anchor candle at configurable time (market open proxy)
- 5m breakout detection + FVG pattern recognition
- Limit order entry at FVG zone midpoint (forward-only, no retroactive)
- Stop at FVG first candle's wick
- RR 2:1 fixed target
- One trade per anchor cycle (4-hour window)
- Minimum risk distance: 0.3% of price

Three instances run simultaneously with different anchor times:
  H FVG-KR: 00:30 UTC (09:30 KST)
  I FVG-PM: 08:00 UTC (17:00 KST)
  J FVG-US: 13:30 UTC (09:30 EDT)
"""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field, asdict
from pathlib import Path

import ccxt
import pandas as pd


@dataclass
class FVGTrade:
    """Record of a completed FVG trade."""
    entry_time: str
    exit_time: str
    side: str
    entry_price: float
    exit_price: float
    qty: float
    pnl: float
    pnl_pct: float
    exit_reason: str
    bars_held: int


@dataclass
class FVGState:
    """Paper trading state (standalone, no heavy deps)."""
    balance: float = 10000.0
    position: int = 0
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
    # Compat fields for dashboard
    pending_intent: str = ""
    intent_price: float = 0.0


# State machine phases
PHASE_IDLE = "IDLE"              # waiting for anchor time
PHASE_ANCHOR = "ANCHOR_SET"      # anchor candle recorded, watching breakout
PHASE_BREAKOUT = "BREAKOUT"      # breakout detected, scanning for FVG
PHASE_PENDING = "FVG_PENDING"    # limit order set, waiting for fill
PHASE_POSITION = "IN_POSITION"   # position open
PHASE_DONE = "DONE"              # daily cycle complete

WINDOW_HOURS = 4       # max hours after anchor to find setup
MIN_RISK_PCT = 0.003   # minimum risk distance as % of price (0.3%)
MIN_FVG_PCT = 0.001    # minimum FVG gap size as % of price (0.1%)


class FVGTrader:
    """FVG rule-based paper trading engine."""

    def __init__(
        self,
        anchor_hour_utc: int,
        anchor_minute_utc: int,
        symbol: str = "ETH/USDT:USDT",
        leverage: int = 10,
        risk_pct: float = 0.005,
        commission_rate: float = 0.0004,
        state_file: str = "data/paper_state_fvg.json",
        log_file: str = "data/paper_log_fvg.jsonl",
        time_func=None,
    ):
        self._now = time_func or (lambda: self._now())
        self.anchor_hour = anchor_hour_utc
        self.anchor_minute = anchor_minute_utc
        self.symbol = symbol
        self.leverage = leverage
        self.risk_pct = risk_pct
        self.commission_rate = commission_rate
        self.state_file = Path(state_file)
        self.log_file = Path(log_file)

        # Shared exchange singleton
        if not hasattr(FVGTrader, '_shared_exchange'):
            FVGTrader._shared_exchange = ccxt.binance(
                {"options": {"defaultType": "future"}}
            )
            FVGTrader._shared_exchange.load_markets()
        self.exchange = FVGTrader._shared_exchange

        self.state = self._load_state()
        self._fvg = self._load_fvg_state()

    # ── State persistence ──────────────────────────────────────

    def _load_state(self) -> FVGState:
        if self.state_file.exists():
            data = json.loads(self.state_file.read_text())
            trades_raw = data.pop("trades", [])
            data.pop("fvg", None)
            state = FVGState(**{k: v for k, v in data.items()
                                  if k in FVGState.__dataclass_fields__})
            state.trades = [FVGTrade(**t) for t in trades_raw]
            return state
        return FVGState()

    def _load_fvg_state(self) -> dict:
        if self.state_file.exists():
            data = json.loads(self.state_file.read_text())
            return data.get("fvg", self._default_fvg())
        return self._default_fvg()

    def _default_fvg(self) -> dict:
        return {
            "phase": PHASE_IDLE,
            "anchor_key": "",
            "anchor_high": 0.0,
            "anchor_low": 0.0,
            "direction": "",       # "long" or "short"
            "fvg_high": 0.0,
            "fvg_low": 0.0,
            "fvg_stop": 0.0,
            "limit_price": 0.0,
            "target_price": 0.0,
            "breakout_time": "",
        }

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
            "trades": [asdict(t) for t in self.state.trades[-100:]],
            "fvg": self._fvg,
        }
        self.state_file.write_text(json.dumps(data, indent=2))

    def _log(self, event: str, details: dict):
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        entry = {"time": self._now().isoformat(),
                 "event": event, **details}
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    # ── Data fetching ──────────────────────────────────────────

    def _fetch(self, timeframe: str, limit: int = 200) -> pd.DataFrame:
        ohlcv = self.exchange.fetch_ohlcv(self.symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        return df

    def _current_price(self) -> float:
        ticker = self.exchange.fetch_ticker(self.symbol)
        return float(ticker["last"])

    # ── Anchor helpers ─────────────────────────────────────────

    def _get_anchor_datetime(self, now: datetime) -> datetime:
        """Get the most recent anchor time (today or yesterday)."""
        today_anchor = now.replace(
            hour=self.anchor_hour, minute=self.anchor_minute, second=0, microsecond=0
        )
        if now >= today_anchor:
            return today_anchor
        return today_anchor - timedelta(days=1)

    def _anchor_key(self, anchor_dt: datetime) -> str:
        return anchor_dt.strftime("%Y-%m-%d-%H%M")

    def _is_within_window(self, now: datetime, anchor_dt: datetime) -> bool:
        return timedelta(0) <= (now - anchor_dt) <= timedelta(hours=WINDOW_HOURS)

    def _find_anchor_bar(self, df_15m: pd.DataFrame, anchor_dt: datetime):
        """Find the 15m bar starting at anchor time."""
        for _, row in df_15m.iterrows():
            bar_start = row["timestamp"].to_pydatetime()
            dt = bar_start if bar_start.tzinfo else bar_start.replace(tzinfo=timezone.utc)
            if (dt.hour == anchor_dt.hour and dt.minute == anchor_dt.minute
                    and dt.date() == anchor_dt.date()):
                return row
        return None

    # ── FVG detection ──────────────────────────────────────────

    def _detect_fvg_pattern(self, df_5m: pd.DataFrame, direction: str,
                            after_time: datetime, ref_price: float):
        """Scan 5m bars for FVG pattern after breakout.

        Only returns FVGs with gap >= MIN_FVG_PCT of price
        and risk >= MIN_RISK_PCT of price.

        Returns (fvg_high, fvg_low, stop_price) or None.
        """
        bars = df_5m[df_5m["timestamp"] >= after_time].reset_index(drop=True)
        if len(bars) < 3:
            return None

        min_gap = ref_price * MIN_FVG_PCT
        min_risk = ref_price * MIN_RISK_PCT

        for i in range(2, len(bars)):
            c0 = bars.iloc[i - 2]  # first candle
            c2 = bars.iloc[i]      # third candle

            if direction == "long":
                # Bullish FVG: gap between c0.high and c2.low
                gap = c2["low"] - c0["high"]
                if gap > min_gap:
                    fvg_low = float(c0["high"])
                    fvg_high = float(c2["low"])
                    stop = float(c0["low"])
                    mid = (fvg_high + fvg_low) / 2
                    risk = abs(mid - stop)
                    if risk >= min_risk:
                        return fvg_high, fvg_low, stop

            elif direction == "short":
                # Bearish FVG: gap between c0.low and c2.high
                gap = c0["low"] - c2["high"]
                if gap > min_gap:
                    fvg_high = float(c0["low"])
                    fvg_low = float(c2["high"])
                    stop = float(c0["high"])
                    mid = (fvg_high + fvg_low) / 2
                    risk = abs(mid - stop)
                    if risk >= min_risk:
                        return fvg_high, fvg_low, stop

        return None

    # ── Main logic ─────────────────────────────────────────────

    def run_once(self):
        """Called every 30 minutes. Advance state machine by ONE phase only."""
        now = self._now()
        anchor_dt = self._get_anchor_datetime(now)
        anchor_key = self._anchor_key(anchor_dt)
        anchor_end = anchor_dt + timedelta(minutes=15)

        # New anchor cycle?
        if self._fvg["anchor_key"] != anchor_key:
            if self.state.position != 0:
                self._close_position("CYCLE_END")
            self._fvg = self._default_fvg()
            self._fvg["anchor_key"] = anchor_key
            self._fvg["phase"] = PHASE_IDLE

        # Done for this cycle
        if self._fvg["phase"] == PHASE_DONE:
            return

        # Too early — anchor candle not complete yet
        if now < anchor_end:
            return

        # Window expired
        if not self._is_within_window(now, anchor_dt):
            if self._fvg["phase"] in (PHASE_PENDING, PHASE_BREAKOUT, PHASE_ANCHOR):
                self._log("FVG_EXPIRED", {"reason": "window_closed",
                                           "phase": self._fvg["phase"]})
            self._fvg["phase"] = PHASE_DONE
            self._save_state()
            return

        # *** KEY FIX: advance only ONE phase per call to prevent retroactive entry ***

        if self._fvg["phase"] == PHASE_IDLE:
            self._phase_set_anchor(anchor_dt, anchor_key)

        elif self._fvg["phase"] == PHASE_ANCHOR:
            self._phase_check_breakout(anchor_end)

        elif self._fvg["phase"] == PHASE_BREAKOUT:
            self._phase_detect_fvg()

        elif self._fvg["phase"] == PHASE_PENDING:
            # Don't fill in run_once — let fast_check handle real-time fill
            pass

        elif self._fvg["phase"] == PHASE_POSITION:
            self._check_exit()

        self._save_state()

    def _phase_set_anchor(self, anchor_dt, anchor_key):
        """IDLE → ANCHOR_SET"""
        df_15m = self._fetch("15m", 50)
        bar = self._find_anchor_bar(df_15m, anchor_dt)
        if bar is not None:
            self._fvg["anchor_high"] = float(bar["high"])
            self._fvg["anchor_low"] = float(bar["low"])
            self._fvg["phase"] = PHASE_ANCHOR
            self._log("FVG_ANCHOR", {
                "high": self._fvg["anchor_high"],
                "low": self._fvg["anchor_low"],
                "anchor": anchor_key,
            })

    def _phase_check_breakout(self, anchor_end):
        """ANCHOR → BREAKOUT"""
        df_5m = self._fetch("5m", 100)
        bars_after = df_5m[df_5m["timestamp"] >= anchor_end]
        for _, bar in bars_after.iterrows():
            if bar["close"] > self._fvg["anchor_high"]:
                self._fvg["direction"] = "long"
                self._fvg["breakout_time"] = bar["timestamp"].isoformat()
                self._fvg["phase"] = PHASE_BREAKOUT
                self._log("FVG_BREAKOUT", {"direction": "long",
                                            "price": float(bar["close"])})
                return
            elif bar["close"] < self._fvg["anchor_low"]:
                self._fvg["direction"] = "short"
                self._fvg["breakout_time"] = bar["timestamp"].isoformat()
                self._fvg["phase"] = PHASE_BREAKOUT
                self._log("FVG_BREAKOUT", {"direction": "short",
                                            "price": float(bar["close"])})
                return

    def _phase_detect_fvg(self):
        """BREAKOUT → FVG_PENDING"""
        df_5m = self._fetch("5m", 100)
        bt = pd.Timestamp(self._fvg["breakout_time"])
        ref_price = self._current_price()
        result = self._detect_fvg_pattern(df_5m, self._fvg["direction"], bt, ref_price)
        if result:
            fvg_high, fvg_low, stop = result
            mid = (fvg_high + fvg_low) / 2
            risk = abs(mid - stop)

            # *** FIX: validate setup hasn't been invalidated ***
            price = self._current_price()
            if self._fvg["direction"] == "long":
                # For long: current price must be ABOVE the FVG zone (hasn't crashed through)
                if price < stop:
                    self._log("FVG_SKIP", {"reason": "price_below_stop",
                                            "price": price, "stop": stop})
                    self._fvg["phase"] = PHASE_DONE
                    return
            else:
                # For short: current price must be BELOW the FVG zone
                if price > stop:
                    self._log("FVG_SKIP", {"reason": "price_above_stop",
                                            "price": price, "stop": stop})
                    self._fvg["phase"] = PHASE_DONE
                    return

            self._fvg["fvg_high"] = fvg_high
            self._fvg["fvg_low"] = fvg_low
            self._fvg["fvg_stop"] = stop
            self._fvg["limit_price"] = mid

            # Target: RR 2:1
            if self._fvg["direction"] == "long":
                self._fvg["target_price"] = mid + risk * 2
            else:
                self._fvg["target_price"] = mid - risk * 2

            self._fvg["phase"] = PHASE_PENDING
            self._log("FVG_DETECTED", {
                "fvg_high": fvg_high, "fvg_low": fvg_low,
                "limit": mid, "stop": stop,
                "target": self._fvg["target_price"],
                "direction": self._fvg["direction"],
                "current_price": price,
            })

    def _check_limit_fill(self):
        """Check if current price reached FVG zone (limit order fill).
        Only called from fast_check for real-time fills."""
        limit = self._fvg["limit_price"]
        if limit <= 0:
            return

        price = self._current_price()
        stop = self._fvg["fvg_stop"]
        direction = self._fvg["direction"]

        # *** FIX: don't fill if price already past stop ***
        if direction == "long" and price < stop:
            self._log("FVG_INVALIDATED", {"reason": "price_below_stop",
                                           "price": price, "stop": stop})
            self._fvg["phase"] = PHASE_DONE
            return
        if direction == "short" and price > stop:
            self._log("FVG_INVALIDATED", {"reason": "price_above_stop",
                                           "price": price, "stop": stop})
            self._fvg["phase"] = PHASE_DONE
            return

        filled = False
        if direction == "long" and price <= limit:
            filled = True
        elif direction == "short" and price >= limit:
            filled = True

        if filled:
            self._open_position(price)  # use actual current price, not theoretical limit

    def _open_position(self, fill_price: float):
        """Open position at fill price."""
        direction = self._fvg["direction"]
        stop = self._fvg["fvg_stop"]
        target = self._fvg["target_price"]
        side = 1 if direction == "long" else -1

        risk_dist = abs(fill_price - stop)

        # *** FIX: enforce minimum risk distance ***
        min_risk = fill_price * MIN_RISK_PCT
        if risk_dist < min_risk:
            self._log("FVG_SKIP", {"reason": "risk_too_small",
                                    "risk": risk_dist, "min": min_risk})
            self._fvg["phase"] = PHASE_DONE
            return

        # Position sizing: risk_pct of balance
        risk_amount = self.state.balance * self.risk_pct
        qty = (risk_amount / risk_dist) * self.leverage

        # *** FIX: cap notional value at 10x balance ***
        max_notional = self.state.balance * 10
        notional = fill_price * qty
        if notional > max_notional:
            qty = max_notional / fill_price

        if qty <= 0:
            self._fvg["phase"] = PHASE_DONE
            return

        # Commission on entry
        comm = fill_price * qty * self.commission_rate
        self.state.balance -= comm

        self.state.position = side
        self.state.entry_price = fill_price
        self.state.stop_price = stop
        self.state.position_qty = qty
        self.state.bars_held = 0
        self.state.entry_time = self._now().isoformat()

        self._fvg["phase"] = PHASE_POSITION

        self._log("FVG_ENTRY", {
            "side": direction.upper(), "price": round(fill_price, 4),
            "stop": round(stop, 4), "target": round(target, 4),
            "qty": round(qty, 4), "risk": round(risk_dist, 4),
            "notional": round(fill_price * qty, 2),
            "commission": round(comm, 2),
        })

    def _check_exit(self):
        """Check stop loss and take profit."""
        if self.state.position == 0:
            return

        price = self._current_price()
        side = self.state.position
        stop = self.state.stop_price
        target = self._fvg["target_price"]

        hit_stop = (side == 1 and price <= stop) or (side == -1 and price >= stop)
        hit_target = (side == 1 and price >= target) or (side == -1 and price <= target)

        if hit_target:
            self._close_position("TARGET", exit_price=target)
        elif hit_stop:
            self._close_position("STOP", exit_price=stop)

    def _close_position(self, reason: str, exit_price: float = None):
        """Close current position."""
        if self.state.position == 0:
            return

        if exit_price is None:
            exit_price = self._current_price()

        side = self.state.position
        qty = self.state.position_qty
        entry = self.state.entry_price

        raw_pnl = (exit_price - entry) * side * qty
        comm = exit_price * qty * self.commission_rate
        pnl = raw_pnl - comm

        self.state.balance += pnl
        self.state.total_trades += 1
        if pnl > 0:
            self.state.wins += 1
        else:
            self.state.losses += 1

        # Track peak/drawdown
        if self.state.balance > self.state.peak_balance:
            self.state.peak_balance = self.state.balance
        dd = (self.state.peak_balance - self.state.balance) / self.state.peak_balance
        if dd > self.state.max_drawdown:
            self.state.max_drawdown = dd

        # Record trade
        trade = FVGTrade(
            entry_time=self.state.entry_time,
            exit_time=self._now().isoformat(),
            side="LONG" if side == 1 else "SHORT",
            entry_price=entry,
            exit_price=exit_price,
            qty=qty,
            pnl=round(pnl, 2),
            pnl_pct=round(pnl / 10000 * 100, 2),
            exit_reason=reason,
            bars_held=self.state.bars_held,
        )
        self.state.trades.append(trade)

        self._log("FVG_EXIT", {
            "reason": reason, "pnl": round(pnl, 2),
            "entry": round(entry, 4), "exit": round(exit_price, 4),
            "balance": round(self.state.balance, 2),
        })

        # Reset position
        self.state.position = 0
        self.state.entry_price = 0.0
        self.state.stop_price = 0.0
        self.state.position_qty = 0.0
        self.state.bars_held = 0
        self.state.entry_time = ""

        self._fvg["phase"] = PHASE_DONE
        self._save_state()

    def fast_check(self):
        """Called every 1 minute. Check stops, targets, and limit fills."""
        if self.state.position != 0:
            self._check_exit()
            if self.state.position == 0:
                self._save_state()
        elif self._fvg.get("phase") == PHASE_PENDING:
            self._check_limit_fill()
            if self.state.position != 0:
                self._save_state()
