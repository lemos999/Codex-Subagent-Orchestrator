"""Train Track C (LSTM + Sharpe) and evaluate B vs C vs Hybrid.

Track B: PPO MLP, PnL reward (v6)
Track C: RecurrentPPO LSTM, Sharpe reward (new)
Hybrid: B+C majority vote ensemble

Usage: cd "Projects/Trading Value" && PYTHONPATH=src py -3 scripts/train_track_c.py [steps]
"""
from __future__ import annotations
import sqlite3, sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from sb3_contrib import RecurrentPPO
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from trading_value.adapters.rl_env import TradingEnv
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


V6_CFG = dict(
    position_change_penalty=0.30, holding_cost=0.002,
    profitable_hold_bonus_max=0.02, profitable_close_bonus=0.2,
    drawdown_penalty_factor=0.15,
)


def make_env_b(data):
    return TradingEnv(
        data=data, symbol="ETHUSDT", initial_balance=10000.0,
        commission_rate=0.0002, episode_bars=960, random_start=True,
        **V6_CFG,
    )


def make_env_c(data):
    return TradingEnvC(
        data=data, symbol="ETHUSDT", initial_balance=10000.0,
        commission_rate=0.0002, episode_bars=960, random_start=True,
        sharpe_window=48,
    )


def evaluate_model(model, env_class, data, df30, label, env_cfg=None):
    """Evaluate a single model on test data with fixed $10K."""
    cfg = env_cfg or V6_CFG
    env = env_class(
        data=data, symbol="ETHUSDT", initial_balance=10000.0,
        commission_rate=0.0004, episode_bars=len(df30) - 50,
        random_start=False, **cfg,
    )
    obs, _ = env.reset()
    lstm_states = None
    episode_start = np.ones((1,), dtype=bool)
    positions = []
    actions_taken = []
    done = False

    while not done:
        if hasattr(model, "predict") and "state" in model.predict.__code__.co_varnames:
            # RecurrentPPO
            action, lstm_states = model.predict(
                obs, state=lstm_states, episode_start=episode_start,
                deterministic=True,
            )
            episode_start = np.zeros((1,), dtype=bool)
        else:
            action, _ = model.predict(obs, deterministic=True)

        obs, _, term, trunc, _ = env.step(action)
        positions.append(env._position)
        actions_taken.append(int(action))
        done = term or trunc

    pnl = env._balance - 10000
    entries = sum(1 for i in range(1, len(positions)) if positions[i] != 0 and positions[i-1] == 0)
    ret = pnl / 100
    return pnl, entries, env._total_commission, ret, positions, actions_taken


def evaluate_hybrid(model_b, model_c, data, df30, label):
    """Hybrid: B and C vote. Majority wins. If disagree on direction, HOLD."""
    env_b = TradingEnv(
        data=data, symbol="ETHUSDT", initial_balance=10000.0,
        commission_rate=0.0004, episode_bars=len(df30) - 50,
        random_start=False, **V6_CFG,
    )
    env_c = TradingEnvC(
        data=data, symbol="ETHUSDT", initial_balance=10000.0,
        commission_rate=0.0004, episode_bars=len(df30) - 50,
        random_start=False, sharpe_window=48,
    )

    obs_b, _ = env_b.reset()
    obs_c, _ = env_c.reset()
    lstm_states = None
    episode_start = np.ones((1,), dtype=bool)

    positions = []
    done_b = done_c = False

    while not done_b and not done_c:
        action_b, _ = model_b.predict(obs_b, deterministic=True)
        action_c, lstm_states = model_c.predict(
            obs_c, state=lstm_states, episode_start=episode_start,
            deterministic=True,
        )
        episode_start = np.zeros((1,), dtype=bool)

        # Hybrid voting: if both agree, use that action. Otherwise HOLD.
        ab = int(action_b)
        ac = int(action_c)
        if ab == ac:
            hybrid_action = ab
        elif ab == 0:  # B says HOLD, use C
            hybrid_action = ac
        elif ac == 0:  # C says HOLD, use B
            hybrid_action = ab
        else:
            # Disagree on direction → conservative: HOLD
            hybrid_action = 0

        obs_b, _, term_b, trunc_b, _ = env_b.step(hybrid_action)
        obs_c, _, term_c, trunc_c, _ = env_c.step(hybrid_action)
        positions.append(env_b._position)
        done_b = term_b or trunc_b
        done_c = term_c or trunc_c

    pnl = env_b._balance - 10000
    entries = sum(1 for i in range(1, len(positions)) if positions[i] != 0 and positions[i-1] == 0)
    return pnl, entries, env_b._total_commission, pnl / 100


