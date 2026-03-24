"""Train B/C/Hybrid on full 6-year history (2019-11 ~ 2025-09).

Training: 2019-11 ~ 2024-06 (4.5 years)
Test: 2024-07 ~ 2025-03 (9 months, unseen)

Usage: cd "Projects/Trading Value" && PYTHONPATH=src py -3 scripts/train_full_history.py [steps]
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

# Split: train on 2019-11 ~ 2024-06, test on 2024-07 ~ 2025-03
TRAIN_START = "2019-11-27"
TRAIN_END = "2024-06-30"
TEST_START = "2024-07-01"
TEST_END = "2025-03-20"


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


V_CFG = dict(
    position_change_penalty=0.30, holding_cost=0.002,
    profitable_hold_bonus_max=0.02, profitable_close_bonus=0.2,
    drawdown_penalty_factor=0.15,
)


def make_env_b(data):
    return TradingEnv(
        data=data, symbol="ETHUSDT", initial_balance=10000.0,
        commission_rate=0.0002, episode_bars=1440, random_start=True,
        **V_CFG,
    )


def make_env_c(data):
    return TradingEnvC(
        data=data, symbol="ETHUSDT", initial_balance=10000.0,
        commission_rate=0.0002, episode_bars=1440, random_start=True,
        sharpe_window=48,
    )


def evaluate_fixed(model, env_class, data, df30, label, is_lstm=False, env_cfg=None):
    cfg = env_cfg or V_CFG
    env = env_class(
        data=data, symbol="ETHUSDT", initial_balance=10000.0,
        commission_rate=0.0004, episode_bars=len(df30) - 100,
        random_start=False, **cfg,
    )
    obs, _ = env.reset()
    lstm_states = None
    episode_start = np.ones((1,), dtype=bool)
    positions = []
    done = False
    while not done:
        if is_lstm:
            action, lstm_states = model.predict(
                obs, state=lstm_states, episode_start=episode_start, deterministic=True)
            episode_start = np.zeros((1,), dtype=bool)
        else:
            action, _ = model.predict(obs, deterministic=True)
        obs, _, term, trunc, _ = env.step(action)
        positions.append(env._position)
        done = term or trunc
    pnl = env._balance - 10000
    entries = sum(1 for i in range(1, len(positions)) if positions[i] != 0 and positions[i-1] == 0)
    return pnl, entries, env._total_commission, pnl / 100


def evaluate_hybrid(model_b, model_c, data, df30, label):
    env = TradingEnv(
        data=data, symbol="ETHUSDT", initial_balance=10000.0,
        commission_rate=0.0004, episode_bars=len(df30) - 100,
        random_start=False, **V_CFG,
    )
    env_c = TradingEnvC(
        data=data, symbol="ETHUSDT", initial_balance=10000.0,
        commission_rate=0.0004, episode_bars=len(df30) - 100,
        random_start=False, sharpe_window=48,
    )
    obs_b, _ = env.reset()
    obs_c, _ = env_c.reset()
    lstm_states = None
    episode_start = np.ones((1,), dtype=bool)
    positions = []
    done = False
    while not done:
        action_b, _ = model_b.predict(obs_b, deterministic=True)
        action_c, lstm_states = model_c.predict(
            obs_c, state=lstm_states, episode_start=episode_start, deterministic=True)
        episode_start = np.zeros((1,), dtype=bool)
        ab, ac = int(action_b), int(action_c)
        hybrid = ab if ab == ac else (ac if ab == 0 else (ab if ac == 0 else 0))
        obs_b, _, term_b, trunc_b, _ = env.step(hybrid)
        obs_c, _, term_c, trunc_c, _ = env_c.step(hybrid)
        positions.append(env._position)
        done = term_b or trunc_b or term_c or trunc_c
    pnl = env._balance - 10000
    entries = sum(1 for i in range(1, len(positions)) if positions[i] != 0 and positions[i-1] == 0)
    return pnl, entries, env._total_commission, pnl / 100


def main():
    total_steps = int(sys.argv[1]) if len(sys.argv) > 1 else 800_000

    print(f"Loading training data ({TRAIN_START} ~ {TRAIN_END})...")
    train_data, train_df30 = load_data(TRAIN_START, TRAIN_END)
    print(f"  30m bars: {len(train_df30):,} ({len(train_df30)/48:.0f} days)")

    # === Track B: PPO MLP on full history ===
    print(f"\n{'='*60}")
    print(f"Track B: PPO MLP ({total_steps:,} steps on 4.5yr data)")
    print(f"{'='*60}")

    print("  Phase 1: 400K, penalty=0.10, ent=0.05...")
    cfg1 = {**V_CFG, "position_change_penalty": 0.10}
    vec_b = DummyVecEnv([lambda: TradingEnv(
        data=train_data, symbol="ETHUSDT", initial_balance=10000.0,
        commission_rate=0.0002, episode_bars=1440, random_start=True, **cfg1)])
    model_b = PPO("MlpPolicy", vec_b, learning_rate=3e-4, n_steps=2048,
        batch_size=256, n_epochs=10, gamma=0.99, ent_coef=0.05, verbose=0)
    model_b.learn(total_timesteps=int(total_steps * 0.5))

    print("  Phase 2: 400K, penalty=0.30, ent=0.02...")
    vec_b2 = DummyVecEnv([lambda: make_env_b(train_data)])
    model_b.set_env(vec_b2)
    model_b.ent_coef = 0.02
    model_b.learn(total_timesteps=int(total_steps * 0.5), reset_num_timesteps=False)
    model_b.save(str(DATA_DIR / "rl_model_b_full"))
    print("  Saved rl_model_b_full")

    # === Track C: RecurrentPPO LSTM on full history ===
    print(f"\n{'='*60}")
    print(f"Track C: RecurrentPPO LSTM ({total_steps:,} steps on 4.5yr data)")
    print(f"{'='*60}")

    print("  Phase 1: 400K, penalty=0.10, ent=0.05...")
    vec_c = DummyVecEnv([lambda: TradingEnvC(
        data=train_data, symbol="ETHUSDT", initial_balance=10000.0,
        commission_rate=0.0002, episode_bars=1440, random_start=True,
        sharpe_window=48, position_change_penalty=0.10)])
    model_c = RecurrentPPO("MlpLstmPolicy", vec_c, learning_rate=3e-4,
        n_steps=2048, batch_size=256, n_epochs=10, gamma=0.99,
        ent_coef=0.05, verbose=0)
    model_c.learn(total_timesteps=int(total_steps * 0.5))

    print("  Phase 2: 400K, penalty=0.35, ent=0.02...")
    vec_c2 = DummyVecEnv([lambda: make_env_c(train_data)])
    model_c.set_env(vec_c2)
    model_c.ent_coef = 0.02
    model_c.learn(total_timesteps=int(total_steps * 0.5), reset_num_timesteps=False)
    model_c.save(str(DATA_DIR / "rl_model_c_full"))
    print("  Saved rl_model_c_full")

    # === Evaluation on UNSEEN test data ===
    print(f"\n{'='*60}")
    print(f"EVALUATION: {TEST_START} ~ {TEST_END} (UNSEEN)")
    print(f"{'='*60}")

    test_periods = [
        (TEST_START, "2024-09-30", "2024 Q3"),
        ("2024-10-01", "2024-12-31", "2024 Q4"),
        ("2025-01-01", TEST_END, "2025 Q1"),
    ]

    results = {"B": [], "C": [], "Hybrid": []}

    for start, end, label in test_periods:
        test_data, test_df30 = load_data(start, end)
        if len(test_df30) < 50:
            print(f"  {label}: insufficient data")
            continue

        pnl_b, ent_b, _, ret_b = evaluate_fixed(
            model_b, TradingEnv, test_data, test_df30, label, env_cfg=V_CFG)
        pnl_c, ent_c, _, ret_c = evaluate_fixed(
            model_c, TradingEnvC, test_data, test_df30, label,
            is_lstm=True, env_cfg={"sharpe_window": 48})
        pnl_h, ent_h, _, ret_h = evaluate_hybrid(
            model_b, model_c, test_data, test_df30, label)

        results["B"].append(ret_b)
        results["C"].append(ret_c)
        results["Hybrid"].append(ret_h)

        print(f"\n  {label}:")
        print(f"    Track B:  PnL=${pnl_b:>+12,.0f} ({ret_b:>+8.1f}%)  entries={ent_b}")
        print(f"    Track C:  PnL=${pnl_c:>+12,.0f} ({ret_c:>+8.1f}%)  entries={ent_c}")
        print(f"    Hybrid:   PnL=${pnl_h:>+12,.0f} ({ret_h:>+8.1f}%)  entries={ent_h}")

    print(f"\n{'='*60}")
    print("SUMMARY (unseen test quarters)")
    print(f"{'='*60}")
    for name, rets in results.items():
        if not rets:
            continue
        avg = np.mean(rets)
        std = np.std(rets)
        wins = sum(1 for r in rets if r > 0)
        sharpe = avg / std if std > 0 else 0
        print(f"  {name:<10s}: avg={avg:>+10.1f}%  std={std:>8.1f}%  "
              f"win={wins}/{len(rets)}  sharpe={sharpe:.2f}")

    print("\nDone.")


if __name__ == "__main__":
    main()
