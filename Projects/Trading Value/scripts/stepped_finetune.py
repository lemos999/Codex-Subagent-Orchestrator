"""Phase 2: Stepped fine-tuning (500K x 4 rounds, market regime-based).

Base: rl_model_c_v2_200k_validation (Phase 1 validated)
Each round uses a different market regime segment.
Checkpoint + evaluation after each round.

Rounds:
  1. Bull market (2020-10 ~ 2021-04, ETH $300 -> $2500)
  2. Bear market (2022-01 ~ 2022-07, ETH $3500 -> $1000)
  3. Sideways (2023-03 ~ 2023-09, ETH $1600 ~ $2000)
  4. High volatility (2021-05 ~ 2021-11, ETH $4000 -> $1700 -> $4800)

Usage: cd "Projects/Trading Value" && PYTHONPATH=src py -3 scripts/stepped_finetune.py
"""
from __future__ import annotations
import sqlite3, sys, json, time, os
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

ROUNDS = [
    {"name": "bull",       "train": ("2020-10-01", "2021-04-30"), "desc": "Bull (ETH $300->$2500)"},
    {"name": "bear",       "train": ("2022-01-01", "2022-07-31"), "desc": "Bear (ETH $3500->$1000)"},
    {"name": "sideways",   "train": ("2023-03-01", "2023-09-30"), "desc": "Sideways (ETH $1600~$2000)"},
    {"name": "volatile",   "train": ("2021-05-01", "2021-11-30"), "desc": "Volatile (ETH swing $1700~$4800)"},
]

TEST_PERIODS = [
    ("2024-07-01", "2024-09-30", "2024 Q3"),
    ("2024-10-01", "2024-12-31", "2024 Q4"),
    ("2025-01-01", "2025-03-20", "2025 Q1"),
]

STEPS_PER_ROUND = 500_000
MIN_ENTRIES = 15


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


