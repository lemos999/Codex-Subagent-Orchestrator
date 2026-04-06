"""Test whether TradingEnvV2's observation features can predict price direction.

Loads ETHUSDT 1m data (2023-01-01 to 2024-01-01), builds features approximating
the 35-dim observation vector, labels 5-min-ahead direction, and trains XGBoost.

Key question: can these features beat 50% accuracy on held-out data?
"""
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, classification_report, roc_auc_score

# ── Load data ──────────────────────────────────────────────────────────────
DB = Path(__file__).resolve().parent.parent / "data" / "sim_1m.sqlite"
conn = sqlite3.connect(str(DB))

df = pd.read_sql_query(
    """
    SELECT timestamp, datetime, open, high, low, close, volume
    FROM ohlcv_1m
    WHERE symbol = 'ETHUSDT'
      AND datetime >= '2023-01-01'
      AND datetime < '2024-01-01'
    ORDER BY timestamp
    """,
    conn,
)
conn.close()

print(f"Loaded {len(df):,} rows  ({df['datetime'].iloc[0]} → {df['datetime'].iloc[-1]})")

# ── Build features (approximating the 35-dim obs) ─────────────────────────
c = df["close"].values.astype(np.float64)
h = df["high"].values.astype(np.float64)
l = df["low"].values.astype(np.float64)
v = df["volume"].values.astype(np.float64)
o = df["open"].values.astype(np.float64)

# Moving averages (normalized as close/MA - 1)
for w in [5, 20, 50, 200]:
    ma = pd.Series(c).rolling(w).mean().values
    df[f"ma{w}_dev"] = (c - ma) / np.where(ma > 0, ma, 1.0)

# RSI 14
delta = pd.Series(c).diff()
gain = delta.clip(lower=0).rolling(14).mean()
loss = (-delta.clip(upper=0)).rolling(14).mean()
rs = gain / loss.replace(0, np.nan)
df["rsi14"] = (100 - (100 / (1 + rs))) / 100.0  # normalize to [0,1]

# ATR 14
tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(l - np.roll(c, 1))))
tr[0] = h[0] - l[0]
atr14 = pd.Series(tr).rolling(14).mean().values
df["atr_norm"] = atr14 / np.where(c > 0, c, 1.0)  # ATR/close

# Donchian 20 (position within channel)
dc_high = pd.Series(h).rolling(20).max().values
dc_low = pd.Series(l).rolling(20).min().values
dc_range = dc_high - dc_low
df["donchian_pos"] = np.where(dc_range > 0, (c - dc_low) / dc_range, 0.5)

# Last 5 bar returns (normalized by ATR)
for j in range(1, 6):
    ret = (c - np.roll(c, j))
    ret[:j] = 0
    df[f"ret_{j}"] = ret / np.where(atr14 > 0, atr14, 1.0)

# Volume ratio (current / SMA20)
vol_ma20 = pd.Series(v).rolling(20).mean().values
df["vol_ratio"] = v / np.where(vol_ma20 > 0, vol_ma20, 1.0)

# Momentum features (1h = 60 bars, 4h = 240 bars)
for span, name in [(60, "1h"), (240, "4h")]:
    ret_span = (c - np.roll(c, span))
    ret_span[:span] = 0
    df[f"trend_{name}"] = ret_span / np.where(atr14 > 0, atr14, 1.0)

# VWAP deviation (rolling 30-bar)
cum_pv = pd.Series(c * v).rolling(30).sum().values
cum_v = pd.Series(v).rolling(30).sum().values
vwap30 = cum_pv / np.where(cum_v > 0, cum_v, 1.0)
df["vwap_dev"] = (c - vwap30) / np.where(c > 0, c, 1.0)

# Volume z-score (5-bar)
vol_mean5 = pd.Series(v).rolling(5).mean().values
vol_std5 = pd.Series(v).rolling(5).std().values
df["vol_zscore5"] = (v - vol_mean5) / np.where(vol_std5 > 0, vol_std5, 1.0)

# Bar range / ATR (volatility ratio)
df["bar_range_atr"] = (h - l) / np.where(atr14 > 0, atr14, 1.0)

# Higher-timeframe EMAs for cloud-like features
for span in [9, 26, 52]:
    ema = pd.Series(c).ewm(span=span * 30, adjust=False).mean().values  # scale to ~30m equiv
    df[f"ema{span}_dev"] = (c - ema) / np.where(ema > 0, ema, 1.0)

# TK cross proxy (EMA9 - EMA26 direction)
ema9 = pd.Series(c).ewm(span=9, adjust=False).mean().values
ema26 = pd.Series(c).ewm(span=26, adjust=False).mean().values
df["tk_cross"] = np.sign(ema9 - ema26)

# ── Label: price direction 5 minutes later ─────────────────────────────────
HORIZON = 5
df["future_close"] = df["close"].shift(-HORIZON)
df["label"] = (df["future_close"] > df["close"]).astype(int)

