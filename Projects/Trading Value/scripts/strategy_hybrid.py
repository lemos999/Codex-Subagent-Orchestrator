"""CMA-ES + XGBoost Hybrid Strategy Backtest

XGBoost direction predictor as entry filter on CMA-ES parametric strategy.
Walk-forward: retrain XGBoost every 3 months, apply hybrid on next 1-month window.

Usage:
    cd "Projects/Trading Value"
    py -3.12 scripts/strategy_hybrid.py
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

# ── Ensure dependencies ──────────────────────────────────────────────────────
try:
    from xgboost import XGBClassifier
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "xgboost"])
    from xgboost import XGBClassifier

# ── Config ───────────────────────────────────────────────────────────────────
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "sim_1m.sqlite"
MODEL_SAVE_PATH = Path(__file__).resolve().parent.parent / "data" / "xgb_direction_model.json"
SYMBOL = "ETHUSDT"
COMMISSION = 0.0004     # 0.04% per trade
SLIPPAGE = 0.0001       # 0.01% per trade
INITIAL_BALANCE = 10_000.0

# Walk-forward for XGBoost
XGB_TRAIN_MONTHS = 6    # rolling training window
XGB_RETRAIN_MONTHS = 3  # retrain every 3 months
XGB_TEST_MONTHS = 1     # apply on next 1-month window

# Full backtest period
BT_START = "2021-03-01"
BT_END = "2026-04-01"

# Confidence thresholds to test
CONF_THRESHOLDS = [0.52, 0.55, 0.58, 0.60]

# ── Best CMA-ES Parameters (from optimization) ──────────────────────────────
CMAES_PARAMS = {
    "ma_fast": 21,
    "ma_slow": 95,
    "rsi_oversold": 28.3,
    "rsi_overbought": 67.5,
    "vol_filter": 2.89,
    "atr_stop_mult": 3.89,
    "atr_tp_mult": 3.75,
    "trail_start": 4.89,
    "trail_step": 0.31,
    "cooldown_bars": 5,
    "risk_per_trade": 0.019,
    "leverage": 1.6,
    "allow_short": False,
}


# ── Data Loading ─────────────────────────────────────────────────────────────
def load_15m_data() -> pd.DataFrame:
    """Load 1m data from sqlite and resample to 15m candles."""
    conn = sqlite3.connect(str(DB_PATH))
    df = pd.read_sql_query(
        "SELECT datetime, open, high, low, close, volume "
        "FROM ohlcv_1m WHERE symbol=? ORDER BY datetime",
        conn, params=(SYMBOL,),
    )
    conn.close()
    df["datetime"] = pd.to_datetime(df["datetime"])
    df.set_index("datetime", inplace=True)

    df_15m = df.resample("15min").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }).dropna()

    print(f"[데이터] {len(df_15m):,}개 15분봉 로드 ({df_15m.index[0]} ~ {df_15m.index[-1]})")
    return df_15m


# ── Feature Engineering (same as timeframe_predictability.py) ────────────────
def compute_xgb_features(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Compute XGBoost prediction features. Returns (df_with_features, feature_col_names)."""
    c = df["close"]
    h = df["high"]
    lo = df["low"]
    v = df["volume"]

    feat = pd.DataFrame(index=df.index)

    # MA positions (price vs MA)
    for w in [5, 20, 50, 200]:
        ma = c.rolling(w).mean()
        feat[f"ma{w}_pos"] = (c - ma) / ma.where(ma > 0, 1.0)

    # MA crossovers
    ma5 = c.rolling(5).mean()
    ma20 = c.rolling(20).mean()
    ma50 = c.rolling(50).mean()
    ma200 = c.rolling(200).mean()
    feat["cross_5_20"] = (ma5 - ma20) / ma20.where(ma20 > 0, 1.0)
    feat["cross_20_50"] = (ma20 - ma50) / ma50.where(ma50 > 0, 1.0)
    feat["cross_50_200"] = (ma50 - ma200) / ma200.where(ma200 > 0, 1.0)

    # RSI(14)
    delta = c.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    feat["rsi14"] = 100 - (100 / (1 + rs))

    # ATR(14) normalized
    tr = pd.concat([
        h - lo,
        (h - c.shift(1)).abs(),
        (lo - c.shift(1)).abs(),
    ], axis=1).max(axis=1)
    atr14 = tr.rolling(14).mean()
    feat["atr_norm"] = atr14 / c.where(c > 0, 1.0)

    # Donchian channel position
    dc_high = h.rolling(20).max()
    dc_low = lo.rolling(20).min()
    dc_range = dc_high - dc_low
    feat["donchian_pos"] = ((c - dc_low) / dc_range.where(dc_range > 0, 1.0))

    # Volume ratio
    vol_ma20 = v.rolling(20).mean()
    feat["vol_ratio"] = v / vol_ma20.where(vol_ma20 > 0, 1.0)

    # Momentum (1-bar, 4-bar, 12-bar returns)
    feat["mom_1"] = c.pct_change(1)
    feat["mom_4"] = c.pct_change(4)
    feat["mom_12"] = c.pct_change(12)

    # Hour of day (sin/cos)
    hour = df.index.hour + df.index.minute / 60.0
    feat["hour_sin"] = np.sin(2 * np.pi * hour / 24)
    feat["hour_cos"] = np.cos(2 * np.pi * hour / 24)

    # Day of week (sin/cos)
    dow = df.index.dayofweek.astype(float)
    feat["dow_sin"] = np.sin(2 * np.pi * dow / 7)
    feat["dow_cos"] = np.cos(2 * np.pi * dow / 7)

    feature_cols = list(feat.columns)
    out = df.join(feat)
    return out, feature_cols


