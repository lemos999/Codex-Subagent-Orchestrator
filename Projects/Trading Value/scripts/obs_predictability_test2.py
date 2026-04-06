"""Extended predictability test: LightGBM, deeper model, and feature engineering."""
import sqlite3
import numpy as np
import pandas as pd
from pathlib import Path
from lightgbm import LGBMClassifier
from sklearn.metrics import accuracy_score, roc_auc_score

DB = Path(__file__).resolve().parent.parent / "data" / "sim_1m.sqlite"
conn = sqlite3.connect(str(DB))
df = pd.read_sql_query(
    """SELECT timestamp, datetime, open, high, low, close, volume
    FROM ohlcv_1m WHERE symbol='ETHUSDT'
    AND datetime >= '2023-01-01' AND datetime < '2024-01-01'
    ORDER BY timestamp""", conn)
conn.close()
print(f"Loaded {len(df):,} rows")

c = df["close"].values.astype(np.float64)
h = df["high"].values.astype(np.float64)
l = df["low"].values.astype(np.float64)
v = df["volume"].values.astype(np.float64)

# ── Extended feature set ──────────────────────────────────────────────────
# Original features
for w in [5, 10, 20, 50, 100, 200]:
    ma = pd.Series(c).rolling(w).mean().values
    df[f"ma{w}_dev"] = (c - ma) / np.where(ma > 0, ma, 1.0)

delta = pd.Series(c).diff()
gain = delta.clip(lower=0).rolling(14).mean()
loss_ = (-delta.clip(upper=0)).rolling(14).mean()
rs = gain / loss_.replace(0, np.nan)
df["rsi14"] = (100 - (100 / (1 + rs))) / 100.0

tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(l - np.roll(c, 1))))
tr[0] = h[0] - l[0]
atr14 = pd.Series(tr).rolling(14).mean().values
df["atr_norm"] = atr14 / np.where(c > 0, c, 1.0)

dc_high = pd.Series(h).rolling(20).max().values
dc_low = pd.Series(l).rolling(20).min().values
dc_range = dc_high - dc_low
df["donchian_pos"] = np.where(dc_range > 0, (c - dc_low) / dc_range, 0.5)

for j in range(1, 11):
    ret = c - np.roll(c, j); ret[:j] = 0
    df[f"ret_{j}"] = ret / np.where(atr14 > 0, atr14, 1.0)

vol_ma20 = pd.Series(v).rolling(20).mean().values
df["vol_ratio"] = v / np.where(vol_ma20 > 0, vol_ma20, 1.0)

for span, name in [(15, "15m"), (60, "1h"), (240, "4h"), (1440, "1d")]:
    ret_span = c - np.roll(c, span); ret_span[:span] = 0
    df[f"trend_{name}"] = ret_span / np.where(atr14 > 0, atr14, 1.0)

# Extra features
# Bollinger band position
bb_ma = pd.Series(c).rolling(20).mean().values
bb_std = pd.Series(c).rolling(20).std().values
df["bb_pos"] = (c - bb_ma) / np.where(bb_std > 0, 2 * bb_std, 1.0)

# MACD
ema12 = pd.Series(c).ewm(span=12).mean().values
ema26 = pd.Series(c).ewm(span=26).mean().values
macd = ema12 - ema26
signal = pd.Series(macd).ewm(span=9).mean().values
df["macd_hist"] = (macd - signal) / np.where(atr14 > 0, atr14, 1.0)

# Stochastic
low14 = pd.Series(l).rolling(14).min().values
high14 = pd.Series(h).rolling(14).max().values
sto_range = high14 - low14
df["stoch_k"] = np.where(sto_range > 0, (c - low14) / sto_range, 0.5)

# OBV trend
obv = np.cumsum(np.where(np.diff(c, prepend=c[0]) > 0, v, -v))
obv_ma = pd.Series(obv).rolling(20).mean().values
df["obv_dev"] = (obv - obv_ma) / np.where(np.abs(obv_ma) > 0, np.abs(obv_ma), 1.0)

# Bar patterns
df["body_ratio"] = (c - df["open"].values) / np.where(h - l > 0, h - l, 1.0)
df["upper_shadow"] = (h - np.maximum(c, df["open"].values)) / np.where(h - l > 0, h - l, 1.0)

# Volatility features
for w in [5, 20, 60]:
    df[f"vol_{w}"] = pd.Series(c).pct_change().rolling(w).std().values