# ── Clean up ───────────────────────────────────────────────────────────────
feature_cols = [
    "ma5_dev", "ma20_dev", "ma50_dev", "ma200_dev",
    "rsi14", "atr_norm", "donchian_pos",
    "ret_1", "ret_2", "ret_3", "ret_4", "ret_5",
    "vol_ratio", "trend_1h", "trend_4h",
    "vwap_dev", "vol_zscore5", "bar_range_atr",
    "ema9_dev", "ema26_dev", "ema52_dev", "tk_cross",
]

# Drop rows with NaN (warmup period + future label)
df_clean = df.dropna(subset=feature_cols + ["label"]).copy()
df_clean["label"] = df_clean["label"].astype(int)
print(f"After cleanup: {len(df_clean):,} rows, {len(feature_cols)} features")
print(f"Label distribution: {df_clean['label'].value_counts().to_dict()}")

# ── Train/test split (chronological 80/20) ─────────────────────────────────
split_idx = int(len(df_clean) * 0.8)
train = df_clean.iloc[:split_idx]
test = df_clean.iloc[split_idx:]

X_train = train[feature_cols].values
y_train = train["label"].values
X_test = test[feature_cols].values
y_test = test["label"].values

print(f"\nTrain: {len(train):,}  Test: {len(test):,}")
print(f"Train label balance: {y_train.mean():.4f}")
print(f"Test label balance:  {y_test.mean():.4f}")

# ── Train XGBoost ──────────────────────────────────────────────────────────
model = XGBClassifier(
    n_estimators=500,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    reg_alpha=0.1,
    reg_lambda=1.0,
    min_child_weight=50,
    random_state=42,
    eval_metric="logloss",
    early_stopping_rounds=30,
    n_jobs=-1,
)

model.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)],
    verbose=False,
)

# ── Evaluate ───────────────────────────────────────────────────────────────
y_pred = model.predict(X_test)
y_proba = model.predict_proba(X_test)[:, 1]

acc = accuracy_score(y_test, y_pred)
auc = roc_auc_score(y_test, y_proba)

print("\n" + "=" * 60)
print("RESULTS: Can the observation features predict 5-min direction?")
print("=" * 60)
print(f"Test Accuracy:  {acc:.4f}  ({'ABOVE' if acc > 0.55 else 'BELOW'} 55%)")
print(f"ROC AUC:        {auc:.4f}")
print(f"Baseline (coin flip): {y_test.mean():.4f}")
print(f"Lift over baseline:   {acc - y_test.mean():+.4f}")
print()
print(classification_report(y_test, y_pred, target_names=["DOWN", "UP"]))

# ── Feature importance ─────────────────────────────────────────────────────
importances = model.feature_importances_
sorted_idx = np.argsort(importances)[::-1]

print("\nTop 10 feature importances:")
for i in range(min(10, len(feature_cols))):
    idx = sorted_idx[i]
    print(f"  {feature_cols[idx]:20s}  {importances[idx]:.4f}")

# ── Additional tests ───────────────────────────────────────────────────────
# Test with different horizons
print("\n" + "=" * 60)
print("HORIZON SWEEP: accuracy at different lookahead windows")
print("=" * 60)
for hz in [1, 3, 5, 10, 15, 30, 60]:
    df_clean[f"label_{hz}"] = (df["close"].shift(-hz) > df["close"]).astype(float)
    tmp = df_clean.dropna(subset=[f"label_{hz}"])
    if len(tmp) < 1000:
        continue
    sp = int(len(tmp) * 0.8)
    Xtr = tmp.iloc[:sp][feature_cols].values
    ytr = tmp.iloc[:sp][f"label_{hz}"].values.astype(int)
    Xte = tmp.iloc[sp:][feature_cols].values
    yte = tmp.iloc[sp:][f"label_{hz}"].values.astype(int)

    m = XGBClassifier(
        n_estimators=300, max_depth=5, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, min_child_weight=50,
        random_state=42, eval_metric="logloss",
        early_stopping_rounds=20, n_jobs=-1,
    )
    m.fit(Xtr, ytr, eval_set=[(Xte, yte)], verbose=False)
    yp = m.predict(Xte)
    a = accuracy_score(yte, yp)
    base = yte.mean()
    print(f"  {hz:3d}-min ahead:  acc={a:.4f}  base={base:.4f}  lift={a - base:+.4f}")

# ── Naive baseline: just predict majority class ────────────────────────────
print("\n" + "=" * 60)
print("SANITY CHECK: majority-class baseline")
print("=" * 60)
majority = int(y_test.mean() > 0.5)
baseline_acc = accuracy_score(y_test, np.full_like(y_test, majority))
print(f"Always predict {'UP' if majority else 'DOWN'}: {baseline_acc:.4f}")
print(f"XGBoost:                       {acc:.4f}")
print(f"XGBoost lift over majority:    {acc - baseline_acc:+.4f}")
