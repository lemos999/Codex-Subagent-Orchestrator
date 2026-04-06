"""Breakthrough Optimization - All dimensions unlocked.

Re-optimize with:
- Wider RSI range (entry not just extreme oversold)
- Higher leverage ceiling (up to 5x)
- Multiple entry patterns (trend pullback, breakout, mean reversion)
- Short selling re-evaluation
- Sortino optimization (penalize downside only)

Usage:
    cd "Projects/Trading Value"
    py -3.12 scripts/breakthrough_optimize.py
"""
from __future__ import annotations

import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import cma
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "cma"])
    import cma

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "sim_1m.sqlite"
SYMBOL = "ETHUSDT"
COMMISSION = 0.0004
SLIPPAGE = 0.0001
INITIAL_BALANCE = 10_000.0

# Walk-forward periods
TRAIN_START = "2021-03-01"
TRAIN_END = "2024-01-01"
VAL_START = "2024-01-01"
VAL_END = "2025-01-01"
TEST_START = "2025-01-01"
TEST_END = "2026-04-01"


def load_15m() -> pd.DataFrame:
    conn = sqlite3.connect(str(DB_PATH))
    df = pd.read_sql_query(
        "SELECT datetime, open, high, low, close, volume "
        "FROM ohlcv_1m WHERE symbol=? ORDER BY datetime",
        conn, params=(SYMBOL,),
    )
    conn.close()
    df["datetime"] = pd.to_datetime(df["datetime"])
    df.set_index("datetime", inplace=True)
    return df.resample("15min").agg({
        "open": "first", "high": "max", "low": "min",
        "close": "last", "volume": "sum",
    }).dropna()


def compute_indicators(df, p):
    c = df["close"].values
    h = df["high"].values
    lo = df["low"].values
    v = df["volume"].values
    n = len(c)

    def sma(arr, w):
        out = np.full(n, np.nan)
        cs = np.cumsum(arr)
        cs = np.insert(cs, 0, 0)
        if n >= w:
            out[w-1:] = (cs[w:] - cs[:-w]) / w
        return out

    ma_f = sma(c, int(p["ma_fast"]))
    ma_s = sma(c, int(p["ma_slow"]))

    delta = np.diff(c, prepend=c[0])
    gain = np.where(delta > 0, delta, 0.0)
    loss_arr = np.where(delta < 0, -delta, 0.0)
    avg_g = sma(gain, 14)
    avg_l = sma(loss_arr, 14)
    rsi = np.full(n, 50.0)
    valid = avg_l > 0
    rsi[valid] = 100 - 100 / (1 + avg_g[valid] / avg_l[valid])

    tr = np.maximum(h[1:] - lo[1:],
                    np.maximum(np.abs(h[1:] - c[:-1]), np.abs(lo[1:] - c[:-1])))
    tr = np.insert(tr, 0, h[0] - lo[0])
    atr = sma(tr, 14)

    vol_ma = sma(v, 20)

    # Donchian for breakout
    don_high = np.full(n, np.nan)
    don_low = np.full(n, np.nan)
    for i in range(20, n):
        don_high[i] = h[i-20:i].max()
        don_low[i] = lo[i-20:i].min()

    # MA pullback distance (how far price is from fast MA)
    ma_dist = np.zeros(n)
    valid_ma = ~np.isnan(ma_f)
    ma_dist[valid_ma] = (c[valid_ma] - ma_f[valid_ma]) / np.maximum(atr[valid_ma], 1e-8)

    return {
        "c": c, "h": h, "lo": lo, "v": v, "n": n,
        "ma_f": ma_f, "ma_s": ma_s, "rsi": rsi, "atr": atr,
        "vol_ma": vol_ma, "don_high": don_high, "don_low": don_low,
        "ma_dist": ma_dist,
    }


