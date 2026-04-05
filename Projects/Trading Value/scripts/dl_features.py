"""Multi-asset deep learning feature engineering.

Generates, validates, and ranks DL features for 3 assets:
  - BTC  (from local sim_1m.sqlite, 4h timeframe)
  - NVDA (from yfinance, daily)
  - AMZN (from yfinance, daily)

Outputs per asset:
  1. Feature matrix (X), target vector (y), feature name list
  2. Per-feature correlation with next-bar direction
  3. XGBoost feature importance ranking
  4. Recommended top-15~20 feature set

Public API:
    get_btc_features(db_path, timeframe="4h") -> (X, y, feature_names)
    get_nvda_features() -> (X, y, feature_names)
    get_amzn_features() -> (X, y, feature_names)

Usage:
    py -3.12 scripts/dl_features.py
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Dependency guard
# ---------------------------------------------------------------------------

def _ensure(pkg: str, import_name: str | None = None) -> None:
    name = import_name or pkg
    try:
        __import__(name)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])


_ensure("yfinance")
_ensure("xgboost")
_ensure("scikit-learn", "sklearn")

import yfinance as yf  # noqa: E402
from xgboost import XGBClassifier  # noqa: E402
from sklearn.metrics import accuracy_score, roc_auc_score  # noqa: E402

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_HERE = Path(__file__).resolve().parent
_DATA = _HERE.parent / "data"
DEFAULT_DB = _DATA / "sim_1m.sqlite"
FUNDING_CACHE = _DATA / "btc_funding_cache.json"

# ---------------------------------------------------------------------------
# Common indicator helpers
# ---------------------------------------------------------------------------


def _sma(s: pd.Series, w: int) -> pd.Series:
    return s.rolling(w, min_periods=w).mean()


def _ema(s: pd.Series, span: int) -> pd.Series:
    return s.ewm(span=span, adjust=False).mean()


def _rsi(s: pd.Series, period: int = 14) -> pd.Series:
    delta = s.diff()
    gain = delta.clip(lower=0).rolling(period, min_periods=period).mean()
    loss = (-delta.clip(upper=0)).rolling(period, min_periods=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    tr = pd.concat(
        [high - low,
         (high - close.shift(1)).abs(),
         (low - close.shift(1)).abs()],
        axis=1,
    ).max(axis=1)
    return tr.rolling(period, min_periods=period).mean()


def _bollinger_position(close: pd.Series, window: int = 20, std: float = 2.0) -> pd.Series:
    """(price - lower) / (upper - lower), clipped to [0, 1]."""
    ma = _sma(close, window)
    sigma = close.rolling(window, min_periods=window).std()
    upper = ma + std * sigma
    lower = ma - std * sigma
    band = upper - lower
    pos = (close - lower) / band.where(band > 0, np.nan)
    return pos.clip(0.0, 1.0)


def _macd_norm(close: pd.Series) -> pd.Series:
    ema12 = _ema(close, 12)
    ema26 = _ema(close, 26)
    return (ema12 - ema26) / close.where(close > 0, np.nan)


def _build_common_features(df: pd.DataFrame) -> pd.DataFrame:
    """Build feature columns shared by all assets.

    df must have columns: open, high, low, close, volume.
    Returns DataFrame of features (same index as df).
    """
    c = df["close"]
    h = df["high"]
    lo = df["low"]
    v = df["volume"]
    feat = pd.DataFrame(index=df.index)

    # -- OHLCV normalised (% vs current close) --
    feat["open_pct"] = (df["open"] - c) / c
    feat["high_pct"] = (h - c) / c
    feat["low_pct"] = (lo - c) / c
    feat["vol_pct"] = v / v.rolling(20, min_periods=1).mean().where(lambda x: x > 0, 1.0)

    # -- RSI --
    feat["rsi14"] = _rsi(c, 14) / 100.0
    feat["rsi7"] = _rsi(c, 7) / 100.0

    # -- ATR normalised --
    feat["atr_norm"] = _atr(h, lo, c, 14) / c.where(c > 0, np.nan)

    # -- MA position: (price - MA) / MA --
    for w in [5, 10, 20, 50, 200]:
        ma = _sma(c, w)
        feat[f"ma{w}_pos"] = (c - ma) / ma.where(ma > 0, np.nan)

    # -- MA cross: fast/slow ratio --
    pairs = [(5, 20), (20, 50), (50, 200)]
    for fast, slow in pairs:
        mf = _sma(c, fast)
        ms = _sma(c, slow)
        feat[f"cross_{fast}_{slow}"] = (mf - ms) / ms.where(ms > 0, np.nan)

    # -- Momentum: N-bar returns --
    for n in [1, 4, 12, 24]:
        feat[f"mom_{n}"] = c.pct_change(n)

    # -- Volume ratio --
    vol_ma20 = _sma(v, 20)
    feat["vol_ratio"] = v / vol_ma20.where(vol_ma20 > 0, np.nan)

    # -- Time encoding --
    hour_float = df.index.hour + df.index.minute / 60.0
    feat["hour_sin"] = np.sin(2 * np.pi * hour_float / 24.0)
    feat["hour_cos"] = np.cos(2 * np.pi * hour_float / 24.0)
    dow = df.index.dayofweek.astype(float)
    feat["dow_sin"] = np.sin(2 * np.pi * dow / 7.0)
    feat["dow_cos"] = np.cos(2 * np.pi * dow / 7.0)

    # -- Bollinger Band position --
    feat["bb_pos"] = _bollinger_position(c, 20)

    # -- MACD normalised --
    feat["macd_norm"] = _macd_norm(c)

    return feat


# ---------------------------------------------------------------------------
# BTC features
# ---------------------------------------------------------------------------


def _load_btc_ohlcv(db_path: Path, timeframe: str) -> pd.DataFrame:
    """Load BTC from sim_1m.sqlite, resample to target timeframe."""
    conn = sqlite3.connect(str(db_path))
    df = pd.read_sql_query(
        "SELECT datetime, open, high, low, close, volume "
        "FROM ohlcv_1m WHERE symbol='BTCUSDT' ORDER BY datetime",
        conn,
    )
    conn.close()
    df["datetime"] = pd.to_datetime(df["datetime"])
    df.set_index("datetime", inplace=True)

    rule_map = {"4h": "4h", "1h": "1h", "15m": "15min", "1m": "1min"}
    rule = rule_map.get(timeframe, timeframe)
    if timeframe != "1m":
        df = df.resample(rule).agg(
            {"open": "first", "high": "max", "low": "min",
             "close": "last", "volume": "sum"}
        ).dropna()
    return df


def _load_funding_cache() -> pd.Series:
    """Load BTC funding rate from cache, return as pd.Series indexed by UTC timestamp."""
    if not FUNDING_CACHE.exists():
        return pd.Series(dtype=float)
    with open(FUNDING_CACHE) as f:
        raw = json.load(f)
    records = []
    for item in raw:
        ts = pd.to_datetime(item["timestamp"], unit="ms", utc=True)
        rate = float(item.get("fundingRate", 0.0))
        records.append((ts, rate))
    if not records:
        return pd.Series(dtype=float)
    idx, vals = zip(*records)
    return pd.Series(vals, index=pd.DatetimeIndex(idx), name="funding_rate").sort_index()


def get_btc_features(
    db_path: Path | str = DEFAULT_DB,
    timeframe: str = "4h",
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Build BTC feature matrix.

    Returns (X, y, feature_names).
      X: shape (n, n_features)
      y: shape (n,) — 1 if next bar close > current close, else 0
    """
    db_path = Path(db_path)
    df = _load_btc_ohlcv(db_path, timeframe)
    feat = _build_common_features(df)

    # -- BTC-specific: funding rate --
    fr_series = _load_funding_cache()
    if not fr_series.empty:
        # Resample funding rate to match OHLCV index (forward-fill)
        # Funding is every 8h on Binance; align to bar timestamps
        feat_idx_utc = feat.index.tz_localize("UTC") if feat.index.tzinfo is None else feat.index
        fr_aligned = fr_series.reindex(feat_idx_utc, method="ffill")
        fr_aligned.index = feat.index  # strip tz for consistency
        feat["funding_rate"] = fr_aligned.values
        # Rate-of-change of funding (momentum of sentiment)
        feat["funding_roc"] = feat["funding_rate"].diff(3)
    else:
        feat["funding_rate"] = np.nan
        feat["funding_roc"] = np.nan

    # -- BTC-specific: open interest change from ccxt (if available live, else NaN) --
    # In analysis mode we leave as NaN; real-time pipeline can inject.
    feat["oi_change_pct"] = np.nan

    # Target: next bar direction
    y = (df["close"].shift(-1) > df["close"]).astype(int)

    # Align and drop NaN
    combined = feat.copy()
    combined["_target"] = y
    combined = combined.dropna(subset=["_target"])

    # Separate out rows where all required base features are available
    base_cols = [c for c in combined.columns if c != "_target"]
    # Fill NaN-only columns (oi_change_pct) with 0 before dropping
    always_nan = [c for c in base_cols if combined[c].isna().all()]
    for c in always_nan:
        combined[c] = 0.0

    combined = combined.dropna(subset=[c for c in base_cols if c not in always_nan])

    X = combined[base_cols].values.astype(np.float32)
    y_out = combined["_target"].values.astype(np.int32)
    names = base_cols

    return X, y_out, names


