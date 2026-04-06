"""Compare all 4 siblings + v2 models on 20 quarters (2020Q1~2025Q1)."""
from __future__ import annotations
import sqlite3, sys, numpy as np, pandas as pd
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from sb3_contrib import RecurrentPPO
from stable_baselines3 import PPO
from trading_value.adapters.rl_env_c import TradingEnvC
from trading_value.adapters.rl_env import TradingEnv
from trading_value.core.models import Timeframe

DB = str(Path(__file__).resolve().parent.parent / "data" / "cache.sqlite")
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

V6_CFG = dict(position_change_penalty=0.30, holding_cost=0.002,
    profitable_hold_bonus_max=0.02, profitable_close_bonus=0.2, drawdown_penalty_factor=0.15)


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


TEST_PERIODS = [
    ("2020-01-01", "2020-03-31", "20Q1"),
    ("2020-04-01", "2020-06-30", "20Q2"),
    ("2020-07-01", "2020-09-30", "20Q3"),
    ("2020-10-01", "2020-12-31", "20Q4"),
    ("2021-01-01", "2021-03-31", "21Q1"),
    ("2021-04-01", "2021-06-30", "21Q2"),
    ("2021-07-01", "2021-09-30", "21Q3"),
    ("2021-10-01", "2021-12-31", "21Q4"),
    ("2022-01-01", "2022-03-31", "22Q1"),
    ("2022-04-01", "2022-06-30", "22Q2"),
    ("2022-07-01", "2022-09-30", "22Q3"),
    ("2022-10-01", "2022-12-31", "22Q4"),
    ("2023-01-01", "2023-03-31", "23Q1"),
    ("2023-04-01", "2023-06-30", "23Q2"),
    ("2023-07-01", "2023-09-30", "23Q3"),
    ("2023-10-01", "2023-12-31", "23Q4"),
    ("2024-01-01", "2024-03-31", "24Q1"),
    ("2024-04-01", "2024-06-30", "24Q2"),  # train data ends here
    ("2024-07-01", "2024-09-30", "24Q3"),  # out-of-sample from here
    ("2024-10-01", "2024-12-31", "24Q4"),
]


def eval_single(model, env_class, env_cfg, test_cache, is_lstm=False):
    pnls = []; entries = []; hold_pcts = []
    for data, df30, label in test_cache:
        env = env_class(data=data, symbol="ETHUSDT", initial_balance=10000.0,
            commission_rate=0.0004, episode_bars=len(df30) - 50, random_start=False, **env_cfg)
        obs, _ = env.reset()
        done = False; ls = None; es = np.ones((1,), dtype=bool)
        positions = []; actions = []
        while not done:
            if is_lstm:
                a, ls = model.predict(obs, state=ls, episode_start=es, deterministic=True)
                es = np.zeros((1,), dtype=bool)
            else:
                a, _ = model.predict(obs, deterministic=True)
            obs, _, t, tr, _ = env.step(a)
            positions.append(env._position); actions.append(int(a))
            done = t or tr
        pnl = env._balance - 10000
        ent = sum(1 for i in range(1, len(positions)) if positions[i] != 0 and positions[i-1] == 0)
        hpct = sum(1 for a in actions if a == 0) / len(actions) * 100 if actions else 100
        pnls.append(pnl); entries.append(ent); hold_pcts.append(hpct)
    return pnls, entries, hold_pcts


def eval_ensemble(m1, m2, test_cache, env_cfg):
    pnls = []; entries = []; hold_pcts = []
    for data, df30, label in test_cache:
        env = TradingEnvC(data=data, symbol="ETHUSDT", initial_balance=10000.0,
            commission_rate=0.0004, episode_bars=len(df30) - 50, random_start=False, **env_cfg)
        obs, _ = env.reset()
        done = False; ls1 = None; ls2 = None; es = np.ones((1,), dtype=bool)
        positions = []; actions = []
        while not done:
            a1, ls1 = m1.predict(obs, state=ls1, episode_start=es, deterministic=True)
            a2, ls2 = m2.predict(obs, state=ls2, episode_start=es, deterministic=True)
            es = np.zeros((1,), dtype=bool)
            a1i, a2i = int(a1), int(a2)
            if a1i == a2i:
                ha = a1i
            elif a1i == 0:
                ha = a2i
            elif a2i == 0:
                ha = a1i
            else:
                ha = 0
            obs, _, t, tr, _ = env.step(ha)
            positions.append(env._position); actions.append(ha)
            done = t or tr
        pnl = env._balance - 10000
        ent = sum(1 for i in range(1, len(positions)) if positions[i] != 0 and positions[i-1] == 0)
        hpct = sum(1 for a in actions if a == 0) / len(actions) * 100
        pnls.append(pnl); entries.append(ent); hold_pcts.append(hpct)
    return pnls, entries, hold_pcts