# ── CMA-ES Strategy Indicators (vectorized) ─────────────────────────────────
def compute_cmaes_indicators(df: pd.DataFrame, p: dict) -> dict:
    """Precompute all CMA-ES strategy indicators as numpy arrays."""
    close = df["close"].values.astype(np.float64)
    high = df["high"].values.astype(np.float64)
    low = df["low"].values.astype(np.float64)
    volume = df["volume"].values.astype(np.float64)
    n = len(close)

    # MA fast / slow
    ma_f = pd.Series(close).rolling(p["ma_fast"]).mean().values
    ma_s = pd.Series(close).rolling(p["ma_slow"]).mean().values

    # RSI(14)
    delta = np.diff(close, prepend=close[0])
    gain = np.where(delta > 0, delta, 0.0)
    loss_arr = np.where(delta < 0, -delta, 0.0)
    avg_gain = pd.Series(gain).rolling(14).mean().values
    avg_loss = pd.Series(loss_arr).rolling(14).mean().values
    with np.errstate(divide="ignore", invalid="ignore"):
        rs = avg_gain / np.where(avg_loss == 0, np.nan, avg_loss)
        rsi = 100.0 - 100.0 / (1.0 + rs)
    rsi = np.nan_to_num(rsi, nan=50.0)

    # ATR(14)
    tr = np.maximum(
        high - low,
        np.maximum(
            np.abs(high - np.roll(close, 1)),
            np.abs(low - np.roll(close, 1)),
        ),
    )
    tr[0] = high[0] - low[0]
    atr = pd.Series(tr).rolling(14).mean().values

    # Volume MA(20)
    vol_ma = pd.Series(volume).rolling(20).mean().values

    return {
        "close": close,
        "high": high,
        "low": low,
        "volume": volume,
        "ma_fast": ma_f,
        "ma_slow": ma_s,
        "rsi": rsi,
        "atr": atr,
        "vol_ma": vol_ma,
        "n": n,
    }


# ── Simulation Result ────────────────────────────────────────────────────────
@dataclass
class SimResult:
    total_return_pct: float
    annual_return_pct: float
    sharpe_ratio: float
    max_drawdown_pct: float
    trades: int
    wins: int
    losses: int
    win_rate: float
    profit_factor: float
    final_balance: float
    equity_curve: np.ndarray | None = None
    trade_log: list | None = None


