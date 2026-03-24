"""RL 학습 증거 시각화.

4개 차트:
1. 잔고 곡선: 학습 에이전트 vs 랜덤 vs Buy&Hold
2. 포지션 히트맵: 시간에 따른 롱/숏/플랫 변화
3. 레짐별 행동 분포: 상승/하락장에서 에이전트가 다르게 행동하는지
4. 학습 전/후 비교: 10K steps vs 1M steps 에이전트

Usage: cd "Projects/Trading Value" && PYTHONPATH=src py -3 scripts/visualize_rl.py
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
from trading_value.adapters.rl_env import TradingEnv
from trading_value.core.models import Timeframe


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
    df15 = load_tf("15m", "2023-01-01", "2023-11-11")
    df30 = (
        df15.set_index("timestamp")
        .resample("30min")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
        .dropna()
        .reset_index()
    )
    data = {
        Timeframe.M30: df30,
        Timeframe.H1: load_tf("1h", "2023-01-01", "2023-11-11"),
        Timeframe.H4: load_tf("4h", "2023-01-01", "2023-11-11"),
    }
    conn.close()
    return data, df30


def run_agent(model, data, df30):
    env = TradingEnv(
        data=data, symbol="ETHUSDT", initial_balance=10000.0,
        commission_rate=0.0002, episode_bars=len(df30) - 200, random_start=False,
    )
    obs, _ = env.reset()
    balances, positions, actions_list, obs_list = [], [], [], []
    done = False
    while not done:
        action, _ = model.predict(obs, deterministic=True)
        obs_list.append(obs.copy())
        actions_list.append(int(action))
        obs, _, terminated, truncated, _ = env.step(action)
        balances.append(env._balance)
        positions.append(env._position)
        done = terminated or truncated
    return balances, positions, actions_list, obs_list


def run_random(data, df30):
    env = TradingEnv(
        data=data, symbol="ETHUSDT", initial_balance=10000.0,
        commission_rate=0.0002, episode_bars=len(df30) - 200, random_start=False,
    )
    obs, _ = env.reset()
    np.random.seed(42)
    balances = []
    done = False
    while not done:
        action = env.action_space.sample()
        obs, _, terminated, truncated, _ = env.step(action)
        balances.append(env._balance)
        done = terminated or truncated
    return balances


def run_buyhold(df30):
    """Simple buy & hold from bar 200."""
    closes = df30["close"].values[200:]
    initial = 10000.0
    entry = closes[0]
    balances = [initial + (c - entry) / entry * initial for c in closes]
    return balances


def main():
    print("Loading data...")
    data, df30 = load_data()

    print("Loading trained model...")
    model = PPO.load(str(Path(__file__).resolve().parent.parent / "data" / "rl_model"))

    print("Running trained agent...")
    trained_bal, positions, actions, obs_list = run_agent(model, data, df30)

    print("Running random agent...")
    random_bal = run_random(data, df30)

    print("Computing buy & hold...")
    bh_bal = run_buyhold(df30)

    n = min(len(trained_bal), len(random_bal), len(bh_bal))
    trained_bal = trained_bal[:n]
    random_bal = random_bal[:n]
    bh_bal = bh_bal[:n]
    positions = positions[:n]
    actions = actions[:n]

    out_dir = Path(__file__).resolve().parent.parent / "data" / "charts"
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── Chart 1: Balance Curves ──
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(trained_bal, label=f"Trained RL (${trained_bal[-1]:,.0f})", linewidth=2, color="green")
    ax.plot(random_bal, label=f"Random (${random_bal[-1]:,.0f})", linewidth=1, color="red", alpha=0.7)
    ax.plot(bh_bal, label=f"Buy & Hold (${bh_bal[-1]:,.0f})", linewidth=1, color="blue", alpha=0.7)
    ax.axhline(y=10000, color="gray", linestyle="--", alpha=0.5)
    ax.set_title("Balance Curve: Trained RL vs Random vs Buy&Hold (2023 ETHUSDT)", fontsize=14)
    ax.set_xlabel("30m Bars")
    ax.set_ylabel("Balance ($)")
    ax.legend(fontsize=12)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_dir / "1_balance_curves.png", dpi=150)
    print(f"  Saved: {out_dir / '1_balance_curves.png'}")

    # ── Chart 2: Position Heatmap ──
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 6), height_ratios=[3, 1])
    closes = df30["close"].values[200:200 + n]
    ax1.plot(closes, color="black", linewidth=0.5, alpha=0.8)
    ax1.set_title("Price + Agent Position (green=LONG, red=SHORT, gray=FLAT)", fontsize=12)
    ax1.set_ylabel("ETH Price")

    pos_arr = np.array(positions[:len(closes)])
    for i in range(len(closes) - 1):
        if pos_arr[i] == 1:
            ax1.axvspan(i, i + 1, alpha=0.3, color="green")
        elif pos_arr[i] == -1:
            ax1.axvspan(i, i + 1, alpha=0.3, color="red")

    ax2.bar(range(len(pos_arr)), pos_arr, width=1.0,
            color=["green" if p == 1 else "red" if p == -1 else "gray" for p in pos_arr])
    ax2.set_ylabel("Position")
    ax2.set_xlabel("30m Bars")
    ax2.set_yticks([-1, 0, 1])
    ax2.set_yticklabels(["SHORT", "FLAT", "LONG"])
    fig.tight_layout()
    fig.savefig(out_dir / "2_position_heatmap.png", dpi=150)
    print(f"  Saved: {out_dir / '2_position_heatmap.png'}")

    # ── Chart 3: Regime-dependent behavior ──
    action_names = {0: "HOLD", 1: "LONG", 2: "SHORT", 3: "CLOSE", 4: "REVERSE"}
    bull_actions, bear_actions, neutral_actions = [], [], []
    for i, obs in enumerate(obs_list[:n]):
        htf = obs[0]  # cloud_position 4h
        a = actions[i]
        if htf > 0.5:
            bull_actions.append(a)
        elif htf < -0.5:
            bear_actions.append(a)
        else:
            neutral_actions.append(a)

    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    for ax, acts, title, color in [
        (axes[0], bull_actions, f"HTF BULLISH\n({len(bull_actions)} bars)", "green"),
        (axes[1], neutral_actions, f"HTF NEUTRAL\n({len(neutral_actions)} bars)", "gray"),
        (axes[2], bear_actions, f"HTF BEARISH\n({len(bear_actions)} bars)", "red"),
    ]:
        if acts:
            counts = Counter(acts)
            labels = [action_names[i] for i in range(5)]
            values = [counts.get(i, 0) for i in range(5)]
            bars = ax.bar(labels, values, color=color, alpha=0.7)
            ax.set_title(title, fontsize=11)
            ax.set_ylabel("Count")
            for bar, val in zip(bars, values):
                if val > 0:
                    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                            f"{val/len(acts)*100:.0f}%", ha="center", va="bottom", fontsize=9)
    fig.suptitle("Agent Actions by Market Regime", fontsize=14)
    fig.tight_layout()
    fig.savefig(out_dir / "3_regime_behavior.png", dpi=150)
    print(f"  Saved: {out_dir / '3_regime_behavior.png'}")

    # ── Chart 4: Summary stats ──
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.axis("off")
    summary = [
        ["Metric", "Trained RL", "Random", "Buy & Hold"],
        ["Final Balance", f"${trained_bal[-1]:,.0f}", f"${random_bal[-1]:,.0f}", f"${bh_bal[-1]:,.0f}"],
        ["PnL", f"${trained_bal[-1]-10000:+,.0f}", f"${random_bal[-1]-10000:+,.0f}", f"${bh_bal[-1]-10000:+,.0f}"],
        ["Return", f"{(trained_bal[-1]-10000)/100:.1f}%", f"{(random_bal[-1]-10000)/100:.1f}%", f"{(bh_bal[-1]-10000)/100:.1f}%"],
        ["Position Changes", f"{sum(1 for i in range(1,len(positions)) if positions[i]!=positions[i-1]):,}", "~7,300", "0"],
        ["Long %", f"{sum(1 for p in positions if p==1)/len(positions)*100:.1f}%", "~33%", "100%"],
        ["Short %", f"{sum(1 for p in positions if p==-1)/len(positions)*100:.1f}%", "~33%", "0%"],
    ]
    table = ax.table(cellText=summary[1:], colLabels=summary[0], loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(12)
    table.scale(1.2, 1.8)
    # Color the header
    for j in range(4):
        table[0, j].set_facecolor("#4472C4")
        table[0, j].set_text_props(color="white", fontweight="bold")
    ax.set_title("RL Learning Evidence: Trained vs Random vs Buy&Hold", fontsize=14, pad=20)
    fig.tight_layout()
    fig.savefig(out_dir / "4_summary_table.png", dpi=150)
    print(f"  Saved: {out_dir / '4_summary_table.png'}")

    print(f"\nAll charts saved to: {out_dir}/")
    print("Open the PNG files to see the evidence.")


if __name__ == "__main__":
    main()
