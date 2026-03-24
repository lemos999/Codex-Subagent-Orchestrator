"""Analyze v2 RL agent strategy patterns."""
from __future__ import annotations
import sqlite3, sys
from pathlib import Path
from collections import defaultdict
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from stable_baselines3 import PPO
from trading_value.adapters.rl_env import TradingEnv
from trading_value.core.models import Timeframe


def cl(v):
    if v > 0.5: return "ABOVE"
    if v < -0.5: return "BELOW"
    return "IN"


def main():
    conn = sqlite3.connect(str(Path(__file__).resolve().parent.parent / "data" / "cache.sqlite"))
    def load_tf(tf_str, start, end):
        df = pd.read_sql_query(
            "SELECT datetime as timestamp, open, high, low, close, volume "
            "FROM ohlcv WHERE symbol='ETHUSDT' AND timeframe=? "
            "AND datetime >= ? AND datetime <= ? ORDER BY timestamp",
            conn, params=(tf_str, start, end),
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        return df

    start, end = sys.argv[1] if len(sys.argv) > 1 else "2024-01-01", sys.argv[2] if len(sys.argv) > 2 else "2024-03-31"
    df15 = load_tf("15m", start, end)
    df30 = df15.set_index("timestamp").resample("30min").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    ).dropna().reset_index()
    data = {
        Timeframe.M30: df30,
        Timeframe.H1: load_tf("1h", start, end),
        Timeframe.H4: load_tf("4h", start, end),
    }
    conn.close()

    model = PPO.load(str(Path(__file__).resolve().parent.parent / "data" / "rl_model_v2"))
    env = TradingEnv(
        data=data, symbol="ETHUSDT", initial_balance=10000.0,
        commission_rate=0.0002, episode_bars=len(df30) - 100, random_start=False,
    )
    obs, _ = env.reset()

    steps = []
    done = False
    while not done:
        action, _ = model.predict(obs, deterministic=True)
        prev_pos = env._position
        obs_c = obs.copy()
        obs, _, term, trunc, _ = env.step(action)
        steps.append({
            "action": int(action), "prev": prev_pos, "new": env._position,
            "bal": env._balance,
            "htf": obs_c[0], "h1": obs_c[3], "m30": obs_c[6],
        })
        done = term or trunc

    transitions = [s for s in steps if s["prev"] != s["new"]]
    f2l = [t for t in transitions if t["prev"] == 0 and t["new"] == 1]
    f2s = [t for t in transitions if t["prev"] == 0 and t["new"] == -1]
    revs = [t for t in transitions if t["prev"] * t["new"] == -1]

    print("=" * 60)
    print(f"v2 STRATEGY ANALYSIS: {start} ~ {end}")
    print("=" * 60)

    print(f"\n--- Transition Counts ---")
    print(f"  Flat->Long:  {len(f2l)}")
    print(f"  Flat->Short: {len(f2s)}")
    print(f"  Reversals:   {len(revs)}")
    print(f"  Total changes: {len(transitions)}")

    print(f"\n--- Long Entry: 4H Regime ---")
    if f2l:
        h = defaultdict(int)
        for t in f2l:
            h[cl(t["htf"])] += 1
        n = len(f2l)
        for k in ["ABOVE", "IN", "BELOW"]:
            v = h.get(k, 0)
            print(f"  {k:8s}: {v:3d} ({v / n * 100:5.1f}%)")

    print(f"\n--- Short Entry: 4H Regime ---")
    if f2s:
        h = defaultdict(int)
        for t in f2s:
            h[cl(t["htf"])] += 1
        n = len(f2s)
        for k in ["ABOVE", "IN", "BELOW"]:
            v = h.get(k, 0)
            print(f"  {k:8s}: {v:3d} ({v / n * 100:5.1f}%)")

    # Segments
    segs = []
    si, sb, sp = 0, 10000.0, steps[0]["new"]
    for i in range(1, len(steps)):
        if steps[i]["new"] != steps[i - 1]["new"]:
            pnl = steps[i - 1]["bal"] - sb
            segs.append({"pos": sp, "pnl": pnl, "dur": i - si, "htf": cl(steps[si]["htf"])})
            si, sb, sp = i, steps[i - 1]["bal"], steps[i]["new"]

    ws = [s for s in segs if s["pnl"] > 0 and s["pos"] != 0]
    ls = [s for s in segs if s["pnl"] < 0 and s["pos"] != 0]

    print(f"\n--- Win/Loss Segments ---")
    if ws:
        avg_w = np.mean([s["pnl"] for s in ws])
        avg_wd = np.mean([s["dur"] for s in ws])
        best = max(s["pnl"] for s in ws)
        wl = len([s for s in ws if s["pos"] == 1])
        wsh = len([s for s in ws if s["pos"] == -1])
        print(f"  Wins:  {len(ws)} (Long {wl}, Short {wsh})")
        print(f"    Avg PnL: ${avg_w:+.0f}, Avg hold: {avg_wd:.0f} bars ({avg_wd * 0.5:.0f}h)")
        print(f"    Best: ${best:+,.0f}")
    if ls:
        avg_l = np.mean([s["pnl"] for s in ls])
        avg_ld = np.mean([s["dur"] for s in ls])
        worst = min(s["pnl"] for s in ls)
        print(f"  Losses: {len(ls)}")
        print(f"    Avg PnL: ${avg_l:+.0f}, Avg hold: {avg_ld:.0f} bars ({avg_ld * 0.5:.0f}h)")
        print(f"    Worst: ${worst:+,.0f}")

    print(f"\n--- Key Strategy Patterns ---")
    la = sum(1 for t in f2l if t["htf"] > 0.5)
    li = sum(1 for t in f2l if -0.5 <= t["htf"] <= 0.5)
    lb = sum(1 for t in f2l if t["htf"] < -0.5)
    sa = sum(1 for t in f2s if t["htf"] > 0.5)
    si2 = sum(1 for t in f2s if -0.5 <= t["htf"] <= 0.5)
    sb2 = sum(1 for t in f2s if t["htf"] < -0.5)
    print(f"  4H ABOVE: Long {la}, Short {sa}")
    print(f"  4H IN:    Long {li}, Short {si2}")
    print(f"  4H BELOW: Long {lb}, Short {sb2}")

    flat_pct = sum(1 for s in steps if s["new"] == 0) / len(steps) * 100
    print(f"\n  Flat (watching): {flat_pct:.0f}% of time")

    if ws and ls:
        wd = np.mean([s["dur"] for s in ws])
        ld = np.mean([s["dur"] for s in ls])
        ratio = wd / ld if ld > 0 else 0
        print(f"  Win hold: {wd:.0f} bars vs Loss hold: {ld:.0f} bars (ratio {ratio:.1f}x)")
        if ratio > 1.3:
            print(f"  -> 'Let winners run, cut losers short'")

    wr = len(ws) / (len(ws) + len(ls)) * 100 if (ws or ls) else 0
    print(f"  Win rate: {wr:.0f}%")


if __name__ == "__main__":
    main()
