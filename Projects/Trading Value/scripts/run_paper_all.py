"""Run 9 models × 4 coins for paper trading comparison.

Models: B Berserker, C Castle, D Diplomat, E Eagle, F Fortress, G Gladiator,
        H FVG-KR, I FVG-PM, J FVG-US
Coins:  ETH, BTC, SOL, XRP

Usage: cd "Projects/Trading Value" && PYTHONPATH=src py -3 scripts/run_paper_all.py
       PYTHONPATH=src py -3 scripts/run_paper_all.py --once   (single cycle)
       PYTHONPATH=src py -3 scripts/run_paper_all.py --status (show all statuses)
"""
from __future__ import annotations
import sys, json, time
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np
from trading_value.adapters.paper import PaperTrader
from trading_value.adapters.fvg_trader import FVGTrader

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

COINS = [
    {"symbol": "ETH/USDT:USDT", "short": "ETH"},
    {"symbol": "BTC/USDT:USDT", "short": "BTC"},
    {"symbol": "SOL/USDT:USDT", "short": "SOL"},
    {"symbol": "XRP/USDT:USDT", "short": "XRP"},
]

RL_MODELS = [
    {"name": "B Berserker", "path": str(DATA_DIR / "rl_model_b_3m")},
    {"name": "C Castle",    "path": str(DATA_DIR / "rl_model_c_b_1350k")},
    {"name": "F Fortress",  "path": str(DATA_DIR / "rl_model_c_v2_200k_validation")},
    {"name": "G Gladiator", "path": str(DATA_DIR / "rl_model_c_v2_r2_p30")},
]

ENSEMBLE_MODELS = [
    {"name": "D Diplomat", "m1": str(DATA_DIR / "rl_model_c_1100k"),
                           "m2": str(DATA_DIR / "rl_model_c_b_1350k")},
    {"name": "E Eagle",    "m1": str(DATA_DIR / "rl_model_c_1350_v1"),
                           "m2": str(DATA_DIR / "rl_model_c_1100k")},
]

FVG_ANCHORS = [
    {"name": "H FVG-KR", "anchor_utc": (0, 30)},   # 09:30 KST
    {"name": "I FVG-PM", "anchor_utc": (8, 0)},     # 17:00 KST
    {"name": "J FVG-US", "anchor_utc": (13, 30)},   # 09:30 EDT
]


class EnsembleTrader:
    """Wrapper for D/E ensemble models that overrides predict."""

    def __init__(self, model1, model2):
        from sb3_contrib import RecurrentPPO
        self.m1 = RecurrentPPO.load(model1)
        self.m2 = RecurrentPPO.load(model2)
        self._ls1 = None
        self._ls2 = None
        self._es = np.ones((1,), dtype=bool)

    def predict(self, obs, **kwargs):
        a1, self._ls1 = self.m1.predict(
            obs, state=self._ls1, episode_start=self._es, deterministic=True)
        a2, self._ls2 = self.m2.predict(
            obs, state=self._ls2, episode_start=self._es, deterministic=True)
        self._es = np.zeros((1,), dtype=bool)
        a1i, a2i = int(a1), int(a2)
        if a1i == a2i:
            ha = a1i
        elif a1i == 0:
            ha = a2i
        elif a2i == 0:
            ha = a1i
        else:
            ha = 0
        return np.array(ha), None


def _state_path(coin_short: str, model_letter: str) -> str:
    if coin_short == "ETH":
        return str(DATA_DIR / f"paper_state_{model_letter}.json")
    return str(DATA_DIR / f"paper_state_{coin_short}_{model_letter}.json")


def _log_path(coin_short: str, model_letter: str) -> str:
    if coin_short == "ETH":
        return str(DATA_DIR / f"paper_log_{model_letter}.jsonl")
    return str(DATA_DIR / f"paper_log_{coin_short}_{model_letter}.jsonl")


def _display_name(coin_short: str, model_name: str) -> str:
    if coin_short == "ETH":
        return model_name
    return f"{coin_short}-{model_name}"


