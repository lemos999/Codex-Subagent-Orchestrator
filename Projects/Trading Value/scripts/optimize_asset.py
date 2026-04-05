"""Per-asset CMA-ES optimizer. Works for both crypto and stocks.

Usage:
    py -3.12 scripts/optimize_asset.py --asset BTC
    py -3.12 scripts/optimize_asset.py --asset NVDA
    py -3.12 scripts/optimize_asset.py --asset AMZN
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
COMMISSION_CRYPTO = 0.0005
COMMISSION_STOCK = 0.001
INITIAL = 10_000.0

ASSET_CONFIG = {
    "BTC": {"type": "crypto", "db_symbol": "BTCUSDT", "yf": None, "tf": "15m"},
    "NVDA": {"type": "stock", "db_symbol": None, "yf": "NVDA", "tf": "1d"},
    "AMZN": {"type": "stock", "db_symbol": None, "yf": "AMZN", "tf": "1d"},
}


def load_data(asset: str) -> pd.DataFrame:
    cfg = ASSET_CONFIG[asset]
    if cfg["type"] == "crypto":
        conn = sqlite3.connect(str(DB_PATH))
        df = pd.read_sql_query(
            "SELECT datetime, open, high, low, close, volume "
            "FROM ohlcv_1m WHERE symbol=? ORDER BY datetime",
            conn, params=(cfg["db_symbol"],))
        conn.close()
        df["datetime"] = pd.to_datetime(df["datetime"])
        df.set_index("datetime", inplace=True)
        return df.resample("15min").agg({
            "open": "first", "high": "max", "low": "min",
            "close": "last", "volume": "sum"}).dropna()
    else:
        tk = yf.Ticker(cfg["yf"])
        interval = cfg.get("tf", "1d")
        period = "5y" if interval == "1d" else "2y"
        df = tk.history(period=period, interval=interval)
        if df is None or len(df) < 200:
            df = tk.history(period="5y", interval="1d")
        df = df.rename(columns={"Open": "open", "High": "high", "Low": "low",
                                "Close": "close", "Volume": "volume"})
        return df[["open", "high", "low", "close", "volume"]].dropna()


def sma_arr(arr, w):
    n = len(arr); out = np.full(n, np.nan)
    cs = np.cumsum(arr); cs = np.insert(cs, 0, 0)
    if n >= w: out[w-1:] = (cs[w:] - cs[:-w]) / w
    return out


def simulate(df, p, comm, cfg_type="crypto"):
    c = df["close"].values; h = df["high"].values; lo = df["low"].values; v = df["volume"].values
    n = len(c)
    ma_f = sma_arr(c, int(p["ma_fast"])); ma_s = sma_arr(c, int(p["ma_slow"]))
    delta = np.diff(c, prepend=c[0])
    gain = np.where(delta > 0, delta, 0.0); loss = np.where(delta < 0, -delta, 0.0)
    avg_g = sma_arr(gain, 14); avg_l = sma_arr(loss, 14)
    rsi = np.full(n, 50.0); valid = avg_l > 0
    rsi[valid] = 100 - 100 / (1 + avg_g[valid] / avg_l[valid])
    tr = np.maximum(h[1:]-lo[1:], np.maximum(np.abs(h[1:]-c[:-1]), np.abs(lo[1:]-c[:-1])))
    tr = np.insert(tr, 0, h[0]-lo[0]); atr = sma_arr(tr, 14)
    vol_ma = sma_arr(v, 20)

    bal = INITIAL; peak = INITIAL; pos = 0; entry = 0.0; stop_p = 0.0; tp_p = 0.0
    last_t = -999; consec_loss = 0; trade_rets = []
    warmup = max(int(p["ma_slow"]), 200) + 1
    lev = p["leverage"]

    for i in range(1, n):
        # Exit
        if pos == 1:
            exited = False; ex_p = 0.0
            if lo[i] <= stop_p: ex_p = stop_p; exited = True
            elif h[i] >= tp_p: ex_p = tp_p; exited = True
            # Trailing
            elif not np.isnan(atr[i]):
                profit = c[i] - entry
                if profit >= p["trail_start"] * atr[i]:
                    new_trail = c[i] - p["trail_step"] * atr[i]
                    if new_trail > stop_p: stop_p = new_trail
            if exited:
                dd = (peak - bal) / peak * 100 if peak > 0 else 0
                sz = 0.25 if dd > 25 else (0.50 if dd > 15 else 1.0)
                if consec_loss >= 3: sz = min(sz, 0.5)
                pnl = (ex_p / entry - 1.0) * lev * sz - comm * lev * sz
                trade_rets.append(pnl); bal *= (1+pnl)
                if pnl < 0: consec_loss += 1
                else: consec_loss = 0
                if bal > peak: peak = bal
                if bal <= 0: break
                pos = 0; last_t = i

        # Entry
        if pos == 0 and i >= warmup and i - last_t >= int(p["cooldown"]):
            mf = ma_f[i]; ms = ma_s[i]
            if np.isnan(mf) or np.isnan(ms): continue
            cur_atr = atr[i] if not np.isnan(atr[i]) else 0
            if cur_atr <= 0: continue
            cur_vm = vol_ma[i] if not np.isnan(vol_ma[i]) else 0
            vol_ok = v[i] > p["vol_filter"] * cur_vm if cur_vm > 0 else False
            if mf > ms and rsi[i] < p["rsi_entry"] and vol_ok:
                pos = 1; entry = c[i]
                stop_p = c[i] - p["stop_atr"] * cur_atr
                tp_p = c[i] + p["tp_atr"] * cur_atr
                last_t = i

    if not trade_rets:
        return {"ret": 0, "sharpe": -10, "dd": 0, "trades": 0, "wr": 0, "pf": 0}
    rets = np.array(trade_rets)
    total_ret = (bal / INITIAL - 1) * 100
    bars_per_year = 252 if cfg_type == "stock_daily" else 252 * 4  # daily vs intraday
    sharpe = rets.mean() / max(rets.std(), 1e-8) * np.sqrt(bars_per_year)
    eq = np.cumprod(1+rets) * INITIAL
    dd = ((np.maximum.accumulate(eq) - eq) / np.maximum.accumulate(eq) * 100).max()
    wins = (rets > 0).sum(); wr = wins / len(rets) * 100
    gw = rets[rets > 0].sum(); gl = abs(rets[rets < 0].sum())
    pf = gw / max(gl, 1e-8)
    return {"ret": total_ret, "sharpe": sharpe, "dd": dd,
            "trades": len(rets), "wr": wr, "pf": pf, "balance": bal}


def vec_to_params(x):
    return {
        "ma_fast": max(5, min(60, int(round(x[0])))),
        "ma_slow": max(30, min(300, int(round(x[1])))),
        "rsi_entry": max(25, min(50, x[2])),
        "vol_filter": max(0.5, min(4.0, x[3])),
        "stop_atr": max(1.0, min(5.0, x[4])),
        "tp_atr": max(1.5, min(8.0, x[5])),
        "trail_start": max(1.0, min(6.0, x[6])),
        "trail_step": max(0.2, min(2.0, x[7])),
        "cooldown": max(1, min(20, int(round(x[8])))),
        "leverage": max(1.0, min(x[9], 2.5)),
    }


def objective(x, df_train, comm, cfg_type="crypto"):
    p = vec_to_params(x)
    if p["ma_fast"] >= p["ma_slow"]: return 10.0
    r = simulate(df_train, p, comm, cfg_type)
    if r["trades"] < 10: return 10.0
    return -r["sharpe"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset", required=True, choices=list(ASSET_CONFIG.keys()))
    args = parser.parse_args()
    asset = args.asset
    cfg = ASSET_CONFIG[asset]
    comm = COMMISSION_CRYPTO if cfg["type"] == "crypto" else COMMISSION_STOCK
    cfg_type = "stock_daily" if cfg["type"] == "stock" and cfg["tf"] == "1d" else cfg["type"]

    print(f"{'='*60}")
    print(f"  {asset} Per-Asset CMA-ES Optimization")
    print(f"  Type: {cfg['type']} | TF: {cfg['tf']}")
    print(f"{'='*60}")

    t0 = time.time()
    df = load_data(asset)
    print(f"  Data: {len(df)} bars ({df.index[0]} ~ {df.index[-1]})")

    # Split: 60% train, 20% val, 20% test
    n = len(df)
    train_end = int(n * 0.6)
    val_end = int(n * 0.8)
    train = df.iloc[:train_end]
    val = df.iloc[train_end:val_end]
    test = df.iloc[val_end:]
    print(f"  Train: {len(train)} | Val: {len(val)} | Test: {len(test)}")

    # CMA-ES - wider search for non-ETH assets
    x0 = [15, 80, 38, 1.5, 2.5, 3.5, 3.0, 0.5, 4, 1.5]
    bounds = [[5, 30, 25, 0.5, 1.0, 1.5, 1.0, 0.2, 1, 1.0],
              [60, 300, 50, 4.0, 5.0, 8.0, 6.0, 2.0, 20, 2.5]]

    es = cma.CMAEvolutionStrategy(x0, 0.4, {
        "popsize": 40, "maxiter": 150, "bounds": bounds, "verbose": -1})

    gen = 0; best = -999
    while not es.stop():
        sols = es.ask()
        fits = [objective(s, train, comm, cfg_type) for s in sols]
        es.tell(sols, fits)
        gen += 1
        cur = -min(fits)
        if cur > best: best = cur
        if gen % 30 == 0:
            p = vec_to_params(es.result.xbest)
            r = simulate(train, p, comm)
            print(f"    Gen {gen:3d} | Sharpe: {best:.2f} | "
                  f"Ret: {r['ret']:+.1f}% | Trades: {r['trades']} | Lev: {p['leverage']:.1f}x")

    best_p = vec_to_params(es.result.xbest)

    print(f"\n  Best: MA {best_p['ma_fast']}/{best_p['ma_slow']}, "
          f"RSI<{best_p['rsi_entry']:.1f}, Vol>{best_p['vol_filter']:.1f}x, "
          f"Stop {best_p['stop_atr']:.1f}*ATR, TP {best_p['tp_atr']:.1f}*ATR, "
          f"Lev {best_p['leverage']:.1f}x")

    for label, data in [("Train", train), ("Val", val), ("Test", test)]:
        r = simulate(data, best_p, comm, cfg_type)
        print(f"  [{label:5s}] Ret={r['ret']:+.1f}% | Sharpe={r['sharpe']:.2f} | "
              f"DD=-{r['dd']:.1f}% | Trades={r['trades']} | WR={r['wr']:.0f}% | PF={r['pf']:.2f}")

    # Verdict
    r_val = simulate(val, best_p, comm, cfg_type)
    r_test = simulate(test, best_p, comm, cfg_type)
    passed = r_val["sharpe"] > 0 and r_test["sharpe"] > 0 and r_test["trades"] >= 5
    print(f"\n  VERDICT: {'PASS - deploy to paper' if passed else 'FAIL - needs more work'}")

    # Save params
    out = {"asset": asset, "params": best_p, "passed": bool(passed),
           "val_ret": round(r_val["ret"], 2), "test_ret": round(r_test["ret"], 2),
           "val_sharpe": round(r_val["sharpe"], 2), "test_sharpe": round(r_test["sharpe"], 2)}
    out_path = DATA_DIR / f"params_{asset.lower()}.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"  Saved: {out_path}")
    print(f"  Time: {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
