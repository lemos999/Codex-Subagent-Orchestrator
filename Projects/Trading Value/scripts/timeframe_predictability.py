"""시간축별 예측력 검증 (Timeframe Predictability Test)

각 시간축(15m, 1H, 4H)에서 기술적 지표가 다음 봉 방향을 예측할 수 있는지 테스트.
Walk-forward 검증 (6개월 학습 → 1개월 테스트, 슬라이딩).

Usage:
    cd "Projects/Trading Value"
    py -3.12 scripts/timeframe_predictability.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, roc_auc_score

try:
    from xgboost import XGBClassifier
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "xgboost"])
    from xgboost import XGBClassifier

# ── Config ────────────────────────────────────────────────────────────────────
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "sim_1m.sqlite"
SYMBOL = "ETHUSDT"
TRAIN_MONTHS = 6
TEST_MONTHS = 1
TIMEFRAMES = {"15m": "15min", "1H": "1h", "4H": "4h"}


# ── Data Loading ──────────────────────────────────────────────────────────────
def load_1m_data() -> pd.DataFrame:
    """Load full 1m data from sqlite."""
    conn = sqlite3.connect(str(DB_PATH))
    df = pd.read_sql_query(
        "SELECT datetime, open, high, low, close, volume "
        "FROM ohlcv_1m WHERE symbol=? ORDER BY datetime",
        conn, params=(SYMBOL,),
    )
    conn.close()
    df["datetime"] = pd.to_datetime(df["datetime"])
    df.set_index("datetime", inplace=True)
    print(f"[데이터] {len(df):,}개 1분봉 로드 ({df.index[0]} ~ {df.index[-1]})")
    return df


def resample(df_1m: pd.DataFrame, freq: str) -> pd.DataFrame:
    """Resample 1m OHLCV to target frequency."""
    agg = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }
    df = df_1m.resample(freq).agg(agg).dropna()
    return df


# ── Feature Engineering ───────────────────────────────────────────────────────
def compute_features(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Compute prediction features. Returns (df_with_features, feature_col_names)."""
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

    # Hour of day (sin/cos) — from index
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