def _clone_trader(src: PaperTrader, symbol: str, state_file: str, log_file: str) -> PaperTrader:
    """Create a PaperTrader sharing model weights with src, for a different coin."""
    t = PaperTrader.__new__(PaperTrader)
    t.model = src.model
    t._is_lstm = src._is_lstm
    if t._is_lstm:
        t._lstm_states = None
        t._episode_start = np.ones((1,), dtype=bool)
    t.symbol = symbol
    t.symbol_short = symbol.replace("/", "").replace(":USDT", "")
    t.leverage = src.leverage
    t.risk_pct = src.risk_pct
    t.commission_rate = src.commission_rate
    t.state_file = Path(state_file)
    t.log_file = Path(log_file)
    t.exchange = src.exchange
    t.state = t._load_state()
    t.bars_30m = []
    t.bars_1h = []
    t.bars_4h = []
    t._snapshot_cache = {}
    return t


class MultiPaperTrader:
    """Runs all models on all coins simultaneously."""

    def __init__(self):
        self.traders: list[tuple[str, object]] = []

        # --- Step 1: Build ETH models (loads model weights) ---
        eth_symbol = "ETH/USDT:USDT"
        eth_traders = {}  # name -> PaperTrader (for cloning)

        for m in RL_MODELS:
            trader = PaperTrader(
                model_path=m["path"], symbol=eth_symbol,
                leverage=10, risk_pct=0.0035, commission_rate=0.0004,
                state_file=_state_path("ETH", m["name"][0]),
                log_file=_log_path("ETH", m["name"][0]),
            )
            eth_traders[m["name"]] = trader
            self.traders.append((m["name"], trader))

        # Ensemble D
        d_trader = PaperTrader(
            model_path=ENSEMBLE_MODELS[0]["m2"], symbol=eth_symbol,
            leverage=10, risk_pct=0.0035, commission_rate=0.0004,
            state_file=_state_path("ETH", "D"),
            log_file=_log_path("ETH", "D"),
        )
        d_trader.model = EnsembleTrader(ENSEMBLE_MODELS[0]["m1"], ENSEMBLE_MODELS[0]["m2"])
        d_trader._is_lstm = False
        eth_traders["D Diplomat"] = d_trader
        self.traders.append(("D Diplomat", d_trader))

        # Ensemble E
        e_trader = PaperTrader(
            model_path=ENSEMBLE_MODELS[1]["m2"], symbol=eth_symbol,
            leverage=10, risk_pct=0.0035, commission_rate=0.0004,
            state_file=_state_path("ETH", "E"),
            log_file=_log_path("ETH", "E"),
        )
        e_trader.model = EnsembleTrader(ENSEMBLE_MODELS[1]["m1"], ENSEMBLE_MODELS[1]["m2"])
        e_trader._is_lstm = False
        eth_traders["E Eagle"] = e_trader
        self.traders.append(("E Eagle", e_trader))

        # FVG for ETH
        for fvg in FVG_ANCHORS:
            h, mn = fvg["anchor_utc"]
            letter = fvg["name"][0]
            t = FVGTrader(
                anchor_hour_utc=h, anchor_minute_utc=mn,
                symbol=eth_symbol, leverage=10,
                risk_pct=0.005, commission_rate=0.0004,
                state_file=_state_path("ETH", letter),
                log_file=_log_path("ETH", letter),
            )
            self.traders.append((fvg["name"], t))

        # --- Step 2: Clone for BTC, SOL, XRP (share model weights) ---
        for coin in COINS[1:]:  # skip ETH
            cs = coin["short"]
            sym = coin["symbol"]

            # Clone RL models
            for m in RL_MODELS:
                src = eth_traders[m["name"]]
                clone = _clone_trader(src, sym,
                    _state_path(cs, m["name"][0]),
                    _log_path(cs, m["name"][0]))
                self.traders.append((_display_name(cs, m["name"]), clone))

            # Clone ensemble D
            d_clone = _clone_trader(eth_traders["D Diplomat"], sym,
                _state_path(cs, "D"), _log_path(cs, "D"))
            d_clone.model = eth_traders["D Diplomat"].model  # share ensemble
            d_clone._is_lstm = False
            self.traders.append((_display_name(cs, "D Diplomat"), d_clone))

            # Clone ensemble E
            e_clone = _clone_trader(eth_traders["E Eagle"], sym,
                _state_path(cs, "E"), _log_path(cs, "E"))
            e_clone.model = eth_traders["E Eagle"].model
            e_clone._is_lstm = False
            self.traders.append((_display_name(cs, "E Eagle"), e_clone))

            # FVG for this coin
            for fvg in FVG_ANCHORS:
                h, mn = fvg["anchor_utc"]
                letter = fvg["name"][0]
                t = FVGTrader(
                    anchor_hour_utc=h, anchor_minute_utc=mn,
                    symbol=sym, leverage=10,
                    risk_pct=0.005, commission_rate=0.0004,
                    state_file=_state_path(cs, letter),
                    log_file=_log_path(cs, letter),
                )
                self.traders.append((_display_name(cs, fvg["name"]), t))

        print(f"  Loaded {len(self.traders)} model instances across {len(COINS)} coins")

    def status(self):
        lines = []
        lines.append("=" * 80)
        lines.append(f"{'Model':<24s} {'Balance':>10s} {'PnL':>10s} {'Pos':>6s} {'Trades':>7s} {'W/L':>7s}")
        lines.append("-" * 80)
        current_coin = ""
        for name, t in self.traders:
            # Detect coin change for separator
            coin = "ETH"
            for c in COINS[1:]:
                if name.startswith(c["short"] + "-"):
                    coin = c["short"]
                    break
            if coin != current_coin:
                if current_coin:
                    lines.append("-" * 80)
                current_coin = coin

            s = t.state
            pnl = s.balance - 10000
            pos = {1: "LONG", -1: "SHORT", 0: "FLAT"}[s.position]
            lines.append(
                f"{name:<24s} ${s.balance:>9,.0f} ${pnl:>+9,.0f} {pos:>6s} "
                f"{s.total_trades:>7d} {s.wins:>3d}/{s.losses:<3d}"
            )
        lines.append("=" * 80)
        return "\n".join(lines)

    def run_once(self):
        """Run one cycle for all models."""
        ts = datetime.now(tz=timezone.utc)
        ts_str = ts.strftime('%H:%M:%S')
        print(f"\n[{ts_str}] Running {len(self.traders)} models...")

        cycle_logs = []
        for name, trader in self.traders:
            try:
                prev_pos = trader.state.position
                prev_bal = trader.state.balance
                trader.run_once()
                s = trader.state
                pos = {1: "LONG", -1: "SHORT", 0: "FLAT"}[s.position]
                pnl = s.balance - 10000

                log_path = Path(trader.log_file)
                last_action = "?"
                if log_path.exists():
                    log_lines = log_path.read_text().strip().split("\n")
                    if log_lines:
                        try:
                            last = json.loads(log_lines[-1])
                            last_action = last.get("action", "?")
                        except Exception:
                            pass

                if prev_pos == 0 and s.position != 0:
                    event = f"ENTERED {pos} @ ${s.entry_price:,.2f}"
                elif prev_pos != 0 and s.position == 0:
                    delta = s.balance - prev_bal
                    event = f"CLOSED (PnL ${delta:+,.0f})"
                elif prev_pos != 0 and s.position != 0 and prev_pos != s.position:
                    event = f"REVERSED to {pos} @ ${s.entry_price:,.2f}"
                elif s.pending_intent:
                    event = f"INTENT {s.pending_intent} (waiting for pullback)"
                    last_action = f"INTENT_{s.pending_intent}"
                else:
                    event = f"action={last_action}"

                print(f"  {name}: {event} | {pos} | PnL=${pnl:+,.0f} | trades={s.total_trades}")

                cycle_logs.append({
                    "time": ts.isoformat(),
                    "model": name,
                    "action": last_action,
                    "event": event,
                    "position": s.position,
                    "balance": s.balance,
                    "pnl": pnl,
                    "total_trades": s.total_trades,
                    "entry_price": s.entry_price,
                })
            except Exception as e:
                print(f"  {name}: ERROR - {e}")
                cycle_logs.append({
                    "time": ts.isoformat(),
                    "model": name,
                    "action": "ERROR",
                    "event": str(e),
                    "position": 0, "balance": 0, "pnl": 0,
                    "total_trades": 0, "entry_price": 0,
                })

        log_path = DATA_DIR / "paper_all_log.jsonl"
        with open(log_path, "a") as f:
            for entry in cycle_logs:
                f.write(json.dumps(entry) + "\n")

    def fast_check_all(self):
        """1-minute fast check: stop loss + trailing + circuit breaker for all models."""
        triggered = False
        for name, trader in self.traders:
            if trader.state.position != 0:
                prev_pos = trader.state.position
                prev_bal = trader.state.balance
                try:
                    trader.fast_check()
                    trader._save_state()
                except Exception:
                    pass
                if trader.state.position == 0 and prev_pos != 0:
                    delta = trader.state.balance - prev_bal
                    ts = datetime.now(tz=timezone.utc)
                    event = f"FAST STOP! (PnL ${delta:+,.0f})"
                    print(f"  [{ts.strftime('%H:%M:%S')}] {name}: {event}")
                    log_entry = {
                        "time": ts.isoformat(),
                        "model": name,
                        "action": "FAST_STOP",
                        "event": event,
                        "position": 0,
                        "balance": trader.state.balance,
                        "pnl": trader.state.balance - 10000,
                        "total_trades": trader.state.total_trades,
                        "entry_price": 0,
                    }
                    log_path = DATA_DIR / "paper_all_log.jsonl"
                    with open(log_path, "a") as f:
                        f.write(json.dumps(log_entry) + "\n")
                    triggered = True
        if triggered:
            self._write_dashboard_status()

    def run_loop(self):
        """Run continuously: 1-min fast checks + 30-min full evaluation."""
        print("Starting multi-coin paper trading")
        print(f"  Coins: {', '.join(c['short'] for c in COINS)}")
        print(f"  Models per coin: 9")
        print(f"  Total instances: {len(self.traders)}")
        print(f"  Full eval:  every 30m (at :00 and :30)")
        print(f"  Fast check: every 60s (stop/trail/circuit breaker)")
        print(self.status())
        self._write_dashboard_status()

        last_30m_eval = None

        while True:
            try:
                now = datetime.now(tz=timezone.utc)

                bar_slot = now.minute // 30
                slot_key = f"{now.hour}:{bar_slot}"
                if slot_key != last_30m_eval and now.second >= 10:
                    print(f"\n[{now.strftime('%H:%M:%S')}] 30m eval...")
                    self.run_once()
                    print()
                    print(self.status())
                    self._write_dashboard_status()
                    last_30m_eval = slot_key

                self.fast_check_all()

                time.sleep(60)

            except KeyboardInterrupt:
                print("\nStopping...")
                for _, t in self.traders:
                    t._save_state()
                break
            except Exception as e:
                print(f"  ERROR: {e}")
                time.sleep(60)

    def _write_dashboard_status(self):
        """Write combined status JSON for dashboard."""
        status = {
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "models": {},
        }
        for name, t in self.traders:
            s = t.state
            # Detect coin from name
            coin = "ETH"
            for c in COINS[1:]:
                if name.startswith(c["short"] + "-"):
                    coin = c["short"]
                    break

            status["models"][name] = {
                "coin": coin,
                "balance": s.balance,
                "pnl": s.balance - 10000,
                "position": s.position,
                "entry_price": s.entry_price,
                "stop_price": s.stop_price,
                "position_qty": s.position_qty,
                "total_trades": s.total_trades,
                "wins": s.wins,
                "losses": s.losses,
                "peak_balance": s.peak_balance,
                "max_drawdown": s.max_drawdown,
                "bars_held": s.bars_held,
                "pending_intent": s.pending_intent,
                "intent_price": s.intent_price,
                "target_price": getattr(t, '_fvg', {}).get("target_price", 0.0),
                "fvg_phase": getattr(t, '_fvg', {}).get("phase", ""),
                "trades": [
                    {
                        "entry_time": tr.entry_time,
                        "exit_time": tr.exit_time,
                        "side": tr.side,
                        "pnl": tr.pnl,
                        "pnl_pct": tr.pnl_pct,
                        "bars_held": tr.bars_held,
                    }
                    for tr in s.trades[-20:]
                ],
            }

        path = DATA_DIR / "paper_all_status.json"
        with open(path, "w") as f:
            json.dump(status, f, indent=2)


def main():
    try:
        multi = MultiPaperTrader()
    except Exception as e:
        print(f"\n[FATAL] Failed to initialize models: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    if "--status" in sys.argv:
        print(multi.status())
    elif "--once" in sys.argv:
        multi.run_once()
        print()
        print(multi.status())
        multi._write_dashboard_status()
    else:
        multi.run_loop()


if __name__ == "__main__":
    main()