def load_15m_data(start, end):
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query(
        "SELECT datetime as timestamp, open, high, low, close, volume "
        "FROM ohlcv WHERE symbol='ETHUSDT' AND timeframe='15m' "
        "AND datetime >= ? AND datetime <= ? ORDER BY timestamp",
        conn, params=(start, end),
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    conn.close()
    return df


def augment_and_resample(df_15m, noise_pct=0.003, vol_jitter=0.15):
    df = df_15m.copy()
    n = len(df)
    noise = 1.0 + np.random.normal(0, noise_pct, n)
    for col in ["open", "high", "low", "close"]:
        df[col] = df[col] * noise
    df["high"] = df[["high", "open", "close"]].max(axis=1)
    df["low"] = df[["low", "open", "close"]].min(axis=1)
    vol_noise = 1.0 + np.random.normal(0, vol_jitter, n)
    df["volume"] = (df["volume"] * vol_noise).clip(lower=0)

    def resample_tf(rule):
        return (
            df.set_index("timestamp")
            .resample(rule)
            .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
            .dropna()
            .reset_index()
        )
    return {Timeframe.M30: resample_tf("30min"), Timeframe.H1: resample_tf("1h"), Timeframe.H4: resample_tf("4h")}


def evaluate(model, test_cache):
    pnls = []; entries = []; hold_pcts = []
    for data, df30 in test_cache:
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
            obs, _, t, tr, info = env.step(a)
            positions.append(env._position)
            actions.append(int(a))
            done = t or tr
        pnl = env._balance - 10000
        entry_count = sum(1 for i in range(1, len(positions))
                         if positions[i] != 0 and positions[i-1] == 0)
        hold_count = sum(1 for a in actions if a == 0)
        hold_pct = hold_count / len(actions) * 100 if actions else 100.0
        pnls.append(pnl)
        entries.append(entry_count)
        hold_pcts.append(hold_pct)
    return pnls, entries, hold_pcts


def make_envs(df_15m):
    """2 envs: 1 clean + 1 augmented."""
    def make_clean():
        data = augment_and_resample(df_15m, noise_pct=0.0, vol_jitter=0.0)
        env = TradingEnvC(
            data=data, symbol="ETHUSDT", initial_balance=10000.0,
            commission_rate=0.0002, episode_bars=min(1440, len(data[Timeframe.M30]) - 100),
            random_start=True, sharpe_window=48,
        )
        env.reset(seed=0)
        return env

    def make_aug():
        data = augment_and_resample(df_15m, noise_pct=0.003, vol_jitter=0.15)
        env = TradingEnvC(
            data=data, symbol="ETHUSDT", initial_balance=10000.0,
            commission_rate=0.0002, episode_bars=min(1440, len(data[Timeframe.M30]) - 100),
            random_start=True, sharpe_window=48,
        )
        env.reset(seed=1)
        return env

    return DummyVecEnv([make_clean, make_aug])


def main():
    print("=" * 60)
    print("PHASE 2: STEPPED FINE-TUNING (500K x 4 rounds)")
    print("=" * 60)

    # Pre-cache test data
    print("\nPre-caching test data...")
    test_cache = []
    for s, e, _ in TEST_PERIODS:
        data, df30 = load_data(s, e)
        test_cache.append((data, df30))

    # Evaluate Phase 1 baseline
    print("Evaluating Phase 1 baseline (v2_200k)...")
    base_model = RecurrentPPO.load(str(DATA_DIR / "rl_model_c_v2_200k_validation"))
    base_pnls, base_entries, base_hold = evaluate(base_model, test_cache)
    base_avg_pnl = np.mean(base_pnls)
    base_avg_entries = np.mean(base_entries)
    print(f"  Baseline: avg=${base_avg_pnl:+,.0f}, entries={base_avg_entries:.0f}")
    del base_model

    # Track results
    all_results = []
    best_avg_pnl = base_avg_pnl
    best_tag = "v2_200k_validation"
    current_model_path = str(DATA_DIR / "rl_model_c_v2_200k_validation")

    labels = [l for _, _, l in TEST_PERIODS]

    for round_idx, rnd in enumerate(ROUNDS, 1):
        print(f"\n{'='*60}")
        print(f"ROUND {round_idx}/4: {rnd['desc']}")
        print(f"  Training period: {rnd['train'][0]} ~ {rnd['train'][1]}")
        print(f"{'='*60}")

        # Load training data for this regime
        df_15m = load_15m_data(rnd["train"][0], rnd["train"][1])
        print(f"  15m bars: {len(df_15m):,}")

        if len(df_15m) < 500:
            print(f"  SKIP: insufficient data ({len(df_15m)} bars)")
            continue

        # Create envs
        vec_env = make_envs(df_15m)

        # Load current best model
        model = RecurrentPPO.load(current_model_path, env=vec_env)
        model.learning_rate = 3e-5
        model.ent_coef = 0.012
        model.n_epochs = 4
        model.target_kl = 0.015
        model.clip_range = lambda _: 0.1

        # Decay learning rate per round
        lr = 3e-5 * (0.8 ** (round_idx - 1))
        model.learning_rate = lr
        print(f"  LR: {lr:.1e} (decayed)")

        # Train
        start = time.time()
        model.learn(total_timesteps=STEPS_PER_ROUND, reset_num_timesteps=False)
        elapsed = time.time() - start
        print(f"  Training done in {elapsed:.0f}s ({elapsed/60:.1f}min)")

        # Save checkpoint
        tag = f"v2_stepped_r{round_idx}_{rnd['name']}"
        save_path = DATA_DIR / f"rl_model_c_{tag}"
        model.save(str(save_path))
        print(f"  Saved: rl_model_c_{tag}")

        # Evaluate
        pnls, entries, hold_pcts = evaluate(model, test_cache)
        avg_pnl = np.mean(pnls)
        avg_entries = np.mean(entries)
        avg_hold = np.mean(hold_pcts)
        sharpe = avg_pnl / max(np.std(pnls), 1.0)

        print(f"\n  Results after round {round_idx}:")
        for l, p, e, h in zip(labels, pnls, entries, hold_pcts):
            print(f"    [{l}] PnL=${p:+,.0f}  entries={e}  HOLD%={h:.1f}%")
        print(f"    Avg: PnL=${avg_pnl:+,.0f}  entries={avg_entries:.0f}  "
              f"HOLD%={avg_hold:.1f}%  Sharpe={sharpe:.2f}")

        result = {
            "round": round_idx,
            "regime": rnd["name"],
            "desc": rnd["desc"],
            "avg_pnl": float(avg_pnl),
            "avg_entries": float(avg_entries),
            "avg_hold_pct": float(avg_hold),
            "sharpe": float(sharpe),
            "pnls": [float(p) for p in pnls],
            "entries": [int(e) for e in entries],
            "elapsed_sec": elapsed,
            "lr": lr,
        }
        all_results.append(result)

        # Validation gate
        if avg_entries < MIN_ENTRIES:
            print(f"\n  WARNING: entries={avg_entries:.0f} < {MIN_ENTRIES}. HOLD convergence risk!")
            print(f"  Rolling back to previous best: {best_tag}")
            current_model_path = str(DATA_DIR / f"rl_model_c_{best_tag}")
            continue

        # Track best
        if avg_pnl > best_avg_pnl:
            best_avg_pnl = avg_pnl
            best_tag = tag
            print(f"  >> New best! tag={tag}, avg=${avg_pnl:+,.0f}")
            current_model_path = str(save_path)
        else:
            print(f"  >> No improvement (best remains {best_tag} at ${best_avg_pnl:+,.0f})")
            # Still use latest model for next round (curriculum learning)
            current_model_path = str(save_path)

        del model

    # --- Final Summary ---
    print(f"\n{'='*60}")
    print("FINAL SUMMARY")
    print(f"{'='*60}")
    print(f"\n  Phase 1 baseline (v2_200k): avg=${base_avg_pnl:+,.0f}, entries={base_avg_entries:.0f}")
    for r in all_results:
        marker = " << BEST" if r["regime"] == best_tag.split("_")[-1] else ""
        print(f"  Round {r['round']} ({r['regime']:>8s}): avg=${r['avg_pnl']:+,.0f}, "
              f"entries={r['avg_entries']:.0f}, Sharpe={r['sharpe']:.2f}{marker}")

    print(f"\n  Best model: rl_model_c_{best_tag}")
    print(f"  Best avg PnL: ${best_avg_pnl:+,.0f}")

    # Save results
    summary = {
        "base": {"avg_pnl": float(base_avg_pnl), "avg_entries": float(base_avg_entries)},
        "rounds": all_results,
        "best_tag": best_tag,
        "best_avg_pnl": float(best_avg_pnl),
    }
    result_path = DATA_DIR / "stepped_finetune_results.json"
    with open(result_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n  Results saved: {result_path}")
    print("\nDone.")


if __name__ == "__main__":
    main()
