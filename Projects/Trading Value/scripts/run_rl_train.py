"""Train RL agent on Trading Value environment.

Usage: cd "Projects/Trading Value" && PYTHONPATH=src py -3 scripts/run_rl_train.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from trading_value.core.models import Timeframe
from trading_value.adapters.rl_env import TradingEnv

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "cache.sqlite"


def load_data(symbol: str, start: str, end: str) -> dict[Timeframe, pd.DataFrame]:
    conn = sqlite3.connect(str(DB_PATH))

    def load_tf(tf_str: str) -> pd.DataFrame:
        df = pd.read_sql_query(
            f"""SELECT datetime as timestamp, open, high, low, close, volume
            FROM ohlcv WHERE symbol=? AND timeframe=?
            AND datetime >= '{start}' AND datetime <= '{end}'
            ORDER BY timestamp""",
            conn, params=(symbol, tf_str),
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        return df

    # Load 15m and resample to 30m
    df15 = load_tf("15m")
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
    }
    conn.close()
    return data


def main() -> None:
    print("Loading training data (2022)...")
    train_data = load_data("ETHUSDT", "2022-01-01", "2022-12-31")
    print(f"  30m: {len(train_data[Timeframe.M30])} bars")
    print(f"  1h:  {len(train_data[Timeframe.H1])} bars")
    print(f"  4h:  {len(train_data[Timeframe.H4])} bars")

    print("\nLoading test data (2023)...")
    test_data = load_data("ETHUSDT", "2023-01-01", "2023-11-11")
    print(f"  30m: {len(test_data[Timeframe.M30])} bars")

    # Create training environment
    print("\nCreating training environment...")
    train_env = TradingEnv(
        data=train_data,
        symbol="ETHUSDT",
        initial_balance=10000.0,
        commission_rate=0.0002,
        episode_bars=960,  # 20 days
        random_start=True,
    )

    # Test environment works
    obs, info = train_env.reset()
    print(f"  Observation shape: {obs.shape}")
    print(f"  Sample obs: {obs[:5]}...")

    # Quick sanity check — run 100 random steps
    total_reward = 0.0
    for _ in range(100):
        action = train_env.action_space.sample()
        obs, reward, terminated, truncated, info = train_env.step(action)
        total_reward += reward
        if terminated or truncated:
            obs, info = train_env.reset()
    print(f"  100 random steps: total_reward={total_reward:.4f}")

    # Train with PPO
    try:
        from stable_baselines3 import PPO
        from stable_baselines3.common.vec_env import DummyVecEnv

        print("\nTraining PPO agent (10K timesteps)...")
        vec_env = DummyVecEnv([lambda: TradingEnv(
            data=train_data, symbol="ETHUSDT",
            initial_balance=10000.0, commission_rate=0.0002,
            episode_bars=960, random_start=True,
        )])

        model = PPO(
            "MlpPolicy", vec_env,
            learning_rate=3e-4,
            n_steps=256,
            batch_size=64,
            n_epochs=10,
            gamma=0.99,
            verbose=1,
        )
        model.learn(total_timesteps=10_000)

        # Evaluate on test data
        print("\nEvaluating on test data...")
        test_env = TradingEnv(
            data=test_data, symbol="ETHUSDT",
            initial_balance=10000.0, commission_rate=0.0002,
            episode_bars=len(test_data[Timeframe.M30]) - 200,
            random_start=False,
        )

        obs, _ = test_env.reset()
        total_reward = 0.0
        trades = 0
        done = False
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = test_env.step(action)
            total_reward += reward
            if info.get("trade_closed"):
                trades += 1
            done = terminated or truncated

        final_balance = test_env._balance
        pnl = final_balance - 10000.0

        print(f"\n{'='*60}")
        print("RL AGENT TEST RESULTS (2023)")
        print(f"{'='*60}")
        print(f"  Total reward:   {total_reward:.4f}")
        print(f"  Trades:         {trades}")
        print(f"  Final balance:  ${final_balance:.2f}")
        print(f"  PnL:            ${pnl:+.2f}")
        print(f"  Return:         {pnl/100:.1f}%")

        # Save model
        model_path = Path(__file__).resolve().parent.parent / "data" / "rl_model"
        model.save(str(model_path))
        print(f"\n  Model saved to: {model_path}")

    except ImportError as e:
        print(f"\nstable-baselines3 not available: {e}")
        print("Skipping PPO training. Environment sanity check passed.")
    except Exception as e:
        print(f"\nTraining error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

    print("\nDone.")


if __name__ == "__main__":
    main()
