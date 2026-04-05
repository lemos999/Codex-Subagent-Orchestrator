"""V3 Ultra-simple strategies - minimum parameters, maximum robustness.

BTC: Daily trend filter (above/below 50-day MA) + 4H RSI entry
NVDA/AMZN: Daily golden cross timing + ATR trailing stop

Philosophy: 2-3 params only. If it can't work with 2-3 params, it won't work with 15.

Usage:
    py -3.12 scripts/optimize_v3.py --asset BTC
    py -3.12 scripts/optimize_v3.py --asset NVDA
    py -3.12 scripts/optimize_v3.py --asset AMZN
"""
from __future__ import annotations
import argparse, json, subprocess, sys, time, sqlite3
from pathlib import Path
import numpy as np, pandas as pd

try:
    import yfinance as yf
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "yfinance"])
    import yfinance as yf

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "sim_1m.sqlite"
INITIAL = 10_000.0


def load_btc_4h():
    conn = sqlite3.connect(str(DB_PATH))
    df = pd.read_sql_query(
        "SELECT datetime, open, high, low, close, volume "
        "FROM ohlcv_1m WHERE symbol='BTCUSDT' ORDER BY datetime", conn)
    conn.close()
    df["datetime"] = pd.to_datetime(df["datetime"])
    df.set_index("datetime", inplace=True)
    return df.resample("4h").agg({"open":"first","high":"max","low":"min","close":"last","volume":"sum"}).dropna()


def load_stock_daily(symbol):
    df = yf.Ticker(symbol).history(period="5y", interval="1d")
    df = df.rename(columns={"Open":"open","High":"high","Low":"low","Close":"close","Volume":"volume"})
    return df[["open","high","low","close","volume"]].dropna()


def sma(arr, w):
    n = len(arr); out = np.full(n, np.nan)
    cs = np.cumsum(arr); cs = np.insert(cs, 0, 0)
    if n >= w: out[w-1:] = (cs[w:] - cs[:-w]) / w
    return out


# ============================================================================
#  BTC: 4H bars. Only 2 params: MA period for trend, RSI threshold for entry.
#  Rule: Buy when price > MA AND RSI < threshold (pullback in uptrend).
#  Exit: price < MA OR trailing stop (2x ATR).
# ============================================================================
def btc_strategy(df, ma_period, rsi_thresh):
    c = df["close"].values; h = df["high"].values; lo = df["low"].values
    n = len(c)
    ma = sma(c, ma_period)
    delta = np.diff(c, prepend=c[0])
    gain = np.where(delta>0, delta, 0.0); loss = np.where(delta<0, -delta, 0.0)
    avg_g = sma(gain, 14); avg_l = sma(loss, 14)
    rsi = np.full(n, 50.0); valid = avg_l > 0
    rsi[valid] = 100 - 100 / (1 + avg_g[valid] / avg_l[valid])
    tr = np.maximum(h[1:]-lo[1:], np.maximum(np.abs(h[1:]-c[:-1]), np.abs(lo[1:]-c[:-1])))
    tr = np.insert(tr, 0, h[0]-lo[0]); atr = sma(tr, 14)

    bal = INITIAL; peak = INITIAL; pos = 0; entry = 0.0; trail = 0.0
    rets = []; last_t = -999; comm = 0.0005; lev = 1.5

    for i in range(ma_period+1, n):
        cur_ma = ma[i]; cur_atr = atr[i]
        if np.isnan(cur_ma) or np.isnan(cur_atr) or cur_atr <= 0: continue

        # Exit
        if pos == 1:
            # Trailing stop: 2x ATR
            new_trail = c[i] - 2.0 * cur_atr
            if new_trail > trail: trail = new_trail
            # Exit on: trailing stop OR trend reversal (price < MA)
            if lo[i] <= trail or c[i] < cur_ma:
                exit_p = max(trail, lo[i]) if lo[i] <= trail else c[i]
                dd = (peak-bal)/peak*100 if peak>0 else 0
                sz = 0.25 if dd>25 else (0.5 if dd>15 else 1.0)
                pnl = (exit_p/entry - 1) * lev * sz - comm * lev * sz
                rets.append(pnl); bal *= (1+pnl)
                if bal<=0: break
                if bal>peak: peak=bal
                pos=0; last_t=i

        # Entry: price > MA AND RSI pullback
        if pos == 0 and i - last_t >= 3:
            if c[i] > cur_ma and rsi[i] < rsi_thresh:
                pos=1; entry=c[i]; trail=c[i]-2.0*cur_atr; last_t=i

    # Force close
    if pos == 1:
        pnl = (c[-1]/entry - 1) * lev - comm * lev
        rets.append(pnl); bal *= (1+pnl)

    return _calc_stats(rets, bal, len(c), 6*365)  # 4H: 6 bars/day * 365