# ---------------------------------------------------------------------------
# NVDA features
# ---------------------------------------------------------------------------


def _load_yf(ticker: str, period: str = "5y", interval: str = "1d") -> pd.DataFrame:
    df = yf.Ticker(ticker).history(period=period, interval=interval)
    df = df.rename(columns={
        "Open": "open", "High": "high", "Low": "low",
        "Close": "close", "Volume": "volume",
    })
    return df[["open", "high", "low", "close", "volume"]].dropna()


def get_nvda_features() -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Build NVDA feature matrix (daily bars).

    Sector context: SOXX, VIX, QQQ.
    Returns (X, y, feature_names).
    """
    print("  Fetching NVDA + SOXX + VIX + QQQ from yfinance...")
    nvda = _load_yf("NVDA")
    soxx = _load_yf("SOXX")
    vix = _load_yf("^VIX")
    qqq = _load_yf("QQQ")

    feat = _build_common_features(nvda)

    # Align external tickers to NVDA index
    def _align_ret(ext: pd.DataFrame, name: str) -> pd.Series:
        ret = ext["close"].pct_change()
        return ret.reindex(nvda.index, method="ffill").rename(name)

    feat["soxx_ret"] = _align_ret(soxx, "soxx_ret")
    feat["qqq_ret"] = _align_ret(qqq, "qqq_ret")

    # VIX level normalised
    vix_aligned = vix["close"].reindex(nvda.index, method="ffill")
    feat["vix_norm"] = (vix_aligned - vix_aligned.rolling(60).mean()) / \
                       vix_aligned.rolling(60).std().where(lambda x: x > 0, 1.0)

    # NVDA relative strength vs QQQ
    qqq_close = qqq["close"].reindex(nvda.index, method="ffill")
    nvda_close = nvda["close"]
    ratio = nvda_close / qqq_close.where(qqq_close > 0, np.nan)
    feat["nvda_qqq_rs"] = ratio / ratio.rolling(20).mean().where(lambda x: x > 0, np.nan) - 1.0

    # Target
    y = (nvda["close"].shift(-1) > nvda["close"]).astype(int)

    combined = feat.copy()
    combined["_target"] = y
    combined = combined.dropna(subset=["_target"])

    base_cols = [c for c in combined.columns if c != "_target"]
    combined = combined.dropna(subset=base_cols)

    X = combined[base_cols].values.astype(np.float32)
    y_out = combined["_target"].values.astype(np.int32)
    return X, y_out, base_cols


# ---------------------------------------------------------------------------
# AMZN features
# ---------------------------------------------------------------------------


def get_amzn_features() -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Build AMZN feature matrix (daily bars).

    Sector context: XLY, QQQ.
    Returns (X, y, feature_names).
    """
    print("  Fetching AMZN + XLY + QQQ from yfinance...")
    amzn = _load_yf("AMZN")
    xly = _load_yf("XLY")
    qqq = _load_yf("QQQ")

    feat = _build_common_features(amzn)

    def _align_ret(ext: pd.DataFrame, name: str) -> pd.Series:
        ret = ext["close"].pct_change()
        return ret.reindex(amzn.index, method="ffill").rename(name)

    feat["xly_ret"] = _align_ret(xly, "xly_ret")
    feat["qqq_ret"] = _align_ret(qqq, "qqq_ret")

    # AMZN relative strength vs QQQ
    qqq_close = qqq["close"].reindex(amzn.index, method="ffill")
    amzn_close = amzn["close"]
    ratio = amzn_close / qqq_close.where(qqq_close > 0, np.nan)
    feat["amzn_qqq_rs"] = ratio / ratio.rolling(20).mean().where(lambda x: x > 0, np.nan) - 1.0

    # Target
    y = (amzn["close"].shift(-1) > amzn["close"]).astype(int)

    combined = feat.copy()
    combined["_target"] = y
    combined = combined.dropna(subset=["_target"])

    base_cols = [c for c in combined.columns if c != "_target"]
    combined = combined.dropna(subset=base_cols)

    X = combined[base_cols].values.astype(np.float32)
    y_out = combined["_target"].values.astype(np.int32)
    return X, y_out, base_cols


