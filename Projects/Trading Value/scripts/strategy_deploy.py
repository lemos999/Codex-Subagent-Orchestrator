"""Hybrid Strategy Deployment Module

Production-ready strategy executor: CMA-ES + XGBoost hybrid.
Loads XGBoost model, computes features on latest 15m candles,
outputs trading signal with stop/tp/position size.

Usage:
    cd "Projects/Trading Value"
    py -3.12 scripts/strategy_deploy.py

As a module:
    from strategy_deploy import HybridStrategy
    strategy = HybridStrategy(model_path="data/xgb_direction_model.json")
    signal = strategy.update(df_15m)
"""
from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from xgboost import XGBClassifier
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "xgboost"])
    from xgboost import XGBClassifier

# ── Defaults ─────────────────────────────────────────────────────────────────
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "sim_1m.sqlite"
DEFAULT_MODEL_PATH = str(Path(__file__).resolve().parent.parent / "data" / "xgb_direction_model.json")
SYMBOL = "ETHUSDT"
COMMISSION = 0.0004
SLIPPAGE = 0.0001

# Best CMA-ES parameters (from optimization)
DEFAULT_PARAMS = {
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
    "confidence_threshold": 0.55,
}


class HybridStrategy:
    """CMA-ES + XGBoost hybrid strategy executor.

    Loads a pre-trained XGBoost direction model and applies CMA-ES
    parametric rules with XGBoost confidence gating.
    """

    def __init__(
        self,
        model_path: str = DEFAULT_MODEL_PATH,
        params: dict | None = None,
    ):
        """Load XGBoost model and strategy params.

        Args:
            model_path: Path to xgb_direction_model.json
            params: Strategy parameters dict. Uses DEFAULT_PARAMS if None.
        """
        self.params = {**DEFAULT_PARAMS, **(params or {})}
        self.model_path = model_path

        # Load XGBoost model
        self.xgb_model = XGBClassifier()
        self.xgb_model.load_model(model_path)

        # Internal state
        self._position = "FLAT"  # FLAT, LONG, SHORT
        self._entry_price = 0.0
        self._stop_price = 0.0
        self._tp_price = 0.0
        self._trail_active = False
        self._trail_price = 0.0
        self._bars_since_trade = 999

    # ── Feature Engineering ───────────────────────────────────────────────
    def _compute_features(self, df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
        """Compute XGBoost features from 15m OHLCV dataframe."""
        c = df["close"]
        h = df["high"]
        lo = df["low"]
        v = df["volume"]

        feat = pd.DataFrame(index=df.index)

        # MA positions
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

        # Momentum
        feat["mom_1"] = c.pct_change(1)
        feat["mom_4"] = c.pct_change(4)
        feat["mom_12"] = c.pct_change(12)

        # Time features
        hour = df.index.hour + df.index.minute / 60.0
        feat["hour_sin"] = np.sin(2 * np.pi * hour / 24)
        feat["hour_cos"] = np.cos(2 * np.pi * hour / 24)
        dow = df.index.dayofweek.astype(float)
        feat["dow_sin"] = np.sin(2 * np.pi * dow / 7)
        feat["dow_cos"] = np.cos(2 * np.pi * dow / 7)

        feature_cols = list(feat.columns)
        out = df.join(feat)
        return out, feature_cols

    # ── CMA-ES Indicators ────────────────────────────────────────────────
    def _compute_indicators(self, df: pd.DataFrame) -> dict:
        """Compute CMA-ES strategy indicators for the latest bar."""
        p = self.params
        c = df["close"]
        h = df["high"]
        lo = df["low"]
        v = df["volume"]

        # MA
        ma_fast = c.rolling(p["ma_fast"]).mean()
        ma_slow = c.rolling(p["ma_slow"]).mean()

        # RSI(14)
        delta = c.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))

        # ATR(14)
        tr = pd.concat([
            h - lo,
            (h - c.shift(1)).abs(),
            (lo - c.shift(1)).abs(),
        ], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()

        # Volume MA
        vol_ma = v.rolling(20).mean()

        return {
            "ma_fast": ma_fast,
            "ma_slow": ma_slow,
            "rsi": rsi,
            "atr": atr,
            "vol_ma": vol_ma,
        }

    # ── Main Update Method ───────────────────────────────────────────────
    def update(self, df_15m: pd.DataFrame) -> dict:
        """Given latest 15m candles (need ~200 bars), return trading signal.

        Args:
            df_15m: DataFrame with columns [open, high, low, close, volume]
                    and DatetimeIndex. At least 200 rows recommended.

        Returns:
            dict with keys: signal, confidence, stop_loss, take_profit,
                           position_size, reason
        """
        if len(df_15m) < 200:
            return {
                "signal": "FLAT",
                "confidence": 0.0,
                "stop_loss": 0.0,
                "take_profit": 0.0,
                "position_size": 0.0,
                "reason": f"Insufficient data ({len(df_15m)} bars, need 200+)",
            }

        p = self.params

        # Compute features and get XGBoost prediction
        df_feat, feature_cols = self._compute_features(df_15m)
        last_features = df_feat[feature_cols].iloc[-1:].values

        # Handle NaN features
        if np.any(np.isnan(last_features)):
            return {
                "signal": "FLAT",
                "confidence": 0.0,
                "stop_loss": 0.0,
                "take_profit": 0.0,
                "position_size": 0.0,
                "reason": "NaN in features (insufficient warmup data)",
            }

        xgb_proba = self.xgb_model.predict_proba(last_features)[0, 1]  # P(up)

        # Compute CMA-ES indicators
        ind = self._compute_indicators(df_15m)
        last_price = df_15m["close"].iloc[-1]
        last_high = df_15m["high"].iloc[-1]
        last_low = df_15m["low"].iloc[-1]

        ma_f_val = ind["ma_fast"].iloc[-1]
        ma_s_val = ind["ma_slow"].iloc[-1]
        rsi_val = ind["rsi"].iloc[-1]
        atr_val = ind["atr"].iloc[-1]
        vol_val = df_15m["volume"].iloc[-1]
        vol_ma_val = ind["vol_ma"].iloc[-1]

        # Check for NaN
        if any(np.isnan(x) for x in [ma_f_val, ma_s_val, rsi_val, atr_val]):
            return {
                "signal": "FLAT",
                "confidence": 0.0,
                "stop_loss": 0.0,
                "take_profit": 0.0,
                "position_size": 0.0,
                "reason": "NaN in indicators",
            }

        self._bars_since_trade += 1

        # ── Exit logic (if in position) ──────────────────────────────────
        if self._position == "LONG":
            exited = False
            reason = ""

            if last_low <= self._stop_price:
                exited = True
                reason = "Stop loss hit"
            elif last_high >= self._tp_price:
                exited = True
                reason = "Take profit hit"
            else:
                profit_dist = last_price - self._entry_price
                trail_threshold = p["trail_start"] * atr_val
                if profit_dist >= trail_threshold:
                    self._trail_active = True
                if self._trail_active:
                    new_trail = last_price - p["trail_step"] * atr_val
                    if new_trail > self._trail_price:
                        self._trail_price = new_trail
                    if last_low <= self._trail_price:
                        exited = True
                        reason = "Trailing stop hit"

            if exited:
                self._position = "FLAT"
                self._bars_since_trade = 0
                return {
                    "signal": "FLAT",
                    "confidence": xgb_proba,
                    "stop_loss": 0.0,
                    "take_profit": 0.0,
                    "position_size": 0.0,
                    "reason": f"Exit LONG: {reason}",
                }

            # Still in position
            return {
                "signal": "LONG",
                "confidence": xgb_proba,
                "stop_loss": self._stop_price,
                "take_profit": self._tp_price,
                "position_size": p["risk_per_trade"],
                "reason": f"Holding LONG (trail={'active' if self._trail_active else 'inactive'})",
            }

        if self._position == "SHORT":
            exited = False
            reason = ""

            if last_high >= self._stop_price:
                exited = True
                reason = "Stop loss hit"
            elif last_low <= self._tp_price:
                exited = True
                reason = "Take profit hit"
            else:
                profit_dist = self._entry_price - last_price
                trail_threshold = p["trail_start"] * atr_val
                if profit_dist >= trail_threshold:
                    self._trail_active = True
                if self._trail_active:
                    new_trail = last_price + p["trail_step"] * atr_val
                    if new_trail < self._trail_price or self._trail_price == 0:
                        self._trail_price = new_trail
                    if last_high >= self._trail_price:
                        exited = True
                        reason = "Trailing stop hit"

            if exited:
                self._position = "FLAT"
                self._bars_since_trade = 0
                return {
                    "signal": "FLAT",
                    "confidence": xgb_proba,
                    "stop_loss": 0.0,
                    "take_profit": 0.0,
                    "position_size": 0.0,
                    "reason": f"Exit SHORT: {reason}",
                }

            return {
                "signal": "SHORT",
                "confidence": 1.0 - xgb_proba,
                "stop_loss": self._stop_price,
                "take_profit": self._tp_price,
                "position_size": p["risk_per_trade"],
                "reason": f"Holding SHORT (trail={'active' if self._trail_active else 'inactive'})",
            }

        # ── Entry logic (FLAT) ───────────────────────────────────────────
        if self._bars_since_trade < p["cooldown_bars"]:
            return {
                "signal": "FLAT",
                "confidence": xgb_proba,
                "stop_loss": 0.0,
                "take_profit": 0.0,
                "position_size": 0.0,
                "reason": f"Cooldown ({self._bars_since_trade}/{p['cooldown_bars']})",
            }

        if atr_val <= 0:
            return {
                "signal": "FLAT",
                "confidence": xgb_proba,
                "stop_loss": 0.0,
                "take_profit": 0.0,
                "position_size": 0.0,
                "reason": "ATR <= 0",
            }

        # Volume filter
        vol_ok = vol_val > p["vol_filter"] * vol_ma_val if vol_ma_val > 0 else False

        # LONG conditions
        trend_up = ma_f_val > ma_s_val
        rsi_ok_long = rsi_val < p["rsi_oversold"]
        xgb_ok_long = xgb_proba > p["confidence_threshold"]

        # SHORT conditions
        trend_down = ma_f_val < ma_s_val
        rsi_ok_short = rsi_val > p["rsi_overbought"]
        xgb_ok_short = (1.0 - xgb_proba) > p["confidence_threshold"]

        reasons_parts = []

        if trend_up and rsi_ok_long and vol_ok and xgb_ok_long:
            stop_dist = p["atr_stop_mult"] * atr_val
            stop_price = last_price - stop_dist
            tp_price = last_price + p["atr_tp_mult"] * atr_val

            # Position size (risk-based)
            risk_fraction = p["risk_per_trade"]
            pos_size = min(risk_fraction * p["leverage"], 1.0)

            self._position = "LONG"
            self._entry_price = last_price
            self._stop_price = stop_price
            self._tp_price = tp_price
            self._trail_active = False
            self._trail_price = stop_price
            self._bars_since_trade = 0

            return {
                "signal": "LONG",
                "confidence": xgb_proba,
                "stop_loss": stop_price,
                "take_profit": tp_price,
                "position_size": pos_size,
                "reason": (f"LONG entry: MA({p['ma_fast']}/{p['ma_slow']}) bullish, "
                          f"RSI={rsi_val:.1f}<{p['rsi_oversold']}, "
                          f"XGB={xgb_proba:.3f}>{p['confidence_threshold']}"),
            }

        if p["allow_short"] and trend_down and rsi_ok_short and vol_ok and xgb_ok_short:
            stop_dist = p["atr_stop_mult"] * atr_val
            stop_price = last_price + stop_dist
            tp_price = last_price - p["atr_tp_mult"] * atr_val

            risk_fraction = p["risk_per_trade"]
            pos_size = min(risk_fraction * p["leverage"], 1.0)

            self._position = "SHORT"
            self._entry_price = last_price
            self._stop_price = stop_price
            self._tp_price = tp_price
            self._trail_active = False
            self._trail_price = stop_price
            self._bars_since_trade = 0

            return {
                "signal": "SHORT",
                "confidence": 1.0 - xgb_proba,
                "stop_loss": stop_price,
                "take_profit": tp_price,
                "position_size": pos_size,
                "reason": (f"SHORT entry: MA bearish, "
                          f"RSI={rsi_val:.1f}>{p['rsi_overbought']}, "
                          f"XGB bear={1-xgb_proba:.3f}>{p['confidence_threshold']}"),
            }

        # No signal - build reason
        if not trend_up and not (p["allow_short"] and trend_down):
            reasons_parts.append("No trend alignment")
        if trend_up and not rsi_ok_long:
            reasons_parts.append(f"RSI={rsi_val:.1f} not oversold (<{p['rsi_oversold']})")
        if trend_up and not xgb_ok_long:
            reasons_parts.append(f"XGB={xgb_proba:.3f} below threshold ({p['confidence_threshold']})")
        if not vol_ok:
            reasons_parts.append("Volume filter failed")

        return {
            "signal": "FLAT",
            "confidence": xgb_proba,
            "stop_loss": 0.0,
            "take_profit": 0.0,
            "position_size": 0.0,
            "reason": "No entry: " + "; ".join(reasons_parts) if reasons_parts else "No conditions met",
        }

    def reset(self):
        """Reset internal state (for new session)."""
        self._position = "FLAT"
        self._entry_price = 0.0
        self._stop_price = 0.0
        self._tp_price = 0.0
        self._trail_active = False
        self._trail_price = 0.0
        self._bars_since_trade = 999


# ── Standalone Demo ──────────────────────────────────────────────────────────
def load_latest_15m(n_bars: int = 200) -> pd.DataFrame:
    """Load latest n_bars of 15m candles from sqlite."""
    conn = sqlite3.connect(str(DB_PATH))

    # Get total count to compute offset
    count_df = pd.read_sql_query(
        "SELECT COUNT(*) as cnt FROM ohlcv_1m WHERE symbol=?",
        conn, params=(SYMBOL,),
    )
    total_1m = count_df["cnt"].iloc[0]

    # We need n_bars * 15 minutes of 1m data
    needed_1m = n_bars * 15 + 200 * 15  # extra for warmup
    offset = max(0, total_1m - needed_1m)

    df = pd.read_sql_query(
        f"SELECT datetime, open, high, low, close, volume "
        f"FROM ohlcv_1m WHERE symbol=? ORDER BY datetime "
        f"LIMIT {needed_1m} OFFSET {offset}",
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

    return df_15m.tail(n_bars)


def main():
    print("=" * 70)
    print("  Hybrid Strategy Deploy - Signal Generator")
    print("=" * 70)

    model_path = DEFAULT_MODEL_PATH
    if not Path(model_path).exists():
        print(f"\n  [경고] XGBoost 모델 없음: {model_path}")
        print("  먼저 strategy_hybrid.py를 실행하여 모델을 학습하세요.")
        print("  데모 모드로 최근 데이터 로드 후 CMA-ES 단독 시그널 표시...")
        print()

        # Load data and show what signal would be (without XGBoost)
        df_15m = load_latest_15m(200)
        print(f"  최근 데이터: {len(df_15m)}개 15분봉")
        print(f"  기간: {df_15m.index[0]} ~ {df_15m.index[-1]}")
        print(f"  현재가: {df_15m['close'].iloc[-1]:,.2f}")

        # Compute indicators manually for display
        c = df_15m["close"]
        ma_f = c.rolling(DEFAULT_PARAMS["ma_fast"]).mean().iloc[-1]
        ma_s = c.rolling(DEFAULT_PARAMS["ma_slow"]).mean().iloc[-1]

        delta = c.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = (100 - (100 / (1 + rs))).iloc[-1]

        tr = pd.concat([
            df_15m["high"] - df_15m["low"],
            (df_15m["high"] - c.shift(1)).abs(),
            (df_15m["low"] - c.shift(1)).abs(),
        ], axis=1).max(axis=1)
        atr_val = tr.rolling(14).mean().iloc[-1]

        print(f"\n  지표:")
        print(f"    MA({DEFAULT_PARAMS['ma_fast']}): {ma_f:,.2f}")
        print(f"    MA({DEFAULT_PARAMS['ma_slow']}): {ma_s:,.2f}")
        print(f"    추세: {'상승 (fast > slow)' if ma_f > ma_s else '하락 (fast < slow)'}")
        print(f"    RSI(14): {rsi:.1f}")
        print(f"    ATR(14): {atr_val:,.2f}")
        print(f"\n  XGBoost 모델 없이는 CMA-ES 조건만 확인:")
        print(f"    추세 정렬: {'O' if ma_f > ma_s else 'X'}")
        print(f"    RSI 과매도 (<{DEFAULT_PARAMS['rsi_oversold']}): {'O' if rsi < DEFAULT_PARAMS['rsi_oversold'] else 'X'}")
        return

    # Normal mode with XGBoost model
    print(f"\n  XGBoost 모델 로드: {model_path}")
    strategy = HybridStrategy(model_path=model_path)

    df_15m = load_latest_15m(200)
    print(f"  최근 데이터: {len(df_15m)}개 15분봉")
    print(f"  기간: {df_15m.index[0]} ~ {df_15m.index[-1]}")
    print(f"  현재가: {df_15m['close'].iloc[-1]:,.2f}")

    signal = strategy.update(df_15m)

    print(f"\n  {'='*50}")
    print(f"  시그널:      {signal['signal']}")
    print(f"  신뢰도:      {signal['confidence']:.4f}")
    print(f"  손절가:      {signal['stop_loss']:,.2f}")
    print(f"  익절가:      {signal['take_profit']:,.2f}")
    print(f"  포지션 크기: {signal['position_size']:.4f}")
    print(f"  사유:        {signal['reason']}")
    print(f"  {'='*50}")


if __name__ == "__main__":
    main()
