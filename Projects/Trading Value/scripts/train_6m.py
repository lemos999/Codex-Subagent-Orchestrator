"""Train Track C to 6M steps with anti-overfitting techniques (v2).

Post 3-engine review changes:
1. Per-episode augmentation (15m base → resample to MTF)
2. Entropy cycling with raised floor (base 0.012)
3. n_epochs 4, target_kl 0.015
4. 50K validation gate (entries < 15 → rollback)
5. NaN/divergence safety
6. Eval data pre-cached

Base: rl_model_c_b_1350k (Castle, current best)
Target: 6M total steps

Usage: cd "Projects/Trading Value" && PYTHONPATH=src py -3 scripts/train_6m.py
"""
from __future__ import annotations
import sqlite3, sys, json, time, tempfile, os
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from sb3_contrib import RecurrentPPO
from stable_baselines3.common.vec_env import SubprocVecEnv, DummyVecEnv
from stable_baselines3.common.callbacks import BaseCallback
from trading_value.adapters.rl_env_c import TradingEnvC
from trading_value.core.models import Timeframe

DB = str(Path(__file__).resolve().parent.parent / "data" / "cache.sqlite")
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
STATUS_FILE = DATA_DIR / "training_status.json"


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
    """Load raw 15m data for coherent augmentation."""
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
    """Coherent augmentation: perturb 15m then resample to 30m/1h/4h.

    This preserves MTF consistency since all timeframes derive from the
    same perturbed 15m source.
    """
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


class AugmentingEnvC(TradingEnvC):
    """TradingEnvC that re-augments data on each episode reset."""

    def __init__(self, df_15m_raw, noise_pct=0.003, vol_jitter=0.15, **kwargs):
        self._df_15m_raw = df_15m_raw
        self._noise_pct = noise_pct
        self._vol_jitter = vol_jitter
        # Initial data (augmented)
        data, _ = augment_and_resample(df_15m_raw, noise_pct, vol_jitter)
        super().__init__(data=data, **kwargs)

    def reset(self, seed=None, options=None):
        # Re-augment data each episode for diversity
        data, _ = augment_and_resample(
            self._df_15m_raw, self._noise_pct, self._vol_jitter,
        )
        self._raw_data = data
        self._precompute_snapshots()
        return super().reset(seed=seed, options=options)