# ── Hybrid Simulation Engine ─────────────────────────────────────────────────
def simulate_hybrid(
    df: pd.DataFrame,
    p: dict,
    xgb_proba: np.ndarray | None,
    conf_threshold: float,
    record_equity: bool = False,
) -> SimResult:
    """Run CMA-ES strategy with optional XGBoost confidence gate.

    If xgb_proba is None, runs CMA-ES only (no filter).
    """
    ind = compute_cmaes_indicators(df, p)
    close = ind["close"]
    high = ind["high"]
    low = ind["low"]
    volume = ind["volume"]
    ma_f = ind["ma_fast"]
    ma_s = ind["ma_slow"]
    rsi = ind["rsi"]
    atr = ind["atr"]
    vol_ma = ind["vol_ma"]
    n = ind["n"]

    balance = INITIAL_BALANCE
    peak_balance = INITIAL_BALANCE
    position = 0       # 0=flat, 1=long, -1=short
    entry_price = 0.0
    stop_price = 0.0
    tp_price = 0.0
    trail_active = False
    trail_price = 0.0
    last_trade_bar = -999
    consecutive_losses = 0
    size_mult = 1.0  # dynamic position sizing multiplier

    equity = np.empty(n, dtype=np.float64) if record_equity else None
    if record_equity:
        equity[0] = balance
    trade_returns: list[float] = []
    trade_log: list[dict] = []

    warmup = max(p["ma_slow"], 200, 20) + 1

    for i in range(1, n):
        price = close[i]
        bar_high = high[i]
        bar_low = low[i]

        # ── Check exit conditions if in position ─────────────────────────
        if position != 0:
            exited = False
            exit_price = 0.0

            if position == 1:  # long
                if bar_low <= stop_price:
                    exit_price = stop_price
                    exited = True
                elif bar_high >= tp_price:
                    exit_price = tp_price
                    exited = True
                else:
                    profit_dist = price - entry_price
                    trail_threshold = p["trail_start"] * atr[i] if not np.isnan(atr[i]) else 1e9
                    if profit_dist >= trail_threshold:
                        trail_active = True
                    if trail_active:
                        new_trail = price - p["trail_step"] * (atr[i] if not np.isnan(atr[i]) else 0)
                        if new_trail > trail_price:
                            trail_price = new_trail
                        if bar_low <= trail_price:
                            exit_price = trail_price
                            exited = True

            elif position == -1:  # short
                if bar_high >= stop_price:
                    exit_price = stop_price
                    exited = True
                elif bar_low <= tp_price:
                    exit_price = tp_price
                    exited = True
                else:
                    profit_dist = entry_price - price
                    trail_threshold = p["trail_start"] * atr[i] if not np.isnan(atr[i]) else 1e9
                    if profit_dist >= trail_threshold:
                        trail_active = True
                    if trail_active:
                        new_trail = price + p["trail_step"] * (atr[i] if not np.isnan(atr[i]) else 0)
                        if new_trail < trail_price or trail_price == 0:
                            trail_price = new_trail
                        if bar_high >= trail_price:
                            exit_price = trail_price
                            exited = True

            if exited:
                if position == 1:
                    pnl_pct = (exit_price / entry_price - 1.0) * p["leverage"] * size_mult
                else:
                    pnl_pct = (1.0 - exit_price / entry_price) * p["leverage"] * size_mult
                pnl_pct -= (COMMISSION + SLIPPAGE) * p["leverage"] * size_mult
                trade_returns.append(pnl_pct)
                trade_log.append({
                    "bar": i,
                    "side": "LONG" if position == 1 else "SHORT",
                    "entry": entry_price,
                    "exit": exit_price,
                    "pnl_pct": pnl_pct,
                    "size_mult": size_mult,
                    "dt": str(df.index[i]),
                })
                balance *= (1.0 + pnl_pct)
                # Track consecutive losses for dynamic sizing
                if pnl_pct < 0:
                    consecutive_losses += 1
                else:
                    consecutive_losses = 0
                # Update peak for DD-based sizing
                if balance > peak_balance:
                    peak_balance = balance
                if balance <= 0:
                    balance = 0.0
                    if record_equity:
                        equity[i:] = 0.0
                    break
                position = 0
                last_trade_bar = i

        # ── Check entry conditions if flat ────────────────────────────────
        if position == 0 and i >= warmup:
            bars_since = i - last_trade_bar
            if bars_since < p["cooldown_bars"]:
                if record_equity:
                    equity[i] = balance
                continue

            cur_atr = atr[i] if not np.isnan(atr[i]) else 0.0
            if cur_atr <= 0:
                if record_equity:
                    equity[i] = balance
                continue

            # Volume filter
            cur_vol_ma = vol_ma[i] if not np.isnan(vol_ma[i]) else 0.0
            vol_ok = volume[i] > p["vol_filter"] * cur_vol_ma if cur_vol_ma > 0 else False

            ma_f_val = ma_f[i]
            ma_s_val = ma_s[i]
            if np.isnan(ma_f_val) or np.isnan(ma_s_val):
                if record_equity:
                    equity[i] = balance
                continue

            # ── XGBoost confidence gate ───────────────────────────────────
            xgb_ok = True
            if xgb_proba is not None:
                # For LONG: need bullish confidence > threshold
                # For SHORT: need bearish confidence > threshold
                if ma_f_val > ma_s_val:
                    # Would be a LONG signal
                    xgb_ok = xgb_proba[i] > conf_threshold
                elif p["allow_short"] and ma_f_val < ma_s_val:
                    # Would be a SHORT signal
                    xgb_ok = (1.0 - xgb_proba[i]) > conf_threshold
                else:
                    xgb_ok = False

            # Dynamic position sizing based on DD and consecutive losses
            dd_pct = (peak_balance - balance) / peak_balance * 100 if peak_balance > 0 else 0
            size_mult = 1.0
            if dd_pct > 25:
                size_mult = 0.25  # severe DD: 25% size
            elif dd_pct > 15:
                size_mult = 0.50  # moderate DD: 50% size
            if consecutive_losses >= 3:
                size_mult = min(size_mult, 0.50)  # 3+ losses: cap at 50%

            # LONG signal
            if (ma_f_val > ma_s_val
                    and rsi[i] < p["rsi_oversold"]
                    and vol_ok
                    and xgb_ok):
                position = 1
                entry_price = price * (1.0 + COMMISSION + SLIPPAGE)
                stop_dist = p["atr_stop_mult"] * cur_atr
                stop_price = price - stop_dist
                tp_price = price + p["atr_tp_mult"] * cur_atr
                trail_active = False
                trail_price = stop_price
                last_trade_bar = i

            # SHORT signal
            elif (p["allow_short"]
                  and ma_f_val < ma_s_val
                  and rsi[i] > p["rsi_overbought"]
                  and vol_ok
                  and xgb_ok):
                position = -1
                entry_price = price * (1.0 - COMMISSION - SLIPPAGE)
                stop_dist = p["atr_stop_mult"] * cur_atr
                stop_price = price + stop_dist
                tp_price = price - p["atr_tp_mult"] * cur_atr
                trail_active = False
                trail_price = stop_price
                last_trade_bar = i

        if record_equity:
            equity[i] = balance

    # ── Compute statistics ────────────────────────────────────────────────
    total_return_pct = (balance / INITIAL_BALANCE - 1.0) * 100.0

    # Annualized return
    n_bars = n
    years = n_bars / 35040.0  # 15m bars per year
    if years > 0 and balance > 0:
        annual_return_pct = ((balance / INITIAL_BALANCE) ** (1.0 / years) - 1.0) * 100.0
    else:
        annual_return_pct = 0.0

    # Sharpe ratio (annualized from 15m bars)
    if record_equity and equity is not None and len(equity) > 1 and equity[0] > 0:
        rets = np.diff(equity) / np.where(equity[:-1] > 0, equity[:-1], 1.0)
        ret_std = rets.std()
        sharpe = (rets.mean() / ret_std * np.sqrt(35040)) if ret_std > 0 else 0.0
    else:
        sharpe = _compute_sharpe_from_balance_trades(trade_returns, n_bars)

    # Max drawdown
    if record_equity and equity is not None and len(equity) > 0 and equity.max() > 0:
        peak = np.maximum.accumulate(equity)
        dd = (equity - peak) / np.where(peak > 0, peak, 1.0)
        max_dd = dd.min() * 100.0
    else:
        max_dd = _estimate_max_dd(trade_returns)

    # Trade stats
    n_trades = len(trade_returns)
    if n_trades > 0:
        wins_arr = [r for r in trade_returns if r > 0]
        losses_arr = [r for r in trade_returns if r <= 0]
        n_wins = len(wins_arr)
        n_losses = len(losses_arr)
        win_rate = n_wins / n_trades * 100.0
        gross_profit = sum(wins_arr) if wins_arr else 0.0
        gross_loss = abs(sum(losses_arr)) if losses_arr else 0.0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
    else:
        n_wins = n_losses = 0
        win_rate = 0.0
        profit_factor = 0.0

    return SimResult(
        total_return_pct=total_return_pct,
        annual_return_pct=annual_return_pct,
        sharpe_ratio=sharpe,
        max_drawdown_pct=max_dd,
        trades=n_trades,
        wins=n_wins,
        losses=n_losses,
        win_rate=win_rate,
        profit_factor=profit_factor,
        final_balance=balance,
        equity_curve=equity,
        trade_log=trade_log,
    )


