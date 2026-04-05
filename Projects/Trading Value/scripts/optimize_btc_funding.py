"""BTC Strategy with Funding Rate + Open Interest signals.

External data that wasn't available before:
- Funding rate: when too positive -> overleveraged longs -> potential crash
- Funding rate negative -> shorts paying longs -> potential squeeze up
- Combined with price action for entry/exit

Usage:
    py -3.12 scripts/optimize_btc_funding.py
"""
from __future__ import annotations
import json, sqlite3, subprocess, sys, time
from pathlib import Path
import numpy as np, pandas as pd

try:
    import ccxt
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "ccxt"])
    import ccxt

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "sim_1m.sqlite"
INITIAL = 10_000.0
COMM = 0.0005


def load_btc_4h():
    conn = sqlite3.connect(str(DB_PATH))
    df = pd.read_sql_query(
        "SELECT datetime, open, high, low, close, volume "
        "FROM ohlcv_1m WHERE symbol='BTCUSDT' ORDER BY datetime", conn)
    conn.close()
    df["datetime"] = pd.to_datetime(df["datetime"])
    df.set_index("datetime", inplace=True)
    return df.resample("4h").agg({"open":"first","high":"max","low":"min","close":"last","volume":"sum"}).dropna()


def fetch_funding_history():
    """Fetch historical funding rates from Binance."""
    ex = ccxt.binance({"options": {"defaultType": "future"}})
    all_rates = []
    # Fetch in batches (API limit 1000)
    since = int(pd.Timestamp("2021-04-01").timestamp() * 1000)
    end = int(pd.Timestamp.now().timestamp() * 1000)
    print("  Fetching funding rate history...")
    while since < end:
        try:
            rates = ex.fetch_funding_rate_history("BTC/USDT:USDT", since=since, limit=1000)
            if not rates: break
            all_rates.extend(rates)
            since = rates[-1]["timestamp"] + 1
            if len(all_rates) % 5000 == 0:
                print(f"    {len(all_rates)} rates fetched...")
        except Exception as e:
            print(f"    Error: {e}, retrying...")
            time.sleep(2)
            continue
    print(f"  Total funding rates: {len(all_rates)}")
    return all_rates


def sma(arr, w):
    n = len(arr); out = np.full(n, np.nan)
    cs = np.cumsum(arr); cs = np.insert(cs, 0, 0)
    if n >= w: out[w-1:] = (cs[w:] - cs[:-w]) / w
    return out


def build_features_with_funding(df_4h, funding_rates):
    """Merge 4H price data with funding rate signals."""
    c = df_4h["close"].values; h = df_4h["high"].values; lo = df_4h["low"].values; v = df_4h["volume"].values
    n = len(c)

    # Price features
    delta = np.diff(c, prepend=c[0])
    gain = np.where(delta>0, delta, 0.0); loss = np.where(delta<0, -delta, 0.0)
    avg_g = sma(gain, 14); avg_l = sma(loss, 14)
    rsi = np.full(n, 50.0); valid = avg_l > 0
    rsi[valid] = 100 - 100 / (1 + avg_g[valid] / avg_l[valid])

    ma50 = sma(c, 50); ma200 = sma(c, 200)
    tr = np.maximum(h[1:]-lo[1:], np.maximum(np.abs(h[1:]-c[:-1]), np.abs(lo[1:]-c[:-1])))
    tr = np.insert(tr, 0, h[0]-lo[0]); atr = sma(tr, 14)

    # Build funding rate series aligned to 4H bars
    fr_df = pd.DataFrame(funding_rates)
    if len(fr_df) > 0:
        fr_df["datetime"] = pd.to_datetime(fr_df["datetime"], utc=True)
        fr_df.set_index("datetime", inplace=True)
        fr_df.index = fr_df.index.tz_localize(None)  # strip tz to match df_4h
        fr_df = fr_df[["fundingRate"]].resample("4h").mean().reindex(df_4h.index, method="ffill")
        funding = fr_df["fundingRate"].values.copy()
        funding = np.nan_to_num(funding, nan=0.0)
        # Rolling average funding (sentiment indicator)
        funding_ma = sma(funding, 7 * 6)  # 7-day avg (6 x 4H bars/day)
    else:
        funding = np.zeros(n)
        funding_ma = np.zeros(n)

    return {
        "c": c, "h": h, "lo": lo, "rsi": rsi, "atr": atr,
        "ma50": ma50, "ma200": ma200,
        "funding": np.nan_to_num(funding, 0),
        "funding_ma": np.nan_to_num(funding_ma, 0),
        "n": n,
    }


