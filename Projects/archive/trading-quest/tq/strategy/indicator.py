"""Technical indicators for Trading Quest.

All functions accept a pandas Series or DataFrame and return Series.
"""
from __future__ import annotations

from typing import Optional, Tuple

import numpy as np
import pandas as pd


# ======================================================================
# Moving Averages
# ======================================================================

def sma(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(window=period, min_periods=period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average."""
    return series.ewm(span=period, adjust=False).mean()


def wma(series: pd.Series, period: int) -> pd.Series:
    """Weighted Moving Average."""
    weights = np.arange(1, period + 1, dtype=float)
    return series.rolling(window=period).apply(
        lambda x: np.dot(x, weights) / weights.sum(), raw=True
    )


def dema(series: pd.Series, period: int) -> pd.Series:
    """Double Exponential Moving Average."""
    e = ema(series, period)
    return 2 * e - ema(e, period)


def tema(series: pd.Series, period: int) -> pd.Series:
    """Triple Exponential Moving Average."""
    e1 = ema(series, period)
    e2 = ema(e1, period)
    e3 = ema(e2, period)
    return 3 * e1 - 3 * e2 + e3


# ======================================================================
# Momentum / Oscillators
# ======================================================================

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def macd(series: pd.Series, fast: int = 12, slow: int = 26,
         signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """MACD: returns (macd_line, signal_line, histogram)."""
    fast_ema = ema(series, fast)
    slow_ema = ema(series, slow)
    macd_line = fast_ema - slow_ema
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def stochastic(high: pd.Series, low: pd.Series, close: pd.Series,
               k_period: int = 14, d_period: int = 3
               ) -> Tuple[pd.Series, pd.Series]:
    """Stochastic Oscillator: returns (%K, %D)."""
    lowest = low.rolling(window=k_period).min()
    highest = high.rolling(window=k_period).max()
    k = 100 * (close - lowest) / (highest - lowest).replace(0, np.nan)
    d = sma(k, d_period)
    return k, d


def williams_r(high: pd.Series, low: pd.Series, close: pd.Series,
               period: int = 14) -> pd.Series:
    """Williams %R."""
    highest = high.rolling(window=period).max()
    lowest = low.rolling(window=period).min()
    return -100 * (highest - close) / (highest - lowest).replace(0, np.nan)


def cci(high: pd.Series, low: pd.Series, close: pd.Series,
        period: int = 20) -> pd.Series:
    """Commodity Channel Index."""
    tp = (high + low + close) / 3
    tp_sma = sma(tp, period)
    mean_dev = tp.rolling(window=period).apply(
        lambda x: np.mean(np.abs(x - np.mean(x))), raw=True
    )
    return (tp - tp_sma) / (0.015 * mean_dev).replace(0, np.nan)


def momentum(series: pd.Series, period: int = 10) -> pd.Series:
    """Momentum indicator."""
    return series - series.shift(period)


def roc(series: pd.Series, period: int = 10) -> pd.Series:
    """Rate of Change."""
    prev = series.shift(period)
    return ((series - prev) / prev.replace(0, np.nan)) * 100


# ======================================================================
# Volatility
# ======================================================================

def bollinger_bands(series: pd.Series, period: int = 20,
                    std_dev: float = 2.0
                    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Bollinger Bands: returns (upper, middle, lower)."""
    middle = sma(series, period)
    std = series.rolling(window=period).std()
    upper = middle + std_dev * std
    lower = middle - std_dev * std
    return upper, middle, lower


def atr(high: pd.Series, low: pd.Series, close: pd.Series,
        period: int = 14) -> pd.Series:
    """Average True Range."""
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()


def keltner_channel(high: pd.Series, low: pd.Series, close: pd.Series,
                    ema_period: int = 20, atr_period: int = 10,
                    multiplier: float = 2.0
                    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Keltner Channel: returns (upper, middle, lower)."""
    middle = ema(close, ema_period)
    atr_val = atr(high, low, close, atr_period)
    upper = middle + multiplier * atr_val
    lower = middle - multiplier * atr_val
    return upper, middle, lower


def donchian_channel(high: pd.Series, low: pd.Series,
                     period: int = 20
                     ) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Donchian Channel: returns (upper, middle, lower)."""
    upper = high.rolling(window=period).max()
    lower = low.rolling(window=period).min()
    middle = (upper + lower) / 2
    return upper, middle, lower


# ======================================================================
# Trend
# ======================================================================

def adx(high: pd.Series, low: pd.Series, close: pd.Series,
        period: int = 14) -> pd.Series:
    """Average Directional Index."""
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

    atr_val = atr(high, low, close, period)
    plus_di = 100 * ema(plus_dm, period) / atr_val.replace(0, np.nan)
    minus_di = 100 * ema(minus_dm, period) / atr_val.replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return ema(dx, period)


def supertrend(high: pd.Series, low: pd.Series, close: pd.Series,
               period: int = 10, multiplier: float = 3.0
               ) -> Tuple[pd.Series, pd.Series]:
    """Supertrend indicator: returns (supertrend_line, direction).

    direction: 1 = uptrend, -1 = downtrend.
    """
    atr_val = atr(high, low, close, period)
    hl2 = (high + low) / 2
    upper_band = hl2 + multiplier * atr_val
    lower_band = hl2 - multiplier * atr_val

    st = pd.Series(index=close.index, dtype=float)
    direction = pd.Series(index=close.index, dtype=float)

    st.iloc[0] = upper_band.iloc[0]
    direction.iloc[0] = 1

    for i in range(1, len(close)):
        if close.iloc[i] > upper_band.iloc[i - 1]:
            direction.iloc[i] = 1
        elif close.iloc[i] < lower_band.iloc[i - 1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i - 1]

        if direction.iloc[i] == 1:
            st.iloc[i] = max(lower_band.iloc[i],
                             st.iloc[i - 1] if direction.iloc[i - 1] == 1 else lower_band.iloc[i])
        else:
            st.iloc[i] = min(upper_band.iloc[i],
                             st.iloc[i - 1] if direction.iloc[i - 1] == -1 else upper_band.iloc[i])

    return st, direction


def ichimoku(high: pd.Series, low: pd.Series, close: pd.Series,
             tenkan: int = 9, kijun: int = 26, senkou_b: int = 52
             ) -> dict[str, pd.Series]:
    """Ichimoku Cloud: returns dict with tenkan_sen, kijun_sen,
    senkou_span_a, senkou_span_b, chikou_span."""
    tenkan_sen = (high.rolling(tenkan).max() + low.rolling(tenkan).min()) / 2
    kijun_sen = (high.rolling(kijun).max() + low.rolling(kijun).min()) / 2
    senkou_a = ((tenkan_sen + kijun_sen) / 2).shift(kijun)
    senkou_b_val = ((high.rolling(senkou_b).max() + low.rolling(senkou_b).min()) / 2).shift(kijun)
    chikou = close.shift(-kijun)
    return {
        "tenkan_sen": tenkan_sen,
        "kijun_sen": kijun_sen,
        "senkou_span_a": senkou_a,
        "senkou_span_b": senkou_b_val,
        "chikou_span": chikou,
    }


def parabolic_sar(high: pd.Series, low: pd.Series,
                  af_start: float = 0.02, af_step: float = 0.02,
                  af_max: float = 0.20) -> pd.Series:
    """Parabolic SAR."""
    length = len(high)
    sar = pd.Series(index=high.index, dtype=float)
    direction = 1  # 1=up, -1=down
    af = af_start
    ep = low.iloc[0]
    sar.iloc[0] = high.iloc[0]

    for i in range(1, length):
        if direction == 1:
            sar.iloc[i] = sar.iloc[i - 1] + af * (ep - sar.iloc[i - 1])
            sar.iloc[i] = min(sar.iloc[i], low.iloc[i - 1])
            if i >= 2:
                sar.iloc[i] = min(sar.iloc[i], low.iloc[i - 2])
            if low.iloc[i] < sar.iloc[i]:
                direction = -1
                sar.iloc[i] = ep
                ep = low.iloc[i]
                af = af_start
            else:
                if high.iloc[i] > ep:
                    ep = high.iloc[i]
                    af = min(af + af_step, af_max)
        else:
            sar.iloc[i] = sar.iloc[i - 1] + af * (ep - sar.iloc[i - 1])
            sar.iloc[i] = max(sar.iloc[i], high.iloc[i - 1])
            if i >= 2:
                sar.iloc[i] = max(sar.iloc[i], high.iloc[i - 2])
            if high.iloc[i] > sar.iloc[i]:
                direction = 1
                sar.iloc[i] = ep
                ep = high.iloc[i]
                af = af_start
            else:
                if low.iloc[i] < ep:
                    ep = low.iloc[i]
                    af = min(af + af_step, af_max)
    return sar


# ======================================================================
# Volume
# ======================================================================

def vwap(high: pd.Series, low: pd.Series, close: pd.Series,
         volume: pd.Series) -> pd.Series:
    """Volume Weighted Average Price."""
    tp = (high + low + close) / 3
    cum_tpv = (tp * volume).cumsum()
    cum_vol = volume.cumsum()
    return cum_tpv / cum_vol.replace(0, np.nan)


def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """On Balance Volume."""
    direction = close.diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
    return (volume * direction).cumsum()


def mfi(high: pd.Series, low: pd.Series, close: pd.Series,
        volume: pd.Series, period: int = 14) -> pd.Series:
    """Money Flow Index."""
    tp = (high + low + close) / 3
    mf = tp * volume
    delta = tp.diff()
    pos_mf = mf.where(delta > 0, 0.0).rolling(period).sum()
    neg_mf = mf.where(delta <= 0, 0.0).rolling(period).sum()
    ratio = pos_mf / neg_mf.replace(0, np.nan)
    return 100 - (100 / (1 + ratio))


def accumulation_distribution(high: pd.Series, low: pd.Series,
                               close: pd.Series, volume: pd.Series) -> pd.Series:
    """Accumulation/Distribution Line."""
    clv = ((close - low) - (high - close)) / (high - low).replace(0, np.nan)
    return (clv * volume).cumsum()


# ======================================================================
# Pattern helpers
# ======================================================================

def crossover(series_a: pd.Series, series_b: pd.Series) -> pd.Series:
    """True where series_a crosses above series_b."""
    return (series_a > series_b) & (series_a.shift(1) <= series_b.shift(1))


def crossunder(series_a: pd.Series, series_b: pd.Series) -> pd.Series:
    """True where series_a crosses below series_b."""
    return (series_a < series_b) & (series_a.shift(1) >= series_b.shift(1))


def highest(series: pd.Series, period: int) -> pd.Series:
    """Rolling highest value."""
    return series.rolling(window=period).max()


def lowest(series: pd.Series, period: int) -> pd.Series:
    """Rolling lowest value."""
    return series.rolling(window=period).min()
