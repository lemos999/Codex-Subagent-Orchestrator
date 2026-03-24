"""Train RL agents with increasing position-change penalties.

Find the sweet spot: fewer trades while maintaining profit.
"""
from __future__ import annotations
import sys, sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
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


def patch_env_penalty(env_class, penalty):
    """Monkey-patch the position change penalty value."""
    original_step = env_class.step

    def patched_step(self, action):
        prev_position = self._position
        obs, reward, terminated, truncated, info = original_step(self, action)
        # The original already applies -0.15 penalty. Adjust the difference.
        if self._position != prev_position:
            extra = penalty - 0.15  # add the difference
            reward -= extra
        return obs, reward, terminated, truncated, info

    env_class.step = patched_step


def evaluate(model, data, df30, commission_rate=0.0004):
    env = TradingEnv(
        data=data, symbol="ETHUSDT", initial_balance=10000.0,
        commission_rate=commission_rate, episode_bars=len(df30) - 100,
        random_start=False,
    )
    obs, _ = env.reset()
    positions = []
    done = False
    while not done:
        action, _ = model.predict(obs, deterministic=True)
        obs, _, term, trunc, _ = env.step(action)
        positions.append(env._position)
        done = term or trunc
    pnl = env._balance - 10000
    changes = sum(1 for i in range(1, len(positions)) if positions[i] != positions[i - 1])
    return pnl, changes, len(positions)


def main():
    print("Loading data...")
    train_data, train_df30 = load_data("2022-01-01", "2022-12-31")
    test_data, test_df30 = load_data("2024-04-01", "2024-05-31")

    penalties = [0.15, 0.30, 0.50, 0.75, 1.00, 1.50]
    results = []

    for penalty in penalties:
        print(f"\n{'='*50}")
        print(f"Training with penalty = {penalty:.2f}R per position change")
        print(f"{'='*50}")

        # Create env factory with patched penalty
        def make_env(p=penalty):
            env = TradingEnv(
                data=train_data, symbol="ETHUSDT", initial_balance=10000.0,
                commission_rate=0.0002, episode_bars=960, random_start=True,
            )
            # Override the change penalty by storing it
            env._change_penalty = p
            return env

        # We need to patch at the instance level instead
        # Simpler approach: modify the env's step to add extra penalty
        class PenalizedEnv(TradingEnv):
            def __init__(self, change_penalty, **kwargs):
                super().__init__(**kwargs)
                self._change_penalty = change_penalty

            def step(self, action):
                prev = self._position
                obs, reward, term, trunc, info = super().step(action)
                if self._position != prev:
                    # Original already has -0.15, add the difference
                    reward -= (self._change_penalty - 0.15)
                return obs, reward, term, trunc, info

        vec_env = DummyVecEnv([lambda p=penalty: PenalizedEnv(
            change_penalty=p,
            data=train_data, symbol="ETHUSDT", initial_balance=10000.0,
            commission_rate=0.0002, episode_bars=960, random_start=True,
        )])

        # Load v2 and fine-tune
        model = PPO.load(
            str(Path(__file__).resolve().parent.parent / "data" / "rl_model_v2"),
            env=vec_env,
        )
        model.learn(total_timesteps=200_000, reset_num_timesteps=False)

        # Save
        save_path = Path(__file__).resolve().parent.parent / "data" / f"rl_model_p{int(penalty*100)}"
        model.save(str(save_path))

        # Evaluate at 0.04% commission (taker)
        pnl_004, changes_004, bars = evaluate(model, test_data, test_df30, 0.0004)
        # Evaluate at 0.02% commission (maker)
        pnl_002, changes_002, _ = evaluate(model, test_data, test_df30, 0.0002)

        bars_per_change = bars / max(changes_004, 1)
        results.append({
            "penalty": penalty,
            "pnl_002": pnl_002,
            "pnl_004": pnl_004,
            "changes": changes_004,
            "bars_per_change": bars_per_change,
        })
        print(f"  PnL@0.02%: ${pnl_002:+,.0f}, PnL@0.04%: ${pnl_004:+,.0f}")
        print(f"  Changes: {changes_004}, Bars/change: {bars_per_change:.1f}")

    # Summary table
    print(f"\n{'='*70}")
    print(f"SUMMARY: Position Change Penalty vs Performance")
    print(f"{'='*70}")
    print(f"{'Penalty':>8s} {'Changes':>8s} {'Bars/Chg':>9s} {'PnL@0.02%':>11s} {'PnL@0.04%':>11s}")
    print(f"{'--------':>8s} {'--------':>8s} {'---------':>9s} {'-----------':>11s} {'-----------':>11s}")
    for r in results:
        print(f"{r['penalty']:>7.2f}R {r['changes']:>8d} {r['bars_per_change']:>9.1f} ${r['pnl_002']:>+10,.0f} ${r['pnl_004']:>+10,.0f}")

    # Find best at 0.04%
    best = max(results, key=lambda r: r["pnl_004"])
    print(f"\nBest at 0.04% taker: penalty={best['penalty']:.2f}R, PnL=${best['pnl_004']:+,.0f}, changes={best['changes']}")


if __name__ == "__main__":
    main()
