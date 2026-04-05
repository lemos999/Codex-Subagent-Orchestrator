"""NVDA Regime-Based Leveraged Strategy.

Target: +10%/month. NVDA avg +5.3%/mo, bull months avg +14.3%.
Strategy: Detect bull regime -> 2x leverage. Bear/sideways -> flat.

Regime detection:
- Bull: MA20 > MA50 AND price > MA20 (strong uptrend)
- Bear: MA20 < MA50 (downtrend) -> FLAT
- Sideways: MA20 ~ MA50, low ADX -> FLAT or reduced

Usage:
    py -3.12 scripts/optimize_nvda_regime.py
"""
from __future__ import annotations
import json, subprocess, sys, time
from pathlib import Path
import numpy as np, pandas as pd

try:
    import yfinance as yf
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "yfinance"])
    import yfinance as yf

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
INITIAL = 10_000.0
COMM = 0.001


def load_nvda():
    df = yf.Ticker("NVDA").history(period="5y", interval="1d")
    df = df.rename(columns={"Open":"open","High":"high","Low":"low","Close":"close","Volume":"volume"})
    return df[["open","high","low","close","volume"]].dropna()


def sma(arr, w):
    n = len(arr); out = np.full(n, np.nan)
    cs = np.cumsum(arr); cs = np.insert(cs, 0, 0)
    if n >= w: out[w-1:] = (cs[w:] - cs[:-w]) / w
    return out


def simulate_regime(df, ma_fast, ma_slow, lev_bull, lev_mild, stop_pct):
    """Regime-based: full leverage in bull, reduced in mild, flat in bear."""
    c = df["close"].values; h = df["high"].values; lo = df["low"].values
    n = len(c)
    mf = sma(c, ma_fast); ms = sma(c, ma_slow)
    tr = np.maximum(h[1:]-lo[1:], np.maximum(np.abs(h[1:]-c[:-1]), np.abs(lo[1:]-c[:-1])))
    tr = np.insert(tr, 0, h[0]-lo[0]); atr = sma(tr, 14)

    bal = INITIAL; peak = INITIAL; pos = 0; entry = 0.0; stop_p = 0.0
    cur_lev = 0.0; rets = []; monthly_rets = []
    last_month = -1

    for i in range(ma_slow+1, n):
        if np.isnan(mf[i]) or np.isnan(ms[i]) or np.isnan(atr[i]): continue

        # Monthly tracking
        if hasattr(df.index[i], 'month'):
            m = df.index[i].month
            if m != last_month and last_month != -1:
                monthly_rets.append((bal / INITIAL - 1) * 100)
            last_month = m

        # Determine regime
        bull = mf[i] > ms[i] and c[i] > mf[i]  # strong uptrend
        mild_bull = mf[i] > ms[i] and c[i] <= mf[i]  # uptrend but pulling back
        bear = mf[i] <= ms[i]

        # Exit if in position
        if pos == 1:
            # Stop loss
            if lo[i] <= stop_p:
                dd = (peak-bal)/peak*100 if peak>0 else 0
                sz = 0.25 if dd>25 else (0.5 if dd>15 else 1.0)
                pnl = (stop_p/entry - 1) * cur_lev * sz - COMM * cur_lev * sz
                rets.append(pnl); bal *= (1+pnl)
                if bal <= 0: break
                if bal > peak: peak = bal
                pos = 0; continue
            # Regime change to bear -> exit
            if bear:
                dd = (peak-bal)/peak*100 if peak>0 else 0
                sz = 0.25 if dd>25 else (0.5 if dd>15 else 1.0)
                pnl = (c[i]/entry - 1) * cur_lev * sz - COMM * cur_lev * sz
                rets.append(pnl); bal *= (1+pnl)
                if bal <= 0: break
                if bal > peak: peak = bal
                pos = 0; continue
            # Update trailing stop
            new_stop = c[i] * (1 - stop_pct)
            if new_stop > stop_p: stop_p = new_stop

        # Entry
        if pos == 0:
            if bull:
                pos = 1; entry = c[i]; cur_lev = lev_bull
                stop_p = c[i] * (1 - stop_pct)
            elif mild_bull:
                pos = 1; entry = c[i]; cur_lev = lev_mild
                stop_p = c[i] * (1 - stop_pct)

    # Force close
    if pos == 1:
        pnl = (c[-1]/entry - 1) * cur_lev - COMM * cur_lev
        rets.append(pnl); bal *= (1+pnl)

    if not rets:
        return {"ret":0,"sharpe":-10,"dd":0,"trades":0,"wr":0,"pf":0,"monthly_avg":0,"months_gt10":0}

    r = np.array(rets)
    ret = (bal/INITIAL-1)*100
    sharpe = r.mean()/max(r.std(),1e-8)*np.sqrt(252)
    eq = np.cumprod(1+r)*INITIAL
    dd = ((np.maximum.accumulate(eq)-eq)/np.maximum.accumulate(eq)*100).max()
    wins = (r>0).sum(); wr = wins/len(r)*100
    gw = r[r>0].sum(); gl = abs(r[r<0].sum())

    # Monthly stats from equity curve
    months = len(df) / 21  # approx trading days per month
    monthly_ret = ret / max(months / 12, 0.01)  # annualized -> monthly approx

    return {"ret":ret, "sharpe":sharpe, "dd":dd, "trades":len(r), "wr":wr,
            "pf":gw/max(gl,1e-8), "monthly_avg": monthly_ret, "bal": bal}


