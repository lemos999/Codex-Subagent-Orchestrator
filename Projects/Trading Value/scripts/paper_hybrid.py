"""Hybrid Strategy Paper Trading — Live Market, Virtual Orders.

Connects to Binance Futures via ccxt for real-time 15m candles.
Uses strategy_deploy.HybridStrategy for signal generation.
Tracks virtual positions/PnL in data/paper_hybrid_state.json.
Dashboard on http://localhost:8895.

Usage:
    cd "Projects/Trading Value"
    py -3.12 scripts/paper_hybrid.py
"""
from __future__ import annotations

import json
import sys
import threading
import time
import http.server
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import ccxt
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "ccxt"])
    import ccxt

# Import our strategy
sys.path.insert(0, str(Path(__file__).resolve().parent))
from strategy_deploy import HybridStrategy, DEFAULT_MODEL_PATH, DEFAULT_PARAMS

# ── Config ────────────────────────────────────────────────────────────────────
SYMBOL = "ETH/USDT:USDT"
SYMBOL_SHORT = "ETHUSDT"
STATE_FILE = Path(__file__).resolve().parent.parent / "data" / "paper_hybrid_state.json"
LOG_FILE = Path(__file__).resolve().parent.parent / "data" / "paper_hybrid_log.jsonl"
DASH_PORT = 8895
INITIAL_BALANCE = 10_000.0
CYCLE_SECONDS = 60  # check every 1 minute, act on 15m bar close


@dataclass
class PaperState:
    balance: float = INITIAL_BALANCE
    position: str = "FLAT"
    entry_price: float = 0.0
    stop_price: float = 0.0
    tp_price: float = 0.0
    position_size: float = 0.0
    entry_time: str = ""
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    peak_balance: float = INITIAL_BALANCE
    max_drawdown_pct: float = 0.0
    current_pnl_pct: float = 0.0
    last_signal: dict = field(default_factory=dict)
    last_update: str = ""
    started_at: str = ""
    total_signals_checked: int = 0
    last_analysis_at_trade: int = 0  # trade count when last auto-analysis ran
    last_retrain_date: str = ""
    evolution_log: list = field(default_factory=list)  # auto-analysis decisions
    paused: bool = False
    pause_reason: str = ""
    confidence_threshold: float = 0.55  # can be auto-adjusted
    leverage: float = 1.6  # can be auto-adjusted (1.0 ~ 2.5, proven safe range)
    pause_count: int = 0  # how many times paused
    trades: list = field(default_factory=list)
    activity_log: list = field(default_factory=list)