def _compute_sharpe_from_balance_trades(trade_returns: list[float], n_bars: int) -> float:
    """Estimate Sharpe from trade returns when equity curve not recorded."""
    if not trade_returns:
        return 0.0
    tr = np.array(trade_returns)
    # Approximate: spread returns over n_bars
    avg_ret_per_bar = tr.sum() / max(n_bars, 1)
    # Rough std per bar
    if len(tr) > 1:
        std_per_bar = tr.std() * np.sqrt(len(tr) / max(n_bars, 1))
    else:
        return 0.0
    if std_per_bar > 0:
        return avg_ret_per_bar / std_per_bar * np.sqrt(35040)
    return 0.0


def _estimate_max_dd(trade_returns: list[float]) -> float:
    """Estimate max drawdown from trade returns (when equity not tracked)."""
    if not trade_returns:
        return 0.0
    cumulative = np.cumprod(1.0 + np.array(trade_returns))
    peak = np.maximum.accumulate(cumulative)
    dd = (cumulative - peak) / peak
    return dd.min() * 100.0


# ── Walk-Forward XGBoost + Hybrid Backtest ───────────────────────────────────
def run_walk_forward_hybrid(
    df_15m: pd.DataFrame,
    conf_threshold: float,
    verbose: bool = True,
) -> SimResult:
    """Full walk-forward backtest.

    1. XGBoost trained on rolling 6-month window, retrained every 3 months.
    2. Predict_proba applied to each bar.
    3. CMA-ES strategy with XGBoost gate on the full period.
    """
    # Compute features for entire dataset
    df_feat, feature_cols = compute_xgb_features(df_15m)

    # Create target: next-1-bar 15m return sign
    df_feat["target"] = (df_feat["close"].shift(-1) > df_feat["close"]).astype(int)
    df_feat = df_feat.dropna(subset=feature_cols + ["target"])

    # Build XGBoost probability array via walk-forward
    xgb_proba = np.full(len(df_feat), 0.5)  # default: neutral

    dates = df_feat.index
    min_date = dates.min()
    max_date = dates.max()

    # Start: need at least 6 months of training data
    first_pred_date = min_date + pd.DateOffset(months=XGB_TRAIN_MONTHS)

    # Walk forward: retrain every 3 months
    train_start = min_date
    retrain_date = first_pred_date
    last_model = None
    windows_trained = 0

    while retrain_date < max_date:
        # Training window: retrain_date - 6 months to retrain_date
        t_start = retrain_date - pd.DateOffset(months=XGB_TRAIN_MONTHS)
        t_end = retrain_date
        next_retrain = retrain_date + pd.DateOffset(months=XGB_RETRAIN_MONTHS)

        train_mask = (df_feat.index >= t_start) & (df_feat.index < t_end)
        X_train = df_feat.loc[train_mask, feature_cols].values
        y_train = df_feat.loc[train_mask, "target"].values

        if len(X_train) >= 100:
            model = XGBClassifier(
                n_estimators=300,
                max_depth=5,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                reg_alpha=0.1,
                reg_lambda=1.0,
                min_child_weight=30,
                random_state=42,
                eval_metric="logloss",
                n_jobs=-1,
                verbosity=0,
            )
            model.fit(X_train, y_train, verbose=False)
            last_model = model
            windows_trained += 1

            if verbose:
                print(f"    XGBoost 학습 #{windows_trained}: "
                      f"{t_start.strftime('%Y-%m')} ~ {t_end.strftime('%Y-%m')} "
                      f"({len(X_train):,} samples)")

        # Apply predictions from retrain_date to next_retrain
        if last_model is not None:
            pred_mask = (df_feat.index >= t_end) & (df_feat.index < next_retrain)
            X_pred = df_feat.loc[pred_mask, feature_cols].values
            if len(X_pred) > 0:
                proba = last_model.predict_proba(X_pred)[:, 1]
                # Get integer positions for these rows
                idx_positions = np.where(pred_mask.values if hasattr(pred_mask, 'values') else pred_mask)[0]
                xgb_proba[idx_positions] = proba

        retrain_date = next_retrain

    if verbose:
        print(f"    총 {windows_trained}개 XGBoost 모델 학습 완료")
        # Show proba distribution
        active_mask = xgb_proba != 0.5
        if active_mask.any():
            active_proba = xgb_proba[active_mask]
            print(f"    XGBoost 예측 분포: "
                  f"mean={active_proba.mean():.3f}, "
                  f"std={active_proba.std():.3f}, "
                  f">{conf_threshold:.0%}: {(active_proba > conf_threshold).sum():,}건")

    # Save the last model
    if last_model is not None:
        last_model.save_model(str(MODEL_SAVE_PATH))
        if verbose:
            print(f"    최종 XGBoost 모델 저장: {MODEL_SAVE_PATH}")

    # Run hybrid simulation
    result = simulate_hybrid(
        df_feat, CMAES_PARAMS, xgb_proba, conf_threshold, record_equity=True,
    )

    return result