# VWAP
cum_pv = pd.Series(c * v).rolling(30).sum().values
cum_v = pd.Series(v).rolling(30).sum().values
vwap30 = cum_pv / np.where(cum_v > 0, cum_v, 1.0)
df["vwap_dev"] = (c - vwap30) / np.where(c > 0, c, 1.0)

# EMA crosses
ema9 = pd.Series(c).ewm(span=9).mean().values
df["tk_cross"] = np.sign(ema9 - ema26)
df["ema_spread_9_26"] = (ema9 - ema26) / np.where(atr14 > 0, atr14, 1.0)

feature_cols = [col for col in df.columns if col not in
    ["timestamp", "datetime", "open", "high", "low", "close", "volume", "future_close", "label"]]

# Label: 5-min direction
HORIZON = 5
df["future_close"] = df["close"].shift(-HORIZON)
df["label"] = (df["future_close"] > df["close"]).astype(int)

df_clean = df.dropna(subset=feature_cols + ["label"]).copy()
df_clean["label"] = df_clean["label"].astype(int)
print(f"Features: {len(feature_cols)}, Rows: {len(df_clean):,}")

split = int(len(df_clean) * 0.8)
train, test = df_clean.iloc[:split], df_clean.iloc[split:]
X_train, y_train = train[feature_cols].values, train["label"].values
X_test, y_test = test[feature_cols].values, test["label"].values

# ── LightGBM (default) ────────────────────────────────────────────────────
lgb1 = LGBMClassifier(
    n_estimators=1000, max_depth=8, learning_rate=0.03,
    subsample=0.8, colsample_bytree=0.6, min_child_samples=100,
    reg_alpha=0.1, reg_lambda=1.0, random_state=42, n_jobs=-1, verbose=-1,
)
lgb1.fit(X_train, y_train, eval_set=[(X_test, y_test)],
    callbacks=[lambda env: None if env.iteration < 50 else None])
y_pred1 = lgb1.predict(X_test)
y_prob1 = lgb1.predict_proba(X_test)[:, 1]

# ── LightGBM (deep, many trees) ───────────────────────────────────────────
lgb2 = LGBMClassifier(
    n_estimators=2000, max_depth=12, learning_rate=0.01, num_leaves=127,
    subsample=0.7, colsample_bytree=0.5, min_child_samples=200,
    reg_alpha=1.0, reg_lambda=5.0, random_state=42, n_jobs=-1, verbose=-1,
)
lgb2.fit(X_train, y_train, eval_set=[(X_test, y_test)],
    callbacks=[lambda env: None if env.iteration < 100 else None])
y_pred2 = lgb2.predict(X_test)
y_prob2 = lgb2.predict_proba(X_test)[:, 1]

base = y_test.mean()
print(f"\nTest baseline (UP%): {base:.4f}")
print(f"\n{'Model':<30s}  {'Acc':>7s}  {'AUC':>7s}  {'Lift':>7s}")
print("-" * 55)
for name, yp, ypr in [
    ("LightGBM (default)", y_pred1, y_prob1),
    ("LightGBM (deep)", y_pred2, y_prob2),
]:
    a = accuracy_score(y_test, yp)
    auc = roc_auc_score(y_test, ypr)
    print(f"{name:<30s}  {a:7.4f}  {auc:7.4f}  {a - base:+7.4f}")

# ── Confidence-filtered predictions ────────────────────────────────────────
print("\n── Confidence-filtered predictions (LightGBM deep) ──")
for threshold in [0.52, 0.55, 0.58, 0.60]:
    mask = (y_prob2 > threshold) | (y_prob2 < (1 - threshold))
    if mask.sum() < 100:
        print(f"  p>{threshold:.2f}: too few predictions ({mask.sum()})")
        continue
    filtered_pred = (y_prob2[mask] > 0.5).astype(int)
    filtered_acc = accuracy_score(y_test[mask], filtered_pred)
    coverage = mask.mean()
    print(f"  p>{threshold:.2f}: acc={filtered_acc:.4f}  coverage={coverage:.1%}  n={mask.sum()}")

# ── Feature importance top 15 ──────────────────────────────────────────────
imp = lgb2.feature_importances_
sorted_idx = np.argsort(imp)[::-1]
print(f"\nTop 15 features (LightGBM deep):")
for i in range(min(15, len(feature_cols))):
    idx = sorted_idx[i]
    print(f"  {feature_cols[idx]:25s}  {imp[idx]:6d}")