class HybridPaperTrader:
    """Live paper trader using Hybrid (CMA-ES + XGBoost) strategy."""

    def __init__(self):
        # Exchange (read-only, public data only)
        self.exchange = ccxt.binance({"options": {"defaultType": "future"}})
        self.exchange.load_markets()

        # Strategy
        model_path = DEFAULT_MODEL_PATH
        if Path(model_path).exists():
            self.strategy = HybridStrategy(model_path=model_path)
            print(f"  [init] XGBoost model loaded: {model_path}")
        else:
            print(f"  [warn] No XGBoost model at {model_path}")
            print(f"         Run strategy_hybrid.py first to train the model.")
            print(f"         Starting in CMA-ES only mode...")
            self.strategy = None

        # State
        self.state = self._load_state()
        if not self.state.started_at:
            self.state.started_at = datetime.now(tz=timezone.utc).isoformat()
        self._last_15m_ts = 0  # timestamp of last processed 15m bar

        print(f"  [init] Balance: ${self.state.balance:,.2f}")
        print(f"  [init] Position: {self.state.position}")
        print(f"  [init] Started: {self.state.started_at[:19]}")
        if self.state.total_trades > 0:
            wr = self.state.wins / self.state.total_trades * 100
            print(f"  [init] Trades: {self.state.total_trades} (WR {wr:.1f}%)")

    def _load_state(self) -> PaperState:
        if STATE_FILE.exists():
            try:
                data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                trades = data.pop("trades", [])
                state = PaperState(**{k: v for k, v in data.items()
                                     if k in PaperState.__dataclass_fields__})
                state.trades = trades
                return state
            except Exception as e:
                print(f"  [warn] Failed to load state: {e}")
        return PaperState()

    def _save_state(self):
        data = asdict(self.state)
        STATE_FILE.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    def _log_trade(self, trade: dict):
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(trade, default=str) + "\n")

    def fetch_15m_candles(self, limit: int = 250) -> pd.DataFrame:
        """Fetch latest 15m candles from Binance."""
        ohlcv = self.exchange.fetch_ohlcv(SYMBOL, "15m", limit=limit)
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("datetime", inplace=True)
        df.drop(columns=["timestamp"], inplace=True)
        return df

    def cycle(self):
        """One trading cycle — called every minute, acts on 15m bar close."""
        now = datetime.now(tz=timezone.utc)

        # Only act on 15m bar boundaries (minute 0, 15, 30, 45)
        if now.minute % 15 != 0:
            return

        # Prevent double-processing same bar
        bar_ts = int(now.timestamp()) // 900 * 900
        if bar_ts == self._last_15m_ts:
            return
        self._last_15m_ts = bar_ts

        try:
            df_15m = self.fetch_15m_candles(250)
        except Exception as e:
            print(f"  [{now:%H:%M}] Fetch error: {e}")
            return

        current_price = df_15m["close"].iloc[-1]
        self.state.last_update = now.isoformat()
        self.state.total_signals_checked += 1

        # Update unrealized PnL
        if self.state.position == "LONG" and self.state.entry_price > 0:
            self.state.current_pnl_pct = (current_price / self.state.entry_price - 1) * 100
        elif self.state.position == "SHORT" and self.state.entry_price > 0:
            self.state.current_pnl_pct = (1 - current_price / self.state.entry_price) * 100
        else:
            self.state.current_pnl_pct = 0.0

        # Paused? Check auto-recovery, then skip trading
        if self.state.paused:
            # Auto-recovery: after 48 hours (192 x 15min bars), resume with min leverage
            pause_checks = sum(1 for l in self.state.activity_log[-192:]
                               if l.get("action") == "PAUSED")
            if pause_checks >= 192:
                self.state.paused = False
                self.state.leverage = 1.0  # minimum leverage on recovery
                self.state.confidence_threshold = min(
                    self.state.confidence_threshold + 0.03, 0.65)  # tighten entry
                if self.strategy:
                    self.strategy.params["leverage"] = 1.0
                    self.strategy.params["confidence_threshold"] = self.state.confidence_threshold
                recovery_msg = (f"Auto-recovery after 48h pause. "
                                f"Lev->1.0x, Conf->{self.state.confidence_threshold:.2f}")
                self.state.evolution_log.append({
                    "time": now.isoformat(),
                    "decision": "RECOVERED",
                    "adjustments": [recovery_msg],
                    "total_trades": self.state.total_trades,
                    "total_return": round((self.state.balance / INITIAL_BALANCE - 1) * 100, 2),
                })
                print(f"  [{now:%H:%M}] AUTO-RECOVERY: {recovery_msg}")
                # Fall through to normal trading
            signal = {"signal": "FLAT", "confidence": 0, "stop_loss": 0,
                      "take_profit": 0, "position_size": 0,
                      "reason": f"PAUSED: {self.state.pause_reason}"}
            self.state.last_signal = signal
            log_entry = {
                "time": now.strftime("%m-%d %H:%M"),
                "price": round(current_price, 2),
                "action": "PAUSED",
                "confidence": 0,
                "reason": self.state.pause_reason,
            }
            self.state.activity_log.append(log_entry)
            if len(self.state.activity_log) > 100:
                self.state.activity_log = self.state.activity_log[-100:]
            print(f"  [{now:%H:%M}] PAUSED: {self.state.pause_reason}")
            self._save_state()
            return

        # Get strategy signal
        if self.strategy:
            signal = self.strategy.update(df_15m)
        else:
            signal = {"signal": "FLAT", "confidence": 0, "stop_loss": 0,
                      "take_profit": 0, "position_size": 0, "reason": "No model"}

        # Ensure all signal values are JSON-native types (not numpy)
        self.state.last_signal = {
            k: float(v) if hasattr(v, 'item') else v
            for k, v in signal.items()
        }
        prev_position = self.state.position

        # ── Execute signal ────────────────────────────────────────────────
        if self.state.position != "FLAT" and signal["signal"] == "FLAT":
            # Close position
            self._close_position(current_price, signal["reason"])

        elif self.state.position == "FLAT" and signal["signal"] in ("LONG", "SHORT"):
            # Open position
            if signal["signal"] == "LONG" and signal.get("stop_loss", 0) > 0:
                self._open_position("LONG", current_price, signal)
            elif signal["signal"] == "SHORT" and signal.get("stop_loss", 0) > 0:
                self._open_position("SHORT", current_price, signal)

        # Log
        action = ""
        if prev_position == "FLAT" and self.state.position != "FLAT":
            action = f"ENTER {self.state.position}"
        elif prev_position != "FLAT" and self.state.position == "FLAT":
            action = f"EXIT {prev_position}"
        else:
            action = self.state.position

        # Activity log (keep last 100)
        log_entry = {
            "time": now.strftime("%m-%d %H:%M"),
            "price": round(current_price, 2),
            "action": action,
            "confidence": round(float(signal.get('confidence', 0)), 4),
            "reason": signal.get('reason', '')[:80],
        }
        self.state.activity_log.append(log_entry)
        if len(self.state.activity_log) > 100:
            self.state.activity_log = self.state.activity_log[-100:]

        print(f"  [{now:%H:%M}] ${current_price:,.2f} | {action} | "
              f"Bal=${self.state.balance:,.0f} | "
              f"Conf={signal['confidence']:.3f} | "
              f"{signal['reason'][:60]}")

        # ── Auto-analysis triggers ───────────────────────────────────────
        if not self.state.paused:
            self._maybe_auto_analyze()
            self._check_no_trade_stagnation()

        self._save_state()

    def _open_position(self, side: str, price: float, signal: dict):
        """Open a new position."""
        leverage = self.state.leverage
        risk = DEFAULT_PARAMS["risk_per_trade"]

        # Dynamic sizing based on DD
        dd_pct = 0
        if self.state.peak_balance > 0:
            dd_pct = (self.state.peak_balance - self.state.balance) / self.state.peak_balance * 100
        size_mult = 1.0
        if dd_pct > 25:
            size_mult = 0.25
        elif dd_pct > 15:
            size_mult = 0.50

        # Check consecutive losses
        recent = self.state.trades[-3:] if len(self.state.trades) >= 3 else []
        if len(recent) == 3 and all(t.get("pnl_pct", 0) < 0 for t in recent):
            size_mult = min(size_mult, 0.50)

        position_value = self.state.balance * risk * leverage * size_mult
        qty = position_value / price

        self.state.position = side
        self.state.entry_price = price
        self.state.stop_price = signal["stop_loss"]
        self.state.tp_price = signal["take_profit"]
        self.state.position_size = size_mult
        self.state.entry_time = datetime.now(tz=timezone.utc).isoformat()

        # Sync strategy internal state
        if self.strategy:
            self.strategy._position = side
            self.strategy._entry_price = price
            self.strategy._stop_price = signal["stop_loss"]
            self.strategy._tp_price = signal["take_profit"]

    def _close_position(self, price: float, reason: str):
        """Close current position and record trade."""
        if self.state.position == "LONG":
            pnl_pct = (price / self.state.entry_price - 1) * self.state.leverage * self.state.position_size
        elif self.state.position == "SHORT":
            pnl_pct = (1 - price / self.state.entry_price) * self.state.leverage * self.state.position_size
        else:
            return

        # Subtract commission
        pnl_pct -= (0.0004 + 0.0001) * self.state.leverage * self.state.position_size

        self.state.balance *= (1.0 + pnl_pct)
        if self.state.balance < 0:
            self.state.balance = 0.0
        self.state.total_trades += 1
        if pnl_pct > 0:
            self.state.wins += 1
        else:
            self.state.losses += 1

        if self.state.balance > self.state.peak_balance:
            self.state.peak_balance = self.state.balance
        dd = (self.state.peak_balance - self.state.balance) / self.state.peak_balance * 100
        if dd > self.state.max_drawdown_pct:
            self.state.max_drawdown_pct = dd

        trade = {
            "time": datetime.now(tz=timezone.utc).isoformat(),
            "side": self.state.position,
            "entry": self.state.entry_price,
            "exit": price,
            "pnl_pct": round(pnl_pct * 100, 2),
            "balance": round(self.state.balance, 2),
            "reason": reason,
        }
        self.state.trades.append(trade)
        self._log_trade(trade)

        # Reset position
        self.state.position = "FLAT"
        self.state.entry_price = 0.0
        self.state.stop_price = 0.0
        self.state.tp_price = 0.0
        self.state.position_size = 0.0
        self.state.current_pnl_pct = 0.0

        # Reset strategy state
        if self.strategy:
            self.strategy._position = "FLAT"
            self.strategy._bars_since_trade = 0

    # ── Auto-Analysis & Evolution Engine ──────────────────────────────────
    def _maybe_auto_analyze(self):
        """Trigger auto-analysis every 5 trades or 7 days."""
        trades_since = self.state.total_trades - self.state.last_analysis_at_trade
        if trades_since < 5:
            return  # not enough new data

        self.state.last_analysis_at_trade = self.state.total_trades
        now = datetime.now(tz=timezone.utc)
        print(f"\n  {'='*50}")
        print(f"  AUTO-ANALYSIS: {self.state.total_trades} trades completed")
        print(f"  {'='*50}")

        recent = self.state.trades[-10:]  # last 10 trades
        all_trades = self.state.trades

        # Compute metrics
        rets = [t.get("pnl_pct", 0) for t in all_trades]
        recent_rets = [t.get("pnl_pct", 0) for t in recent]
        total_ret = (self.state.balance / INITIAL_BALANCE - 1) * 100
        wr = self.state.wins / max(self.state.total_trades, 1) * 100
        recent_wr = sum(1 for r in recent_rets if r > 0) / max(len(recent_rets), 1) * 100
        avg_win = np.mean([r for r in rets if r > 0]) if any(r > 0 for r in rets) else 0
        avg_loss = np.mean([r for r in rets if r < 0]) if any(r < 0 for r in rets) else 0
        dd = self.state.max_drawdown_pct

        analysis = {
            "time": now.isoformat(),
            "total_trades": self.state.total_trades,
            "total_return": round(total_ret, 2),
            "win_rate": round(wr, 1),
            "recent_wr": round(recent_wr, 1),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "max_dd": round(dd, 2),
            "balance": round(self.state.balance, 2),
            "leverage": self.state.leverage,
            "confidence_threshold": self.state.confidence_threshold,
        }

        print(f"  Return: {total_ret:+.2f}% | WR: {wr:.0f}% | DD: -{dd:.1f}% | Lev: {self.state.leverage}x")
        print(f"  Recent 10: WR {recent_wr:.0f}% | Avg Win: {avg_win:+.2f}% | Avg Loss: {avg_loss:.2f}%")

        # ── Decision Engine ───────────────────────────────────────────────
        decision = "CONTINUE"
        adjustments = []

        # GOAL CHECK: sustained positive return with enough trades
        if total_ret > 10 and self.state.total_trades >= 20 and wr >= 50:
            decision = "GOAL_APPROACHING"
            adjustments.append("Target zone! Return +10%+ with 20+ trades. Keep monitoring.")

        # EMERGENCY: DD > 30% → pause
        if dd > 30:
            decision = "PAUSE"
            self.state.paused = True
            self.state.pause_count += 1
            self.state.pause_reason = f"DD {dd:.1f}% > 30% limit (pause #{self.state.pause_count})"
            adjustments.append(f"PAUSED: DD {dd:.1f}% exceeds safety limit. Auto-recovery in 48h with min leverage.")

        # UNDERPERFORMING: recent WR < 35% on 5+ trades
        elif len(recent) >= 5 and recent_wr < 35:
            # Tighten confidence threshold
            old_conf = self.state.confidence_threshold
            new_conf = min(old_conf + 0.02, 0.65)  # raise threshold, max 0.65
            if new_conf != old_conf:
                self.state.confidence_threshold = new_conf
                if self.strategy:
                    self.strategy.params["confidence_threshold"] = new_conf
                adjustments.append(f"Confidence threshold: {old_conf:.2f} → {new_conf:.2f} (tightened)")
                decision = "ADJUSTED"

        # OVERPERFORMING with very few trades: loosen threshold
        elif total_ret > 5 and self.state.total_trades >= 10 and wr >= 60:
            old_conf = self.state.confidence_threshold
            new_conf = max(old_conf - 0.01, 0.50)  # lower threshold, min 0.50
            if new_conf != old_conf:
                self.state.confidence_threshold = new_conf
                if self.strategy:
                    self.strategy.params["confidence_threshold"] = new_conf
                adjustments.append(f"Confidence threshold: {old_conf:.2f} → {new_conf:.2f} (loosened)")
                decision = "ADJUSTED"

        # AUTO RETRAIN: every 30 days
        should_retrain = False
        if self.state.last_retrain_date:
            try:
                last = datetime.fromisoformat(self.state.last_retrain_date)
                if (now - last).days >= 30:
                    should_retrain = True
            except Exception:
                should_retrain = True
        else:
            should_retrain = self.state.total_trades >= 10  # first retrain after 10 trades

        if should_retrain:
            adjustments.append("XGBoost retrain triggered (30-day cycle)")
            self._auto_retrain_xgb()
            self.state.last_retrain_date = now.isoformat()
            decision = "RETRAINED" if decision == "CONTINUE" else decision

        # LEVERAGE AUTO-ADJUST based on performance
        if self.state.total_trades >= 10 and decision not in ("PAUSE",):
            old_lev = self.state.leverage
            profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 1.0

            if total_ret > 5 and wr >= 55 and profit_factor >= 1.2 and dd < 20:
                # Strong performance → scale up (max 2.5x, proven safe)
                new_lev = min(old_lev + 0.2, 2.5)
            elif total_ret > 0 and wr >= 50 and dd < 25:
                # Decent performance → slight increase
                new_lev = min(old_lev + 0.1, 2.0)
            elif total_ret < -5 or dd > 20:
                # Losing → scale down
                new_lev = max(old_lev - 0.3, 1.0)
            elif recent_wr < 40 and len(recent) >= 5:
                # Recent slump → reduce
                new_lev = max(old_lev - 0.2, 1.0)
            else:
                new_lev = old_lev

            new_lev = round(new_lev, 1)
            if new_lev != old_lev:
                self.state.leverage = new_lev
                if self.strategy:
                    self.strategy.params["leverage"] = new_lev
                adjustments.append(f"Leverage: {old_lev}x → {new_lev}x "
                                   f"(PF={profit_factor:.2f}, DD={dd:.1f}%)")
                if decision == "CONTINUE":
                    decision = "ADJUSTED"

        # NO TRADES for too long: loosen threshold
        if self.state.total_signals_checked > 200 and self.state.total_trades == 0:
            old_conf = self.state.confidence_threshold
            new_conf = max(old_conf - 0.03, 0.50)
            if new_conf != old_conf:
                self.state.confidence_threshold = new_conf
                if self.strategy:
                    self.strategy.params["confidence_threshold"] = new_conf
                adjustments.append(f"No trades after {self.state.total_signals_checked} checks. "
                                   f"Threshold: {old_conf:.2f} → {new_conf:.2f}")
                decision = "ADJUSTED"

        if not adjustments:
            adjustments.append("No changes needed. Strategy performing within parameters.")

        analysis["decision"] = decision
        analysis["adjustments"] = adjustments
        self.state.evolution_log.append(analysis)

        # Keep last 50 evolution entries
        if len(self.state.evolution_log) > 50:
            self.state.evolution_log = self.state.evolution_log[-50:]

        for adj in adjustments:
            print(f"  >> {adj}")
        print(f"  Decision: {decision}")
        print(f"  {'='*50}\n")

        # Log to file
        evo_log_path = Path(__file__).resolve().parent.parent / "data" / "paper_evolution.jsonl"
        with open(evo_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(analysis, default=str) + "\n")

    def _auto_retrain_xgb(self):
        """Auto-retrain XGBoost model with latest data."""
        import subprocess
        retrain_script = Path(__file__).resolve().parent / "retrain_xgb.py"
        if not retrain_script.exists():
            print("  [retrain] retrain_xgb.py not found, skipping")
            return
        try:
            print("  [retrain] Starting XGBoost retrain...")
            result = subprocess.run(
                [sys.executable, str(retrain_script)],
                capture_output=True, text=True, timeout=300,
                cwd=str(Path(__file__).resolve().parent.parent),
            )
            if result.returncode == 0:
                print("  [retrain] XGBoost retrain complete. Reloading model...")
                # Reload model
                if self.strategy and Path(DEFAULT_MODEL_PATH).exists():
                    self.strategy.xgb_model.load_model(DEFAULT_MODEL_PATH)
                    print("  [retrain] Model reloaded successfully")
            else:
                print(f"  [retrain] Failed: {result.stderr[:200]}")
        except subprocess.TimeoutExpired:
            print("  [retrain] Timeout (5min)")
        except Exception as e:
            print(f"  [retrain] Error: {e}")

    def _check_no_trade_stagnation(self):
        """If no trades for too long, auto-adjust. Does NOT call _maybe_auto_analyze to avoid recursion."""
        if (self.state.total_signals_checked > 0
                and self.state.total_signals_checked % 200 == 0
                and self.state.total_trades == 0):
            old_conf = self.state.confidence_threshold
            new_conf = max(old_conf - 0.03, 0.50)
            if new_conf != old_conf:
                self.state.confidence_threshold = new_conf
                if self.strategy:
                    self.strategy.params["confidence_threshold"] = new_conf
                msg = (f"Stagnation: {self.state.total_signals_checked} checks, 0 trades. "
                       f"Threshold: {old_conf:.2f} -> {new_conf:.2f}")
                self.state.evolution_log.append({
                    "time": datetime.now(tz=timezone.utc).isoformat(),
                    "decision": "STAGNATION_ADJUST",
                    "adjustments": [msg],
                    "total_trades": 0,
                    "total_return": 0,
                })
                print(f"  >> {msg}")


