"""V2 Per-asset optimizer with asset-appropriate strategies.

BTC: Mean-reversion (RSI bounce from extremes)
NVDA/AMZN: Momentum breakout (new high + volume)

Usage:
    py -3.12 scripts/optimize_v2.py --asset BTC
    py -3.12 scripts/optimize_v2.py --asset NVDA
    py -3.12 scripts/optimize_v2.py --asset AMZN
"""
from __future__ import annotations
import argparse, json, sqlite3, subprocess, sys, time
from pathlib import Path
import numpy as np, pandas as pd

try:
    import cma
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "cma"])
    import cma
try:
    import yfinance as yf
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "yfinance"])
    import yfinance as yf

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "sim_1m.sqlite"
INITIAL = 10_000.0

CONFIGS = {
    "BTC": {"type": "crypto", "strategy": "mean_reversion",
            "db_symbol": "BTCUSDT", "tf": "15m", "comm": 0.0005},
    "NVDA": {"type": "stock", "strategy": "momentum_breakout",
             "yf": "NVDA", "tf": "1d", "comm": 0.001},
    "AMZN": {"type": "stock", "strategy": "momentum_breakout",
             "yf": "AMZN", "tf": "1d", "comm": 0.001},
}


def load_data(asset):
    cfg = CONFIGS[asset]
    if cfg["type"] == "crypto":
        conn = sqlite3.connect(str(DB_PATH))
        df = pd.read_sql_query(
            "SELECT datetime, open, high, low, close, volume "
            "FROM ohlcv_1m WHERE symbol=? ORDER BY datetime",
            conn, params=(cfg["db_symbol"],))
        conn.close()
        df["datetime"] = pd.to_datetime(df["datetime"])
        df.set_index("datetime", inplace=True)
        return df.resample("15min").agg({"open":"first","high":"max","low":"min","close":"last","volume":"sum"}).dropna()
    else:
        df = yf.Ticker(cfg["yf"]).history(period="5y", interval="1d")
        df = df.rename(columns={"Open":"open","High":"high","Low":"low","Close":"close","Volume":"volume"})
        return df[["open","high","low","close","volume"]].dropna()


def sma(arr, w):
    n = len(arr); out = np.full(n, np.nan)
    cs = np.cumsum(arr); cs = np.insert(cs, 0, 0)
    if n >= w: out[w-1:] = (cs[w:] - cs[:-w]) / w
    return out


def simulate_mean_reversion(df, p, comm):
    """BTC: Buy when RSI oversold, sell when RSI overbought. No trend filter."""
    c = df["close"].values; h = df["high"].values; lo = df["low"].values; v = df["volume"].values
    n = len(c)
    delta = np.diff(c, prepend=c[0])
    gain = np.where(delta>0, delta, 0.0); loss = np.where(delta<0, -delta, 0.0)
    avg_g = sma(gain, 14); avg_l = sma(loss, 14)
    rsi = np.full(n, 50.0); valid = avg_l > 0
    rsi[valid] = 100 - 100 / (1 + avg_g[valid] / avg_l[valid])
    tr = np.maximum(h[1:]-lo[1:], np.maximum(np.abs(h[1:]-c[:-1]), np.abs(lo[1:]-c[:-1])))
    tr = np.insert(tr, 0, h[0]-lo[0]); atr = sma(tr, 14)

    bal = INITIAL; peak = INITIAL; pos = 0; entry = 0.0; stop_p = 0.0; tp_p = 0.0
    last_t = -999; consec_loss = 0; rets = []
    lev = p["leverage"]

    for i in range(20, n):
        cur_atr = atr[i] if not np.isnan(atr[i]) else 0
        # Exit
        if pos == 1:
            if lo[i] <= stop_p:
                dd = (peak-bal)/peak*100 if peak>0 else 0
                sz = 0.25 if dd>25 else (0.5 if dd>15 else 1.0)
                pnl = (stop_p/entry-1)*lev*sz - comm*lev*sz
                rets.append(pnl); bal *= (1+pnl)
                if pnl<0: consec_loss+=1
                else: consec_loss=0
                if bal>peak: peak=bal
                if bal<=0: break
                pos=0; last_t=i
            elif h[i] >= tp_p:
                dd = (peak-bal)/peak*100 if peak>0 else 0
                sz = 0.25 if dd>25 else (0.5 if dd>15 else 1.0)
                pnl = (tp_p/entry-1)*lev*sz - comm*lev*sz
                rets.append(pnl); bal *= (1+pnl)
                consec_loss=0
                if bal>peak: peak=bal
                pos=0; last_t=i
            elif rsi[i] > p["rsi_exit"]:
                # Exit on RSI recovery
                dd = (peak-bal)/peak*100 if peak>0 else 0
                sz = 0.25 if dd>25 else (0.5 if dd>15 else 1.0)
                pnl = (c[i]/entry-1)*lev*sz - comm*lev*sz
                rets.append(pnl); bal *= (1+pnl)
                if pnl<0: consec_loss+=1
                else: consec_loss=0
                if bal>peak: peak=bal
                if bal<=0: break
                pos=0; last_t=i

        # Entry: RSI oversold bounce
        if pos == 0 and i - last_t >= int(p["cooldown"]) and cur_atr > 0:
            if rsi[i] < p["rsi_buy"] and rsi[i-1] >= p["rsi_buy"]:  # RSI crosses below
                pos=1; entry=c[i]
                stop_p = c[i] - p["stop_atr"]*cur_atr
                tp_p = c[i] + p["tp_atr"]*cur_atr
                last_t=i

    return _stats(rets, bal, n, 252*4)


