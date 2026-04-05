"""BTC/ETH Pairs Trading - Market Neutral Strategy.

Instead of predicting BTC direction (proven impossible with 51.5%),
trade the ETH/BTC ratio mean-reversion.

When ETH/BTC deviates from its moving average, bet on reversion.
Delta-neutral: long one, short the other. Market direction irrelevant.

Usage:
    py -3.12 scripts/pairs_btc_eth.py
"""
from __future__ import annotations
import json, sqlite3, sys, time
from pathlib import Path
import numpy as np, pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "sim_1m.sqlite"
INITIAL = 10_000.0
COMM = 0.0005  # per side


def load_pair_4h():
    """Load BTC and ETH 4H data, compute ratio."""
    conn = sqlite3.connect(str(DB_PATH))
    btc = pd.read_sql_query(
        "SELECT datetime, close as btc_close FROM ohlcv_1m WHERE symbol='BTCUSDT' ORDER BY datetime", conn)
    eth = pd.read_sql_query(
        "SELECT datetime, close as eth_close FROM ohlcv_1m WHERE symbol='ETHUSDT' ORDER BY datetime", conn)
    conn.close()

    btc["datetime"] = pd.to_datetime(btc["datetime"])
    eth["datetime"] = pd.to_datetime(eth["datetime"])
    btc.set_index("datetime", inplace=True)
    eth.set_index("datetime", inplace=True)

    btc_4h = btc.resample("4h").last().dropna()
    eth_4h = eth.resample("4h").last().dropna()

    df = btc_4h.join(eth_4h, how="inner")
    df["ratio"] = df["eth_close"] / df["btc_close"]
    return df


def sma(arr, w):
    n = len(arr); out = np.full(n, np.nan)
    cs = np.cumsum(arr); cs = np.insert(cs, 0, 0)
    if n >= w: out[w-1:] = (cs[w:] - cs[:-w]) / w
    return out


def simulate_pairs(df, lookback, entry_z, exit_z, stop_z, leverage):
    """
    Mean-reversion on ETH/BTC ratio.
    - Ratio above MA + entry_z*std: SHORT ratio (short ETH, long BTC)
    - Ratio below MA - entry_z*std: LONG ratio (long ETH, short BTC)
    - Exit when ratio returns to MA +/- exit_z*std
    - Stop at MA +/- stop_z*std
    """
    ratio = df["ratio"].values
    btc = df["btc_close"].values
    eth = df["eth_close"].values
    n = len(ratio)

    ratio_ma = sma(ratio, lookback)
    ratio_std = np.full(n, np.nan)
    for i in range(lookback, n):
        ratio_std[i] = ratio[i-lookback:i].std()

    bal = INITIAL; peak = INITIAL; pos = 0  # +1=long ratio, -1=short ratio
    entry_ratio = 0.0; rets = []; last_t = -999

    for i in range(lookback + 1, n):
        if np.isnan(ratio_ma[i]) or np.isnan(ratio_std[i]) or ratio_std[i] <= 0:
            continue

        z = (ratio[i] - ratio_ma[i]) / ratio_std[i]

        # Exit
        if pos == 1:  # long ratio (long ETH, short BTC)
            if z >= -exit_z or z >= stop_z:  # ratio reverted or stop
                # PnL from ratio change
                ratio_change = (ratio[i] / entry_ratio - 1)
                dd = (peak - bal) / peak * 100 if peak > 0 else 0
                sz = 0.25 if dd > 25 else (0.5 if dd > 15 else 1.0)
                pnl = ratio_change * leverage * sz - 2 * COMM * leverage * sz  # 2x comm (both legs)
                rets.append(pnl); bal *= (1 + pnl)
                if bal <= 0: break
                if bal > peak: peak = bal
                pos = 0; last_t = i
        elif pos == -1:  # short ratio (short ETH, long BTC)
            if z <= exit_z or z <= -stop_z:
                ratio_change = (entry_ratio / ratio[i] - 1)
                dd = (peak - bal) / peak * 100 if peak > 0 else 0
                sz = 0.25 if dd > 25 else (0.5 if dd > 15 else 1.0)
                pnl = ratio_change * leverage * sz - 2 * COMM * leverage * sz
                rets.append(pnl); bal *= (1 + pnl)
                if bal <= 0: break
                if bal > peak: peak = bal
                pos = 0; last_t = i

        # Entry
        if pos == 0 and i - last_t >= 6:
            if z < -entry_z:  # ratio below mean -> long ratio (expect reversion up)
                pos = 1; entry_ratio = ratio[i]; last_t = i
            elif z > entry_z:  # ratio above mean -> short ratio (expect reversion down)
                pos = -1; entry_ratio = ratio[i]; last_t = i

    # Force close
    if pos != 0 and len(ratio) > 0:
        ratio_change = (ratio[-1] / entry_ratio - 1) if pos == 1 else (entry_ratio / ratio[-1] - 1)
        pnl = ratio_change * leverage - 2 * COMM * leverage
        rets.append(pnl); bal *= (1 + pnl)

    if not rets:
        return {"ret": 0, "sharpe": -10, "dd": 0, "trades": 0, "wr": 0, "pf": 0}
    r = np.array(rets)
    ret = (bal / INITIAL - 1) * 100
    sharpe = r.mean() / max(r.std(), 1e-8) * np.sqrt(6 * 365)
    eq = np.cumprod(1 + r) * INITIAL
    dd = ((np.maximum.accumulate(eq) - eq) / np.maximum.accumulate(eq) * 100).max()
    wins = (r > 0).sum()
    gw = r[r > 0].sum(); gl = abs(r[r < 0].sum())
    return {"ret": ret, "sharpe": sharpe, "dd": dd, "trades": len(r),
            "wr": wins / len(r) * 100, "pf": gw / max(gl, 1e-8), "bal": bal}