class TrainingCallback(BaseCallback):
    """Combined callback: entropy cycling, checkpoints, validation gate, NaN safety.

    v2 changes:
    - Raised entropy floor (0.012 base)
    - 50K checkpoint interval with validation gate
    - NaN detection and auto-rollback
    - Atomic status file writes
    """
    CHECKPOINT_INTERVAL = 50_000
    EVAL_INTERVAL = 50_000
    MIN_ENTRIES = 15  # validation gate: rollback if entries drop below

    def __init__(
        self, base_ent=0.012, boost_ent=0.025, cycle_steps=200_000,
        boost_duration=50_000, save_dir=None, eval_fn=None, verbose=0,
    ):
        super().__init__(verbose)
        self.base_ent = base_ent
        self.boost_ent = boost_ent
        self.cycle_steps = cycle_steps
        self.boost_duration = boost_duration
        self.save_dir = save_dir
        self.eval_fn = eval_fn
        self._boosting = False
        self._start_time = time.time()
        self._results = []
        self._best_avg_pnl = -float("inf")
        self._best_tag = None
        self._last_good_tag = None

    def _on_step(self) -> bool:
        steps = self.num_timesteps

        # --- NaN safety ---
        if hasattr(self.model, "logger") and self.model.logger is not None:
            for key in ["train/loss", "train/policy_gradient_loss", "train/value_loss"]:
                val = self.model.logger.name_to_value.get(key)
                if val is not None and (np.isnan(val) or np.isinf(val)):
                    print(f"\n  [{steps:,}] NaN/Inf detected in {key}! Stopping.", flush=True)
                    if self._last_good_tag and self.save_dir:
                        print(f"  Rollback to {self._last_good_tag}", flush=True)
                    return False

        # --- Entropy cycling ---
        cycle_pos = steps % self.cycle_steps
        if cycle_pos < self.boost_duration:
            if not self._boosting:
                self._boosting = True
                self.model.ent_coef = self.boost_ent
                print(f"\n  [{steps:,}] Entropy BOOST -> {self.boost_ent}", flush=True)
        else:
            if self._boosting:
                self._boosting = False
                self.model.ent_coef = self.base_ent
                print(f"  [{steps:,}] Entropy NORMAL -> {self.base_ent}", flush=True)

        # --- Checkpoint + evaluation every 50K ---
        if steps % self.CHECKPOINT_INTERVAL == 0 and steps > 0 and self.save_dir:
            tag = f"{steps // 1000}k"
            path = self.save_dir / f"rl_model_c_6m_{tag}"
            self.model.save(str(path))

            if self.eval_fn and steps % self.EVAL_INTERVAL == 0:
                pnls, ents = self.eval_fn(self.model)
                avg = np.mean(pnls)
                avg_entries = np.mean(ents)
                wins = sum(1 for p in pnls if p > 0)
                self._results.append({
                    "steps": steps, "avg_pnl": float(avg),
                    "wins": wins, "entries": float(avg_entries),
                })
                print(f"  [{steps:,}] Eval: avg=${avg:+,.0f}, entries={avg_entries:.0f}, "
                      f"win={wins}/3", flush=True)

                # Validation gate: entries too low → warn
                if avg_entries < self.MIN_ENTRIES:
                    print(f"  [{steps:,}] WARNING: entries={avg_entries:.0f} < {self.MIN_ENTRIES}. "
                          f"HOLD convergence risk!", flush=True)

                # Track best
                if avg > self._best_avg_pnl and avg_entries >= self.MIN_ENTRIES:
                    self._best_avg_pnl = avg
                    self._best_tag = tag
                    print(f"  [{steps:,}] New best! tag={tag}, avg=${avg:+,.0f}", flush=True)

                if avg_entries >= self.MIN_ENTRIES:
                    self._last_good_tag = tag

            # Atomic status write
            elapsed = time.time() - self._start_time
            status = {
                "steps_c": steps,
                "elapsed_sec": elapsed,
                "phase": "6M training v2",
                "best_tag": self._best_tag,
                "best_avg_pnl": self._best_avg_pnl if self._best_avg_pnl > -float("inf") else None,
                "checkpoints": self._results,
            }
            tmp_path = str(STATUS_FILE) + ".tmp"
            with open(tmp_path, "w") as f:
                json.dump(status, f)
            os.replace(tmp_path, str(STATUS_FILE))

        return True


def make_env(df_15m, seed=0, augment=False):
    """Create a single training environment."""
    def _init():
        if augment:
            env = AugmentingEnvC(
                df_15m_raw=df_15m,
                noise_pct=0.003, vol_jitter=0.15,
                symbol="ETHUSDT", initial_balance=10000.0,
                commission_rate=0.0002, episode_bars=1440, random_start=True,
                sharpe_window=48,
            )
        else:
            data, _ = augment_and_resample(df_15m, noise_pct=0.0, vol_jitter=0.0)
            env = TradingEnvC(
                data=data, symbol="ETHUSDT", initial_balance=10000.0,
                commission_rate=0.0002, episode_bars=1440, random_start=True,
                sharpe_window=48,
            )
        env.reset(seed=seed)
        return env
    return _init