def simulate_funding_strategy(feat, fr_buy_thresh, fr_sell_thresh, rsi_buy, stop_mult, tp_mult, leverage):
    """
    Entry LONG: funding_ma < fr_buy_thresh (shorts paying -> squeeze potential) AND RSI < rsi_buy AND uptrend
    Entry SHORT: funding_ma > fr_sell_thresh (longs overleveraged -> crash potential) AND RSI > (100-rsi_buy) AND downtrend
    """
    c = feat["c"]; h = feat["h"]; lo = feat["lo"]; n = feat["n"]
    rsi = feat["rsi"]; atr = feat["atr"]; ma50 = feat["ma50"]; ma200 = feat["ma200"]
    fr = feat["funding"]; fr_ma = feat["funding_ma"]

    bal = INITIAL; peak = INITIAL; pos = 0; entry = 0.0; stop_p = 0.0; tp_p = 0.0
    rets = []; last_t = -999; lev = leverage

    for i in range(201, n):
        if np.isnan(ma50[i]) or np.isnan(ma200[i]) or np.isnan(atr[i]) or atr[i] <= 0: continue

        # Exit
        if pos == 1:
            if lo[i] <= stop_p or h[i] >= tp_p:
                ex_p = stop_p if lo[i] <= stop_p else tp_p
                dd = (peak-bal)/peak*100 if peak>0 else 0
                sz = 0.25 if dd>25 else (0.5 if dd>15 else 1.0)
                pnl = (ex_p/entry - 1) * lev * sz - COMM * lev * sz
                rets.append(pnl); bal *= (1+pnl)
                if bal<=0: break
                if bal>peak: peak=bal
                pos=0; last_t=i
        elif pos == -1:
            if h[i] >= stop_p or lo[i] <= tp_p:
                ex_p = stop_p if h[i] >= stop_p else tp_p
                dd = (peak-bal)/peak*100 if peak>0 else 0
                sz = 0.25 if dd>25 else (0.5 if dd>15 else 1.0)
                pnl = (1 - ex_p/entry) * lev * sz - COMM * lev * sz
                rets.append(pnl); bal *= (1+pnl)
                if bal<=0: break
                if bal>peak: peak=bal
                pos=0; last_t=i

        # Entry
        if pos == 0 and i - last_t >= 6:  # 1-day cooldown
            uptrend = ma50[i] > ma200[i]
            downtrend = ma50[i] < ma200[i]
            cur_atr = atr[i]

            # LONG: negative funding (shorts squeezed) + RSI oversold + uptrend
            if fr_ma[i] < fr_buy_thresh and rsi[i] < rsi_buy and uptrend:
                pos=1; entry=c[i]
                stop_p = c[i] - stop_mult * cur_atr
                tp_p = c[i] + tp_mult * cur_atr
                last_t=i

            # SHORT: high funding (longs overleveraged) + RSI overbought + downtrend
            elif fr_ma[i] > fr_sell_thresh and rsi[i] > (100 - rsi_buy) and downtrend:
                pos=-1; entry=c[i]
                stop_p = c[i] + stop_mult * cur_atr
                tp_p = c[i] - tp_mult * cur_atr
                last_t=i

    if pos != 0:
        pnl = ((c[-1]/entry - 1) if pos==1 else (1 - c[-1]/entry)) * lev - COMM * lev
        rets.append(pnl); bal *= (1+pnl)

    if not rets:
        return {"ret":0,"sharpe":-10,"dd":0,"trades":0,"wr":0,"pf":0}
    r = np.array(rets)
    ret = (bal/INITIAL-1)*100
    sharpe = r.mean()/max(r.std(),1e-8)*np.sqrt(6*365)
    eq = np.cumprod(1+r)*INITIAL
    dd = ((np.maximum.accumulate(eq)-eq)/np.maximum.accumulate(eq)*100).max()
    wins = (r>0).sum(); gw = r[r>0].sum(); gl = abs(r[r<0].sum())
    return {"ret":ret,"sharpe":sharpe,"dd":dd,"trades":len(r),"wr":wins/len(r)*100,"pf":gw/max(gl,1e-8)}