def main():
    print("=" * 60)
    print("  BTC/ETH Pairs Trading - Market Neutral")
    print("  No need to predict BTC direction!")
    print("=" * 60)

    t0 = time.time()
    df = load_pair_4h()
    print(f"  Data: {len(df)} 4H bars ({df.index[0]} ~ {df.index[-1]})")
    print(f"  ETH/BTC ratio: mean={df['ratio'].mean():.6f}, std={df['ratio'].std():.6f}")

    n = len(df)
    train = df.iloc[:int(n * 0.6)]
    val = df.iloc[int(n * 0.6):int(n * 0.8)]
    test = df.iloc[int(n * 0.8):]
    print(f"  Train: {len(train)} | Val: {len(val)} | Test: {len(test)}")

    # Grid search
    print("\n  Grid search: lookback x z-scores x leverage")
    best = None; best_score = -999; results = []

    for lb in [50, 80, 100, 150, 200]:
        for ez in [1.0, 1.5, 2.0, 2.5]:
            for xz in [0.0, 0.3, 0.5]:
                for sz in [3.0, 4.0, 5.0]:
                    for lev in [1.0, 1.5, 2.0]:
                        if xz >= ez: continue
                        r_tr = simulate_pairs(train, lb, ez, xz, sz, lev)
                        r_va = simulate_pairs(val, lb, ez, xz, sz, lev)
                        if r_tr["trades"] < 10 or r_va["trades"] < 5: continue
                        score = r_va["sharpe"]
                        results.append((lb, ez, xz, sz, lev, r_tr, r_va, score))
                        if score > best_score:
                            best_score = score; best = (lb, ez, xz, sz, lev)

    if not best:
        print("  No valid parameters found!")
        return

    results.sort(key=lambda x: -x[7])
    print(f"\n  Top 5:")
    for lb, ez, xz, sz, lv, rtr, rva, _ in results[:5]:
        print(f"  LB={lb:3d} Entry={ez:.1f}z Exit={xz:.1f}z Stop={sz:.1f}z Lev={lv:.1f} | "
              f"Tr={rtr['ret']:+.1f}% Va={rva['ret']:+.1f}% VaShp={rva['sharpe']:.2f} VaTr={rva['trades']}")

    lb, ez, xz, sz, lv = best
    r_tr = simulate_pairs(train, lb, ez, xz, sz, lv)
    r_va = simulate_pairs(val, lb, ez, xz, sz, lv)
    r_te = simulate_pairs(test, lb, ez, xz, sz, lv)

    print(f"\n  Best: LB={lb}, Entry={ez}z, Exit={xz}z, Stop={sz}z, Lev={lv}x")
    print(f"  [Train] Ret={r_tr['ret']:+.1f}% Sharpe={r_tr['sharpe']:.2f} DD=-{r_tr['dd']:.1f}% Trades={r_tr['trades']} WR={r_tr['wr']:.0f}%")
    print(f"  [Val  ] Ret={r_va['ret']:+.1f}% Sharpe={r_va['sharpe']:.2f} DD=-{r_va['dd']:.1f}% Trades={r_va['trades']} WR={r_va['wr']:.0f}%")
    print(f"  [Test ] Ret={r_te['ret']:+.1f}% Sharpe={r_te['sharpe']:.2f} DD=-{r_te['dd']:.1f}% Trades={r_te['trades']} WR={r_te['wr']:.0f}%")

    passed = r_va["ret"] > 0 and r_te["ret"] > 0 and r_te["trades"] >= 5
    print(f"\n  Market neutral: NO directional BTC exposure")
    print(f"  VERDICT: {'PASS' if passed else 'FAIL'}")

    out = {"asset": "BTC_ETH_PAIR", "strategy": "pairs_mean_reversion",
           "lookback": lb, "entry_z": ez, "exit_z": xz, "stop_z": sz, "leverage": lv,
           "passed": bool(passed), "test_ret": round(r_te["ret"], 2),
           "test_sharpe": round(r_te["sharpe"], 2), "test_trades": r_te["trades"]}
    (DATA_DIR / "params_pairs_btc_eth.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"  Saved: params_pairs_btc_eth.json ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
