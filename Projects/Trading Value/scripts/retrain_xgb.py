"""XGBoost 방향 예측 모델 재학습 스크립트.

최근 6개월 데이터로 XGBoost를 재학습하고 xgb_direction_model.json을 업데이트.
3개월마다 실행 권장 (cron 또는 수동).

Usage:
    cd "Projects/Trading Value"
    py -3.12 scripts/retrain_xgb.py
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from xgboost import XGBClassifier
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "xgboost"])
    from xgboost import XGBClassifier

from sklearn.metrics import accuracy_score, roc_auc_score

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "sim_1m.sqlite"
MODEL_PATH = Path(__file__).resolve().parent.parent / "data" / "xgb_direction_model.json"
HISTORY_PATH = Path(__file__).resolve().parent.parent / "data" / "xgb_retrain_history.jsonl"
SYMBOL = "ETHUSDT"
TRAIN_MONTHS = 6


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


def compute_features(df: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
    c = df["close"]; h = df["high"]; lo = df["low"]; v = df["volume"]
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


def main():
    print("=" * 60)
    print("  XGBoost Direction Model Retrain")
    print(f"  Symbol: {SYMBOL}")
    print(f"  Training window: last {TRAIN_MONTHS} months")
    print("=" * 60)

    df = load_15m()
    print(f"  Data: {len(df)} bars ({df.index[0]} ~ {df.index[-1]})")

    # Use last TRAIN_MONTHS for training, last 1 month for validation
    train_bars = TRAIN_MONTHS * 30 * 24 * 4
    val_bars = 1 * 30 * 24 * 4

    df_train = df.iloc[-(train_bars + val_bars):-val_bars]
    df_val = df.iloc[-val_bars:]

    print(f"  Train: {len(df_train)} bars ({df_train.index[0]:%Y-%m-%d} ~ {df_train.index[-1]:%Y-%m-%d})")
    print(f"  Val:   {len(df_val)} bars ({df_val.index[0]:%Y-%m-%d} ~ {df_val.index[-1]:%Y-%m-%d})")

    # Features
    feat_all, cols = compute_features(df)
    target = (df["close"].shift(-1) > df["close"]).astype(int).values

    train_idx = df.index.isin(df_train.index)
    val_idx = df.index.isin(df_val.index)

    X_train = feat_all[train_idx]
    y_train = target[train_idx]
    X_val = feat_all[val_idx]
    y_val = target[val_idx]

    # Remove NaN rows
    mask_tr = ~np.isnan(X_train).any(axis=1)
    mask_val = ~np.isnan(X_val).any(axis=1)
    X_train = X_train[mask_tr]; y_train = y_train[mask_tr]
    X_val = X_val[mask_val]; y_val = y_val[mask_val]

    print(f"\n  Training: {len(X_train)} samples, {len(cols)} features")

    model = XGBClassifier(
        n_estimators=100, max_depth=4, learning_rate=0.1,
        subsample=0.8, colsample_bytree=0.8,
        use_label_encoder=False, eval_metric="logloss",
        verbosity=0, random_state=42,
    )
    model.fit(X_train, y_train)

    # Validate
    y_pred = model.predict(X_val)
    y_proba = model.predict_proba(X_val)[:, 1]
    acc = accuracy_score(y_val, y_pred)
    auc = roc_auc_score(y_val, y_proba)

    # High confidence
    high_conf_mask = y_proba > 0.55
    if high_conf_mask.sum() > 0:
        acc_high = accuracy_score(y_val[high_conf_mask], y_pred[high_conf_mask])
        n_high = high_conf_mask.sum()
    else:
        acc_high = 0; n_high = 0

    print(f"\n  Validation Results:")
    print(f"    Accuracy: {acc:.4f}")
    print(f"    AUC-ROC:  {auc:.4f}")
    print(f"    High conf (>55%): acc={acc_high:.4f}, n={n_high}")

    # Feature importance
    imp = model.feature_importances_
    top_idx = np.argsort(imp)[::-1][:5]
    print(f"\n  Top 5 Features:")
    for idx in top_idx:
        print(f"    {cols[idx]:20s} {imp[idx]:.4f}")

    # Save model
    old_exists = MODEL_PATH.exists()
    model.save_model(str(MODEL_PATH))
    print(f"\n  Model saved: {MODEL_PATH}")
    print(f"  {'(updated)' if old_exists else '(new)'}")

    # Log
    entry = {
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "train_period": f"{df_train.index[0]:%Y-%m-%d}~{df_train.index[-1]:%Y-%m-%d}",
        "val_period": f"{df_val.index[0]:%Y-%m-%d}~{df_val.index[-1]:%Y-%m-%d}",
        "train_samples": len(X_train),
        "accuracy": round(acc, 4),
        "auc": round(auc, 4),
        "high_conf_acc": round(acc_high, 4),
        "high_conf_n": int(n_high),
    }
    with open(HISTORY_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    print(f"\n  Done. Retrain history: {HISTORY_PATH}")


if __name__ == "__main__":
    main()
