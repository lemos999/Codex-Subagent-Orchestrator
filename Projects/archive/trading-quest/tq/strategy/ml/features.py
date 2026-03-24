"""Feature engineering pipeline for ML trading models.

Converts raw OHLCV DataFrames into ML-ready feature matrices.
All computations use pandas/numpy only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from tq.strategy.indicator import (
    rsi, macd, bollinger_bands, atr, sma, stochastic,
)


class FeatureEngineering:
    """Convert OHLCV data into ML-ready features."""

    # Minimum rows required to compute all features (SMA50 needs 50)
    MIN_ROWS = 60

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------

    def build_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create feature matrix from OHLCV data.

        Expected columns (case-insensitive): open, high, low, close, volume.

        Features produced:
        - Returns (1d, 5d, 10d, 20d)
        - RSI(14), RSI(7)
        - MACD histogram
        - Bollinger Band %B
        - ATR normalized
        - Volume change ratio
        - SMA ratios (close/SMA20, close/SMA50)
        - Stochastic %K, %D
        - Day of week (one-hot, 5 columns)

        Returns a DataFrame aligned to *df*'s index (rows with NaN
        from look-back windows are dropped).
        """
        close, high, low, volume = self._extract_columns(df)

        feats: dict[str, pd.Series] = {}

        # -- Returns --
        for n in (1, 5, 10, 20):
            feats[f"ret_{n}d"] = close.pct_change(n)

        # -- RSI --
        feats["rsi_14"] = rsi(close, 14) / 100.0
        feats["rsi_7"] = rsi(close, 7) / 100.0

        # -- MACD histogram --
        _, _, hist = macd(close, 12, 26, 9)
        feats["macd_hist"] = hist / close  # normalise by price

        # -- Bollinger %B --
        upper, middle, lower = bollinger_bands(close, 20, 2.0)
        band_width = (upper - lower).replace(0, np.nan)
        feats["bb_pctb"] = (close - lower) / band_width

        # -- ATR normalised --
        atr_val = atr(high, low, close, 14)
        feats["atr_norm"] = atr_val / close

        # -- Volume change ratio --
        vol_sma = volume.rolling(20).mean().replace(0, np.nan)
        feats["vol_ratio"] = volume / vol_sma

        # -- SMA ratios --
        sma20 = sma(close, 20).replace(0, np.nan)
        sma50 = sma(close, 50).replace(0, np.nan)
        feats["close_sma20"] = close / sma20
        feats["close_sma50"] = close / sma50

        # -- Stochastic --
        k, d = stochastic(high, low, close, 14, 3)
        feats["stoch_k"] = k / 100.0
        feats["stoch_d"] = d / 100.0

        # -- Day of week one-hot --
        if hasattr(df.index, "dayofweek"):
            dow = df.index.dayofweek
        else:
            dow = pd.to_datetime(df.index).dayofweek
        for day_i in range(5):
            feats[f"dow_{day_i}"] = (dow == day_i).astype(float)

        result = pd.DataFrame(feats, index=df.index)
        result.replace([np.inf, -np.inf], np.nan, inplace=True)
        result.dropna(inplace=True)
        return result

    def build_labels(
        self,
        df: pd.DataFrame,
        horizon: int = 5,
        threshold: float = 0.01,
    ) -> pd.Series:
        """Create binary labels: 1 if price rises > *threshold* within
        *horizon* days, 0 otherwise."""
        close, _, _, _ = self._extract_columns(df)
        future_ret = close.shift(-horizon) / close - 1.0
        labels = (future_ret > threshold).astype(float)
        labels.name = "label"
        return labels

    def prepare_sequences(
        self,
        features: pd.DataFrame,
        labels: pd.Series,
        seq_length: int = 30,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Create sliding-window sequences for LSTM-like models.

        Returns
        -------
        X : ndarray of shape (n_samples, seq_length, n_features)
        y : ndarray of shape (n_samples,)
        """
        # Align features and labels
        common = features.index.intersection(labels.dropna().index)
        feat = features.loc[common].values
        lab = labels.loc[common].values

        X_list: list[np.ndarray] = []
        y_list: list[float] = []
        for i in range(seq_length, len(feat)):
            X_list.append(feat[i - seq_length : i])
            y_list.append(lab[i])
        if not X_list:
            return np.empty((0, seq_length, features.shape[1])), np.empty(0)
        return np.array(X_list), np.array(y_list)

    # -----------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------

    @staticmethod
    def _extract_columns(
        df: pd.DataFrame,
    ) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
        """Extract close/high/low/volume handling mixed-case columns."""
        cols = {c.lower(): c for c in df.columns}
        close = df[cols.get("close", "close")]
        high = df[cols.get("high", "high")]
        low = df[cols.get("low", "low")]
        volume = df[cols.get("volume", "volume")] if "volume" in cols else pd.Series(
            0.0, index=df.index
        )
        return close, high, low, volume
