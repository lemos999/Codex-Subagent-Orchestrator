"""Phase 1: 200K validation of reward v2 on Castle base.

Runs +200K steps with v2 reward structure (mark-to-market Sharpe,
no position_change_penalty) and checks pass/fail criteria from
3-engine discussion consensus:

  PASS criteria:
  - HOLD% change within ±20% of Castle baseline
  - avg reward >= 60% of Castle
  - Sharpe remains positive
  - No HOLD collapse (entries > 0 in all test periods)

Usage: cd "Projects/Trading Value" && PYTHONPATH=src py -3 scripts/validate_v2.py
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

# --- Castle baseline (from historical evaluation) ---
CASTLE_AVG_PNL = 5762.0
CASTLE_AVG_ENTRIES = 43.0


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

    df30 = resample_tf("30min")
    df1h = resample_tf("1h")
    df4h = resample_tf("4h")
    return {Timeframe.M30: df30, Timeframe.H1: df1h, Timeframe.H4: df4h}, df30


def evaluate(model, test_cache):
    """Evaluate model on cached test data. Returns (pnls, entries, hold_pcts)."""
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


def main():
    VALIDATION_STEPS = 200_000

    print("=" * 60)
    print("PHASE 1: 200K VALIDATION (v2 reward structure)")
    print("=" * 60)

    # --- Step 1: Evaluate Castle baseline first ---
    print("\n[1/4] Evaluating Castle baseline...")
    test_periods = [
        ("2024-07-01", "2024-09-30"),
        ("2024-10-01", "2024-12-31"),
        ("2025-01-01", "2025-03-20"),
    ]
    test_cache = []
    for s, e in test_periods:
        data, df30 = load_data(s, e)
        test_cache.append((data, df30))

    castle_model = RecurrentPPO.load(str(DATA_DIR / "rl_model_c_b_1350k"))
    castle_pnls, castle_entries, castle_hold_pcts = evaluate(castle_model, test_cache)

    castle_avg_pnl = np.mean(castle_pnls)
    castle_avg_entries = np.mean(castle_entries)
    castle_avg_hold_pct = np.mean(castle_hold_pcts)
    castle_sharpe = castle_avg_pnl / max(np.std(castle_pnls), 1.0)

    labels = ["2024 Q3", "2024 Q4", "2025 Q1"]
    print(f"\n  Castle baseline (v1 reward):")
    for l, p, e, h in zip(labels, castle_pnls, castle_entries, castle_hold_pcts):
        print(f"    [{l}] PnL=${p:+,.0f}  entries={e}  HOLD%={h:.1f}%")
    print(f"    Avg: PnL=${castle_avg_pnl:+,.0f}  entries={castle_avg_entries:.0f}  "
          f"HOLD%={castle_avg_hold_pct:.1f}%  Sharpe={castle_sharpe:.2f}")

    # --- Step 2: Train +200K with v2 ---
    print(f"\n[2/4] Loading 15m training data...")
    df_15m = load_15m_data("2019-11-27", "2024-06-30")
    print(f"  15m bars: {len(df_15m):,}")

    print(f"\n[3/4] Training +{VALIDATION_STEPS:,} steps with v2 reward...")

    # 2 envs (1 clean + 1 augmented) for faster validation
    def make_clean():
        data, _ = augment_and_resample(df_15m, noise_pct=0.0, vol_jitter=0.0)
        env = TradingEnvC(
            data=data, symbol="ETHUSDT", initial_balance=10000.0,
            commission_rate=0.0002, episode_bars=1440, random_start=True,
            sharpe_window=48,
        )
        env.reset(seed=0)
        return env

    def make_augmented():
        data, _ = augment_and_resample(df_15m, noise_pct=0.003, vol_jitter=0.15)
        env = TradingEnvC(
            data=data, symbol="ETHUSDT", initial_balance=10000.0,
            commission_rate=0.0002, episode_bars=1440, random_start=True,
            sharpe_window=48,
        )
        env.reset(seed=1)
        return env

    vec_env = DummyVecEnv([make_clean, make_augmented])

    model = RecurrentPPO.load(str(DATA_DIR / "rl_model_c_b_1350k"), env=vec_env)
    model.learning_rate = 3e-5
    model.ent_coef = 0.012
    model.n_epochs = 4
    model.target_kl = 0.015
    model.clip_range = lambda _: 0.1

    start = time.time()
    model.learn(total_timesteps=VALIDATION_STEPS, reset_num_timesteps=False)
    elapsed = time.time() - start
    print(f"  Training done in {elapsed:.0f}s ({elapsed/60:.1f}min)")

    # Save validation checkpoint
    model.save(str(DATA_DIR / "rl_model_c_v2_200k_validation"))
    print(f"  Saved: rl_model_c_v2_200k_validation")

    # --- Step 4: Evaluate and judge ---
    print(f"\n[4/4] Evaluating v2 model...")
    v2_pnls, v2_entries, v2_hold_pcts = evaluate(model, test_cache)

    v2_avg_pnl = np.mean(v2_pnls)
    v2_avg_entries = np.mean(v2_entries)
    v2_avg_hold_pct = np.mean(v2_hold_pcts)
    v2_sharpe = v2_avg_pnl / max(np.std(v2_pnls), 1.0)

    print(f"\n  v2 after +200K:")
    for l, p, e, h in zip(labels, v2_pnls, v2_entries, v2_hold_pcts):
        print(f"    [{l}] PnL=${p:+,.0f}  entries={e}  HOLD%={h:.1f}%")
    print(f"    Avg: PnL=${v2_avg_pnl:+,.0f}  entries={v2_avg_entries:.0f}  "
          f"HOLD%={v2_avg_hold_pct:.1f}%  Sharpe={v2_sharpe:.2f}")

    # --- Pass/Fail judgment ---
    print(f"\n{'='*60}")
    print("VALIDATION JUDGMENT")
    print(f"{'='*60}")

    hold_change = abs(v2_avg_hold_pct - castle_avg_hold_pct)
    reward_ratio = v2_avg_pnl / castle_avg_pnl if castle_avg_pnl != 0 else 0
    all_have_entries = all(e > 0 for e in v2_entries)

    criteria = {
        "HOLD% within ±20%": (hold_change <= 20.0, f"{hold_change:.1f}%"),
        "Reward >= 60% of Castle": (reward_ratio >= 0.6, f"{reward_ratio*100:.0f}%"),
        "Sharpe positive": (v2_sharpe > 0, f"{v2_sharpe:.2f}"),
        "No HOLD collapse": (all_have_entries, f"entries={v2_entries}"),
    }

    all_pass = True
    for name, (passed, detail) in criteria.items():
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
        print(f"  [{status}] {name}: {detail}")

    print(f"\n  {'='*40}")
    if all_pass:
        print(f"  OVERALL: PASS — v2 reward structure is safe")
        print(f"  NEXT: Proceed to Phase 2 (500K x 4 stepped fine-tuning)")
    else:
        print(f"  OVERALL: FAIL — v2 needs parameter adjustment")
        print(f"  NEXT: Review failed criteria, adjust v2 parameters, re-validate")
    print(f"  {'='*40}")

    # Save results
    results = {
        "castle": {
            "avg_pnl": float(castle_avg_pnl),
            "avg_entries": float(castle_avg_entries),
            "avg_hold_pct": float(castle_avg_hold_pct),
            "sharpe": float(castle_sharpe),
            "pnls": [float(p) for p in castle_pnls],
            "entries": [int(e) for e in castle_entries],
        },
        "v2_200k": {
            "avg_pnl": float(v2_avg_pnl),
            "avg_entries": float(v2_avg_entries),
            "avg_hold_pct": float(v2_avg_hold_pct),
            "sharpe": float(v2_sharpe),
            "pnls": [float(p) for p in v2_pnls],
            "entries": [int(e) for e in v2_entries],
        },
        "judgment": {
            "overall": "PASS" if all_pass else "FAIL",
            "criteria": {k: {"pass": v[0], "detail": v[1]} for k, v in criteria.items()},
        },
        "elapsed_sec": elapsed,
    }
    result_path = DATA_DIR / "validation_v2_results.json"
    with open(result_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Results saved: {result_path}")


if __name__ == "__main__":
    main()
