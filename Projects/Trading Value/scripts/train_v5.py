"""Train RL v5 model: reward tuning + cloud twist observation.

Fine-tunes from v4 checkpoint with:
- Position change penalty: 0.40R (was 0.15R)
- Asymmetric holding cost (losers only)
- Reduced drawdown penalty factor: 0.15 (was 0.5)
- Forward cloud twist in observation (25 -> 29 dims)

Usage: cd "Projects/Trading Value" && PYTHONPATH=src py -3 scripts/train_v5.py [steps]
"""
from __future__ import annotations
import sqlite3, sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
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


V5_REWARD_CONFIG = dict(
    position_change_penalty=0.40,
    holding_cost=0.002,
    profitable_hold_bonus_max=0.02,
    profitable_close_bonus=0.2,
    drawdown_penalty_factor=0.15,
)


def make_env(data, episode_bars=960, random_start=True):
    return TradingEnv(
        data=data, symbol="ETHUSDT",
        initial_balance=10000.0, commission_rate=0.0002,
        episode_bars=episode_bars, random_start=random_start,
        **V5_REWARD_CONFIG,
    )


def evaluate(model, data, df30, label=""):
    env = make_env(data, episode_bars=len(df30) - 100, random_start=False)
    obs, _ = env.reset()
    positions = []
    done = False
    while not done:
        action, _ = model.predict(obs, deterministic=True)
        obs, _, term, trunc, _ = env.step(action)
        positions.append(env._position)
        done = term or trunc

    pnl = env._balance - 10000
    entries = sum(1 for i in range(1, len(positions))
                  if positions[i] != 0 and positions[i-1] == 0)
    changes = sum(1 for i in range(1, len(positions)) if positions[i] != positions[i-1])
    commission = env._total_commission

    print(f"  [{label}] PnL: ${pnl:+,.0f} | Entries: {entries} | "
          f"Changes: {changes} | Commission: ${commission:,.0f} | "
          f"Balance: ${env._balance:,.0f}")
    return pnl, entries, changes


def main():
    total_steps = int(sys.argv[1]) if len(sys.argv) > 1 else 400_000

    print("Loading training data (2022)...")
    train_data, train_df30 = load_data("2022-01-01", "2022-12-31")
    print(f"  30m: {len(train_df30)} bars")

    # Sanity check: new env works
    print("\nSanity check (v5 env)...")
    env = make_env(train_data)
    obs, _ = env.reset()
    print(f"  Observation shape: {obs.shape}")
    print(f"  Cloud twist features [25:29]: {obs[25:29]}")
    total_reward = 0.0
    for _ in range(100):
        action = env.action_space.sample()
        obs, reward, term, trunc, _ = env.step(action)
        total_reward += reward
        if term or trunc:
            obs, _ = env.reset()
    print(f"  100 random steps: reward={total_reward:.4f}")

    # Create vectorized env for training
    print(f"\nTraining v5 PPO ({total_steps:,} steps, from scratch)...")
    vec_env = DummyVecEnv([lambda: make_env(train_data)])

    model = PPO(
        "MlpPolicy", vec_env,
        learning_rate=3e-4,
        n_steps=2048,
        batch_size=256,
        n_epochs=10,
        gamma=0.99,
        ent_coef=0.01,
        verbose=1,
    )
    model.learn(total_timesteps=total_steps)

    # Save v5
    save_path = DATA_DIR / "rl_model_v5"
    model.save(str(save_path))
    print(f"\nModel saved: {save_path}")

    # Evaluate on multiple test periods
    print("\n" + "=" * 60)
    print("V5 EVALUATION RESULTS")
    print("=" * 60)

    test_periods = [
        ("2023-01-01", "2023-11-11", "2023"),
        ("2024-04-01", "2024-05-31", "2024 Apr-May"),
        ("2024-06-01", "2024-07-31", "2024 Jun-Jul"),
    ]

    for start, end, label in test_periods:
        try:
            test_data, test_df30 = load_data(start, end)
            evaluate(model, test_data, test_df30, label)
        except Exception as e:
            print(f"  [{label}] Error: {e}")

    print(f"\nReward config: {V5_REWARD_CONFIG}")
    print("Done.")


if __name__ == "__main__":
    main()