def run_cmaes_only(df_15m: pd.DataFrame) -> SimResult:
    """Run CMA-ES strategy without XGBoost filter (baseline)."""
    df_feat, _ = compute_xgb_features(df_15m)
    df_feat = df_feat.dropna()
    result = simulate_hybrid(
        df_feat, CMAES_PARAMS, None, 0.0, record_equity=True,
    )
    return result


# ── Monthly Breakdown ────────────────────────────────────────────────────────
def monthly_breakdown(result: SimResult, df: pd.DataFrame) -> pd.DataFrame:
    """Compute monthly returns from trade log."""
    if not result.trade_log:
        return pd.DataFrame()

    trades = pd.DataFrame(result.trade_log)
    trades["dt"] = pd.to_datetime(trades["dt"])
    trades["month"] = trades["dt"].dt.to_period("M")

    monthly = trades.groupby("month").agg(
        n_trades=("pnl_pct", "count"),
        total_pnl=("pnl_pct", "sum"),
        avg_pnl=("pnl_pct", "mean"),
        win_rate=("pnl_pct", lambda x: (x > 0).mean() * 100),
    ).reset_index()
    monthly["total_pnl_pct"] = monthly["total_pnl"] * 100
    return monthly


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    t0 = time.time()

    print("=" * 90)
    print("  CMA-ES + XGBoost 하이브리드 전략 백테스트")
    print(f"  심볼: {SYMBOL} | 타임프레임: 15m")
    print(f"  커미션: {COMMISSION*100:.2f}% + 슬리피지: {SLIPPAGE*100:.2f}%")
    print(f"  기간: {BT_START} ~ {BT_END}")
    print(f"  XGBoost: {XGB_TRAIN_MONTHS}개월 학습, {XGB_RETRAIN_MONTHS}개월마다 재학습")
    print(f"  신뢰도 임계값: {CONF_THRESHOLDS}")
    print("=" * 90)

    # ── Load data ─────────────────────────────────────────────────────────
    df_all = load_15m_data()
    df = df_all[(df_all.index >= BT_START) & (df_all.index < BT_END)].copy()
    print(f"  백테스트 기간: {len(df):,}개 봉 ({df.index[0]} ~ {df.index[-1]})")

    # ── CMA-ES only baseline ─────────────────────────────────────────────
    print("\n" + "-" * 90)
    print("  [1/3] CMA-ES 단독 (베이스라인)")
    print("-" * 90)
    r_base = run_cmaes_only(df)
    print(f"    수익률: {r_base.total_return_pct:+.2f}%  |  연수익: {r_base.annual_return_pct:+.2f}%  |  "
          f"샤프: {r_base.sharpe_ratio:.2f}")
    print(f"    최대DD: {r_base.max_drawdown_pct:.2f}%  |  거래: {r_base.trades}건  |  "
          f"승률: {r_base.win_rate:.1f}%  |  PF: {r_base.profit_factor:.2f}")

    # ── Hybrid at each threshold ─────────────────────────────────────────
    print("\n" + "-" * 90)
    print("  [2/3] 하이브리드 전략 (각 신뢰도 임계값)")
    print("-" * 90)

    hybrid_results: dict[float, SimResult] = {}

    for thresh in CONF_THRESHOLDS:
        print(f"\n  ── 신뢰도 임계값: {thresh:.0%} ──")
        r = run_walk_forward_hybrid(df, thresh, verbose=True)
        hybrid_results[thresh] = r
        print(f"    수익률: {r.total_return_pct:+.2f}%  |  연수익: {r.annual_return_pct:+.2f}%  |  "
              f"샤프: {r.sharpe_ratio:.2f}")
        print(f"    최대DD: {r.max_drawdown_pct:.2f}%  |  거래: {r.trades}건  |  "
              f"승률: {r.win_rate:.1f}%  |  PF: {r.profit_factor:.2f}")

    # ── Comparison Table ─────────────────────────────────────────────────
    print("\n" + "=" * 110)
    print("  [3/3] 비교 테이블: CMA-ES only vs Hybrid")
    print("=" * 110)

    header = (f"{'전략':22s} {'총수익%':>10s} {'연수익%':>10s} {'샤프':>8s} "
              f"{'최대DD%':>10s} {'거래수':>8s} {'승률%':>8s} {'PF':>8s}")
    print(header)
    print("-" * 110)

    all_results = {"CMA-ES only": r_base}
    for thresh in CONF_THRESHOLDS:
        all_results[f"Hybrid (>{thresh:.0%})"] = hybrid_results[thresh]

    for name, r in all_results.items():
        print(f"{name:22s} {r.total_return_pct:>+10.2f} {r.annual_return_pct:>+10.2f} "
              f"{r.sharpe_ratio:>8.2f} {r.max_drawdown_pct:>10.2f} {r.trades:>8d} "
              f"{r.win_rate:>8.1f} {r.profit_factor:>8.2f}")

    # ── Best threshold selection ─────────────────────────────────────────
    print("\n" + "-" * 90)
    print("  최적 임계값 선택")
    print("-" * 90)

    best_thresh = None
    best_sharpe = -999
    for thresh, r in hybrid_results.items():
        if r.sharpe_ratio > best_sharpe and r.trades >= 10:
            best_sharpe = r.sharpe_ratio
            best_thresh = thresh

    if best_thresh is not None:
        best_r = hybrid_results[best_thresh]
        print(f"  최적 임계값: {best_thresh:.0%}")
        print(f"  샤프: {best_r.sharpe_ratio:.2f}  |  수익률: {best_r.total_return_pct:+.2f}%  |  "
              f"거래: {best_r.trades}건")

        # Compare with baseline
        sharpe_improve = best_r.sharpe_ratio - r_base.sharpe_ratio
        dd_improve = best_r.max_drawdown_pct - r_base.max_drawdown_pct
        print(f"  vs CMA-ES only: Sharpe {sharpe_improve:+.2f}, DD {dd_improve:+.2f}%p")

        # ── Monthly breakdown for best ───────────────────────────────────
        print("\n" + "-" * 90)
        print(f"  월별 수익 분석 (Hybrid >{best_thresh:.0%})")
        print("-" * 90)

        monthly = monthly_breakdown(best_r, df)
        if not monthly.empty:
            print(f"  {'월':10s} {'거래수':>6s} {'총PnL%':>10s} {'평균PnL%':>10s} {'승률%':>8s}")
            print("  " + "-" * 50)
            for _, row in monthly.iterrows():
                print(f"  {str(row['month']):10s} {row['n_trades']:>6d} "
                      f"{row['total_pnl_pct']:>+10.2f} {row['avg_pnl']*100:>+10.3f} "
                      f"{row['win_rate']:>8.1f}")

            # Summary stats
            pos_months = (monthly["total_pnl"] > 0).sum()
            neg_months = (monthly["total_pnl"] <= 0).sum()
            print(f"\n  수익 월: {pos_months}  |  손실 월: {neg_months}  |  "
                  f"월 승률: {pos_months/(pos_months+neg_months)*100:.0f}%")
        else:
            print("  거래 없음")
    else:
        print("  유효한 하이브리드 결과 없음 (거래 부족)")

    # ── Verdict ───────────────────────────────────────────────────────────
    print("\n" + "=" * 90)
    print("  최종 판정")
    print("=" * 90)

    if best_thresh is not None:
        best_r = hybrid_results[best_thresh]
        issues = []
        goods = []

        if best_r.sharpe_ratio > r_base.sharpe_ratio:
            goods.append(f"하이브리드 Sharpe ({best_r.sharpe_ratio:.2f}) > CMA-ES ({r_base.sharpe_ratio:.2f})")
        else:
            issues.append(f"하이브리드 Sharpe ({best_r.sharpe_ratio:.2f}) <= CMA-ES ({r_base.sharpe_ratio:.2f})")

        if best_r.total_return_pct > r_base.total_return_pct:
            goods.append(f"하이브리드 수익률 ({best_r.total_return_pct:+.2f}%) > CMA-ES ({r_base.total_return_pct:+.2f}%)")
        else:
            issues.append(f"하이브리드 수익률 ({best_r.total_return_pct:+.2f}%) <= CMA-ES ({r_base.total_return_pct:+.2f}%)")

        if best_r.max_drawdown_pct > r_base.max_drawdown_pct:
            goods.append(f"하이브리드 DD ({best_r.max_drawdown_pct:.1f}%) < CMA-ES ({r_base.max_drawdown_pct:.1f}%)")
        else:
            issues.append(f"하이브리드 DD ({best_r.max_drawdown_pct:.1f}%) >= CMA-ES ({r_base.max_drawdown_pct:.1f}%)")

        if best_r.win_rate > r_base.win_rate:
            goods.append(f"하이브리드 승률 ({best_r.win_rate:.1f}%) > CMA-ES ({r_base.win_rate:.1f}%)")

        if best_r.trades >= 20:
            goods.append(f"충분한 거래 수 ({best_r.trades}건)")
        else:
            issues.append(f"거래 수 부족 ({best_r.trades}건 < 20)")

        print()
        for g in goods:
            print(f"  [PASS] {g}")
        for issue in issues:
            print(f"  [FAIL] {issue}")

        print()
        if len(goods) >= 3 and len(issues) <= 1:
            print(f"  >>> 판정: XGBoost 필터 유효. 임계값 {best_thresh:.0%}로 배포 권장.")
            print(f"       strategy_deploy.py에서 이 설정 사용 가능.")
        elif len(goods) >= 2:
            print(f"  >>> 판정: XGBoost 필터 부분 유효. 추가 검증 후 소규모 배포 권장.")
        else:
            print(f"  >>> 판정: XGBoost 필터 무효. CMA-ES 단독이 더 나음.")
            print(f"       XGBoost 피처/학습 방식 재설계 필요.")
    else:
        print("  >>> 판정: 충분한 데이터/거래 없음. 판단 불가.")

    total_time = time.time() - t0
    print(f"\n  총 소요 시간: {total_time:.0f}초 ({total_time/60:.1f}분)")


if __name__ == "__main__":
    main()
