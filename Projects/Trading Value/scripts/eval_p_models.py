"""Evaluate v2 R2 p20/p25/p30 on 20 quarters."""
from __future__ import annotations
import sqlite3, sys, numpy as np, pandas as pd
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from sb3_contrib import RecurrentPPO
from trading_value.adapters.rl_env_c import TradingEnvC
from trading_value.core.models import Timeframe

DB = str(Path(__file__).resolve().parent.parent / "data" / "cache.sqlite")
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

TEST_PERIODS = [
    ("2020-01-01", "2020-03-31", "20Q1"), ("2020-04-01", "2020-06-30", "20Q2"),
    ("2020-07-01", "2020-09-30", "20Q3"), ("2020-10-01", "2020-12-31", "20Q4"),
    ("2021-01-01", "2021-03-31", "21Q1"), ("2021-04-01", "2021-06-30", "21Q2"),
    ("2021-07-01", "2021-09-30", "21Q3"), ("2021-10-01", "2021-12-31", "21Q4"),
    ("2022-01-01", "2022-03-31", "22Q1"), ("2022-04-01", "2022-06-30", "22Q2"),
    ("2022-07-01", "2022-09-30", "22Q3"), ("2022-10-01", "2022-12-31", "22Q4"),
    ("2023-01-01", "2023-03-31", "23Q1"), ("2023-04-01", "2023-06-30", "23Q2"),
    ("2023-07-01", "2023-09-30", "23Q3"), ("2023-10-01", "2023-12-31", "23Q4"),
    ("2024-01-01", "2024-03-31", "24Q1"), ("2024-04-01", "2024-06-30", "24Q2"),
    ("2024-07-01", "2024-09-30", "24Q3"), ("2024-10-01", "2024-12-31", "24Q4"),
]

def load_data(start, end):
    conn = sqlite3.connect(DB)
    def load_tf(tf_str):
        df = pd.read_sql_query(
            "SELECT datetime as timestamp, open, high, low, close, volume "
            "FROM ohlcv WHERE symbol='ETHUSDT' AND timeframe=? "
            "AND datetime >= ? AND datetime <= ? ORDER BY timestamp",
            conn, params=(tf_str, start, end))
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        return df
    df15 = load_tf("15m")
    df30 = df15.set_index("timestamp").resample("30min").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna().reset_index()
    data = {Timeframe.M30: df30, Timeframe.H1: load_tf("1h"), Timeframe.H4: load_tf("4h")}
    conn.close()
    return data, df30

def evaluate(model, test_cache):
    pnls = []; entries = []; hold_pcts = []
    for data, df30, label in test_cache:
        env = TradingEnvC(data=data, symbol="ETHUSDT", initial_balance=10000.0,
            commission_rate=0.0004, episode_bars=len(df30) - 50,
            random_start=False, sharpe_window=48)
        obs, _ = env.reset()
        done = False; ls = None; es = np.ones((1,), dtype=bool)
        positions = []; actions = []
        while not done:
            a, ls = model.predict(obs, state=ls, episode_start=es, deterministic=True)
            es = np.zeros((1,), dtype=bool)
            obs, _, t, tr, _ = env.step(a)
            positions.append(env._position); actions.append(int(a))
            done = t or tr
        pnl = env._balance - 10000
        ent = sum(1 for i in range(1, len(positions)) if positions[i] != 0 and positions[i-1] == 0)
        hpct = sum(1 for a in actions if a == 0) / len(actions) * 100 if actions else 100
        pnls.append(pnl); entries.append(ent); hold_pcts.append(hpct)
    return pnls, entries, hold_pcts

def main():
    test_cache = []
    for s, e, l in TEST_PERIODS:
        data, df30 = load_data(s, e)
        test_cache.append((data, df30, l))

    labels = [l for _, _, l in TEST_PERIODS]
    models = [
        ("v2 R2 p20", "rl_model_c_v2_r2_p20"),
        ("v2 R2 p25", "rl_model_c_v2_r2_p25"),
        ("v2 R2 p30", "rl_model_c_v2_r2_p30"),
    ]

    results = []
    for name, fname in models:
        print(f"Evaluating {name}...")
        m = RecurrentPPO.load(str(DATA_DIR / fname))
        p, e, h = evaluate(m, test_cache)
        results.append((name, p, e, h))
        del m

    # Summary
    print()
    print("=" * 80)
    print(f"v2 R2 PENALTY VARIANTS - 20 QUARTERS (2020Q1 ~ 2024Q4)")
    print("=" * 80)
    print()
    print(f"{'Model':<16s} {'Avg PnL':>12s} {'Entries':>8s} {'HOLD%':>7s} {'Sharpe':>8s} {'PnL/Ent':>9s} {'Win':>5s} {'Loss':>5s}")
    print("-" * 75)
    for name, pnls, ents, holds in results:
        ap = np.mean(pnls); ae = np.mean(ents); ah = np.mean(holds)
        sh = ap / max(np.std(pnls), 1.0)
        pe = ap / ae if ae > 0 else 0
        wins = sum(1 for p in pnls if p > 0)
        losses = sum(1 for p in pnls if p <= 0)
        print(f"{name:<16s} ${ap:>+10,.0f} {ae:>7.0f} {ah:>6.1f}% {sh:>7.2f} ${pe:>7,.0f} {wins:>4d} {losses:>4d}")

    # IS vs OOS
    oos_start = 18
    print()
    print("IN-SAMPLE (18Q) vs OUT-OF-SAMPLE (2Q):")
    print("-" * 75)
    for name, pnls, ents, holds in results:
        is_pnls = pnls[:oos_start]; oos_pnls = pnls[oos_start:]
        is_avg = np.mean(is_pnls); oos_avg = np.mean(oos_pnls)
        is_wins = sum(1 for p in is_pnls if p > 0)
        oos_wins = sum(1 for p in oos_pnls if p > 0)
        is_ent = np.mean(ents[:oos_start]); oos_ent = np.mean(ents[oos_start:])
        print(f"  {name:<14s} IS: ${is_avg:>+10,.0f} ({is_wins}/18 win, {is_ent:.0f} ent)  "
              f"OOS: ${oos_avg:>+10,.0f} ({oos_wins}/2 win, {oos_ent:.0f} ent)")

    # PnL by quarter
    print()
    print("PnL BY QUARTER ($K):")
    print("-" * 80)
    hdr = f"{'Model':<14s}"
    for l in labels:
        hdr += f" {l:>6s}"
    print(hdr)
    print("-" * 80)
    for name, pnls, ents, holds in results:
        line = f"{name:<14s}"
        for p in pnls:
            line += f" {p/1000:>+6.0f}"
        print(line)

    # Entries by quarter
    print()
    print("ENTRIES BY QUARTER:")
    print("-" * 80)
    hdr = f"{'Model':<14s}"
    for l in labels:
        hdr += f" {l:>6s}"
    print(hdr)
    print("-" * 80)
    for name, pnls, ents, holds in results:
        line = f"{name:<14s}"
        for e in ents:
            line += f" {e:>6d}"
        print(line)

    print("\nDone.")

if __name__ == "__main__":
    main()