# ---------------------------------------------------------------------------
# Analysis helpers
# ---------------------------------------------------------------------------


def _correlation_analysis(
    X: np.ndarray, y: np.ndarray, names: list[str]
) -> pd.DataFrame:
    """Point-biserial correlation of each feature with binary target."""
    rows = []
    for i, name in enumerate(names):
        col = X[:, i]
        mask = np.isfinite(col)
        if mask.sum() < 30:
            rows.append({"feature": name, "corr": 0.0})
            continue
        corr = np.corrcoef(col[mask], y[mask])[0, 1]
        rows.append({"feature": name, "corr": float(corr) if np.isfinite(corr) else 0.0})
    return pd.DataFrame(rows).sort_values("corr", key=abs, ascending=False)


def _xgb_importance(
    X: np.ndarray, y: np.ndarray, names: list[str], n_top: int = 20
) -> pd.DataFrame:
    """Train XGBoost on 80% of data, return feature importance ranking."""
    n = len(X)
    split = int(n * 0.8)
    X_tr, X_val = X[:split], X[split:]
    y_tr, y_val = y[:split], y[split:]

    # Remove rows with any NaN
    mask_tr = np.isfinite(X_tr).all(axis=1)
    mask_val = np.isfinite(X_val).all(axis=1)
    X_tr, y_tr = X_tr[mask_tr], y_tr[mask_tr]
    X_val, y_val = X_val[mask_val], y_val[mask_val]

    model = XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="logloss",
        verbosity=0,
        random_state=42,
    )
    model.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], verbose=False)

    y_pred = model.predict(X_val)
    y_proba = model.predict_proba(X_val)[:, 1]
    acc = accuracy_score(y_val, y_pred)
    auc = roc_auc_score(y_val, y_proba) if len(np.unique(y_val)) > 1 else 0.5

    imp = model.feature_importances_
    df_imp = pd.DataFrame({"feature": names, "importance": imp})
    df_imp = df_imp.sort_values("importance", ascending=False).reset_index(drop=True)

    return df_imp, acc, auc