# ============================================================================
#  NVDA/AMZN: Daily. Only 2 params: fast MA, slow MA.
#  Rule: Buy when fast > slow (golden cross). Sell when fast < slow (death cross).
#  Trailing stop: 2x ATR to protect gains.
# ============================================================================
def stock_strategy(df, ma_fast, ma_slow):
    c = df["close"].values; h = df["high"].values; lo = df["low"].values
    n = len(c)
    mf = sma(c, ma_fast); ms = sma(c, ma_slow)
    tr = np.maximum(h[1:]-lo[1:], np.maximum(np.abs(h[1:]-c[:-1]), np.abs(lo[1:]-c[:-1])))
    tr = np.insert(tr, 0, h[0]-lo[0]); atr = sma(tr, 14)

    bal = INITIAL; peak = INITIAL; pos = 0; entry = 0.0; trail = 0.0
    rets = []; comm = 0.001  # stock commission

    for i in range(ma_slow+1, n):
        if np.isnan(mf[i]) or np.isnan(ms[i]) or np.isnan(atr[i]): continue
        cur_atr = atr[i]

        # Exit
        if pos == 1:
            new_trail = c[i] - 2.0 * cur_atr
            if new_trail > trail: trail = new_trail
            # Death cross OR trailing stop
            if mf[i] < ms[i] or lo[i] <= trail:
                exit_p = max(trail, lo[i]) if lo[i] <= trail else c[i]
                dd = (peak-bal)/peak*100 if peak>0 else 0
                sz = 0.25 if dd>25 else (0.5 if dd>15 else 1.0)
                pnl = (exit_p/entry - 1) * sz - comm * sz
                rets.append(pnl); bal *= (1+pnl)
                if bal<=0: break
                if bal>peak: peak=bal
                pos=0

        # Golden cross entry
        if pos == 0 and mf[i] > ms[i] and mf[i-1] <= ms[i-1]:
            pos=1; entry=c[i]; trail=c[i]-2.0*cur_atr

    if pos == 1:
        pnl = (c[-1]/entry - 1) - comm
        rets.append(pnl); bal *= (1+pnl)

    return _calc_stats(rets, bal, len(c), 252)


def _calc_stats(rets, bal, n_bars, bars_yr):
    if not rets:
        return {"ret":0,"sharpe":-10,"dd":0,"trades":0,"wr":0,"pf":0,"bal":INITIAL}
    r = np.array(rets)
    ret = (bal/INITIAL-1)*100
    sharpe = r.mean()/max(r.std(),1e-8)*np.sqrt(bars_yr)
    eq = np.cumprod(1+r)*INITIAL
    dd = ((np.maximum.accumulate(eq)-eq)/np.maximum.accumulate(eq)*100).max()
    wins = (r>0).sum(); wr = wins/len(r)*100
    gw = r[r>0].sum(); gl = abs(r[r<0].sum())
    return {"ret":ret,"sharpe":sharpe,"dd":dd,"trades":len(r),"wr":wr,"pf":gw/max(gl,1e-8),"bal":bal}


