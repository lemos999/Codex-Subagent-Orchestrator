"""RL 학습 과정 시각화 — 에이전트가 어떻게 발전하는지 단계별로 보여줌.

5개 체크포인트에서 에이전트를 저장하고, 각각의 행동을 비교.
Usage: cd "Projects/Trading Value" && PYTHONPATH=src py -3 scripts/visualize_rl_learning.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import sqlite3
from collections import Counter

from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.callbacks import BaseCallback
from trading_value.adapters.rl_env import TradingEnv
from trading_value.core.models import Timeframe


class CheckpointCallback(BaseCallback):
    """Save model at regular intervals and record training metrics."""
    def __init__(self, save_freq, save_path, verbose=0):
        super().__init__(verbose)
        self.save_freq = save_freq
        self.save_path = Path(save_path)
        self.save_path.mkdir(parents=True, exist_ok=True)
        self.episode_rewards = []
        self.current_episode_reward = 0.0
        self.checkpoint_rewards = {}  # {step: [episode_rewards]}

    def _on_step(self):
        reward = self.locals["rewards"][0]
        self.current_episode_reward += reward

        done = self.locals["dones"][0]
        if done:
            self.episode_rewards.append(self.current_episode_reward)
            self.current_episode_reward = 0.0

        if self.num_timesteps % self.save_freq == 0:
            path = self.save_path / f"model_{self.num_timesteps}"
            self.model.save(str(path))
            self.checkpoint_rewards[self.num_timesteps] = list(self.episode_rewards)
            if self.verbose:
                print(f"  Checkpoint {self.num_timesteps}: {len(self.episode_rewards)} episodes")
        return True


def load_data():
    conn = sqlite3.connect(str(Path(__file__).resolve().parent.parent / "data" / "cache.sqlite"))
    def load_tf(tf_str, start, end):
        df = pd.read_sql_query(
            f"""SELECT datetime as timestamp, open, high, low, close, volume
            FROM ohlcv WHERE symbol='ETHUSDT' AND timeframe=?
            AND datetime >= '{start}' AND datetime <= '{end}'
            ORDER BY timestamp""",
            conn, params=(tf_str,),
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        return df

    # Train data
    df15_train = load_tf("15m", "2022-01-01", "2022-12-31")
    df30_train = df15_train.set_index("timestamp").resample("30min").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    ).dropna().reset_index()
    train_data = {
        Timeframe.M30: df30_train,
        Timeframe.H1: load_tf("1h", "2022-01-01", "2022-12-31"),
        Timeframe.H4: load_tf("4h", "2022-01-01", "2022-12-31"),
    }

    # Test data
    df15_test = load_tf("15m", "2023-01-01", "2023-11-11")
    df30_test = df15_test.set_index("timestamp").resample("30min").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    ).dropna().reset_index()
    test_data = {
        Timeframe.M30: df30_test,
        Timeframe.H1: load_tf("1h", "2023-01-01", "2023-11-11"),
        Timeframe.H4: load_tf("4h", "2023-01-01", "2023-11-11"),
    }
    conn.close()
    return train_data, test_data, df30_test


def evaluate_model(model, data, df30, n_bars=None):
    """Run model on data and return metrics."""
    env = TradingEnv(
        data=data, symbol="ETHUSDT", initial_balance=10000.0,
        commission_rate=0.0002, episode_bars=n_bars or (len(df30) - 200),
        random_start=False,
    )
    obs, _ = env.reset()
    actions = []
    balances = []
    positions = []
    done = False
    while not done:
        action, _ = model.predict(obs, deterministic=True)
        actions.append(int(action))
        obs, _, terminated, truncated, _ = env.step(action)
        balances.append(env._balance)
        positions.append(env._position)
        done = terminated or truncated
    return balances, positions, actions


def main():
    print("=" * 60)
    print("RL 학습 과정 시각화")
    print("=" * 60)

    train_data, test_data, df30_test = load_data()
    out_dir = Path(__file__).resolve().parent.parent / "data" / "charts"
    out_dir.mkdir(parents=True, exist_ok=True)
    ckpt_dir = Path(__file__).resolve().parent.parent / "data" / "checkpoints"

    # === Phase 1: Train with checkpoints ===
    total_steps = 500_000
    ckpt_freq = 100_000
    checkpoints = [ckpt_freq * i for i in range(1, total_steps // ckpt_freq + 1)]

    print(f"\nTraining PPO for {total_steps:,} steps with checkpoints every {ckpt_freq:,}...")

    vec_env = DummyVecEnv([lambda: TradingEnv(
        data=train_data, symbol="ETHUSDT",
        initial_balance=10000.0, commission_rate=0.0002,
        episode_bars=960, random_start=True,
    )])

    callback = CheckpointCallback(save_freq=ckpt_freq, save_path=str(ckpt_dir), verbose=1)

    model = PPO(
        "MlpPolicy", vec_env,
        learning_rate=3e-4, n_steps=2048, batch_size=256,
        n_epochs=10, gamma=0.99, ent_coef=0.01, verbose=0,
    )
    model.learn(total_timesteps=total_steps, callback=callback)

    # Save final
    model.save(str(ckpt_dir / f"model_{total_steps}"))
    callback.checkpoint_rewards[total_steps] = list(callback.episode_rewards)

    # === Phase 2: Evaluate each checkpoint on test data ===
    print("\nEvaluating checkpoints on test data...")

    ckpt_results = {}
    for step in checkpoints + [total_steps]:
        ckpt_model = PPO.load(str(ckpt_dir / f"model_{step}"))
        bal, pos, acts = evaluate_model(ckpt_model, test_data, df30_test)
        pnl = bal[-1] - 10000.0
        long_pct = sum(1 for p in pos if p == 1) / len(pos) * 100
        short_pct = sum(1 for p in pos if p == -1) / len(pos) * 100
        changes = sum(1 for i in range(1, len(pos)) if pos[i] != pos[i-1])
        ckpt_results[step] = {
            "balances": bal, "pnl": pnl,
            "long_pct": long_pct, "short_pct": short_pct,
            "changes": changes, "actions": acts,
        }
        print(f"  {step:>7,} steps: PnL=${pnl:+,.0f}, Long={long_pct:.0f}%, Short={short_pct:.0f}%, Changes={changes}")

    # === Chart 1: Learning Curve (episode rewards) ===
    fig, ax = plt.subplots(figsize=(12, 5))
    ep_rewards = callback.episode_rewards
    if len(ep_rewards) > 20:
        window = max(len(ep_rewards) // 50, 5)
        smoothed = pd.Series(ep_rewards).rolling(window).mean()
        ax.plot(smoothed, color="blue", linewidth=1.5, label=f"Smoothed (window={window})")
        ax.plot(ep_rewards, color="lightblue", alpha=0.3, linewidth=0.5, label="Raw")
    else:
        ax.plot(ep_rewards, color="blue", marker="o")
    ax.set_title("Training Episode Rewards Over Time", fontsize=14)
    ax.set_xlabel("Episode")
    ax.set_ylabel("Total Episode Reward")
    ax.legend()
    ax.grid(True, alpha=0.3)
    # Mark checkpoint positions
    ep_count = 0
    for step in checkpoints:
        ep_count = len(callback.checkpoint_rewards.get(step, []))
        if ep_count > 0:
            ax.axvline(x=ep_count, color="red", alpha=0.3, linestyle="--")
    fig.tight_layout()
    fig.savefig(out_dir / "5_learning_curve.png", dpi=150)
    print(f"\n  Saved: {out_dir / '5_learning_curve.png'}")

    # === Chart 2: PnL at each checkpoint ===
    fig, ax = plt.subplots(figsize=(10, 5))
    steps = sorted(ckpt_results.keys())
    pnls = [ckpt_results[s]["pnl"] for s in steps]
    colors = ["green" if p > 0 else "red" for p in pnls]
    bars = ax.bar([f"{s//1000}K" for s in steps], pnls, color=colors, alpha=0.8)
    ax.axhline(y=0, color="black", linewidth=0.5)
    for bar, val in zip(bars, pnls):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f"${val:+,.0f}", ha="center", va="bottom" if val > 0 else "top", fontsize=10)
    ax.set_title("Test PnL at Each Training Checkpoint", fontsize=14)
    ax.set_xlabel("Training Steps")
    ax.set_ylabel("Test PnL ($)")
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(out_dir / "6_checkpoint_pnl.png", dpi=150)
    print(f"  Saved: {out_dir / '6_checkpoint_pnl.png'}")

    # === Chart 3: Balance curves at different checkpoints ===
    fig, ax = plt.subplots(figsize=(14, 6))
    cmap = plt.cm.viridis
    for i, step in enumerate(steps):
        bal = ckpt_results[step]["balances"]
        alpha = 0.4 + 0.6 * (i / len(steps))
        color = cmap(i / len(steps))
        ax.plot(bal, label=f"{step//1000}K steps (${bal[-1]-10000:+,.0f})",
                color=color, alpha=alpha, linewidth=1.5)
    ax.axhline(y=10000, color="gray", linestyle="--", alpha=0.5)
    ax.set_title("How the Agent Improves: Balance Curves at Each Checkpoint", fontsize=14)
    ax.set_xlabel("Test Period (30m Bars)")
    ax.set_ylabel("Balance ($)")
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_dir / "7_checkpoint_balances.png", dpi=150)
    print(f"  Saved: {out_dir / '7_checkpoint_balances.png'}")

    # === Chart 4: Behavior evolution ===
    fig, axes = plt.subplots(1, len(steps), figsize=(3 * len(steps), 4), sharey=True)
    action_names = ["HOLD", "LONG", "SHORT", "CLOSE", "REV"]
    for i, step in enumerate(steps):
        ax = axes[i] if len(steps) > 1 else axes
        acts = ckpt_results[step]["actions"]
        counts = Counter(acts)
        values = [counts.get(a, 0) / len(acts) * 100 for a in range(5)]
        ax.bar(action_names, values, color=["gray", "green", "red", "blue", "orange"], alpha=0.7)
        ax.set_title(f"{step//1000}K", fontsize=11)
        ax.set_ylim(0, 60)
        if i == 0:
            ax.set_ylabel("Action %")
    fig.suptitle("Action Distribution Evolution During Training", fontsize=14)
    fig.tight_layout()
    fig.savefig(out_dir / "8_behavior_evolution.png", dpi=150)
    print(f"  Saved: {out_dir / '8_behavior_evolution.png'}")

    print(f"\nAll learning process charts saved to: {out_dir}/")


if __name__ == "__main__":
    main()
