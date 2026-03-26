"""Simulation runner — replays historical data through paper trading models.

Replays 1m candles at configurable speed, running the same 36 models
(9 models × 4 coins) as run_paper_all.py but against historical data.

Usage:
    cd "Projects/Trading Value" && PYTHONPATH=src py -3 scripts/run_sim.py
    PYTHONPATH=src py -3 scripts/run_sim.py --start 2026-03-01 --days 7
    PYTHONPATH=src py -3 scripts/run_sim.py --start 2026-03-01 --days 7 --speed 0
    PYTHONPATH=src py -3 scripts/run_sim.py --start 2026-03-01 --days 7 --speed 60

Speed:
    --speed 1    = 1 second per simulated minute (default, realtime feel)
    --speed 0    = instant (max speed, no delay)
    --speed 0.1  = 10x speed
    --speed 60   = 1 second per simulated hour
"""
from __future__ import annotations
import sys, json, time, argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np
from trading_value.adapters.paper import PaperTrader
from trading_value.adapters.fvg_trader import FVGTrader
from trading_value.adapters.sim_exchange import SimClock, MockExchange

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "sim_1m.sqlite"
SIM_STATUS_FILE = DATA_DIR / "sim_status.json"
SIM_LOG_FILE = DATA_DIR / "sim_log.jsonl"

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

ENSEMBLE_CONFIGS = [
    {"name": "D Diplomat", "m1": str(DATA_DIR / "rl_model_c_1100k"),
                           "m2": str(DATA_DIR / "rl_model_c_b_1350k")},
    {"name": "E Eagle",    "m1": str(DATA_DIR / "rl_model_c_1350_v1"),
                           "m2": str(DATA_DIR / "rl_model_c_1100k")},
]

FVG_ANCHORS = [
    {"name": "H FVG-KR", "anchor_utc": (0, 30)},
    {"name": "I FVG-PM", "anchor_utc": (8, 0)},
    {"name": "J FVG-US", "anchor_utc": (13, 30)},
]


class EnsembleTrader:
    def __init__(self, model1, model2):
        from sb3_contrib import RecurrentPPO
        self.m1 = RecurrentPPO.load(model1)
        self.m2 = RecurrentPPO.load(model2)
        self._ls1 = None
        self._ls2 = None
        self._es = np.ones((1,), dtype=bool)

    def predict(self, obs, **kwargs):
        a1, self._ls1 = self.m1.predict(obs, state=self._ls1, episode_start=self._es, deterministic=True)
        a2, self._ls2 = self.m2.predict(obs, state=self._ls2, episode_start=self._es, deterministic=True)
        self._es = np.zeros((1,), dtype=bool)
        a1i, a2i = int(a1), int(a2)
        if a1i == a2i: return np.array(a1i), None
        if a1i == 0: return np.array(a2i), None
        if a2i == 0: return np.array(a1i), None
        return np.array(0), None


def _display_name(coin_short, model_name):
    return model_name if coin_short == "ETH" else f"{coin_short}-{model_name}"


def _sim_state_path(coin_short, letter):
    prefix = "" if coin_short == "ETH" else f"{coin_short}_"
    return str(DATA_DIR / f"sim_state_{prefix}{letter}.json")


def _sim_log_path(coin_short, letter):
    prefix = "" if coin_short == "ETH" else f"{coin_short}_"
    return str(DATA_DIR / f"sim_log_{prefix}{letter}.jsonl")


def _clone_trader(src, symbol, state_file, log_file, exchange, time_func=None):
    """Clone a PaperTrader for a different coin, sharing model weights."""
    t = PaperTrader.__new__(PaperTrader)
    t._now = time_func or src._now
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
    t.exchange = exchange
    t.state = t._load_state()
    t.bars_30m = []
    t.bars_1h = []
    t.bars_4h = []
    t._snapshot_cache = {}
    return t