def grid_search_btc(df_train, df_val, df_test):
    """Exhaustive grid over 2 params - no CMA-ES needed for 2 params."""
    print("\n  Grid search: MA period x RSI threshold")
    best = None; best_val = -999
    results = []

    for ma_p in [20, 30, 40, 50, 60, 80, 100, 120, 150, 200]:
        for rsi_t in [30, 33, 35, 38, 40, 42, 45, 48, 50]:
            r_train = btc_strategy(df_train, ma_p, rsi_t)
            r_val = btc_strategy(df_val, ma_p, rsi_t)
            if r_train["trades"] < 10 or r_val["trades"] < 5: continue
            score = r_val["sharpe"]
            results.append((ma_p, rsi_t, r_train, r_val, score))
            if score > best_val:
                best_val = score
                best = (ma_p, rsi_t)

    if not best:
        print("  No valid parameter combination found!")
        return

    # Top 5
    results.sort(key=lambda x: -x[4])
    print(f"\n  Top 5 (by Validation Sharpe):")
    print(f"  {'MA':>5} {'RSI':>5} {'Tr Ret%':>8} {'Tr Shp':>7} {'Va Ret%':>8} {'Va Shp':>7} {'Va Trades':>9}")
    for ma_p, rsi_t, r_tr, r_va, _ in results[:5]:
        print(f"  {ma_p:5d} {rsi_t:5d} {r_tr['ret']:+8.1f} {r_tr['sharpe']:7.2f} "
              f"{r_va['ret']:+8.1f} {r_va['sharpe']:7.2f} {r_va['trades']:9d}")

    # Best on test
    ma_p, rsi_t = best
    r_tr = btc_strategy(df_train, ma_p, rsi_t)
    r_va = btc_strategy(df_val, ma_p, rsi_t)
    r_te = btc_strategy(df_test, ma_p, rsi_t)

    print(f"\n  Best: MA={ma_p}, RSI<{rsi_t}")
    print(f"  [Train] Ret={r_tr['ret']:+.1f}% Sharpe={r_tr['sharpe']:.2f} DD=-{r_tr['dd']:.1f}% Trades={r_tr['trades']} WR={r_tr['wr']:.0f}%")
    print(f"  [Val  ] Ret={r_va['ret']:+.1f}% Sharpe={r_va['sharpe']:.2f} DD=-{r_va['dd']:.1f}% Trades={r_va['trades']} WR={r_va['wr']:.0f}%")
    print(f"  [Test ] Ret={r_te['ret']:+.1f}% Sharpe={r_te['sharpe']:.2f} DD=-{r_te['dd']:.1f}% Trades={r_te['trades']} WR={r_te['wr']:.0f}%")

    passed = r_va["ret"] > 0 and r_te["ret"] > 0 and r_te["trades"] >= 3
    print(f"\n  VERDICT: {'PASS' if passed else 'FAIL'}")

    # Also show buy & hold comparison
    bh_ret = (df_test["close"].iloc[-1] / df_test["close"].iloc[0] - 1) * 100
    print(f"  Buy&Hold (test): {bh_ret:+.1f}%")
    if passed:
        print(f"  Strategy vs B&H: {r_te['ret']-bh_ret:+.1f}%p")

    out = {"asset": "BTC", "strategy": "4h_trend_pullback", "ma": ma_p, "rsi": rsi_t,
           "passed": bool(passed), "test_ret": round(r_te["ret"], 2), "test_sharpe": round(r_te["sharpe"], 2),
           "bh_ret": round(bh_ret, 2)}
    (DATA_DIR / "params_btc_v3.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


def grid_search_stock(symbol, df_train, df_val, df_test):
    """Grid search over MA fast/slow."""
    print(f"\n  Grid search: MA fast x MA slow")
    best = None; best_val = -999
    results = []

    for fast in [5, 10, 15, 20, 30, 40, 50]:
        for slow in [20, 30, 50, 80, 100, 150, 200]:
            if fast >= slow: continue
            r_tr = stock_strategy(df_train, fast, slow)
            r_va = stock_strategy(df_val, fast, slow)
            if r_tr["trades"] < 3 or r_va["trades"] < 2: continue
            score = r_va["sharpe"]
            results.append((fast, slow, r_tr, r_va, score))
            if score > best_val:
                best_val = score; best = (fast, slow)

    if not best:
        print("  No valid combination!")
        return

    results.sort(key=lambda x: -x[4])
    print(f"\n  Top 5:")
    print(f"  {'Fast':>5} {'Slow':>5} {'Tr Ret%':>8} {'Va Ret%':>8} {'Va Shp':>7} {'Va Trades':>9}")
    for f, s, r_tr, r_va, _ in results[:5]:
        print(f"  {f:5d} {s:5d} {r_tr['ret']:+8.1f} {r_va['ret']:+8.1f} {r_va['sharpe']:7.2f} {r_va['trades']:9d}")

    fast, slow = best
    r_tr = stock_strategy(df_train, fast, slow)
    r_va = stock_strategy(df_val, fast, slow)
    r_te = stock_strategy(df_test, fast, slow)

    print(f"\n  Best: MA {fast}/{slow}")
    print(f"  [Train] Ret={r_tr['ret']:+.1f}% Sharpe={r_tr['sharpe']:.2f} DD=-{r_tr['dd']:.1f}% Trades={r_tr['trades']} WR={r_tr['wr']:.0f}%")
    print(f"  [Val  ] Ret={r_va['ret']:+.1f}% Sharpe={r_va['sharpe']:.2f} DD=-{r_va['dd']:.1f}% Trades={r_va['trades']} WR={r_va['wr']:.0f}%")
    print(f"  [Test ] Ret={r_te['ret']:+.1f}% Sharpe={r_te['sharpe']:.2f} DD=-{r_te['dd']:.1f}% Trades={r_te['trades']} WR={r_te['wr']:.0f}%")

    bh_ret = (df_test["close"].iloc[-1] / df_test["close"].iloc[0] - 1) * 100
    passed = r_va["ret"] > 0 and r_te["ret"] > 0 and r_te["trades"] >= 2
    print(f"\n  VERDICT: {'PASS' if passed else 'FAIL'}")
    print(f"  Buy&Hold (test): {bh_ret:+.1f}%")
    if r_te["ret"] > 0:
        print(f"  Strategy vs B&H: {r_te['ret']-bh_ret:+.1f}%p")
        print(f"  Strategy DD: -{r_te['dd']:.1f}% (B&H DD likely worse)")

    out = {"asset": symbol, "strategy": "golden_cross_trail", "ma_fast": fast, "ma_slow": slow,
           "passed": bool(passed), "test_ret": round(r_te["ret"], 2), "test_sharpe": round(r_te["sharpe"], 2),
           "bh_ret": round(bh_ret, 2)}
    (DATA_DIR / f"params_{symbol.lower()}_v3.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset", required=True, choices=["BTC", "NVDA", "AMZN"])
    args = parser.parse_args()
    asset = args.asset

    print(f"{'='*60}")
    print(f"  {asset} V3 Ultra-Simple Optimization")
    print(f"  Philosophy: 2 params only. Overfitting impossible.")
    print(f"{'='*60}")

    t0 = time.time()

    if asset == "BTC":
        df = load_btc_4h()
        print(f"  Data: {len(df)} 4H bars ({df.index[0]} ~ {df.index[-1]})")
        n = len(df)
        train = df.iloc[:int(n*0.6)]
        val = df.iloc[int(n*0.6):int(n*0.8)]
        test = df.iloc[int(n*0.8):]
        print(f"  Train: {len(train)} | Val: {len(val)} | Test: {len(test)}")
        grid_search_btc(train, val, test)
    else:
        df = load_stock_daily(asset)
        print(f"  Data: {len(df)} daily bars ({df.index[0].date()} ~ {df.index[-1].date()})")
        n = len(df)
        train = df.iloc[:int(n*0.6)]
        val = df.iloc[int(n*0.6):int(n*0.8)]
        test = df.iloc[int(n*0.8):]
        print(f"  Train: {len(train)} | Val: {len(val)} | Test: {len(test)}")
        grid_search_stock(asset, train, val, test)

    print(f"\n  Time: {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