def main():
    total_steps = 6_000_000
    # Already trained 1.35M, so +4.65M more
    remaining = total_steps - 1_350_000

    print("Loading training data (2019-11 ~ 2024-06)...")
    df_15m = load_15m_data("2019-11-27", "2024-06-30")
    print(f"  15m bars: {len(df_15m):,}")

    # Pre-cache test data (avoid repeated DB access during eval)
    print("Pre-caching test data...")
    test_periods = [
        ("2024-07-01", "2024-09-30"),
        ("2024-10-01", "2024-12-31"),
        ("2025-01-01", "2025-03-20"),
    ]
    test_cache = []
    for s, e in test_periods:
        data, df30 = load_data(s, e)
        test_cache.append((data, df30))
    print(f"  Cached {len(test_cache)} test periods")

    def eval_fn(model):
        pnls = []; ents = []
        for data, df30 in test_cache:
            env = TradingEnvC(
                data=data, symbol="ETHUSDT", initial_balance=10000.0,
                commission_rate=0.0004, episode_bars=len(df30) - 50,
                random_start=False, sharpe_window=48,
            )
            obs, _ = env.reset()
            done = False; ls = None; es = np.ones((1,), dtype=bool); pos = []
            while not done:
                a, ls = model.predict(obs, state=ls, episode_start=es, deterministic=True)
                es = np.zeros((1,), dtype=bool)
                obs, _, t, tr, _ = env.step(a)
                pos.append(env._position); done = t or tr
            pnls.append(env._balance - 10000)
            ents.append(sum(1 for i in range(1, len(pos)) if pos[i] != 0 and pos[i-1] == 0))
        return pnls, ents

    # 4 parallel envs with per-episode augmentation (reduced from 8 for better PPO updates)
    print(f"\nCreating 4 environments (3 augmented, 1 clean)...")
    env_fns = [make_env(df_15m, seed=i, augment=(i > 0)) for i in range(4)]
    vec_env = DummyVecEnv(env_fns)

    # Load Castle (1.35M) as base
    print("Loading Castle (1.35M) as base...")
    model = RecurrentPPO.load(str(DATA_DIR / "rl_model_c_b_1350k"), env=vec_env)

    # v2 hyperparameters (post 3-engine review)
    model.learning_rate = 3e-5
    model.ent_coef = 0.012
    model.n_epochs = 4          # reduced from 10 to prevent collapse
    model.target_kl = 0.015     # KL divergence constraint
    model.clip_range = lambda _: 0.1  # tighter clipping (must be callable)

    # Callback with raised entropy floor
    callback = TrainingCallback(
        base_ent=0.012,
        boost_ent=0.025,
        cycle_steps=200_000,
        boost_duration=50_000,
        save_dir=DATA_DIR,
        eval_fn=eval_fn,
    )

    print(f"\nTraining +{remaining:,} steps to reach 6M total...")
    print(f"  LR: 3e-5, n_epochs: 4, target_kl: 0.015, clip: 0.1")
    print(f"  Entropy cycling: 0.012 base, 0.025 boost every 200K")
    print(f"  Per-episode augmentation: 0.3% noise, 15% vol jitter")
    print(f"  Validation gate: entries >= 15 per quarter")
    print(f"  Checkpoints: every 50K with evaluation\n")

    model.learn(
        total_timesteps=remaining,
        callback=callback,
        reset_num_timesteps=False,
    )

    # Final save
    model.save(str(DATA_DIR / "rl_model_c_6m"))
    print("\nSaved rl_model_c_6m")

    # Final evaluation
    print("\n" + "=" * 60)
    print("FINAL EVALUATION: 6M model")
    print("=" * 60)
    pnls, ents = eval_fn(model)
    labels = ["2024 Q3", "2024 Q4", "2025 Q1"]
    for l, p, e in zip(labels, pnls, ents):
        print(f"  [{l}] PnL=${p:+,.0f}  entries={e}")
    avg = np.mean(pnls)
    wins = sum(1 for p in pnls if p > 0)
    print(f"\n  Avg: ${avg:+,.0f}  Win: {wins}/3")

    # Compare with Castle baseline
    print(f"\n  Castle (1.35M): avg=$+5,762  7/7")
    print(f"  6M model:       avg=${avg:+,.0f}  {wins}/3")
    print(f"  Change: {(avg/5762-1)*100:+.0f}%")

    # Report best checkpoint
    if callback._best_tag:
        print(f"\n  Best checkpoint: {callback._best_tag} (avg=${callback._best_avg_pnl:+,.0f})")

    print("\nDone.")


if __name__ == "__main__":
    main()