class SimRunner:
    """Simulation engine: replays historical data through trading models."""

    def __init__(self, clock: SimClock, mock_exchange: MockExchange):
        self.clock = clock
        self.exchange = mock_exchange
        self.traders: list[tuple[str, object]] = []
        self._build_models()

    def _build_models(self):
        """Build all 36 model instances, injecting MockExchange + SimClock."""
        eth_sym = "ETH/USDT:USDT"
        eth_traders = {}
        sim_time = self.clock.now  # inject sim clock

        # RL models (ETH first, loads weights)
        for m in RL_MODELS:
            t = PaperTrader(
                model_path=m["path"], symbol=eth_sym,
                leverage=10, risk_pct=0.0035, commission_rate=0.0004,
                state_file=_sim_state_path("ETH", m["name"][0]),
                log_file=_sim_log_path("ETH", m["name"][0]),
                time_func=sim_time,
            )
            t.exchange = self.exchange  # inject mock
            eth_traders[m["name"]] = t
            self.traders.append((m["name"], t))

        # Ensembles
        for cfg in ENSEMBLE_CONFIGS:
            t = PaperTrader(
                model_path=cfg["m2"], symbol=eth_sym,
                leverage=10, risk_pct=0.0035, commission_rate=0.0004,
                state_file=_sim_state_path("ETH", cfg["name"][0]),
                log_file=_sim_log_path("ETH", cfg["name"][0]),
                time_func=sim_time,
            )
            t.model = EnsembleTrader(cfg["m1"], cfg["m2"])
            t._is_lstm = False
            t.exchange = self.exchange
            eth_traders[cfg["name"]] = t
            self.traders.append((cfg["name"], t))

        # FVG ETH
        for fvg in FVG_ANCHORS:
            h, mn = fvg["anchor_utc"]
            t = FVGTrader(
                anchor_hour_utc=h, anchor_minute_utc=mn,
                symbol=eth_sym, leverage=10,
                risk_pct=0.005, commission_rate=0.0004,
                state_file=_sim_state_path("ETH", fvg["name"][0]),
                log_file=_sim_log_path("ETH", fvg["name"][0]),
                time_func=sim_time,
            )
            t.exchange = self.exchange
            self.traders.append((fvg["name"], t))

        # Clone for BTC, SOL, XRP
        for coin in COINS[1:]:
            cs, sym = coin["short"], coin["symbol"]
            for m in RL_MODELS:
                src = eth_traders[m["name"]]
                clone = _clone_trader(src, sym,
                    _sim_state_path(cs, m["name"][0]),
                    _sim_log_path(cs, m["name"][0]),
                    self.exchange, time_func=sim_time)
                self.traders.append((_display_name(cs, m["name"]), clone))

            for cfg in ENSEMBLE_CONFIGS:
                src = eth_traders[cfg["name"]]
                clone = _clone_trader(src, sym,
                    _sim_state_path(cs, cfg["name"][0]),
                    _sim_log_path(cs, cfg["name"][0]),
                    self.exchange, time_func=sim_time)
                clone.model = src.model
                clone._is_lstm = False
                self.traders.append((_display_name(cs, cfg["name"]), clone))

            for fvg in FVG_ANCHORS:
                h, mn = fvg["anchor_utc"]
                t = FVGTrader(
                    anchor_hour_utc=h, anchor_minute_utc=mn,
                    symbol=sym, leverage=10,
                    risk_pct=0.005, commission_rate=0.0004,
                    state_file=_sim_state_path(cs, fvg["name"][0]),
                    log_file=_sim_log_path(cs, fvg["name"][0]),
                    time_func=sim_time,
                )
                t.exchange = self.exchange
                self.traders.append((_display_name(cs, fvg["name"]), t))

        print(f"  [sim] {len(self.traders)} model instances ready")

    def _run_once_all(self):
        """30-minute evaluation for all models."""
        for name, t in self.traders:
            try:
                t.run_once()
            except Exception as e:
                pass  # silent in sim

    def _fast_check_all(self):
        """1-minute fast check for all models."""
        for name, t in self.traders:
            try:
                t.fast_check()
                t._save_state()
            except Exception:
                pass

    def _write_status(self):
        """Write sim status JSON for dashboard."""
        now = self.clock.now()
        status = {
            "timestamp": now.isoformat(),
            "sim_progress": round(self.clock.progress() * 100, 1),
            "sim_elapsed_min": self.clock.elapsed_minutes(),
            "sim_total_min": self.clock.total_minutes(),
            "models": {},
        }
        for name, t in self.traders:
            s = t.state
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
                "target_price": getattr(t, '_fvg', {}).get("target_price", 0.0),
                "fvg_phase": getattr(t, '_fvg', {}).get("phase", ""),
            }

        SIM_STATUS_FILE.write_text(json.dumps(status, indent=2))

    def run(self, speed: float = 1.0):
        """Run simulation loop.

        Args:
            speed: seconds of real time per simulated minute.
                   0 = instant, 1 = realtime (1s per min), 0.1 = 10x
        """
        total = self.clock.total_minutes()
        print(f"\n  [sim] Starting simulation")
        print(f"  [sim] Period: {self.clock.start} -> {self.clock.end}")
        print(f"  [sim] Total: {total:,} minutes ({total/60:.0f} hours, {total/1440:.1f} days)")
        print(f"  [sim] Speed: {'instant' if speed == 0 else f'{speed}s per sim-minute'}")
        if speed > 0 and total:
            eta = total * speed / 60
            print(f"  [sim] ETA: {eta:.0f} minutes real time")
        print()

        # Clean sim state files
        for f in DATA_DIR.glob("sim_state_*.json"):
            f.unlink()
        for f in DATA_DIR.glob("sim_log_*.jsonl"):
            f.unlink()
        if SIM_LOG_FILE.exists():
            SIM_LOG_FILE.unlink()

        last_status_min = -1

        while self.clock.tick():
            now = self.clock.now()
            elapsed = self.clock.elapsed_minutes()

            # 30-minute boundary: full eval
            if self.clock.is_30m_boundary():
                self._run_once_all()
                self._write_status()

                # Progress line
                pct = self.clock.progress() * 100
                # Count active positions and total PnL
                total_pnl = sum(t.state.balance - 10000 for _, t in self.traders)
                active = sum(1 for _, t in self.traders if t.state.position != 0)
                total_trades = sum(t.state.total_trades for _, t in self.traders)
                print(
                    f"  [{now.strftime('%Y-%m-%d %H:%M')}] "
                    f"{pct:5.1f}% | PnL ${total_pnl:+,.0f} | "
                    f"active={active} trades={total_trades}",
                    end="\r"
                )

            # Every minute: fast check
            self._fast_check_all()

            # Speed control
            if speed > 0:
                time.sleep(speed)

        # Final status
        self._run_once_all()
        self._write_status()
        print("\n")
        self._print_results()

    def _print_results(self):
        """Print final simulation results."""
        print("=" * 90)
        print(f"  SIMULATION RESULTS: {self.clock.start.strftime('%Y-%m-%d')} to {self.clock.end.strftime('%Y-%m-%d')}")
        print("=" * 90)
        print(f"{'Model':<24s} {'PnL':>10s} {'Trades':>7s} {'W/L':>7s} {'WinRate':>8s} {'MaxDD':>7s}")
        print("-" * 90)

        results = []
        for name, t in self.traders:
            s = t.state
            pnl = s.balance - 10000
            wr = f"{s.wins/s.total_trades*100:.0f}%" if s.total_trades > 0 else "-"
            dd = f"{s.max_drawdown*100:.1f}%"
            print(f"{name:<24s} ${pnl:>+9,.0f} {s.total_trades:>7d} {s.wins:>3d}/{s.losses:<3d} {wr:>8s} {dd:>7s}")
            results.append({"name": name, "pnl": pnl, "trades": s.total_trades,
                           "wins": s.wins, "losses": s.losses, "max_dd": s.max_drawdown})

        print("=" * 90)

        # Top 5 / Bottom 5
        results.sort(key=lambda x: x["pnl"], reverse=True)
        print(f"\n  TOP 5:")
        for r in results[:5]:
            print(f"    {r['name']:<24s} ${r['pnl']:>+9,.0f}")
        print(f"\n  BOTTOM 5:")
        for r in results[-5:]:
            print(f"    {r['name']:<24s} ${r['pnl']:>+9,.0f}")

        # Save results
        results_path = DATA_DIR / "sim_results.json"
        results_path.write_text(json.dumps(results, indent=2))
        print(f"\n  Results saved: {results_path}")


def main():
    parser = argparse.ArgumentParser(description="Simulation Trading Runner")
    parser.add_argument("--start", default="2026-03-19 00:00:00",
                       help="Start datetime (UTC)")
    parser.add_argument("--days", type=int, default=7,
                       help="Number of days to simulate")
    parser.add_argument("--speed", type=float, default=1.0,
                       help="Seconds per sim-minute (0=instant)")
    args = parser.parse_args()

    end_dt = datetime.strptime(args.start, "%Y-%m-%d %H:%M:%S") + timedelta(days=args.days)
    end_str = end_dt.strftime("%Y-%m-%d %H:%M:%S")

    print(f"Simulation Trading")
    print(f"  DB: {DB_PATH}")
    print(f"  Period: {args.start} -> {end_str} ({args.days} days)")

    clock = SimClock(start=args.start, end=end_str)
    exchange = MockExchange(clock, db_path=str(DB_PATH))

    print(f"  Loading models...")
    runner = SimRunner(clock, exchange)

    runner.run(speed=args.speed)


if __name__ == "__main__":
    main()