def simulate(df, p):
    """Multi-pattern simulation with expanded parameter space."""
    ind = compute_indicators(df, p)
    c, h, lo, v = ind["c"], ind["h"], ind["lo"], ind["v"]
    ma_f, ma_s, rsi, atr = ind["ma_f"], ind["ma_s"], ind["rsi"], ind["atr"]
    vol_ma, don_high, ma_dist = ind["vol_ma"], ind["don_high"], ind["ma_dist"]
    n = ind["n"]

    balance = INITIAL_BALANCE
    peak = INITIAL_BALANCE
    position = 0  # 0=flat, 1=long, -1=short
    entry_price = 0.0
    stop_price = 0.0
    tp_price = 0.0
    trail_active = False
    trail_price = 0.0
    last_trade = -999
    consec_loss = 0

    trade_rets = []
    warmup = max(int(p["ma_slow"]), 200) + 1
    leverage = p["leverage"]

    for i in range(1, n):
        price = c[i]
        bar_h = h[i]
        bar_l = lo[i]

        # Exit logic
        if position != 0:
            exited = False
            exit_p = 0.0

            if position == 1:
                if bar_l <= stop_price:
                    exit_p = stop_price; exited = True
                elif bar_h >= tp_price:
                    exit_p = tp_price; exited = True
                else:
                    pd_ = price - entry_price
                    tt = p["trail_start"] * (atr[i] if not np.isnan(atr[i]) else 1e9)
                    if pd_ >= tt:
                        trail_active = True
                    if trail_active:
                        nt = price - p["trail_step"] * (atr[i] if not np.isnan(atr[i]) else 0)
                        if nt > trail_price:
                            trail_price = nt
                        if bar_l <= trail_price:
                            exit_p = trail_price; exited = True
            elif position == -1:
                if bar_h >= stop_price:
                    exit_p = stop_price; exited = True
                elif bar_l <= tp_price:
                    exit_p = tp_price; exited = True
                else:
                    pd_ = entry_price - price
                    tt = p["trail_start"] * (atr[i] if not np.isnan(atr[i]) else 1e9)
                    if pd_ >= tt:
                        trail_active = True
                    if trail_active:
                        nt = price + p["trail_step"] * (atr[i] if not np.isnan(atr[i]) else 0)
                        if nt < trail_price or trail_price == 0:
                            trail_price = nt
                        if bar_h >= trail_price:
                            exit_p = trail_price; exited = True

            if exited:
                # DD-based sizing
                dd = (peak - balance) / peak * 100 if peak > 0 else 0
                size = 1.0
                if dd > 25: size = 0.25
                elif dd > 15: size = 0.50
                if consec_loss >= 3: size = min(size, 0.50)

                if position == 1:
                    pnl = (exit_p / entry_price - 1.0) * leverage * size
                else:
                    pnl = (1.0 - exit_p / entry_price) * leverage * size
                pnl -= (COMMISSION + SLIPPAGE) * leverage * size
                trade_rets.append(pnl)
                balance *= (1.0 + pnl)
                if pnl < 0:
                    consec_loss += 1
                else:
                    consec_loss = 0
                if balance > peak:
                    peak = balance
                if balance <= 0:
                    break
                position = 0
                last_trade = i

        # Entry logic - MULTI-PATTERN
        if position == 0 and i >= warmup:
            if i - last_trade < int(p["cooldown"]):
                continue
            cur_atr = atr[i] if not np.isnan(atr[i]) else 0.0
            if cur_atr <= 0:
                continue

            mf = ma_f[i]
            ms = ma_s[i]
            if np.isnan(mf) or np.isnan(ms):
                continue

            cur_vm = vol_ma[i] if not np.isnan(vol_ma[i]) else 0.0
            vol_ok = v[i] > p["vol_filter"] * cur_vm if cur_vm > 0 else False

            uptrend = mf > ms
            downtrend = mf < ms

            # === PATTERN 1: Trend + RSI pullback (original, now with relaxed RSI) ===
            if uptrend and rsi[i] < p["rsi_entry_long"] and vol_ok:
                position = 1
                entry_price = price * (1 + COMMISSION + SLIPPAGE)
                stop_price = price - p["stop_atr"] * cur_atr
                tp_price = price + p["tp_atr"] * cur_atr
                trail_active = False
                trail_price = stop_price
                last_trade = i
                continue

            # === PATTERN 2: MA pullback entry (price dips to fast MA in uptrend) ===
            if uptrend and p.get("enable_pullback", 0) > 0.5:
                pullback_dist = ma_dist[i]  # negative = below MA
                if -p["pullback_depth"] < pullback_dist < 0 and vol_ok:
                    position = 1
                    entry_price = price * (1 + COMMISSION + SLIPPAGE)
                    stop_price = price - p["stop_atr"] * cur_atr
                    tp_price = price + p["tp_atr"] * cur_atr
                    trail_active = False
                    trail_price = stop_price
                    last_trade = i
                    continue

            # === PATTERN 3: Breakout (price breaks Donchian high with volume) ===
            if p.get("enable_breakout", 0) > 0.5:
                if not np.isnan(don_high[i]) and bar_h > don_high[i] and vol_ok and uptrend:
                    position = 1
                    entry_price = price * (1 + COMMISSION + SLIPPAGE)
                    stop_price = price - p["stop_atr"] * cur_atr * 1.5  # wider stop for breakout
                    tp_price = price + p["tp_atr"] * cur_atr * 1.5
                    trail_active = False
                    trail_price = stop_price
                    last_trade = i
                    continue

            # === PATTERN 4: Short in downtrend (if enabled) ===
            if p.get("allow_short", 0) > 0.5 and downtrend:
                if rsi[i] > p.get("rsi_entry_short", 72) and vol_ok:
                    position = -1
                    entry_price = price * (1 - COMMISSION - SLIPPAGE)
                    stop_price = price + p["stop_atr"] * cur_atr
                    tp_price = price - p["tp_atr"] * cur_atr
                    trail_active = False
                    trail_price = stop_price
                    last_trade = i
                    continue

    # Stats
    total_ret = (balance / INITIAL_BALANCE - 1.0) * 100
    if not trade_rets:
        return {"ret": 0, "sharpe": -10, "sortino": -10, "dd": 0, "trades": 0,
                "wr": 0, "pf": 0, "balance": INITIAL_BALANCE}

    rets = np.array(trade_rets)
    years = n / 35040.0

    # Sortino ratio (penalize downside only)
    downside = rets[rets < 0]
    downside_std = downside.std() if len(downside) > 1 else 1e-8
    sortino = rets.mean() / max(downside_std, 1e-8) * np.sqrt(365 * 24 * 4)

    sharpe = rets.mean() / max(rets.std(), 1e-8) * np.sqrt(365 * 24 * 4)

    eq = np.cumprod(1 + rets) * INITIAL_BALANCE
    peak_eq = np.maximum.accumulate(eq)
    dd = ((peak_eq - eq) / peak_eq * 100).max()

    wins = (rets > 0).sum()
    wr = wins / len(rets) * 100
    gross_w = rets[rets > 0].sum()
    gross_l = abs(rets[rets < 0].sum())
    pf = gross_w / max(gross_l, 1e-8)

    return {"ret": total_ret, "sharpe": sharpe, "sortino": sortino, "dd": dd,
            "trades": len(rets), "wr": wr, "pf": pf, "balance": balance}