def main():
    # Load test data
    test_cache = []
    for s, e, l in TEST_PERIODS:
        data, df30 = load_data(s, e)
        test_cache.append((data, df30, l))

    results = []

    # B Berserker
    print("Evaluating B Berserker...")
    m = PPO.load(str(DATA_DIR / "rl_model_b_3m"))
    p, e, h = eval_single(m, TradingEnv, V6_CFG, test_cache, is_lstm=False)
    results.append(("B Berserker", p, e, h))
    del m

    # C Castle (v1 reward with penalty 0.35)
    print("Evaluating C Castle...")
    m = RecurrentPPO.load(str(DATA_DIR / "rl_model_c_b_1350k"))
    p, e, h = eval_single(m, TradingEnvC, {"sharpe_window": 48, "position_change_penalty": 0.35}, test_cache, is_lstm=True)
    results.append(("C Castle", p, e, h))
    del m

    # D Diplomat (ensemble 1100k + 1350k)
    print("Evaluating D Diplomat...")
    m1 = RecurrentPPO.load(str(DATA_DIR / "rl_model_c_1100k"))
    m2 = RecurrentPPO.load(str(DATA_DIR / "rl_model_c_b_1350k"))
    p, e, h = eval_ensemble(m1, m2, test_cache, {"sharpe_window": 48, "position_change_penalty": 0.35})
    results.append(("D Diplomat", p, e, h))
    del m1, m2

    # E Eagle (ensemble v1 + 1100k)
    print("Evaluating E Eagle...")
    m1 = RecurrentPPO.load(str(DATA_DIR / "rl_model_c_1350_v1"))
    m2 = RecurrentPPO.load(str(DATA_DIR / "rl_model_c_1100k"))
    p, e, h = eval_ensemble(m1, m2, test_cache, {"sharpe_window": 48, "position_change_penalty": 0.35})
    results.append(("E Eagle", p, e, h))
    del m1, m2

    # v2 Phase 1
    print("Evaluating v2 Phase1...")
    m = RecurrentPPO.load(str(DATA_DIR / "rl_model_c_v2_200k_validation"))
    p, e, h = eval_single(m, TradingEnvC, {"sharpe_window": 48}, test_cache, is_lstm=True)
    results.append(("v2 Phase1", p, e, h))
    del m

    # v2 R2 Bear (best stepped)
    print("Evaluating v2 R2 Bear...")
    m = RecurrentPPO.load(str(DATA_DIR / "rl_model_c_v2_stepped_r2_bear"))
    p, e, h = eval_single(m, TradingEnvC, {"sharpe_window": 48}, test_cache, is_lstm=True)
    results.append(("v2 R2 Bear", p, e, h))
    del m

    # Print results
    labels = [l for _, _, l in TEST_PERIODS]
    n_q = len(labels)
    print()
    print("=" * 90)
    print(f"4 SIBLINGS + v2 COMPARISON ({n_q} quarters, 2020Q1 ~ 2024Q4)")
    print("=" * 90)

    # Summary table
    print()
    print(f"{'Model':<16s} {'Avg PnL':>12s} {'Entries':>8s} {'HOLD%':>7s} {'Sharpe':>8s} {'PnL/Ent':>9s} {'Win':>6s} {'Loss':>6s}")
    print("-" * 78)
    for name, pnls, ents, holds in results:
        ap = np.mean(pnls)
        ae = np.mean(ents)
        ah = np.mean(holds)
        sh = ap / max(np.std(pnls), 1.0)
        pe = ap / ae if ae > 0 else 0
        wins = sum(1 for p in pnls if p > 0)
        losses = sum(1 for p in pnls if p <= 0)
        print(f"{name:<16s} ${ap:>+10,.0f} {ae:>7.0f} {ah:>6.1f}% {sh:>7.2f} ${pe:>7,.0f} {wins:>5d} {losses:>5d}")

    # In-sample vs Out-of-sample split (train data ends at 2024-06)
    # Quarters 0-17 (20Q1~24Q2) = in-sample, 18-19 (24Q3~24Q4) = out-of-sample
    oos_start = 18  # index of 24Q3
    print()
    print("IN-SAMPLE (20Q1~24Q2, 18 quarters) vs OUT-OF-SAMPLE (24Q3~24Q4, 2 quarters):")
    print("-" * 78)
    for name, pnls, ents, holds in results:
        is_pnls = pnls[:oos_start]
        oos_pnls = pnls[oos_start:]
        is_avg = np.mean(is_pnls) if is_pnls else 0
        oos_avg = np.mean(oos_pnls) if oos_pnls else 0
        is_wins = sum(1 for p in is_pnls if p > 0)
        oos_wins = sum(1 for p in oos_pnls if p > 0)
        print(f"  {name:<14s} IS: ${is_avg:>+10,.0f} ({is_wins}/{len(is_pnls)} win)  "
              f"OOS: ${oos_avg:>+10,.0f} ({oos_wins}/{len(oos_pnls)} win)")

    # Detail by quarter
    print()
    print("DETAIL BY QUARTER (PnL / entries):")
    print("-" * 90)
    # Header
    hdr = f"{'Model':<14s}"
    for l in labels:
        hdr += f" {l:>8s}"
    print(hdr)
    print("-" * 90)

    for name, pnls, ents, holds in results:
        line = f"{name:<14s}"
        for p in pnls:
            if p >= 0:
                line += f" {p:>+7,.0f}"
            else:
                line += f" {p:>+7,.0f}"
        print(line)

    # Entries row
    print()
    print("ENTRIES BY QUARTER:")
    print("-" * 90)
    hdr = f"{'Model':<14s}"
    for l in labels:
        hdr += f" {l:>8s}"
    print(hdr)
    print("-" * 90)
    for name, pnls, ents, holds in results:
        line = f"{name:<14s}"
        for e in ents:
            line += f" {e:>8d}"
        print(line)

    print()
    print("Done.")


if __name__ == "__main__":
    main()