def simulate_momentum_breakout(df, p, comm):
    """NVDA/AMZN: Buy on new N-day high with volume confirmation."""
    c = df["close"].values; h = df["high"].values; lo = df["low"].values; v = df["volume"].values
    n = len(c)
    tr = np.maximum(h[1:]-lo[1:], np.maximum(np.abs(h[1:]-c[:-1]), np.abs(lo[1:]-c[:-1])))
    tr = np.insert(tr, 0, h[0]-lo[0]); atr = sma(tr, 14)
    vol_ma = sma(v, 20)
    lookback = int(p["breakout_period"])

    bal = INITIAL; peak = INITIAL; pos = 0; entry = 0.0; stop_p = 0.0; trail_p = 0.0
    last_t = -999; consec_loss = 0; rets = []
    lev = p["leverage"]

    for i in range(max(lookback+1, 21), n):
        cur_atr = atr[i] if not np.isnan(atr[i]) else 0
        # Exit
        if pos == 1:
            if lo[i] <= stop_p:
                dd = (peak-bal)/peak*100 if peak>0 else 0
                sz = 0.25 if dd>25 else (0.5 if dd>15 else 1.0)
                pnl = (stop_p/entry-1)*lev*sz - comm*lev*sz
                rets.append(pnl); bal *= (1+pnl)
                if pnl<0: consec_loss+=1
                else: consec_loss=0
                if bal>peak: peak=bal
                if bal<=0: break
                pos=0; last_t=i
            else:
                # Trailing stop
                if cur_atr > 0:
                    new_trail = c[i] - p["trail_atr"]*cur_atr
                    if new_trail > trail_p: trail_p = new_trail
                    if lo[i] <= trail_p and trail_p > entry:
                        dd = (peak-bal)/peak*100 if peak>0 else 0
                        sz = 0.25 if dd>25 else (0.5 if dd>15 else 1.0)
                        pnl = (trail_p/entry-1)*lev*sz - comm*lev*sz
                        rets.append(pnl); bal *= (1+pnl)
                        if pnl<0: consec_loss+=1
                        else: consec_loss=0
                        if bal>peak: peak=bal
                        if bal<=0: break
                        pos=0; last_t=i

        # Entry: new N-day high + volume
        if pos == 0 and i - last_t >= int(p["cooldown"]) and cur_atr > 0:
            high_n = h[i-lookback:i].max()
            cur_vm = vol_ma[i] if not np.isnan(vol_ma[i]) else 0
            vol_ok = v[i] > p["vol_mult"] * cur_vm if cur_vm > 0 else False
            if c[i] > high_n and vol_ok:
                pos=1; entry=c[i]
                stop_p = c[i] - p["stop_atr"]*cur_atr
                trail_p = stop_p
                last_t=i

    return _stats(rets, bal, n, 252)


def _stats(rets, bal, n_bars, bars_per_year):
    if not rets:
        return {"ret":0, "sharpe":-10, "dd":0, "trades":0, "wr":0, "pf":0, "balance":INITIAL}
    r = np.array(rets)
    ret = (bal/INITIAL-1)*100
    sharpe = r.mean() / max(r.std(), 1e-8) * np.sqrt(bars_per_year)
    eq = np.cumprod(1+r)*INITIAL
    dd = ((np.maximum.accumulate(eq)-eq)/np.maximum.accumulate(eq)*100).max()
    wins = (r>0).sum(); wr = wins/len(r)*100
    gw = r[r>0].sum(); gl = abs(r[r<0].sum())
    pf = gw/max(gl, 1e-8)
    return {"ret":ret, "sharpe":sharpe, "dd":dd, "trades":len(r), "wr":wr, "pf":pf, "balance":bal}


