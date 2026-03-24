"""Compare Track A (rule-based optimizer) vs Track B (RL v2) on out-of-sample data.

Usage: PYTHONPATH=src py -3 scripts/compare_tracks.py 2024-04-01 2024-05-31
"""
from __future__ import annotations
import sqlite3, sys
from pathlib import Path
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from stable_baselines3 import PPO
from trading_value.adapters.backtest import BacktestConfig, BacktestEngine
from trading_value.adapters.rl_env import TradingEnv
from trading_value.core.models import Timeframe

DB = str(Path(__file__).resolve().parent.parent / "data" / "cache.sqlite")


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
    df30 = (
        df15.set_index("timestamp")
        .resample("30min")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
        .dropna()
        .reset_index()
    )
    data = {Timeframe.M30: df30, Timeframe.H1: load_tf("1h"), Timeframe.H4: load_tf("4h")}
    conn.close()
    return data, df30


def run_track_a(data, df30):
    """Track A: rule-based backtest with optimized params."""
    config = BacktestConfig(
        symbols=["ETHUSDT"],
        initial_balance=10000.0,
        commission_rate=0.0004,
        primary_timeframe=Timeframe.M30,
        # Optimized params from Phase 5
        min_rr=2.28,
        risk_pct=0.001,
        cooldown_normal_bars=1,
        cooldown_stop_bars=8,
        max_hold_bars=73,
        zone_width_pct=0.0028,
        zone_width_atr_factor=0.237,
    )
    engine = BacktestEngine(config)
    # Need dict[str, dict[Timeframe, DataFrame]]
    bt_data = {"ETHUSDT": data}
    result = engine.run(bt_data)
    balances = []
    bal = 10000.0
    # Reconstruct balance curve from trades
    bar_count = len(df30) - 100
    if result.trades:
        # Simple: use final balance
        bal = result.final_balance
    return result, bal


def run_track_b(data, df30):
    """Track B: RL v2 agent."""
    model = PPO.load(str(Path(__file__).resolve().parent.parent / "data" / "rl_model_v4"))
    env = TradingEnv(
        data=data, symbol="ETHUSDT", initial_balance=10000.0,
        commission_rate=0.0004, episode_bars=len(df30) - 100, random_start=False,
    )
    obs, _ = env.reset()
    balances = []
    positions = []
    done = False
    while not done:
        action, _ = model.predict(obs, deterministic=True)
        obs, _, term, trunc, _ = env.step(action)
        balances.append(env._balance)
        positions.append(env._position)
        done = term or trunc
    return balances, positions


def main():
    start = sys.argv[1] if len(sys.argv) > 1 else "2024-04-01"
    end = sys.argv[2] if len(sys.argv) > 2 else "2024-05-31"

    print(f"Loading data: {start} ~ {end}")
    data, df30 = load_data(start, end)
    print(f"  30m bars: {len(df30)}")

    closes = df30["close"].values
    price_start = closes[100]
    price_end = closes[-1]
    bh_return = (price_end / price_start - 1) * 100

    # Track A
    print("\nRunning Track A (rule-based)...")
    a_result, a_final = run_track_a(data, df30)
    a_pnl = a_result.total_pnl
    a_trades = a_result.total_trades

    # Track B
    print("Running Track B (RL v2)...")
    b_bal, b_pos = run_track_b(data, df30)
    b_pnl = b_bal[-1] - 10000
    b_changes = sum(1 for i in range(1, len(b_pos)) if b_pos[i] != b_pos[i - 1])

    # Buy & Hold
    n = len(b_bal)
    bh_bal = [10000 * closes[100 + i] / closes[100] for i in range(n)]

    # Max drawdown
    def max_dd(bals):
        peak = bals[0]
        dd = 0
        for b in bals:
            if b > peak: peak = b
            if peak - b > dd: dd = peak - b
        return dd

    b_dd = max_dd(b_bal)

    print(f"\n{'=' * 60}")
    print(f"  2nd OOS TEST: {start} ~ {end}")
    print(f"{'=' * 60}")
    print(f"  ETH: ${price_start:,.0f} -> ${price_end:,.0f} ({bh_return:+.1f}%)")
    print(f"")
    print(f"  {'':20s} {'Track A':>12s} {'Track B (RL)':>12s} {'Buy&Hold':>12s}")
    print(f"  {'':20s} {'----------':>12s} {'----------':>12s} {'----------':>12s}")
    print(f"  {'PnL':20s} {'$' + f'{a_pnl:+,.0f}':>12s} {'$' + f'{b_pnl:+,.0f}':>12s} {'$' + f'{bh_return / 100 * 10000:+,.0f}':>12s}")
    print(f"  {'Return':20s} {a_pnl / 100:>+11.1f}% {b_pnl / 100:>+11.1f}% {bh_return:>+11.1f}%")
    print(f"  {'Trades':20s} {a_trades:>12d} {b_changes:>12d} {'0':>12s}")
    print(f"  {'Max DD':20s} {'$' + f'{a_result.max_drawdown:,.0f}':>12s} {'$' + f'{b_dd:,.0f}':>12s} {'--':>12s}")
    print(f"  {'Win Rate':20s} {a_result.win_rate:>11.1f}% {'--':>12s} {'--':>12s}")
    print(f"{'=' * 60}")

    winner = "Track A" if a_pnl > b_pnl else "Track B" if b_pnl > a_pnl else "Tie"
    vs_bh = "Track A" if a_pnl > bh_return / 100 * 10000 else "Track B" if b_pnl > bh_return / 100 * 10000 else "B&H"
    print(f"  Winner: {winner}")
    print(f"  vs B&H: {vs_bh}")

    # Chart
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(b_bal, label=f"Track B RL (${b_pnl:+,.0f})", color="green", linewidth=2)
    ax.plot(bh_bal[:n], label=f"Buy&Hold (${bh_return / 100 * 10000:+,.0f})", color="blue", alpha=0.7)
    ax.axhline(10000, color="gray", linestyle="--", alpha=0.5)
    # Track A: single point
    if a_trades > 0:
        ax.axhline(a_final, color="orange", linestyle=":", alpha=0.8, label=f"Track A final (${a_pnl:+,.0f})")
    else:
        ax.axhline(10000, color="orange", linestyle=":", alpha=0.8, label=f"Track A (0 trades)")
    ax.set_title(f"Track A vs Track B vs B&H: {start} ~ {end}", fontsize=14)
    ax.set_ylabel("Balance ($)")
    ax.set_xlabel("30m Bars")
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    out = Path(__file__).resolve().parent.parent / "data" / "charts" / f"compare_{start[:7]}.png"
    fig.savefig(out, dpi=150)
    print(f"\n  Chart: {out}")


if __name__ == "__main__":
    main()
