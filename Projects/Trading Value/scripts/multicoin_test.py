"""Multi-coin validation: test the hybrid strategy on BTC, SOL, XRP.

Reuses strategy_hybrid.py logic with different symbols.

Usage:
    cd "Projects/Trading Value"
    py -3.12 scripts/multicoin_test.py
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
    from xgboost import XGBClassifier
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "xgboost"])
    from xgboost import XGBClassifier

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "sim_1m.sqlite"
COMMISSION = 0.0004
SLIPPAGE = 0.0001
INITIAL_BALANCE = 10_000.0

# Best CMA-ES params (from ETH optimization)
PARAMS = {
    "ma_fast": 21, "ma_slow": 95,
    "rsi_oversold": 28.3, "rsi_overbought": 67.5,
    "vol_filter": 2.89,
    "atr_stop_mult": 3.89, "atr_tp_mult": 3.75,
    "trail_start": 4.89, "trail_step": 0.31,
    "cooldown_bars": 5, "risk_per_trade": 0.019,
    "leverage": 1.6, "allow_short": False,
}
CONF_THRESHOLD = 0.55
SYMBOLS = ["ETHUSDT", "BTCUSDT", "SOLUSDT", "XRPUSDT"]


def load_15m(symbol: str) -> pd.DataFrame:
    conn = sqlite3.connect(str(DB_PATH))
    df = pd.read_sql_query(
        "SELECT datetime, open, high, low, close, volume "
        "FROM ohlcv_1m WHERE symbol=? ORDER BY datetime",
        conn, params=(symbol,),
    )
    conn.close()
    df["datetime"] = pd.to_datetime(df["datetime"])
    df.set_index("datetime", inplace=True)
    df_15m = df.resample("15min").agg({
        "open": "first", "high": "max", "low": "min",
        "close": "last", "volume": "sum",
    }).dropna()
    return df_15m


def compute_features(df: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
    c = df["close"]
    h = df["high"]
    lo = df["low"]
    v = df["volume"]
    feat = pd.DataFrame(index=df.index)
    for w in [5, 20, 50, 200]:
        ma = c.rolling(w).mean()
        feat[f"ma{w}_pos"] = (c - ma) / ma.where(ma > 0, 1.0)
    ma5 = c.rolling(5).mean(); ma20 = c.rolling(20).mean()
    ma50 = c.rolling(50).mean(); ma200 = c.rolling(200).mean()
    feat["cross_5_20"] = (ma5 - ma20) / ma20.where(ma20 > 0, 1.0)
    feat["cross_20_50"] = (ma20 - ma50) / ma50.where(ma50 > 0, 1.0)
    feat["cross_50_200"] = (ma50 - ma200) / ma200.where(ma200 > 0, 1.0)
    delta = c.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    feat["rsi14"] = 100 - (100 / (1 + rs))
    tr = pd.concat([h - lo, (h - c.shift(1)).abs(), (lo - c.shift(1)).abs()], axis=1).max(axis=1)
    feat["atr_norm"] = tr.rolling(14).mean() / c.where(c > 0, 1.0)
    dc_high = h.rolling(20).max(); dc_low = lo.rolling(20).min()
    dc_range = dc_high - dc_low
    feat["donchian_pos"] = (c - dc_low) / dc_range.where(dc_range > 0, 1.0)
    vol_ma20 = v.rolling(20).mean()
    feat["vol_ratio"] = v / vol_ma20.where(vol_ma20 > 0, 1.0)
    feat["mom_1"] = c.pct_change(1)
    feat["mom_4"] = c.pct_change(4)
    feat["mom_12"] = c.pct_change(12)
    hour = df.index.hour + df.index.minute / 60.0
    feat["hour_sin"] = np.sin(2 * np.pi * hour / 24)
    feat["hour_cos"] = np.cos(2 * np.pi * hour / 24)
    dow = df.index.dayofweek.astype(float)
    feat["dow_sin"] = np.sin(2 * np.pi * dow / 7)
    feat["dow_cos"] = np.cos(2 * np.pi * dow / 7)
    cols = list(feat.columns)
    return feat.values, cols


def compute_indicators(df: pd.DataFrame, p: dict) -> dict:
    c = df["close"].values; h = df["high"].values; lo = df["low"].values; v = df["volume"].values
    n = len(c)
    def rolling_mean(arr, w):
        out = np.full(n, np.nan)
        cs = np.cumsum(arr); cs = np.insert(cs, 0, 0)
        if n >= w: out[w-1:] = (cs[w:] - cs[:-w]) / w
        return out
    ma_f = rolling_mean(c, p["ma_fast"])
    ma_s = rolling_mean(c, p["ma_slow"])
    delta = np.diff(c, prepend=c[0])
    gain = np.where(delta > 0, delta, 0.0)
    loss_arr = np.where(delta < 0, -delta, 0.0)
    avg_g = rolling_mean(gain, 14); avg_l = rolling_mean(loss_arr, 14)
    rsi = np.full(n, 50.0)
    valid = avg_l > 0
    rsi[valid] = 100 - 100 / (1 + avg_g[valid] / avg_l[valid])
    tr = np.maximum(h[1:] - lo[1:], np.maximum(np.abs(h[1:] - c[:-1]), np.abs(lo[1:] - c[:-1])))
    tr = np.insert(tr, 0, h[0] - lo[0])
    atr = rolling_mean(tr, 14)
    vol_ma = rolling_mean(v, 20)
    return {"close": c, "high": h, "low": lo, "volume": v,
            "ma_fast": ma_f, "ma_slow": ma_s, "rsi": rsi, "atr": atr, "vol_ma": vol_ma, "n": n}


def simulate(df: pd.DataFrame, p: dict, xgb_proba: np.ndarray | None, conf: float) -> dict:
    ind = compute_indicators(df, p)
    c = ind["close"]; h = ind["high"]; lo = ind["low"]; v = ind["volume"]
    ma_f = ind["ma_fast"]; ma_s = ind["ma_slow"]; rsi = ind["rsi"]
    atr = ind["atr"]; vol_ma = ind["vol_ma"]; n = ind["n"]

    balance = INITIAL_BALANCE; peak = INITIAL_BALANCE
    position = 0; entry_price = 0.0; stop_price = 0.0; tp_price = 0.0
    trail_active = False; trail_price = 0.0; last_trade = -999
    consec_loss = 0; size_mult = 1.0
    trade_rets = []
    warmup = max(p["ma_slow"], 200) + 1

    for i in range(1, n):
        price = c[i]; bar_h = h[i]; bar_l = lo[i]
        if position != 0:
            exited = False; exit_p = 0.0
            if position == 1:
                if bar_l <= stop_price: exit_p = stop_price; exited = True
                elif bar_h >= tp_price: exit_p = tp_price; exited = True
                else:
                    pd_ = price - entry_price
                    tt = p["trail_start"] * atr[i] if not np.isnan(atr[i]) else 1e9
                    if pd_ >= tt: trail_active = True
                    if trail_active:
                        nt = price - p["trail_step"] * (atr[i] if not np.isnan(atr[i]) else 0)
                        if nt > trail_price: trail_price = nt
                        if bar_l <= trail_price: exit_p = trail_price; exited = True
            if exited:
                pnl = (exit_p / entry_price - 1.0) * p["leverage"] * size_mult
                pnl -= (COMMISSION + SLIPPAGE) * p["leverage"] * size_mult
                trade_rets.append(pnl)
                balance *= (1.0 + pnl)
                if pnl < 0: consec_loss += 1
                else: consec_loss = 0
                if balance > peak: peak = balance
                if balance <= 0: break
                position = 0; last_trade = i

        if position == 0 and i >= warmup:
            if i - last_trade < p["cooldown_bars"]: continue
            cur_atr = atr[i] if not np.isnan(atr[i]) else 0.0
            if cur_atr <= 0: continue
            cur_vm = vol_ma[i] if not np.isnan(vol_ma[i]) else 0.0
            vol_ok = v[i] > p["vol_filter"] * cur_vm if cur_vm > 0 else False
            mf = ma_f[i]; ms = ma_s[i]
            if np.isnan(mf) or np.isnan(ms): continue

            # DD-based sizing
            dd = (peak - balance) / peak * 100 if peak > 0 else 0
            size_mult = 1.0
            if dd > 25: size_mult = 0.25
            elif dd > 15: size_mult = 0.50
            if consec_loss >= 3: size_mult = min(size_mult, 0.50)

            xgb_ok = True
            if xgb_proba is not None:
                if mf > ms: xgb_ok = xgb_proba[i] > conf
                else: xgb_ok = False

            if mf > ms and rsi[i] < p["rsi_oversold"] and vol_ok and xgb_ok:
                position = 1
                entry_price = price * (1.0 + COMMISSION + SLIPPAGE)
                stop_price = price - p["atr_stop_mult"] * cur_atr
                tp_price = price + p["atr_tp_mult"] * cur_atr
                trail_active = False; trail_price = stop_price; last_trade = i

    total_ret = (balance / INITIAL_BALANCE - 1.0) * 100
    years = n / 35040.0
    ann_ret = ((balance / INITIAL_BALANCE) ** (1/max(years, 0.01)) - 1) * 100 if balance > 0 else -100
    rets = np.array(trade_rets) if trade_rets else np.array([0.0])
    sharpe = rets.mean() / max(rets.std(), 1e-8) * np.sqrt(365 * 24 * 4)
    eq = np.cumprod(1 + rets) * INITIAL_BALANCE if len(trade_rets) > 0 else np.array([INITIAL_BALANCE])
    peak_eq = np.maximum.accumulate(eq)
    dd = ((peak_eq - eq) / peak_eq * 100)
    max_dd = dd.max() if len(dd) > 0 else 0
    wins = sum(1 for r in trade_rets if r > 0)
    losses = sum(1 for r in trade_rets if r <= 0)
    wr = wins / len(trade_rets) * 100 if trade_rets else 0
    gross_win = sum(r for r in trade_rets if r > 0)
    gross_loss = abs(sum(r for r in trade_rets if r < 0))
    pf = gross_win / max(gross_loss, 1e-8)
    return {"total_ret": total_ret, "ann_ret": ann_ret, "sharpe": sharpe,
            "max_dd": max_dd, "trades": len(trade_rets), "wr": wr, "pf": pf, "balance": balance}


def run_coin(symbol: str):
    print(f"\n{'='*70}")
    print(f"  {symbol}")
    print(f"{'='*70}")
    t0 = time.time()
    df = load_15m(symbol)
    print(f"  {len(df):,} bars loaded ({time.time()-t0:.1f}s)")

    # Train XGBoost walk-forward
    feat_vals, feat_cols = compute_features(df)
    target = (df["close"].shift(-1) > df["close"]).astype(int).values
    n = len(df)
    xgb_proba = np.full(n, 0.5)
    train_months = 6; retrain_months = 3
    train_bars = train_months * 30 * 24 * 4
    retrain_bars = retrain_months * 30 * 24 * 4
    models_trained = 0

    start = train_bars
    while start < n - 100:
        t_start = max(0, start - train_bars)
        t_end = start
        mask = ~np.isnan(feat_vals[t_start:t_end]).any(axis=1) & (target[t_start:t_end] >= 0)
        X_tr = feat_vals[t_start:t_end][mask]
        y_tr = target[t_start:t_end][mask]
        if len(X_tr) < 100:
            start += retrain_bars; continue
        model = XGBClassifier(n_estimators=100, max_depth=4, learning_rate=0.1,
                              subsample=0.8, colsample_bytree=0.8, use_label_encoder=False,
                              eval_metric="logloss", verbosity=0, random_state=42)
        model.fit(X_tr, y_tr)
        models_trained += 1
        apply_end = min(start + retrain_bars, n)
        for j in range(start, apply_end):
            if j < n and not np.any(np.isnan(feat_vals[j])):
                xgb_proba[j] = model.predict_proba(feat_vals[j:j+1])[0, 1]
        start += retrain_bars

    print(f"  XGBoost: {models_trained} models trained")

    # CMA-ES only
    r1 = simulate(df, PARAMS, None, 0)
    # Hybrid
    r2 = simulate(df, PARAMS, xgb_proba, CONF_THRESHOLD)

    return {"symbol": symbol, "cmaes": r1, "hybrid": r2}


def main():
    print("=" * 70)
    print("  Multi-Coin Validation")
    print("  Strategy: CMA-ES (MA 21/95) + XGBoost (>55%)")
    print(f"  Coins: {', '.join(SYMBOLS)}")
    print("=" * 70)

    results = []
    for sym in SYMBOLS:
        r = run_coin(sym)
        results.append(r)
        print(f"\n  {'CMA-ES only':20s}: Ret={r['cmaes']['total_ret']:+.1f}%, "
              f"Sharpe={r['cmaes']['sharpe']:.2f}, DD={r['cmaes']['max_dd']:.1f}%, "
              f"Trades={r['cmaes']['trades']}, WR={r['cmaes']['wr']:.0f}%")
        print(f"  {'Hybrid (>55%)':20s}: Ret={r['hybrid']['total_ret']:+.1f}%, "
              f"Sharpe={r['hybrid']['sharpe']:.2f}, DD={r['hybrid']['max_dd']:.1f}%, "
              f"Trades={r['hybrid']['trades']}, WR={r['hybrid']['wr']:.0f}%")

    print(f"\n{'='*90}")
    print(f"  Multi-Coin Summary")
    print(f"{'='*90}")
    print(f"{'Symbol':10s} {'':5s} {'Return%':>10s} {'Sharpe':>8s} {'MaxDD%':>8s} {'Trades':>8s} {'WR%':>6s} {'PF':>6s}")
    print("-" * 90)
    for r in results:
        sym = r["symbol"]
        for label, data in [("CMA-ES", r["cmaes"]), ("Hybrid", r["hybrid"])]:
            print(f"{sym:10s} {label:5s} {data['total_ret']:>+10.1f} {data['sharpe']:>8.2f} "
                  f"{data['max_dd']:>8.1f} {data['trades']:>8d} {data['wr']:>6.0f} {data['pf']:>6.2f}")
        print()

    # Verdict
    hybrid_wins = sum(1 for r in results if r["hybrid"]["total_ret"] > 0)
    print(f"  Hybrid profitable on {hybrid_wins}/{len(results)} coins")
    avg_ret = np.mean([r["hybrid"]["total_ret"] for r in results])
    avg_sharpe = np.mean([r["hybrid"]["sharpe"] for r in results])
    print(f"  Average: Ret={avg_ret:+.1f}%, Sharpe={avg_sharpe:.2f}")

    if hybrid_wins >= 3:
        print(f"\n  >>> VERDICT: Strategy is GENERALIZABLE across coins")
    elif hybrid_wins >= 2:
        print(f"\n  >>> VERDICT: Strategy works on SOME coins, needs per-coin tuning")
    else:
        print(f"\n  >>> VERDICT: Strategy is ETH-SPECIFIC, not generalizable")


if __name__ == "__main__":
    main()