def _recommend_features(
    corr_df: pd.DataFrame,
    imp_df: pd.DataFrame,
    n_top: int = 17,
) -> list[str]:
    """Combine correlation rank and importance rank; recommend top N."""
    corr_rank = {row.feature: i for i, row in enumerate(corr_df.itertuples())}
    imp_rank = {row.feature: i for i, row in enumerate(imp_df.itertuples())}
    all_features = set(corr_rank) | set(imp_rank)
    n = len(all_features)

    scores = {}
    for f in all_features:
        cr = corr_rank.get(f, n)
        ir = imp_rank.get(f, n)
        # Lower combined rank = better
        scores[f] = cr + ir

    ranked = sorted(scores, key=scores.__getitem__)
    return ranked[:n_top]


# ---------------------------------------------------------------------------
# Report printer
# ---------------------------------------------------------------------------


def _print_report(
    asset: str,
    X: np.ndarray,
    y: np.ndarray,
    names: list[str],
    n_top: int = 17,
) -> None:
    sep = "=" * 64
    print(f"\n{sep}")
    print(f"  {asset} FEATURE ANALYSIS")
    print(f"  Samples: {len(X)}   Features: {len(names)}")
    print(sep)

    # Correlation
    corr_df = _correlation_analysis(X, y, names)
    print("\n  [Correlation with next-bar direction] top 10:")
    for _, row in corr_df.head(10).iterrows():
        bar = "+" * int(abs(row["corr"]) * 40)
        print(f"    {row['feature']:30s}  {row['corr']:+.4f}  {bar}")

    # XGBoost importance
    print("\n  [XGBoost importance] training (80/20 split)...")
    imp_df, acc, auc = _xgb_importance(X, y, names, n_top)
    print(f"    Val accuracy: {acc:.4f}   AUC-ROC: {auc:.4f}")
    print(f"\n  [Top-{min(n_top, len(imp_df))} by importance]:")
    for i, row in imp_df.head(n_top).iterrows():
        bar = "#" * int(row["importance"] * 400)
        print(f"    {i+1:2d}. {row['feature']:30s}  {row['importance']:.4f}  {bar}")

    # Recommendation
    rec = _recommend_features(corr_df, imp_df, n_top)
    print(f"\n  [Recommended top-{n_top} feature set]:")
    for i, name in enumerate(rec, 1):
        print(f"    {i:2d}. {name}")

    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    print("=" * 64)
    print("  Multi-Asset DL Feature Engineering")
    print("  Assets: BTC (4h), NVDA (1d), AMZN (1d)")
    print("=" * 64)

    # -- BTC --
    print("\n[1/3] BTC - loading from sim_1m.sqlite (4h bars)...")
    X_btc, y_btc, names_btc = get_btc_features(DEFAULT_DB, "4h")
    print(f"  Loaded {len(X_btc)} bars, {len(names_btc)} features")
    _print_report("BTC/USDT (4h)", X_btc, y_btc, names_btc)

    # -- NVDA --
    print("\n[2/3] NVDA - loading from yfinance...")
    X_nvda, y_nvda, names_nvda = get_nvda_features()
    print(f"  Loaded {len(X_nvda)} bars, {len(names_nvda)} features")
    _print_report("NVDA (1d)", X_nvda, y_nvda, names_nvda)

    # -- AMZN --
    print("\n[3/3] AMZN - loading from yfinance...")
    X_amzn, y_amzn, names_amzn = get_amzn_features()
    print(f"  Loaded {len(X_amzn)} bars, {len(names_amzn)} features")
    _print_report("AMZN (1d)", X_amzn, y_amzn, names_amzn)

    print("=" * 64)
    print("  Done. Use get_btc_features() / get_nvda_features() /")
    print("  get_amzn_features() to obtain (X, y, feature_names).")
    print("=" * 64)


if __name__ == "__main__":
    main()