def vector_to_params(x):
    """Convert CMA-ES vector to strategy params dict."""
    return {
        "ma_fast": max(5, min(60, int(round(x[0])))),
        "ma_slow": max(50, min(300, int(round(x[1])))),
        "rsi_entry_long": max(25, min(50, x[2])),        # RELAXED: up to 50 (was 28)
        "rsi_entry_short": max(50, min(80, x[3])),
        "vol_filter": max(1.0, min(4.0, x[4])),
        "stop_atr": max(1.0, min(5.0, x[5])),
        "tp_atr": max(1.5, min(8.0, x[6])),
        "trail_start": max(1.0, min(6.0, x[7])),
        "trail_step": max(0.2, min(2.0, x[8])),
        "cooldown": max(1, min(20, int(round(x[9])))),
        "leverage": max(1.0, min(5.0, x[10])),            # UP TO 5x
        "enable_pullback": 1.0 if x[11] > 0.5 else 0.0,  # pattern toggle
        "pullback_depth": max(0.5, min(3.0, x[12])),
        "enable_breakout": 1.0 if x[13] > 0.5 else 0.0,  # pattern toggle
        "allow_short": 1.0 if x[14] > 0.5 else 0.0,      # short toggle
    }


def objective(x, df_train):
    p = vector_to_params(x)
    if p["ma_fast"] >= p["ma_slow"]:
        return 10.0
    r = simulate(df_train, p)
    if r["trades"] < 20:
        return 10.0  # need enough trades
    # Optimize SORTINO (not Sharpe) - reward upside, penalize downside
    return -r["sortino"]


