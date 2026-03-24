"""Compare all RL models: entry count, commission, PnL, score efficiency.

Evaluates every saved model on 2024 test data and produces a summary table.
"""
from __future__ import annotations
import sys, sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from stable_baselines3 import PPO
from trading_value.adapters.rl_env import TradingEnv
from trading_value.core.models import Timeframe

DB = str(Path(__file__).resolve().parent.parent / "data" / "cache.sqlite")
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


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


def evaluate_model(model_path, data, df30, commission_rate=0.0004):
    """Run one model on test data, return detailed stats."""
    model = PPO.load(str(model_path))
    env = TradingEnv(
        data=data, symbol="ETHUSDT", initial_balance=10000.0,
        commission_rate=commission_rate,
        episode_bars=len(df30) - 100,
        random_start=False,
    )
    obs, _ = env.reset()
    positions = []
    actions_taken = []
    trade_pnls = []  # PnL per closed trade
    entry_count = 0
    prev_position = 0
    balance_history = [10000.0]

    done = False
    while not done:
        action, _ = model.predict(obs, deterministic=True)
        prev_pos = env._position
        prev_bal = env._balance
        obs, reward, term, trunc, info = env.step(action)
        positions.append(env._position)
        actions_taken.append(int(action))
        balance_history.append(env._balance)

        # Detect new entry
        if prev_pos == 0 and env._position != 0:
            entry_count += 1
        # Detect trade close
        if prev_pos != 0 and env._position == 0:
            # Balance change = trade PnL (approximate)
            trade_pnls.append(env._balance - prev_bal)

        done = term or trunc

    final_balance = env._balance
    pnl = final_balance - 10000.0
    total_commission = env._total_commission
    total_bars = len(positions)

    # Position change count
    pos_changes = sum(1 for i in range(1, len(positions)) if positions[i] != positions[i-1])

    # Win rate
    wins = sum(1 for p in trade_pnls if p > 0)
    losses = sum(1 for p in trade_pnls if p <= 0)
    win_rate = wins / max(wins + losses, 1) * 100

    # Max drawdown
    peak = 10000.0
    max_dd = 0.0
    for b in balance_history:
        if b > peak:
            peak = b
        dd = (peak - b) / peak
        if dd > max_dd:
            max_dd = dd

    # Average bars per trade
    bars_per_trade = total_bars / max(entry_count, 1)

    # Commission as % of initial balance
    comm_pct = total_commission / 10000.0 * 100

    # Net PnL after commission (already included in balance, but show ratio)
    pnl_to_comm_ratio = pnl / max(total_commission, 0.01)

    return {
        "pnl": pnl,
        "return_pct": pnl / 100,
        "entries": entry_count,
        "pos_changes": pos_changes,
        "total_commission": total_commission,
        "comm_pct": comm_pct,
        "win_rate": win_rate,
        "wins": wins,
        "losses": losses,
        "max_dd_pct": max_dd * 100,
        "bars_per_trade": bars_per_trade,
        "pnl_comm_ratio": pnl_to_comm_ratio,
        "avg_trade_pnl": np.mean(trade_pnls) if trade_pnls else 0,
        "total_bars": total_bars,
    }


def main():
    # Test periods
    periods = [
        ("2023-01-01", "2023-11-11", "2023"),
        ("2024-04-01", "2024-05-31", "2024 Apr-May"),
    ]

    # Find all models
    model_files = sorted(DATA_DIR.glob("rl_model*.zip"))
    model_names = [f.stem for f in model_files]
    print(f"Found {len(model_names)} models: {', '.join(model_names)}")

    for start, end, period_label in periods:
        print(f"\n{'='*90}")
        print(f"TEST PERIOD: {period_label} ({start} ~ {end})")
        print(f"{'='*90}")

        data, df30 = load_data(start, end)
        print(f"  30m bars: {len(df30)}")

        results = []
        for model_path in model_files:
            name = model_path.stem
            print(f"\n  Evaluating {name}...")
            try:
                stats = evaluate_model(model_path, data, df30, commission_rate=0.0004)
                stats["model"] = name
                results.append(stats)
                print(f"    PnL: ${stats['pnl']:+,.0f} | Entries: {stats['entries']} | "
                      f"Commission: ${stats['total_commission']:,.0f} ({stats['comm_pct']:.1f}%) | "
                      f"Win: {stats['win_rate']:.0f}%")
            except Exception as e:
                print(f"    ERROR: {e}")

        if not results:
            continue

        # Summary table
        print(f"\n{'='*90}")
        print(f"SUMMARY: {period_label} @ 0.04% taker commission")
        print(f"{'='*90}")
        header = (f"{'Model':<20s} {'PnL':>9s} {'Return':>8s} {'Entries':>8s} "
                  f"{'Bars/Tr':>8s} {'Commiss':>9s} {'Comm%':>6s} "
                  f"{'WinRate':>8s} {'W/L':>7s} {'MaxDD':>7s} {'PnL/Com':>8s}")
        print(header)
        print("-" * len(header))

        for r in sorted(results, key=lambda x: x["pnl"], reverse=True):
            print(f"{r['model']:<20s} ${r['pnl']:>+8,.0f} {r['return_pct']:>+7.1f}% "
                  f"{r['entries']:>8d} {r['bars_per_trade']:>8.1f} "
                  f"${r['total_commission']:>8,.0f} {r['comm_pct']:>5.1f}% "
                  f"{r['win_rate']:>7.1f}% {r['wins']:>3d}/{r['losses']:<3d} "
                  f"{r['max_dd_pct']:>6.1f}% {r['pnl_comm_ratio']:>+7.1f}")

        # Efficiency analysis
        print(f"\n--- Efficiency Analysis ---")
        best_pnl = max(results, key=lambda x: x["pnl"])
        best_ratio = max(results, key=lambda x: x["pnl_comm_ratio"])
        fewest_entries = min(results, key=lambda x: x["entries"])
        best_winrate = max(results, key=lambda x: x["win_rate"])

        print(f"  Best PnL:           {best_pnl['model']} (${best_pnl['pnl']:+,.0f})")
        print(f"  Best PnL/Comm:      {best_ratio['model']} (ratio={best_ratio['pnl_comm_ratio']:+.1f})")
        print(f"  Fewest entries:     {fewest_entries['model']} ({fewest_entries['entries']} entries)")
        print(f"  Best win rate:      {best_winrate['model']} ({best_winrate['win_rate']:.1f}%)")

        # Find sweet spot: highest PnL among models with entries < median
        median_entries = np.median([r["entries"] for r in results])
        low_freq = [r for r in results if r["entries"] <= median_entries]
        if low_freq:
            sweet_spot = max(low_freq, key=lambda x: x["pnl"])
            print(f"\n  SWEET SPOT (entries <= {median_entries:.0f}, best PnL):")
            print(f"    {sweet_spot['model']}: PnL=${sweet_spot['pnl']:+,.0f}, "
                  f"Entries={sweet_spot['entries']}, "
                  f"Bars/Trade={sweet_spot['bars_per_trade']:.1f}, "
                  f"Commission=${sweet_spot['total_commission']:,.0f}")


if __name__ == "__main__":
    main()