# ── Walk-Forward Evaluation ───────────────────────────────────────────────────
def walk_forward_eval(
    df: pd.DataFrame,
    feature_cols: list[str],
    horizon: int,
    label: str,
) -> dict:
    """Walk-forward: train TRAIN_MONTHS, test TEST_MONTHS, slide."""
    # Create target
    df = df.copy()
    df["target"] = (df["close"].shift(-horizon) > df["close"]).astype(int)
    df = df.dropna(subset=feature_cols + ["target"])

    if len(df) < 500:
        return {"accuracy": np.nan, "auc": np.nan, "n_samples": 0}

    # Define windows
    dates = df.index
    min_date = dates.min()
    max_date = dates.max()

    all_y_true = []
    all_y_proba = []
    all_y_pred = []
    window_results = []

    train_start = min_date
    while True:
        train_end = train_start + pd.DateOffset(months=TRAIN_MONTHS)
        test_end = train_end + pd.DateOffset(months=TEST_MONTHS)

        if test_end > max_date:
            break

        train_mask = (df.index >= train_start) & (df.index < train_end)
        test_mask = (df.index >= train_end) & (df.index < test_end)

        X_train = df.loc[train_mask, feature_cols].values
        y_train = df.loc[train_mask, "target"].values
        X_test = df.loc[test_mask, feature_cols].values
        y_test = df.loc[test_mask, "target"].values

        if len(X_train) < 100 or len(X_test) < 20:
            train_start += pd.DateOffset(months=TEST_MONTHS)
            continue

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

        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)[:, 1]

        all_y_true.extend(y_test.tolist())
        all_y_proba.extend(y_proba.tolist())
        all_y_pred.extend(y_pred.tolist())

        window_results.append({
            "period": f"{train_end.strftime('%Y-%m')}",
            "n_test": len(y_test),
            "acc": accuracy_score(y_test, y_pred),
            "importances": dict(zip(feature_cols, model.feature_importances_)),
        })

        train_start += pd.DateOffset(months=TEST_MONTHS)

    if not all_y_true:
        return {"accuracy": np.nan, "auc": np.nan, "n_samples": 0}

    all_y_true = np.array(all_y_true)
    all_y_proba = np.array(all_y_proba)
    all_y_pred = np.array(all_y_pred)

    # Overall metrics
    acc = accuracy_score(all_y_true, all_y_pred)
    try:
        auc = roc_auc_score(all_y_true, all_y_proba)
    except ValueError:
        auc = np.nan

    # High confidence subsets
    conf_results = {}
    for thresh in [0.55, 0.60]:
        mask = (all_y_proba > thresh) | (all_y_proba < (1 - thresh))
        if mask.sum() > 10:
            conf_pred = (all_y_proba[mask] > 0.5).astype(int)
            conf_results[thresh] = {
                "accuracy": accuracy_score(all_y_true[mask], conf_pred),
                "count": int(mask.sum()),
                "pct": mask.sum() / len(all_y_true) * 100,
                "per_month": mask.sum() / max(len(window_results), 1),
            }
        else:
            conf_results[thresh] = {
                "accuracy": np.nan, "count": 0, "pct": 0, "per_month": 0,
            }

    # Feature importance (averaged across windows)
    avg_importance = {}
    for fc in feature_cols:
        avg_importance[fc] = np.mean([w["importances"].get(fc, 0) for w in window_results])
    top_features = sorted(avg_importance.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "accuracy": acc,
        "auc": auc,
        "n_samples": len(all_y_true),
        "n_windows": len(window_results),
        "baseline": all_y_true.mean(),
        "confidence": conf_results,
        "top_features": top_features,
        "per_window": window_results,
    }


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 70)
    print("  시간축별 예측력 검증 (Timeframe Predictability Test)")
    print("  모델: XGBoost | 검증: Walk-Forward (6개월 학습 → 1개월 테스트)")
    print("=" * 70)

    df_1m = load_1m_data()

    results = {}

    for tf_name, freq in TIMEFRAMES.items():
        print(f"\n{'─' * 70}")
        print(f"  시간축: {tf_name}")
        print(f"{'─' * 70}")

        df_tf = resample(df_1m, freq)
        print(f"  리샘플 완료: {len(df_tf):,}개 봉")

        df_feat, feature_cols = compute_features(df_tf)
        print(f"  피처 수: {len(feature_cols)}")

        # Test two horizons: next-1-bar and next-4-bar
        for horizon, horizon_name in [(1, "다음 1봉"), (4, "다음 4봉")]:
            key = f"{tf_name}_{horizon_name}"
            print(f"\n  >>> 예측 목표: {horizon_name} 방향 (horizon={horizon})")

            result = walk_forward_eval(df_feat, feature_cols, horizon, horizon_name)
            results[key] = {**result, "tf": tf_name, "horizon": horizon_name}

            if np.isnan(result["accuracy"]):
                print(f"      데이터 부족으로 테스트 불가")
                continue

            print(f"      전체 정확도: {result['accuracy']:.4f}")
            print(f"      AUC-ROC:    {result['auc']:.4f}")
            print(f"      베이스라인:  {result['baseline']:.4f}")
            print(f"      리프트:      {result['accuracy'] - result['baseline']:+.4f}")
            print(f"      테스트 샘플: {result['n_samples']:,} ({result['n_windows']}개 윈도우)")

            for thresh, cr in result["confidence"].items():
                if cr["count"] > 0:
                    print(f"      신뢰도 > {thresh:.0%}: 정확도 {cr['accuracy']:.4f}, "
                          f"건수 {cr['count']:,} ({cr['pct']:.1f}%), "
                          f"월평균 {cr['per_month']:.0f}건")

            print(f"      상위 10 피처:")
            for fname, fimp in result["top_features"]:
                print(f"        {fname:20s}  {fimp:.4f}")

    # ── Comparison Table ──────────────────────────────────────────────────────
    print("\n" + "=" * 100)
    print("  종합 비교 테이블")
    print("=" * 100)
    header = f"{'시간축+목표':20s} {'정확도':>8s} {'AUC':>8s} {'베이스라인':>8s} {'리프트':>8s} {'신뢰55%':>10s} {'신뢰60%':>10s} {'샘플수':>8s}"
    print(header)
    print("-" * 100)

    for key, r in results.items():
        if np.isnan(r.get("accuracy", np.nan)):
            print(f"{key:20s}  {'N/A':>8s}")
            continue

        c55 = r["confidence"].get(0.55, {})
        c60 = r["confidence"].get(0.60, {})
        c55_str = f"{c55.get('accuracy', 0):.3f}/{c55.get('count', 0)}" if c55.get("count", 0) > 0 else "N/A"
        c60_str = f"{c60.get('accuracy', 0):.3f}/{c60.get('count', 0)}" if c60.get("count", 0) > 0 else "N/A"

        print(f"{key:20s} {r['accuracy']:8.4f} {r['auc']:8.4f} {r['baseline']:8.4f} "
              f"{r['accuracy'] - r['baseline']:+8.4f} {c55_str:>10s} {c60_str:>10s} {r['n_samples']:>8,}")

    # ── Verdict ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  판정")
    print("=" * 70)

    best_key = None
    best_lift = -1.0
    for key, r in results.items():
        if not np.isnan(r.get("accuracy", np.nan)):
            lift = r["accuracy"] - r["baseline"]
            if lift > best_lift:
                best_lift = lift
                best_key = key

    if best_key and best_lift > 0.02:
        r = results[best_key]
        print(f"  최고 성과: {best_key}")
        print(f"  리프트: {best_lift:+.4f} (베이스라인 대비)")
        print(f"  → 예측 가능성 있음. 이 시간축에서 추가 연구 가치 있음.")
    elif best_key and best_lift > 0:
        print(f"  최고 성과: {best_key}, 리프트: {best_lift:+.4f}")
        print(f"  → 미약한 시그널. 비용 고려 시 수익화 어려울 수 있음.")
    else:
        print(f"  → 모든 시간축에서 의미있는 예측력 없음. 피처 재설계 필요.")


if __name__ == "__main__":
    main()