def main():
    total_steps = int(sys.argv[1]) if len(sys.argv) > 1 else 500_000

    print("Loading training data (2022)...")
    train_data, train_df30 = load_data("2022-01-01", "2022-12-31")
    print(f"  30m: {len(train_df30)} bars")

    # Sanity check Track C env
    env_c = make_env_c(train_data)
    obs, _ = env_c.reset()
    print(f"  Track C obs shape: {obs.shape}")

    # Train Track C: RecurrentPPO with LSTM
    print(f"\nTraining Track C: RecurrentPPO LSTM ({total_steps:,} steps)...")
    print("  Phase 1: 300K steps, low penalty...")
    vec_env_c = DummyVecEnv([lambda: TradingEnvC(
        data=train_data, symbol="ETHUSDT", initial_balance=10000.0,
        commission_rate=0.0002, episode_bars=960, random_start=True,
        sharpe_window=48,
        position_change_penalty=0.10,  # low to learn trading first
    )])

    model_c = RecurrentPPO(
        "MlpLstmPolicy", vec_env_c,
        learning_rate=3e-4,
        n_steps=2048,
        batch_size=256,
        n_epochs=10,
        gamma=0.99,
        ent_coef=0.05,  # high exploration
        verbose=0,
    )
    model_c.learn(total_timesteps=300_000)

    print("  Phase 2: 200K steps, higher penalty...")
    vec_env_c2 = DummyVecEnv([lambda: make_env_c(train_data)])
    model_c.set_env(vec_env_c2)
    model_c.ent_coef = 0.02
    model_c.learn(total_timesteps=200_000, reset_num_timesteps=False)

    model_c.save(str(DATA_DIR / "rl_model_c"))
    print("  Saved rl_model_c")

    # Load Track B (v6)
    print("\nLoading Track B (v6)...")
    model_b = PPO.load(str(DATA_DIR / "rl_model_v6"))

    # Evaluate all three on quarterly test data
    print("\n" + "=" * 75)
    print("TRACK B vs C vs HYBRID — Fixed $10K, 0.04% taker")
    print("=" * 75)

    test_periods = [
        ("2023-01-01", "2023-03-31", "2023 Q1"),
        ("2023-04-01", "2023-06-30", "2023 Q2"),
        ("2023-07-01", "2023-09-30", "2023 Q3"),
        ("2024-01-01", "2024-03-31", "2024 Q1"),
        ("2024-04-01", "2024-06-30", "2024 Q2"),
        ("2024-07-01", "2024-09-30", "2024 Q3"),
    ]

    results_b = []
    results_c = []
    results_h = []

    for start, end, label in test_periods:
        test_data, test_df30 = load_data(start, end)

        pnl_b, ent_b, _, ret_b, _, _ = evaluate_model(
            model_b, TradingEnv, test_data, test_df30, label, V6_CFG)
        pnl_c, ent_c, _, ret_c, _, _ = evaluate_model(
            model_c, TradingEnvC, test_data, test_df30, label,
            {"sharpe_window": 48})
        pnl_h, ent_h, _, ret_h = evaluate_hybrid(
            model_b, model_c, test_data, test_df30, label)

        results_b.append(ret_b)
        results_c.append(ret_c)
        results_h.append(ret_h)

        print(f"\n  {label}:")
        print(f"    Track B (PPO MLP):      PnL=${pnl_b:>+10,.0f} ({ret_b:>+7.1f}%)  entries={ent_b}")
        print(f"    Track C (LSTM Sharpe):   PnL=${pnl_c:>+10,.0f} ({ret_c:>+7.1f}%)  entries={ent_c}")
        print(f"    Hybrid (B+C vote):       PnL=${pnl_h:>+10,.0f} ({ret_h:>+7.1f}%)  entries={ent_h}")

    print(f"\n{'='*75}")
    print("SUMMARY")
    print(f"{'='*75}")
    for name, rets in [("Track B", results_b), ("Track C", results_c), ("Hybrid", results_h)]:
        avg = np.mean(rets)
        med = np.median(rets)
        std = np.std(rets)
        wins = sum(1 for r in rets if r > 0)
        sharpe = avg / std if std > 0 else 0
        print(f"  {name:<20s}: avg={avg:>+8.1f}%  med={med:>+8.1f}%  std={std:>7.1f}%  "
              f"win={wins}/{len(rets)}  sharpe={sharpe:.2f}")

    print("\nDone.")


if __name__ == "__main__":
    main()