def vec_to_mr(x):
    """Mean-reversion params for BTC."""
    return {"rsi_buy": max(20, min(40, x[0])),
            "rsi_exit": max(45, min(70, x[1])),
            "stop_atr": max(1.0, min(4.0, x[2])),
            "tp_atr": max(1.5, min(6.0, x[3])),
            "cooldown": max(2, min(20, int(round(x[4])))),
            "leverage": max(1.0, min(2.5, x[5]))}

def vec_to_mb(x):
    """Momentum breakout params for stocks."""
    return {"breakout_period": max(5, min(60, int(round(x[0])))),
            "vol_mult": max(0.5, min(3.0, x[1])),
            "stop_atr": max(1.0, min(4.0, x[2])),
            "trail_atr": max(1.5, min(5.0, x[3])),
            "cooldown": max(1, min(10, int(round(x[4])))),
            "leverage": max(1.0, min(2.0, x[5]))}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset", required=True, choices=list(CONFIGS.keys()))
    args = parser.parse_args()
    asset = args.asset
    cfg = CONFIGS[asset]

    print(f"{'='*60}")
    print(f"  {asset} V2 Optimization ({cfg['strategy']})")
    print(f"{'='*60}")

    t0 = time.time()
    df = load_data(asset)
    print(f"  Data: {len(df)} bars ({df.index[0]} ~ {df.index[-1]})")

    n = len(df)
    train = df.iloc[:int(n*0.6)]
    val = df.iloc[int(n*0.6):int(n*0.8)]
    test = df.iloc[int(n*0.8):]
    print(f"  Train: {len(train)} | Val: {len(val)} | Test: {len(test)}")

    if cfg["strategy"] == "mean_reversion":
        x0 = [30, 55, 2.0, 3.0, 6, 1.5]
        bounds = [[20, 45, 1.0, 1.5, 2, 1.0], [40, 70, 4.0, 6.0, 20, 2.5]]
        vec_fn = vec_to_mr
        sim_fn = simulate_mean_reversion
    else:
        x0 = [20, 1.5, 2.0, 3.0, 3, 1.0]
        bounds = [[5, 0.5, 1.0, 1.5, 1, 1.0], [60, 3.0, 4.0, 5.0, 10, 2.0]]
        vec_fn = vec_to_mb
        sim_fn = simulate_momentum_breakout

    def objective(x):
        p = vec_fn(x)
        r = sim_fn(train, p, cfg["comm"])
        if r["trades"] < 5: return 10.0
        return -r["sharpe"]

    es = cma.CMAEvolutionStrategy(x0, 0.3, {
        "popsize": 40, "maxiter": 150, "bounds": bounds, "verbose": -1})

    gen = 0; best = -999
    while not es.stop():
        sols = es.ask()
        fits = [objective(s) for s in sols]
        es.tell(sols, fits)
        gen += 1
        cur = -min(fits)
        if cur > best: best = cur
        if gen % 30 == 0:
            p = vec_fn(es.result.xbest)
            r = sim_fn(train, p, cfg["comm"])
            print(f"    Gen {gen:3d} | Sharpe: {best:.2f} | Ret: {r['ret']:+.1f}% | "
                  f"Trades: {r['trades']} | WR: {r['wr']:.0f}%")

    best_p = vec_fn(es.result.xbest)
    print(f"\n  Best params: {best_p}")

    for label, data in [("Train", train), ("Val", val), ("Test", test)]:
        r = sim_fn(data, best_p, cfg["comm"])
        print(f"  [{label:5s}] Ret={r['ret']:+.1f}% | Sharpe={r['sharpe']:.2f} | "
              f"DD=-{r['dd']:.1f}% | Trades={r['trades']} | WR={r['wr']:.0f}% | PF={r['pf']:.2f}")

    r_val = sim_fn(val, best_p, cfg["comm"])
    r_test = sim_fn(test, best_p, cfg["comm"])
    passed = r_val["sharpe"] > 0 and r_test["ret"] > 0 and r_test["trades"] >= 3
    print(f"\n  VERDICT: {'PASS' if passed else 'FAIL'}")

    out = {"asset": asset, "strategy": cfg["strategy"], "params": best_p,
           "passed": bool(passed),
           "val_ret": round(r_val["ret"], 2), "test_ret": round(r_test["ret"], 2),
           "val_sharpe": round(r_val["sharpe"], 2), "test_sharpe": round(r_test["sharpe"], 2)}
    out_path = DATA_DIR / f"params_{asset.lower()}_v2.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"  Saved: {out_path} ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