def main():
    print("=" * 70)
    print("  BREAKTHROUGH OPTIMIZATION - All Dimensions Unlocked")
    print("  Sortino optimization | Multi-pattern | Short enabled")
    print("  Leverage up to 5x | RSI relaxed to 50")
    print("=" * 70)

    t0 = time.time()
    df = load_15m()
    print(f"  Data: {len(df)} bars ({time.time()-t0:.1f}s)")

    # Split
    train = df[TRAIN_START:TRAIN_END]
    val = df[VAL_START:VAL_END]
    test = df[TEST_START:TEST_END]
    print(f"  Train: {len(train)} | Val: {len(val)} | Test: {len(test)}")

    # CMA-ES
    # Initial guess (based on previous best + expanded)
    x0 = [
        21,     # ma_fast
        95,     # ma_slow
        35,     # rsi_entry_long (RELAXED from 28)
        72,     # rsi_entry_short
        2.0,    # vol_filter (RELAXED from 2.89)
        3.0,    # stop_atr
        4.0,    # tp_atr
        4.0,    # trail_start
        0.5,    # trail_step
        4,      # cooldown
        2.5,    # leverage (HIGHER from 1.6)
        1.0,    # enable_pullback
        1.5,    # pullback_depth
        0.0,    # enable_breakout
        0.0,    # allow_short
    ]

    bounds = [
        [5, 50, 25, 50, 1.0, 1.0, 1.5, 1.0, 0.2, 1, 1.0, 0, 0.5, 0, 0],      # lower
        [60, 300, 50, 80, 4.0, 5.0, 8.0, 6.0, 2.0, 20, 5.0, 1, 3.0, 1, 1],     # upper
    ]

    print(f"\n  CMA-ES: 15 params, popsize=50, maxiter=300")
    print(f"  Optimizing Sortino ratio on train period...")

    es = cma.CMAEvolutionStrategy(x0, 0.3, {
        "popsize": 50,
        "maxiter": 150,
        "bounds": bounds,
        "verbose": -1,
    })

    gen = 0
    best_sortino = -999
    while not es.stop():
        solutions = es.ask()
        fitnesses = [objective(s, train) for s in solutions]
        es.tell(solutions, fitnesses)
        gen += 1
        cur_best = -min(fitnesses)
        if cur_best > best_sortino:
            best_sortino = cur_best
        if gen % 30 == 0:
            p = vector_to_params(es.result.xbest)
            r = simulate(train, p)
            print(f"    Gen {gen:4d} | Sortino: {best_sortino:.2f} | "
                  f"Ret: {r['ret']:+.1f}% | Trades: {r['trades']} | "
                  f"Lev: {p['leverage']:.1f}x | RSI<{p['rsi_entry_long']:.0f}")

    best_x = es.result.xbest
    best_p = vector_to_params(best_x)

    # Results
    print(f"\n{'='*70}")
    print(f"  RESULTS")
    print(f"{'='*70}")

    print(f"\n  Best Parameters:")
    print(f"    MA: {best_p['ma_fast']}/{best_p['ma_slow']}")
    print(f"    RSI Long entry: < {best_p['rsi_entry_long']:.1f}")
    print(f"    RSI Short entry: > {best_p['rsi_entry_short']:.1f}")
    print(f"    Vol filter: {best_p['vol_filter']:.2f}x")
    print(f"    Stop: {best_p['stop_atr']:.2f}*ATR | TP: {best_p['tp_atr']:.2f}*ATR")
    print(f"    Trail: {best_p['trail_start']:.2f}/{best_p['trail_step']:.2f}*ATR")
    print(f"    Cooldown: {best_p['cooldown']} bars")
    print(f"    Leverage: {best_p['leverage']:.1f}x")
    print(f"    Pullback: {'ON' if best_p['enable_pullback'] > 0.5 else 'OFF'}")
    print(f"    Breakout: {'ON' if best_p['enable_breakout'] > 0.5 else 'OFF'}")
    print(f"    Short: {'ON' if best_p['allow_short'] > 0.5 else 'OFF'}")

    for label, data in [("Train", train), ("Val", val), ("Test", test)]:
        r = simulate(data, best_p)
        print(f"\n  [{label}]")
        print(f"    Return: {r['ret']:+.1f}% | Sortino: {r['sortino']:.2f} | Sharpe: {r['sharpe']:.2f}")
        print(f"    DD: -{r['dd']:.1f}% | Trades: {r['trades']} | WR: {r['wr']:.0f}% | PF: {r['pf']:.2f}")

    # Compare with previous best
    prev_p = {
        "ma_fast": 21, "ma_slow": 95, "rsi_entry_long": 28.3, "rsi_entry_short": 72,
        "vol_filter": 2.89, "stop_atr": 3.89, "tp_atr": 3.75,
        "trail_start": 4.89, "trail_step": 0.31, "cooldown": 5,
        "leverage": 1.6, "enable_pullback": 0, "pullback_depth": 1.5,
        "enable_breakout": 0, "allow_short": 0,
    }

    print(f"\n  === vs Previous Best (on Test) ===")
    r_prev = simulate(test, prev_p)
    r_new = simulate(test, best_p)
    print(f"  Previous: Ret {r_prev['ret']:+.1f}% | Sharpe {r_prev['sharpe']:.2f} | DD -{r_prev['dd']:.1f}% | {r_prev['trades']} trades")
    print(f"  New:      Ret {r_new['ret']:+.1f}% | Sharpe {r_new['sharpe']:.2f} | DD -{r_new['dd']:.1f}% | {r_new['trades']} trades")
    improvement = r_new['ret'] - r_prev['ret']
    print(f"  Improvement: {improvement:+.1f}%p")

    # Save best params
    import json
    params_path = Path(__file__).resolve().parent.parent / "data" / "breakthrough_params.json"
    params_path.write_text(json.dumps(best_p, indent=2), encoding="utf-8")
    print(f"\n  Params saved: {params_path}")
    print(f"  Total time: {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
