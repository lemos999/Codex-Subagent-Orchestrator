"""Staged backtest: 3-month sequential validation.

Simulates real trading progression:
- Stage 1: Month 1 — must be PnL > 0 to advance
- Stage 2: Month 2 — must be PnL > 0 to advance
- Stage 3: Month 3 — must be PnL > 0 to pass

Balance carries forward between stages (like real trading).
Tests both Track A (rule-based) and Track B (RL v5).

Usage: cd "Projects/Trading Value" && PYTHONPATH=src py -3 scripts/staged_backtest.py
"""
from __future__ import annotations
import sqlite3, sys, random
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from stable_baselines3 import PPO
from trading_value.adapters.backtest import BacktestConfig, BacktestEngine
from trading_value.adapters.rl_env import TradingEnv
from trading_value.core.models import Timeframe

DB = str(Path(__file__).resolve().parent.parent / "data" / "cache.sqlite")
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Available data range (from DB)
DATA_START = "2022-01-01"
DATA_END = "2025-01-31"


def load_data(start, end):
    conn = sqlite3.connect(DB)
    def load_tf(tf_str):
        df = pd.read_sql_query(
            "SELECT datetime as timestamp, open, high, low, close, volume "
            "FROM ohlcv WHERE symbol='ETHUSDT' AND timeframe=? "
            "AND datetime >= ? AND datetime <= ? ORDER BY timestamp",
            conn, params=(tf_str, start, end),
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        return df
    df15 = load_tf("15m")
    if df15.empty:
        conn.close()
        return None, None
    df30 = (
        df15.set_index("timestamp")
        .resample("30min")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
        .dropna()
        .reset_index()
    )
    data = {
        Timeframe.M30: df30,
        Timeframe.H1: load_tf("1h"),
        Timeframe.H4: load_tf("4h"),
        Timeframe.M15: df15,
    }
    conn.close()
    return data, df30


def pick_3month_start():
    """Pick a random 3-month start date from available data (excluding last 3 months)."""
    # Available months: 2022-01 to 2024-10 (leave 3 months buffer)
    candidates = []
    for year in range(2022, 2025):
        for month in range(1, 13):
            dt = datetime(year, month, 1)
            end_dt = datetime(year + (month + 2) // 12, ((month + 2) % 12) or 12, 28)
            if end_dt <= datetime(2025, 1, 1):
                candidates.append(dt)
    return random.choice(candidates)


def month_range(start_dt, month_offset):
    """Get (start, end) date strings for a month at offset from start_dt."""
    y = start_dt.year + (start_dt.month + month_offset - 1) // 12
    m = ((start_dt.month + month_offset - 1) % 12) + 1
    start = f"{y}-{m:02d}-01"
    # End of month
    if m == 12:
        end = f"{y + 1}-01-01"
    else:
        end = f"{y}-{m + 1:02d}-01"
    return start, end


# ---------------------------------------------------------------------------
# Track A: Rule-based backtest
# ---------------------------------------------------------------------------

def run_track_a_month(start, end, balance):
    """Run Track A backtest for one month, return (pnl, trades, balance, win_rate)."""
    data, df30 = load_data(start, end)
    if data is None or df30 is None or len(df30) < 50:
        return 0, 0, balance, 0, 0

    bt_data = {"ETHUSDT": data}
    config = BacktestConfig(
        symbols=["ETHUSDT"],
        initial_balance=balance,
        commission_rate=0.0004,
        primary_timeframe=Timeframe.M15,
        min_rr=2.28,
        risk_pct=0.001,
        use_full_triggers=True,
    )
    engine = BacktestEngine(config)
    result = engine.run(bt_data)
    new_balance = balance + result.total_pnl
    return result.total_pnl, result.total_trades, new_balance, result.win_rate, result.max_drawdown


# ---------------------------------------------------------------------------
# Track B: RL v5 backtest
# ---------------------------------------------------------------------------

V5_CONFIG = dict(
    position_change_penalty=0.30,
    holding_cost=0.002,
    profitable_hold_bonus_max=0.02,
    profitable_close_bonus=0.2,
    drawdown_penalty_factor=0.15,
)


def run_track_b_month(start, end, balance, model, obs_dim=29):
    """Run Track B (RL) for one month, return (pnl, entries, balance, commission)."""
    data, df30 = load_data(start, end)
    if data is None or df30 is None or len(df30) < 50:
        return 0, 0, balance, 0

    # Remove M15 from data to keep only 4h/1h/30m
    data_rl = {k: v for k, v in data.items() if k in (Timeframe.M30, Timeframe.H1, Timeframe.H4)}

    env = TradingEnv(
        data=data_rl, symbol="ETHUSDT",
        initial_balance=balance,
        commission_rate=0.0004,
        episode_bars=len(df30) - 50,
        random_start=False,
        **V5_CONFIG,
    )
    obs, _ = env.reset()
    positions = []
    done = False
    while not done:
        action, _ = model.predict(obs, deterministic=True)
        obs, _, term, trunc, _ = env.step(action)
        positions.append(env._position)
        done = term or trunc

    pnl = env._balance - balance
    entries = sum(1 for i in range(1, len(positions)) if positions[i] != 0 and positions[i-1] == 0)
    return pnl, entries, env._balance, env._total_commission


# ---------------------------------------------------------------------------
# Main staged test
# ---------------------------------------------------------------------------

def run_staged_test(start_dt, track, model=None):
    """Run 3-stage sequential test. Returns (passed, results_per_stage)."""
    balance = 10000.0
    results = []

    for stage in range(3):
        m_start, m_end = month_range(start_dt, stage)
        month_label = m_start[:7]

        if track == "A":
            pnl, trades, balance, wr, mdd = run_track_a_month(m_start, m_end, balance)
            info = f"trades={trades}, WR={wr:.0f}%, MDD=${mdd:,.0f}"
        else:
            pnl, entries, balance, comm = run_track_b_month(m_start, m_end, balance, model)
            info = f"entries={entries}, comm=${comm:,.0f}"

        passed = pnl > 0
        status = "PASS" if passed else "FAIL"
        results.append({
            "stage": stage + 1,
            "month": month_label,
            "pnl": pnl,
            "balance": balance,
            "passed": passed,
            "info": info,
        })

        print(f"    Stage {stage+1} [{month_label}]: PnL=${pnl:+,.0f} → Balance=${balance:,.0f} [{status}] ({info})")

        if not passed:
            return False, results

    return True, results


def main():
    random.seed(42)
    n_tests = int(sys.argv[1]) if len(sys.argv) > 1 else 5

    # Load RL model
    v5_path = DATA_DIR / "rl_model_v5"
    model = None
    try:
        model = PPO.load(str(v5_path))
        print(f"Loaded RL v5 model: {v5_path}")
    except Exception as e:
        print(f"Warning: Could not load v5 model: {e}")

    # Generate test periods
    test_starts = []
    used = set()
    for _ in range(n_tests * 3):  # oversample to get unique periods
        dt = pick_3month_start()
        key = f"{dt.year}-{dt.month:02d}"
        if key not in used:
            used.add(key)
            test_starts.append(dt)
        if len(test_starts) >= n_tests:
            break

    # Run tests — Track A only (v5 model is 29-dim, env is now 33-dim; needs retrain)
    tracks = ["A"]

    for track in tracks:
        print(f"\n{'='*70}")
        print(f"STAGED BACKTEST: Track {track} ({'Rule-based + Full Triggers' if track == 'A' else 'RL v5 (33-dim)'})")
        print(f"{'='*70}")

        pass_count = 0
        total = len(test_starts)

        for i, start_dt in enumerate(test_starts):
            period = f"{start_dt.year}-{start_dt.month:02d} ~ +3m"
            print(f"\n  Test {i+1}/{total}: {period}")
            passed, results = run_staged_test(
                start_dt, track,
                model=model if track == "B" else None,
            )
            if passed:
                pass_count += 1
                total_pnl = sum(r["pnl"] for r in results)
                print(f"    → ALL 3 STAGES PASSED (total PnL: ${total_pnl:+,.0f})")
            else:
                fail_stage = results[-1]["stage"]
                print(f"    → FAILED at Stage {fail_stage}")

        print(f"\n{'─'*70}")
        print(f"  Track {track} RESULT: {pass_count}/{total} tests passed all 3 stages")
        print(f"{'─'*70}")


if __name__ == "__main__":
    main()
