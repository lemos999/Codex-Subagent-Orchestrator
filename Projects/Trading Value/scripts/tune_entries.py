"""Tune R2 Bear's entry frequency by fine-tuning with small position_change_penalty.

Tests penalty=0.05, 0.10, 0.15 at 100K steps each.
Goal: reduce entries from ~330/Q to Castle-like ~40-80/Q without losing PnL.

Usage: cd "Projects/Trading Value" && PYTHONPATH=src py -3 scripts/tune_entries.py
"""
from __future__ import annotations
import sqlite3, sys, time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from sb3_contrib import RecurrentPPO
from stable_baselines3.common.vec_env import DummyVecEnv
from trading_value.adapters.rl_env_c import TradingEnvC
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
        env = TradingEnvC(
            data=data, symbol="ETHUSDT", initial_balance=10000.0,
            commission_rate=0.0004, episode_bars=len(df30) - 50,
            random_start=False, sharpe_window=48,
        )
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
    # Test periods (same 20Q as compare_all)
    test_periods = [
        ("2024-07-01", "2024-09-30", "24Q3"),
        ("2024-10-01", "2024-12-31", "24Q4"),
        ("2025-01-01", "2025-03-20", "25Q1"),
    ]
    test_cache = []
    for s, e, l in test_periods:
        data, df30 = load_data(s, e)
        test_cache.append((data, df30, l))

    # Training data
    train_data, train_df30 = load_data("2019-11-27", "2024-06-30")

    # Evaluate R2 Bear baseline
    print("Evaluating R2 Bear baseline...")
    base = RecurrentPPO.load(str(DATA_DIR / "rl_model_c_v2_stepped_r2_bear"))
    b_pnls, b_ents, b_hold = evaluate(base, test_cache)
    del base
    print(f"  Baseline: avg=${np.mean(b_pnls):+,.0f}, entries={np.mean(b_ents):.0f}")

    penalties = [0.20, 0.25, 0.30]
    results = []

    for penalty in penalties:
        print(f"\n{'='*60}")
        print(f"Fine-tuning with position_change_penalty={penalty}")
        print(f"{'='*60}")

        vec_env = DummyVecEnv([lambda p=penalty: TradingEnvC(
            data=train_data, symbol="ETHUSDT", initial_balance=10000.0,
            commission_rate=0.0002, episode_bars=1440, random_start=True,
            sharpe_window=48, position_change_penalty=p,
        )])

        model = RecurrentPPO.load(str(DATA_DIR / "rl_model_c_v2_stepped_r2_bear"), env=vec_env)
        model.learning_rate = 2e-5
        model.ent_coef = 0.012
        model.n_epochs = 4
        model.target_kl = 0.015
        model.clip_range = lambda _: 0.1

        start = time.time()
        model.learn(total_timesteps=300_000, reset_num_timesteps=False)
        elapsed = time.time() - start
        print(f"  Done in {elapsed:.0f}s")

        tag = f"v2_r2_p{int(penalty*100):02d}"
        model.save(str(DATA_DIR / f"rl_model_c_{tag}"))

        pnls, ents, holds = evaluate(model, test_cache)
        avg_pnl = np.mean(pnls)
        avg_ent = np.mean(ents)
        avg_hold = np.mean(holds)

        labels = ["24Q3", "24Q4", "25Q1"]
        for l, p, e in zip(labels, pnls, ents):
            print(f"  [{l}] PnL=${p:+,.0f}  entries={e}")
        print(f"  Avg: PnL=${avg_pnl:+,.0f}  entries={avg_ent:.0f}  HOLD%={avg_hold:.1f}%")

        results.append({
            "penalty": penalty,
            "tag": tag,
            "avg_pnl": avg_pnl,
            "avg_entries": avg_ent,
            "avg_hold": avg_hold,
            "pnls": pnls,
            "entries": ents,
        })
        del model

    # Summary
    print(f"\n{'='*60}")
    print("ENTRY TUNING SUMMARY")
    print(f"{'='*60}")
    print(f"{'Penalty':>8s} {'Avg PnL':>12s} {'Entries':>8s} {'HOLD%':>7s} {'PnL/Ent':>9s}")
    print("-" * 50)
    print(f"{'0.00':>8s} ${np.mean(b_pnls):>+10,.0f} {np.mean(b_ents):>7.0f} {np.mean(b_hold):>6.1f}% ${np.mean(b_pnls)/np.mean(b_ents):>7,.0f}")
    for r in results:
        pe = r["avg_pnl"] / r["avg_entries"] if r["avg_entries"] > 0 else 0
        print(f"{r['penalty']:>8.2f} ${r['avg_pnl']:>+10,.0f} {r['avg_entries']:>7.0f} {r['avg_hold']:>6.1f}% ${pe:>7,.0f}")

    print("\nDone.")


if __name__ == "__main__":
    main()