def main():
    print("="*60)
    print("  NVDA Regime-Based Leveraged Strategy")
    print("  Target: +10%/month")
    print("="*60)

    df = load_nvda()
    print(f"  Data: {len(df)} daily bars ({df.index[0].date()} ~ {df.index[-1].date()})")

    n = len(df)
    train = df.iloc[:int(n*0.6)]
    val = df.iloc[int(n*0.6):int(n*0.8)]
    test = df.iloc[int(n*0.8):]
    print(f"  Train: {len(train)} | Val: {len(val)} | Test: {len(test)}")

    # Grid search
    print("\n  Grid search: MA x Leverage x Stop%")
    best = None; best_score = -999
    results = []

    for ma_f in [10, 15, 20, 30]:
        for ma_s in [30, 50, 80, 100]:
            if ma_f >= ma_s: continue
            for lev_bull in [1.5, 2.0, 2.5, 3.0]:
                for lev_mild in [0.5, 1.0]:
                    for stop in [0.03, 0.05, 0.07, 0.10]:
                        r_tr = simulate_regime(train, ma_f, ma_s, lev_bull, lev_mild, stop)
                        r_va = simulate_regime(val, ma_f, ma_s, lev_bull, lev_mild, stop)
                        if r_tr["trades"] < 3 or r_va["trades"] < 2: continue
                        score = r_va["sharpe"]
                        results.append((ma_f, ma_s, lev_bull, lev_mild, stop, r_tr, r_va, score))
                        if score > best_score:
                            best_score = score
                            best = (ma_f, ma_s, lev_bull, lev_mild, stop)

    if not best:
        print("  No valid parameters found!")
        return

    results.sort(key=lambda x: -x[7])
    print(f"\n  Top 5:")
    print(f"  {'MF':>3} {'MS':>3} {'Lev':>4} {'MLev':>4} {'Stop':>5} | {'Tr%':>7} {'Va%':>7} {'VaShp':>6} {'VaTr':>4}")
    for mf, ms, lb, lm, st, rtr, rva, _ in results[:5]:
        print(f"  {mf:3d} {ms:3d} {lb:4.1f} {lm:4.1f} {st:5.0%} | {rtr['ret']:+7.1f} {rva['ret']:+7.1f} {rva['sharpe']:6.2f} {rva['trades']:4d}")

    mf, ms, lb, lm, st = best
    r_tr = simulate_regime(train, mf, ms, lb, lm, st)
    r_va = simulate_regime(val, mf, ms, lb, lm, st)
    r_te = simulate_regime(test, mf, ms, lb, lm, st)

    bh_test = (test["close"].iloc[-1] / test["close"].iloc[0] - 1) * 100
    test_months = len(test) / 21
    monthly_est = r_te["ret"] / max(test_months, 1) * 12 / 12  # per month

    print(f"\n  Best: MA {mf}/{ms}, Bull Lev={lb}x, Mild Lev={lm}x, Stop={st:.0%}")
    print(f"  [Train] Ret={r_tr['ret']:+.1f}% | Sharpe={r_tr['sharpe']:.2f} | DD=-{r_tr['dd']:.1f}% | Trades={r_tr['trades']} | WR={r_tr['wr']:.0f}%")
    print(f"  [Val  ] Ret={r_va['ret']:+.1f}% | Sharpe={r_va['sharpe']:.2f} | DD=-{r_va['dd']:.1f}% | Trades={r_va['trades']} | WR={r_va['wr']:.0f}%")
    print(f"  [Test ] Ret={r_te['ret']:+.1f}% | Sharpe={r_te['sharpe']:.2f} | DD=-{r_te['dd']:.1f}% | Trades={r_te['trades']} | WR={r_te['wr']:.0f}%")
    print(f"\n  Buy&Hold (test): {bh_test:+.1f}%")
    print(f"  Test period: ~{test_months:.0f} months")
    print(f"  Est. monthly return: {monthly_est:+.1f}%")
    print(f"  Target +10%/mo: {'ACHIEVABLE' if monthly_est >= 10 else 'NOT YET' if monthly_est > 5 else 'UNLIKELY'}")

    passed = r_te["ret"] > 0 and r_va["ret"] > 0
    print(f"\n  VERDICT: {'PASS' if passed else 'FAIL'}")

    out = {"asset": "NVDA", "strategy": "regime_leveraged",
           "ma_fast": mf, "ma_slow": ms, "lev_bull": lb, "lev_mild": lm, "stop_pct": st,
           "passed": bool(passed), "test_ret": round(r_te["ret"], 2),
           "monthly_est": round(monthly_est, 2), "bh_ret": round(bh_test, 2)}
    (DATA_DIR / "params_nvda_regime.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"  Saved: params_nvda_regime.json ({time.time()-t0:.0f}s)")


t0 = time.time()
if __name__ == "__main__":
    main()