# ── Dashboard ─────────────────────────────────────────────────────────────────
_trader: HybridPaperTrader | None = None

DASH_HTML = """<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8">
<title>Hybrid Paper Trading</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0e17;color:#e0e0e0;font-family:'Segoe UI',system-ui,monospace;min-height:100vh}
.hdr{background:#141926;padding:14px 24px;border-bottom:1px solid #2a3040;display:flex;justify-content:space-between;align-items:center}
.hdr h1{font-size:16px;color:#ff9800;letter-spacing:1px}
.hdr .sub{font-size:10px;color:#666;margin-left:12px}
.hdr .ts{font-size:11px;color:#555}
.wrap{padding:16px 24px;max-width:1000px;margin:0 auto}
.section{background:#141926;border:1px solid #2a3040;border-radius:8px;padding:16px;margin-bottom:14px}
.section h2{font-size:11px;color:#555;margin-bottom:10px;text-transform:uppercase;letter-spacing:1px}
.gn{color:#00d4aa}.rd{color:#ff4d6a}.yl{color:#ffd700}.bl{color:#4dabf7}.gy{color:#555}
.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:14px}
.metric{background:#0a0e17;padding:12px;border-radius:6px;border:1px solid #2a3040;text-align:center}
.metric .label{font-size:9px;color:#555;margin-bottom:4px}
.metric .value{font-size:18px;font-weight:bold}
table{width:100%;border-collapse:collapse;font-size:11px}
th{text-align:left;color:#555;padding:5px 6px;border-bottom:1px solid #2a3040;font-size:10px}
td{padding:5px 6px;border-bottom:1px solid #1a2030}
.pos-card{background:#0a0e17;border:1px solid #2a3040;border-radius:8px;padding:16px;margin-bottom:14px}
.pos-card .pos-title{font-size:13px;font-weight:bold;margin-bottom:8px}
.signal-box{background:#1a2030;border-left:3px solid #ff9800;padding:10px 12px;margin-top:8px;border-radius:0 6px 6px 0;font-size:11px}
.log-row{padding:4px 8px;border-bottom:1px solid #1a2030;font-size:10px;display:flex;gap:8px}
.log-row:hover{background:#1a2030}
.log-time{color:#555;min-width:75px}
.log-price{color:#888;min-width:70px}
.log-action{min-width:50px;font-weight:bold}
.log-conf{color:#666;min-width:50px}
.log-reason{color:#555;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.strategy-info{background:#1a2030;border-radius:6px;padding:12px;font-size:10px;color:#888;margin-bottom:14px}
.strategy-info b{color:#ff9800}
</style></head><body>
<div class="hdr">
  <div><h1>Hybrid Paper Trading</h1></div>
  <div class="ts" id="clock">--</div>
</div>
<div class="wrap">
  <div class="strategy-info">
    <b>ETH/USDT</b> | CMA-ES (MA 21/95) + XGBoost (&gt;55%) | Long Only |
    Stop: 3.89*ATR | TP: 3.75*ATR | Trail: 4.89/0.31*ATR | Lev: 1.6x | Risk: 1.9%/trade
  </div>
  <div class="metrics" id="metrics"></div>
  <div class="pos-card" id="posCard"></div>
  <div class="section"><h2>Latest Signal</h2><div class="signal-box" id="signal"></div></div>
  <div class="section" id="evoSection" style="display:none"><h2>Evolution Engine</h2><div id="evoLog"></div></div>
  <div class="two-col">
    <div class="section"><h2>Trade History</h2>
      <table><thead><tr><th>Time</th><th>Side</th><th>Entry</th><th>Exit</th><th>PnL%</th><th>Balance</th><th>Reason</th></tr></thead>
      <tbody id="trades"></tbody></table>
    </div>
    <div class="section"><h2>Activity Log (15m checks)</h2>
      <div id="activityLog" style="max-height:350px;overflow-y:auto"></div>
    </div>
  </div>
</div>
<script>
function fmt(v){return v>=0?'+'+v.toFixed(2):v.toFixed(2)}
async function refresh(){
  document.getElementById('clock').textContent=new Date().toLocaleString('ko-KR');
  try{
    const r=await fetch('/api/status?'+Date.now());
    if(!r.ok)return;
    const d=await r.json();
    const wr=d.total_trades>0?(d.wins/d.total_trades*100).toFixed(0)+'%':'--';
    const ret=((d.balance/10000-1)*100);
    const uptime=d.uptime||'--';
    const checks=d.total_signals_checked||0;

    document.getElementById('metrics').innerHTML=`
      <div class="metric"><div class="label">Balance</div><div class="value ${d.balance>=10000?'gn':'rd'}">$${Math.round(d.balance).toLocaleString()}</div></div>
      <div class="metric"><div class="label">Return</div><div class="value ${ret>=0?'gn':'rd'}">${fmt(ret)}%</div></div>
      <div class="metric"><div class="label">Win Rate</div><div class="value">${wr}</div></div>
      <div class="metric"><div class="label">Max DD</div><div class="value rd">${d.max_drawdown_pct>0?'-'+d.max_drawdown_pct.toFixed(1)+'%':'0%'}</div></div>
      <div class="metric"><div class="label">Uptime</div><div class="value bl">${uptime}</div></div>
      <div class="metric"><div class="label">Signals</div><div class="value gy">${checks}</div></div>
      <div class="metric"><div class="label">Leverage</div><div class="value yl">${(d.leverage||1.6).toFixed(1)}x</div></div>
      <div class="metric"><div class="label">Threshold</div><div class="value bl">${((d.confidence_threshold||0.55)*100).toFixed(0)}%</div></div>`;

    const pos=d.position;
    const pnl=d.current_pnl_pct||0;
    let posHtml='';
    if(pos!=='FLAT'){
      posHtml=`<div class="pos-title ${pos==='LONG'?'gn':'rd'}">${pos} @ $${parseFloat(d.entry_price).toFixed(2)}</div>
        <div style="font-size:11px;color:#888;margin-top:4px">
          Stop: $${parseFloat(d.stop_price).toFixed(2)} | TP: $${parseFloat(d.tp_price||0).toFixed(2)}</div>
        <div style="font-size:14px;margin-top:6px">Unrealized: <span class="${pnl>=0?'gn':'rd'}">${fmt(pnl)}%</span></div>`;
    } else {
      posHtml=`<div class="pos-title gy">FLAT — Waiting for entry signal</div>
        <div style="font-size:10px;color:#444;margin-top:4px">Entry: MA(21)&gt;MA(95) AND RSI&lt;28.3 AND Vol&gt;2.89x AND XGB&gt;55%</div>`;
    }
    document.getElementById('posCard').innerHTML=posHtml;

    const sig=d.last_signal||{};
    const conf=parseFloat(sig.confidence)||0;
    const lastUp=d.last_update?new Date(d.last_update).toLocaleString('ko-KR'):'--';
    document.getElementById('signal').innerHTML=`
      <div style="margin-bottom:4px"><b>${sig.signal||'--'}</b> | Confidence: <b>${conf.toFixed(3)}</b> | Updated: ${lastUp}</div>
      <div style="color:#666">${sig.reason||'--'}</div>`;

    // Trade history
    let rows='';
    const trades=(d.trades||[]).slice(-20).reverse();
    for(const t of trades){
      const pnl=t.pnl_pct||0;
      rows+=`<tr><td>${(t.time||'').slice(5,16)}</td><td class="${t.side==='LONG'?'gn':'rd'}">${t.side}</td>
        <td>$${parseFloat(t.entry||0).toFixed(2)}</td><td>$${parseFloat(t.exit||0).toFixed(2)}</td>
        <td class="${pnl>=0?'gn':'rd'}">${fmt(pnl)}%</td>
        <td>$${Math.round(t.balance||0).toLocaleString()}</td>
        <td style="color:#888;font-size:10px">${(t.reason||'').slice(0,40)}</td></tr>`;
    }
    if(!rows)rows='<tr><td colspan="7" class="gy" style="text-align:center;padding:20px">No trades yet — waiting for entry conditions</td></tr>';
    document.getElementById('trades').innerHTML=rows;

    // Activity log
    const logs=(d.activity_log||[]).slice(-30).reverse();
    let logHtml='';
    for(const l of logs){
      const actionCls=l.action==='FLAT'?'gy':l.action.includes('ENTER')?'gn':l.action.includes('EXIT')?'yl':'gy';
      logHtml+=`<div class="log-row">
        <span class="log-time">${l.time||''}</span>
        <span class="log-price">$${parseFloat(l.price||0).toLocaleString()}</span>
        <span class="log-action ${actionCls}">${l.action||''}</span>
        <span class="log-conf">${parseFloat(l.confidence||0).toFixed(3)}</span>
        <span class="log-reason">${l.reason||''}</span>
      </div>`;
    }
    if(!logHtml)logHtml='<div class="gy" style="text-align:center;padding:20px">Waiting for first 15m bar check...</div>';
    document.getElementById('activityLog').innerHTML=logHtml;

    // Evolution log
    const evos=(d.evolution_log||[]).slice(-10).reverse();
    const evoEl=document.getElementById('evoSection');
    if(evos.length>0){
      evoEl.style.display='block';
      let evoHtml='';
      for(const e of evos){
        const decCls=e.decision==='PAUSE'?'rd':e.decision==='GOAL_APPROACHING'?'gn':e.decision==='ADJUSTED'?'yl':'gy';
        evoHtml+=`<div style="background:#0a0e17;border:1px solid #2a3040;border-radius:6px;padding:10px;margin-bottom:8px">
          <div style="display:flex;justify-content:space-between;margin-bottom:6px">
            <span class="${decCls}" style="font-weight:bold">${e.decision}</span>
            <span class="gy" style="font-size:10px">${(e.time||'').slice(0,16)} | ${e.total_trades} trades</span>
          </div>
          <div style="font-size:11px;margin-bottom:4px">
            Return: <span class="${(e.total_return||0)>=0?'gn':'rd'}">${fmt(e.total_return||0)}%</span> |
            WR: ${e.win_rate||0}% | Recent WR: ${e.recent_wr||0}% | DD: -${e.max_dd||0}%
          </div>
          <div style="font-size:10px;color:#888">${(e.adjustments||[]).join(' | ')}</div>
        </div>`;
      }
      document.getElementById('evoLog').innerHTML=evoHtml;
    }

    // Pause banner
    if(d.paused){
      document.getElementById('posCard').innerHTML=`
        <div class="pos-title rd">PAUSED</div>
        <div style="color:#888;margin-top:4px">${d.pause_reason||'Safety limit reached'}</div>`;
    }

  }catch(e){console.error(e)}
}
refresh();setInterval(refresh,5000);
</script></body></html>"""


class DashHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/status"):
            data = asdict(_trader.state) if _trader else {}
            # Add computed uptime
            if _trader and _trader.state.started_at:
                try:
                    started = datetime.fromisoformat(_trader.state.started_at)
                    now = datetime.now(tz=timezone.utc)
                    delta = now - started
                    days = delta.days
                    hours = delta.seconds // 3600
                    mins = (delta.seconds % 3600) // 60
                    data["uptime"] = f"{days}d {hours}h {mins}m"
                    data["uptime_hours"] = round(delta.total_seconds() / 3600, 1)
                except Exception:
                    data["uptime"] = "--"
                    data["uptime_hours"] = 0
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(data, default=str).encode())
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(DASH_HTML.encode())

    def log_message(self, *a):
        pass


def start_dashboard(port=DASH_PORT):
    server = http.server.HTTPServer(("0.0.0.0", port), DashHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    print(f"  Dashboard: http://localhost:{port}")


def main():
    global _trader

    print("=" * 60)
    print("  Hybrid Strategy Paper Trading")
    print(f"  Symbol: {SYMBOL}")
    print(f"  Strategy: CMA-ES (MA 21/95) + XGBoost (>55%)")
    print(f"  Dashboard: http://localhost:{DASH_PORT}")
    print("=" * 60)

    _trader = HybridPaperTrader()
    start_dashboard()

    print(f"\n  Running... (Ctrl+C to stop)")
    print(f"  Checks every {CYCLE_SECONDS}s, acts on 15m bar close\n")

    try:
        while True:
            try:
                _trader.cycle()
            except KeyboardInterrupt:
                raise
            except Exception as e:
                print(f"  [error] {e}")
            time.sleep(CYCLE_SECONDS)
    except KeyboardInterrupt:
        print("\n  Stopped.")
        _trader._save_state()


if __name__ == "__main__":
    main()