def main():
    print("="*60)
    print("  BTC Funding Rate Strategy")
    print("  New alpha source: funding rate + open interest")
    print("="*60)

    t0 = time.time()
    df = load_btc_4h()
    print(f"  Price data: {len(df)} 4H bars")

    fr_cache = DATA_DIR / "btc_funding_cache.json"
    if fr_cache.exists():
        print("  Loading cached funding rates...")
        rates = json.loads(fr_cache.read_text(encoding="utf-8"))
    else:
        rates = fetch_funding_history()
        fr_cache.write_text(json.dumps(rates, default=str), encoding="utf-8")

    print(f"  Funding rates: {len(rates)}")

    feat_all = build_features_with_funding(df, rates)
    fr_vals = feat_all["funding_ma"]
    valid_fr = fr_vals[~np.isnan(fr_vals) & (fr_vals != 0)]
    if len(valid_fr) > 0:
        print(f"  Funding rate stats: mean={valid_fr.mean()*10000:.2f}bp, "
              f"std={valid_fr.std()*10000:.2f}bp, "
              f"min={valid_fr.min()*10000:.2f}bp, max={valid_fr.max()*10000:.2f}bp")

    # Split
    n = feat_all["n"]
    split1 = int(n * 0.6); split2 = int(n * 0.8)

    def split_feat(f, s, e):
        return {k: v[s:e] if isinstance(v, np.ndarray) else e-s for k, v in f.items()}

    feat_tr = split_feat(feat_all, 0, split1)
    feat_va = split_feat(feat_all, split1, split2)
    feat_te = split_feat(feat_all, split2, n)

    # Grid search
    print("\n  Grid search: funding thresholds x RSI x risk params")
    best = None; best_score = -999; results = []

    for fr_buy in [-0.0005, -0.0003, -0.0001, 0.0, 0.0001]:
        for fr_sell in [0.0003, 0.0005, 0.0008, 0.001]:
            for rsi_b in [30, 35, 40, 45]:
                for stop_m in [2.0, 3.0]:
                    for tp_m in [3.0, 4.0, 5.0]:
                        for lev in [1.0, 1.5, 2.0]:
                            r = simulate_funding_strategy(feat_tr, fr_buy, fr_sell, rsi_b, stop_m, tp_m, lev)
                            rv = simulate_funding_strategy(feat_va, fr_buy, fr_sell, rsi_b, stop_m, tp_m, lev)
                            if r["trades"] < 5 or rv["trades"] < 3: continue
                            score = rv["sharpe"]
                            results.append((fr_buy, fr_sell, rsi_b, stop_m, tp_m, lev, r, rv, score))
                            if score > best_score:
                                best_score = score
                                best = (fr_buy, fr_sell, rsi_b, stop_m, tp_m, lev)

    if not best:
        print("  No valid parameters found!")
        print(f"  Time: {time.time()-t0:.0f}s")
        return

    results.sort(key=lambda x: -x[8])
    print(f"\n  Top 5:")
    for fb, fs, rb, sm, tm, lv, rtr, rva, _ in results[:5]:
        print(f"  FR_buy={fb:+.4f} FR_sell={fs:.4f} RSI<{rb} Stop={sm} TP={tm} Lev={lv} | "
              f"Tr={rtr['ret']:+.1f}% Va={rva['ret']:+.1f}% VaShp={rva['sharpe']:.2f}")

    fb, fs, rb, sm, tm, lv = best
    r_tr = simulate_funding_strategy(feat_tr, fb, fs, rb, sm, tm, lv)
    r_va = simulate_funding_strategy(feat_va, fb, fs, rb, sm, tm, lv)
    r_te = simulate_funding_strategy(feat_te, fb, fs, rb, sm, tm, lv)

    print(f"\n  Best: FR_buy={fb:+.4f} FR_sell={fs:.4f} RSI<{rb} Stop={sm}*ATR TP={tm}*ATR Lev={lv}x")
    print(f"  [Train] Ret={r_tr['ret']:+.1f}% Sharpe={r_tr['sharpe']:.2f} DD=-{r_tr['dd']:.1f}% Trades={r_tr['trades']} WR={r_tr['wr']:.0f}%")
    print(f"  [Val  ] Ret={r_va['ret']:+.1f}% Sharpe={r_va['sharpe']:.2f} DD=-{r_va['dd']:.1f}% Trades={r_va['trades']} WR={r_va['wr']:.0f}%")
    print(f"  [Test ] Ret={r_te['ret']:+.1f}% Sharpe={r_te['sharpe']:.2f} DD=-{r_te['dd']:.1f}% Trades={r_te['trades']} WR={r_te['wr']:.0f}%")

    bh = (feat_te["c"][-1] / feat_te["c"][0] - 1) * 100
    passed = r_va["ret"] > 0 and r_te["ret"] > 0 and r_te["trades"] >= 3
    print(f"\n  Buy&Hold (test): {bh:+.1f}%")
    print(f"  VERDICT: {'PASS' if passed else 'FAIL'}")

    out = {"asset": "BTC", "strategy": "funding_rate",
           "fr_buy": fb, "fr_sell": fs, "rsi_buy": rb,
           "stop_mult": sm, "tp_mult": tm, "leverage": lv,
           "passed": bool(passed), "test_ret": round(r_te["ret"], 2),
           "bh_ret": round(bh, 2)}
    (DATA_DIR / "params_btc_funding.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"  Saved: params_btc_funding.json ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
