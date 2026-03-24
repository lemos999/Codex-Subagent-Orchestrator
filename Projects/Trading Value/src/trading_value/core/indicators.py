"""Pure-function indicator engine for the Trading Value automated trading system.

All functions take pandas DataFrames or numeric inputs and return computed values.
No side effects, no API calls, no state.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from .models import (
    CloudPosition,
    OHLCV,
    ProfileBias,
    Timeframe,
    TimeframeSnapshot,
    TkState,
    Zone,
)

# ---------------------------------------------------------------------------
# 1. Ichimoku (spec v2 §5.2)
# ---------------------------------------------------------------------------


def compute_ichimoku(
    df: pd.DataFrame,
    tenkan: int = 9,
    kijun: int = 26,
    senkou_b: int = 52,
) -> pd.DataFrame:
    """Add ichimoku columns to OHLCV DataFrame.

    Adds columns: tenkan, kijun, senkou_a, senkou_b, cloud_top, cloud_bottom

    Important per spec v2 §5.2:
    - cloud_top = max(senkou_a, senkou_b) at CURRENT bar (not forward-shifted)
    - cloud_bottom = min(senkou_a, senkou_b) at CURRENT bar
    - Do NOT use chart UI forward-shift rendering values
    """
    if len(df) < senkou_b:
        raise ValueError(
            f"Need at least {senkou_b} bars for Ichimoku, got {len(df)}"
        )

    high = df["high"]
    low = df["low"]

    # Tenkan = (highest_high + lowest_low) / 2 over tenkan period
    tenkan_high = high.rolling(window=tenkan, min_periods=tenkan).max()
    tenkan_low = low.rolling(window=tenkan, min_periods=tenkan).min()
    df = df.copy()
    df["tenkan"] = (tenkan_high + tenkan_low) / 2

    # Kijun = (highest_high + lowest_low) / 2 over kijun period
    kijun_high = high.rolling(window=kijun, min_periods=kijun).max()
    kijun_low = low.rolling(window=kijun, min_periods=kijun).min()
    df["kijun"] = (kijun_high + kijun_low) / 2

    # Senkou A = (tenkan + kijun) / 2
    df["senkou_a"] = (df["tenkan"] + df["kijun"]) / 2

    # Senkou B = (highest_high + lowest_low) / 2 over senkou_b period
    sb_high = high.rolling(window=senkou_b, min_periods=senkou_b).max()
    sb_low = low.rolling(window=senkou_b, min_periods=senkou_b).min()
    df["senkou_b"] = (sb_high + sb_low) / 2

    # Cloud boundaries at current bar (no forward shift)
    df["cloud_top"] = df[["senkou_a", "senkou_b"]].max(axis=1)
    df["cloud_bottom"] = df[["senkou_a", "senkou_b"]].min(axis=1)

    return df


# ---------------------------------------------------------------------------
# 1b. Forward Cloud Analysis — use Ichimoku's predictive power
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ForwardCloudAnalysis:
    """Analysis of the Ichimoku forward (leading) cloud."""
    # Future cloud at +26 bars
    future_cloud_top: float
    future_cloud_bottom: float
    future_cloud_thickness: float  # absolute
    future_cloud_thickness_pct: float  # relative to price
    # Cloud direction
    cloud_rising: bool  # future cloud top > current cloud top
    cloud_falling: bool
    # Cloud twist (senkou_a crosses senkou_b within next 26 bars)
    twist_detected: bool
    twist_direction: str  # "bullish" (a crosses above b) / "bearish" / "none"
    # Cloud as future support/resistance zones
    future_support: float  # cloud bottom as support
    future_resistance: float  # cloud top as resistance


def analyze_forward_cloud(
    df: pd.DataFrame,
    displacement: int = 26,
    tenkan: int = 9,
    kijun: int = 26,
    senkou_b_period: int = 52,
) -> ForwardCloudAnalysis | None:
    """Analyze the forward (leading) cloud for predictive signals.

    The forward cloud is senkou_a and senkou_b shifted 26 bars into the future.
    This is what makes Ichimoku unique — it predicts future support/resistance.
    """
    n = len(df)
    if n < senkou_b_period + displacement:
        return None

    high = df["high"].values
    low = df["low"].values

    def _midpoint(arr, period, idx):
        start = max(0, idx - period + 1)
        return (np.max(arr[start:idx + 1]) + np.min(arr[start:idx + 1])) / 2

    last = n - 1

    # Current senkou values (at current bar)
    tenkan_now = _midpoint(high, tenkan, last) / 2 + _midpoint(low, tenkan, last) / 2
    kijun_now = _midpoint(high, kijun, last) / 2 + _midpoint(low, kijun, last) / 2
    # Recompute properly
    t_h = np.max(high[max(0, last - tenkan + 1):last + 1])
    t_l = np.min(low[max(0, last - tenkan + 1):last + 1])
    tenkan_now = (t_h + t_l) / 2

    k_h = np.max(high[max(0, last - kijun + 1):last + 1])
    k_l = np.min(low[max(0, last - kijun + 1):last + 1])
    kijun_now = (k_h + k_l) / 2

    senkou_a_now = (tenkan_now + kijun_now) / 2
    sb_h = np.max(high[max(0, last - senkou_b_period + 1):last + 1])
    sb_l = np.min(low[max(0, last - senkou_b_period + 1):last + 1])
    senkou_b_now = (sb_h + sb_l) / 2

    current_cloud_top = max(senkou_a_now, senkou_b_now)
    current_cloud_bottom = min(senkou_a_now, senkou_b_now)

    # Future cloud = current senkou values (they will be displayed 26 bars ahead)
    future_top = current_cloud_top
    future_bottom = current_cloud_bottom
    thickness = future_top - future_bottom
    price = float(df["close"].iloc[-1])
    thickness_pct = thickness / price * 100 if price > 0 else 0

    # Cloud 26 bars ago (what was predicted for now)
    past_idx = max(0, last - displacement)
    pt_h = np.max(high[max(0, past_idx - tenkan + 1):past_idx + 1])
    pt_l = np.min(low[max(0, past_idx - tenkan + 1):past_idx + 1])
    pk_h = np.max(high[max(0, past_idx - kijun + 1):past_idx + 1])
    pk_l = np.min(low[max(0, past_idx - kijun + 1):past_idx + 1])
    past_sa = ((pt_h + pt_l) / 2 + (pk_h + pk_l) / 2) / 2
    psb_h = np.max(high[max(0, past_idx - senkou_b_period + 1):past_idx + 1])
    psb_l = np.min(low[max(0, past_idx - senkou_b_period + 1):past_idx + 1])
    past_sb = (psb_h + psb_l) / 2
    past_cloud_top = max(past_sa, past_sb)

    cloud_rising = future_top > past_cloud_top
    cloud_falling = future_top < past_cloud_top

    # Twist detection: check if senkou_a and senkou_b cross in recent bars
    twist_detected = False
    twist_direction = "none"
    for i in range(max(0, last - displacement), last):
        i_t_h = np.max(high[max(0, i - tenkan + 1):i + 1])
        i_t_l = np.min(low[max(0, i - tenkan + 1):i + 1])
        i_k_h = np.max(high[max(0, i - kijun + 1):i + 1])
        i_k_l = np.min(low[max(0, i - kijun + 1):i + 1])
        sa_i = ((i_t_h + i_t_l) / 2 + (i_k_h + i_k_l) / 2) / 2

        i1 = i + 1
        if i1 >= n:
            break
        i1_t_h = np.max(high[max(0, i1 - tenkan + 1):i1 + 1])
        i1_t_l = np.min(low[max(0, i1 - tenkan + 1):i1 + 1])
        i1_k_h = np.max(high[max(0, i1 - kijun + 1):i1 + 1])
        i1_k_l = np.min(low[max(0, i1 - kijun + 1):i1 + 1])
        sa_i1 = ((i1_t_h + i1_t_l) / 2 + (i1_k_h + i1_k_l) / 2) / 2

        isb_h = np.max(high[max(0, i - senkou_b_period + 1):i + 1])
        isb_l = np.min(low[max(0, i - senkou_b_period + 1):i + 1])
        sb_i = (isb_h + isb_l) / 2

        i1sb_h = np.max(high[max(0, i1 - senkou_b_period + 1):i1 + 1])
        i1sb_l = np.min(low[max(0, i1 - senkou_b_period + 1):i1 + 1])
        sb_i1 = (i1sb_h + i1sb_l) / 2

        if sa_i <= sb_i and sa_i1 > sb_i1:
            twist_detected = True
            twist_direction = "bullish"
        elif sa_i >= sb_i and sa_i1 < sb_i1:
            twist_detected = True
            twist_direction = "bearish"

    return ForwardCloudAnalysis(
        future_cloud_top=future_top,
        future_cloud_bottom=future_bottom,
        future_cloud_thickness=thickness,
        future_cloud_thickness_pct=thickness_pct,
        cloud_rising=cloud_rising,
        cloud_falling=cloud_falling,
        twist_detected=twist_detected,
        twist_direction=twist_direction,
        future_support=future_bottom,
        future_resistance=future_top,
    )


# ---------------------------------------------------------------------------
# 1c. Donchian Channel
# ---------------------------------------------------------------------------


def compute_donchian(df: pd.DataFrame, period: int = 20) -> tuple[float, float, float]:
    """Compute Donchian Channel for the most recent bar.

    Returns (upper, lower, middle) where:
    - upper = highest high over last `period` bars
    - lower = lowest low over last `period` bars
    - middle = (upper + lower) / 2
    """
    if len(df) < period:
        raise ValueError(f"Need at least {period} bars, got {len(df)}")
    recent = df.iloc[-period:]
    upper = float(recent["high"].max())
    lower = float(recent["low"].min())
    middle = (upper + lower) / 2
    return upper, lower, middle


def compute_donchian_series(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """Compute Donchian Channel for all bars. Returns DataFrame with upper/lower/middle columns."""
    result = df.copy()
    result["dc_upper"] = df["high"].rolling(window=period, min_periods=period).max()
    result["dc_lower"] = df["low"].rolling(window=period, min_periods=period).min()
    result["dc_middle"] = (result["dc_upper"] + result["dc_lower"]) / 2
    return result


# ---------------------------------------------------------------------------
# 2. ATR (spec v2 §5.4) — Wilder's smoothing
# ---------------------------------------------------------------------------


def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Compute ATR using Wilder's smoothing method."""
    if len(df) < period + 1:
        raise ValueError(
            f"Need at least {period + 1} bars for ATR({period}), got {len(df)}"
        )

    high = df["high"].values
    low = df["low"].values
    close = df["close"].values

    tr = np.empty(len(df))
    tr[0] = high[0] - low[0]
    for i in range(1, len(df)):
        tr[i] = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1]),
        )

    atr = np.full(len(df), np.nan)
    # First ATR = simple mean of first `period` TR values
    atr[period] = np.mean(tr[1 : period + 1])
    # Wilder's smoothing: ATR_i = (ATR_{i-1} * (period-1) + TR_i) / period
    for i in range(period + 1, len(df)):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period

    return pd.Series(atr, index=df.index, name="atr")


# ---------------------------------------------------------------------------
# 3. Volume Profile (spec v2 §5.3)
# ---------------------------------------------------------------------------


def compute_volume_profile(
    df: pd.DataFrame, window: int
) -> tuple[float, float, float]:
    """Compute fixed-window volume profile.

    Args:
        df: OHLCV DataFrame with at least ``window`` rows.
        window: number of bars for the profile (96 for 30m, 120 for 1h, 90 for 4h).

    Returns:
        (poc, vah, val) where:
        - poc: Point of Control — price level with highest volume
        - vah: Value Area High — upper bound of 70% volume area
        - val: Value Area Low — lower bound of 70% volume area
    """
    if len(df) < window:
        raise ValueError(
            f"Need at least {window} bars for volume profile, got {len(df)}"
        )

    subset = df.iloc[-window:]
    price_low = subset["low"].min()
    price_high = subset["high"].max()

    if price_high == price_low:
        return float(price_low), float(price_high), float(price_low)

    num_bins = 100
    bin_edges = np.linspace(price_low, price_high, num_bins + 1)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    volume_at_bin = np.zeros(num_bins)

    # Distribute each bar's volume across overlapping bins
    for _, row in subset.iterrows():
        bar_low = row["low"]
        bar_high = row["high"]
        bar_vol = row["volume"]
        if bar_high == bar_low:
            # Single-tick bar — put all volume in the matching bin
            idx = int(
                np.clip(
                    np.searchsorted(bin_edges, bar_low, side="right") - 1,
                    0,
                    num_bins - 1,
                )
            )
            volume_at_bin[idx] += bar_vol
            continue

        # Find bins that overlap with [bar_low, bar_high]
        low_idx = max(
            int(np.searchsorted(bin_edges, bar_low, side="right") - 1), 0
        )
        high_idx = min(
            int(np.searchsorted(bin_edges, bar_high, side="left")),
            num_bins - 1,
        )
        if low_idx > high_idx:
            low_idx = high_idx

        overlap_count = high_idx - low_idx + 1
        if overlap_count > 0:
            vol_per_bin = bar_vol / overlap_count
            volume_at_bin[low_idx : high_idx + 1] += vol_per_bin

    # POC = bin center with maximum volume
    poc_idx = int(np.argmax(volume_at_bin))
    poc = float(bin_centers[poc_idx])

    # Value Area: expand from POC outward until 70% of total volume is captured
    total_volume = volume_at_bin.sum()
    if total_volume == 0:
        return poc, float(bin_centers[-1]), float(bin_centers[0])

    target_volume = total_volume * 0.70
    va_volume = volume_at_bin[poc_idx]
    va_low_idx = poc_idx
    va_high_idx = poc_idx

    while va_volume < target_volume:
        # Look at adjacent bins and add the one with more volume
        left_vol = volume_at_bin[va_low_idx - 1] if va_low_idx > 0 else -1.0
        right_vol = (
            volume_at_bin[va_high_idx + 1]
            if va_high_idx < num_bins - 1
            else -1.0
        )

        if left_vol < 0 and right_vol < 0:
            break

        if left_vol >= right_vol:
            va_low_idx -= 1
            va_volume += volume_at_bin[va_low_idx]
        else:
            va_high_idx += 1
            va_volume += volume_at_bin[va_high_idx]

    vah = float(bin_edges[va_high_idx + 1])  # upper edge
    val = float(bin_edges[va_low_idx])  # lower edge

    return poc, vah, val


# ---------------------------------------------------------------------------
# 4. Swing Detection (spec v2 §5.5)
# ---------------------------------------------------------------------------


def detect_swings(
    df: pd.DataFrame, left: int = 2, right: int = 2
) -> tuple[list[tuple[int, float]], list[tuple[int, float]]]:
    """Detect confirmed swing highs and lows using fractal method.

    A swing high at index i is confirmed when:
    - high[i] >= high[i-left:i] and high[i] >= high[i+1:i+right+1]
    - At least ``right`` bars have completed after the swing

    Returns:
        (swing_highs, swing_lows) — lists of (index, price) tuples, most recent last
    """
    highs = df["high"].values
    lows = df["low"].values
    n = len(df)

    swing_highs: list[tuple[int, float]] = []
    swing_lows: list[tuple[int, float]] = []

    # We can only confirm up to n - right - 1
    for i in range(left, n - right):
        # Swing high check
        is_swing_high = True
        for j in range(i - left, i):
            if highs[j] > highs[i]:
                is_swing_high = False
                break
        if is_swing_high:
            for j in range(i + 1, i + right + 1):
                if highs[j] > highs[i]:
                    is_swing_high = False
                    break
        if is_swing_high:
            swing_highs.append((i, float(highs[i])))

        # Swing low check
        is_swing_low = True
        for j in range(i - left, i):
            if lows[j] < lows[i]:
                is_swing_low = False
                break
        if is_swing_low:
            for j in range(i + 1, i + right + 1):
                if lows[j] < lows[i]:
                    is_swing_low = False
                    break
        if is_swing_low:
            swing_lows.append((i, float(lows[i])))

    return swing_highs, swing_lows


# ---------------------------------------------------------------------------
# 5. Volume SMAs
# ---------------------------------------------------------------------------


def compute_volume_sma(df: pd.DataFrame, period: int) -> pd.Series:
    """Simple moving average of volume."""
    return df["volume"].rolling(window=period, min_periods=period).mean()


# ---------------------------------------------------------------------------
# 6. Derived Field Computations (spec v2 §6)
# ---------------------------------------------------------------------------


def classify_cloud_position(
    close: float, cloud_top: float, cloud_bottom: float
) -> CloudPosition:
    """Spec v2 §6: above/in/below cloud."""
    if close > cloud_top:
        return CloudPosition.ABOVE
    if close < cloud_bottom:
        return CloudPosition.BELOW
    return CloudPosition.IN


def classify_tk_state(tenkan: float, kijun: float) -> TkState:
    """Spec v2 §6: bullish if tenkan >= kijun, bearish otherwise."""
    if tenkan >= kijun:
        return TkState.BULLISH
    return TkState.BEARISH


def classify_profile_bias(
    close: float, vah: float, val: float
) -> ProfileBias:
    """Spec v2 §6: above_va/inside_va/below_va."""
    if close > vah:
        return ProfileBias.ABOVE_VA
    if close < val:
        return ProfileBias.BELOW_VA
    return ProfileBias.INSIDE_VA


# ---------------------------------------------------------------------------
# 7. Quantitative Helpers (spec v2 §7)
# ---------------------------------------------------------------------------


def compute_zone_width(
    current_price: float,
    atr_15m: float,
    width_pct: float = 0.0015,
    atr_factor: float = 0.25,
) -> float:
    """Spec v2 §7.1: zone_width = max(current_price * width_pct, atr_15m * atr_factor)"""
    return max(current_price * width_pct, atr_15m * atr_factor)


def make_zone(
    zone_id: str,
    level: float,
    zone_width: float,
    timeframe: Timeframe,
    source: str,
) -> Zone:
    """Create a Zone with [level - width, level, level + width]."""
    return Zone(
        id=zone_id,
        level=level,
        low=level - zone_width,
        mid=level,
        high=level + zone_width,
        timeframe=timeframe,
        source=source,
    )


def merge_overlapping_zones(zones: list[Zone]) -> list[Zone]:
    """Spec v2 §7.1: merge adjacent zones that overlap into composite zones.

    Two zones overlap if zone_a.high >= zone_b.low and zone_a.low <= zone_b.high.
    Merged zone: low = min(lows), high = max(highs), mid = (low+high)/2,
    level = mid, id = joined ids, source = joined sources.
    Uses the first zone's timeframe for the merged zone.
    """
    if len(zones) <= 1:
        return list(zones)

    sorted_zones = sorted(zones, key=lambda z: z.low)
    merged: list[Zone] = []
    current = sorted_zones[0]

    for next_zone in sorted_zones[1:]:
        if current.high >= next_zone.low:
            # Overlap — merge
            new_low = min(current.low, next_zone.low)
            new_high = max(current.high, next_zone.high)
            new_mid = (new_low + new_high) / 2
            current = Zone(
                id=f"{current.id}+{next_zone.id}",
                level=new_mid,
                low=new_low,
                mid=new_mid,
                high=new_high,
                timeframe=current.timeframe,
                source=f"{current.source}+{next_zone.source}",
            )
        else:
            merged.append(current)
            current = next_zone

    merged.append(current)
    return merged


def check_upper_rejection(
    high: float,
    close: float,
    open_price: float,
    zone_high: float,
    zone_mid: float,
) -> bool:
    """Spec v2 §7.2: upper_rejection.

    - high >= zone.high
    - close < zone.mid
    - upper_wick >= body
    """
    if high < zone_high:
        return False
    if close >= zone_mid:
        return False
    body = abs(close - open_price)
    upper_wick = high - max(close, open_price)
    return upper_wick >= body


def check_support_hold(
    low: float,
    close: float,
    open_price: float,
    zone_low: float,
    zone_mid: float,
) -> bool:
    """Spec v2 §7.3: support_hold.

    - low < zone.low  (note: spec says "저가가 zone.low 아래")
    - close > zone.mid
    - lower_wick >= body
    """
    if low >= zone_low:
        return False
    if close <= zone_mid:
        return False
    body = abs(close - open_price)
    lower_wick = min(close, open_price) - low
    return lower_wick >= body


def check_maintain_above(closes: list[float], level: float) -> bool:
    """Spec v2 §7.4: last 2 consecutive closes above level."""
    if len(closes) < 2:
        return False
    return closes[-1] > level and closes[-2] > level


def check_maintain_below(closes: list[float], level: float) -> bool:
    """Spec v2 §7.4: last 2 consecutive closes below level."""
    if len(closes) < 2:
        return False
    return closes[-1] < level and closes[-2] < level


def check_box_center(
    highs_48: list[float],
    lows_48: list[float],
    current_close: float,
    atr_30m: float,
    zones: list[Zone],
    range_low_pct: float = 0.40,
    range_high_pct: float = 0.60,
    min_distance_factor: float = 0.5,
) -> bool:
    """Spec v2 §7.5: box_center_30m check.

    Uses highest high and lowest low of last 48 30m bars (not just closes).

    1. Range = highest high - lowest low of last 48 30m bars.
    2. Current close is within 40%-60% of that range.
    3. Distance to nearest active zone >= 0.5 * ATR_30m.
    """
    if len(highs_48) < 48 or len(lows_48) < 48:
        return False

    range_high = max(highs_48[-48:])
    range_low = min(lows_48[-48:])
    range_size = range_high - range_low
    if range_size <= 0:
        return False

    position = (current_close - range_low) / range_size
    if not (range_low_pct <= position <= range_high_pct):
        return False

    min_dist = min_distance_factor * atr_30m
    for zone in zones:
        if abs(current_close - zone.mid) < min_dist:
            return False

    return True


def compute_retracement(
    swing_high: float, swing_low: float, current_close: float
) -> float:
    """Spec v2 §7.6: retracement_pct = (current_close - swing_low) / (swing_high - swing_low)"""
    drop = swing_high - swing_low
    if drop == 0:
        return 0.0
    return (current_close - swing_low) / drop


def check_abnormal_volatility(
    range_15m: float,
    atr_15m: float,
    range_30m: float,
    atr_30m: float,
    m15_factor: float = 2.5,
    m30_factor: float = 2.0,
) -> bool:
    """Spec v2 §7.7: abnormal_volatility check.

    True if either:
    - 15m bar range > 2.5 * ATR_15m
    - 30m bar range > 2.0 * ATR_30m
    """
    if range_15m > m15_factor * atr_15m:
        return True
    if range_30m > m30_factor * atr_30m:
        return True
    return False


def check_hammer(
    open_price: float,
    high: float,
    low: float,
    close: float,
    body_max_pct: float = 0.35,
    wick_min_ratio: float = 2.0,
) -> bool:
    """Spec v2 §11.2: hammer candle for PULLBACK_LONG trigger.

    Conditions:
    - Body <= 35% of total candle length
    - Lower wick >= 2x body
    - close >= open (bullish close)
    """
    candle_length = high - low
    if candle_length == 0:
        return False

    body = abs(close - open_price)
    if body / candle_length > body_max_pct:
        return False

    lower_wick = min(close, open_price) - low
    if body == 0:
        # Zero body — any lower wick qualifies
        return lower_wick > 0 and close >= open_price
    if lower_wick < wick_min_ratio * body:
        return False

    return close >= open_price


# ---------------------------------------------------------------------------
# 8. TimeframeSnapshot Builder
# ---------------------------------------------------------------------------


def build_timeframe_snapshot(
    df: pd.DataFrame,
    timeframe: Timeframe,
    ichimoku_params: dict | None = None,
    atr_period: int = 14,
    profile_window: int | None = None,
) -> TimeframeSnapshot:
    """Build a complete TimeframeSnapshot from an OHLCV DataFrame.

    This is the main entry point. It computes all indicators and derived fields,
    then returns a TimeframeSnapshot for the most recent completed bar.

    Args:
        df: OHLCV DataFrame with columns: timestamp, open, high, low, close, volume.
        timeframe: The timeframe enum value.
        ichimoku_params: Override dict with keys tenkan/kijun/senkou_b. Defaults to 9/26/52.
        atr_period: ATR period (default 14).
        profile_window: If None, skip volume profile (for 15m, 5m which don't use profiles per spec).

    Returns:
        TimeframeSnapshot for the most recent completed bar.
    """
    if ichimoku_params is None:
        ichimoku_params = {}

    # --- Ichimoku ---
    ichi_df = compute_ichimoku(
        df,
        tenkan=ichimoku_params.get("tenkan", 9),
        kijun=ichimoku_params.get("kijun", 26),
        senkou_b=ichimoku_params.get("senkou_b", 52),
    )

    # --- ATR ---
    atr_series = compute_atr(df, period=atr_period)

    # --- Volume SMAs ---
    vol_sma_5 = compute_volume_sma(df, period=5)
    vol_sma_20 = compute_volume_sma(df, period=20)

    # --- Volume Profile ---
    if profile_window is not None and len(df) >= profile_window:
        poc, vah, val = compute_volume_profile(df, window=profile_window)
    else:
        # No profile for this timeframe or insufficient data — use NaN
        poc, vah, val = np.nan, np.nan, np.nan

    # --- Extract latest bar values ---
    last_idx = ichi_df.index[-1]
    last_row = ichi_df.loc[last_idx]

    close = float(last_row["close"])
    tenkan_val = float(last_row["tenkan"])
    kijun_val = float(last_row["kijun"])
    cloud_top_val = float(last_row["cloud_top"])
    cloud_bottom_val = float(last_row["cloud_bottom"])
    volume_val = float(last_row["volume"])
    atr_val = float(atr_series.iloc[-1])
    vol_sma_5_val = float(vol_sma_5.iloc[-1]) if not pd.isna(vol_sma_5.iloc[-1]) else 0.0
    vol_sma_20_val = float(vol_sma_20.iloc[-1]) if not pd.isna(vol_sma_20.iloc[-1]) else 0.0

    # --- Derived classifications ---
    cloud_position = classify_cloud_position(close, cloud_top_val, cloud_bottom_val)
    tk_state = classify_tk_state(tenkan_val, kijun_val)
    profile_bias = classify_profile_bias(close, vah, val) if not np.isnan(vah) else ProfileBias.INSIDE_VA

    # --- Timestamp ---
    ts = last_row.get("timestamp", None)
    if ts is None or (isinstance(ts, float) and np.isnan(ts)):
        ts = datetime.now(tz=timezone.utc)
    elif not isinstance(ts, datetime):
        ts = pd.Timestamp(ts).to_pydatetime()

    return TimeframeSnapshot(
        timeframe=timeframe,
        timestamp=ts,
        close=close,
        tenkan=tenkan_val,
        kijun=kijun_val,
        cloud_top=cloud_top_val,
        cloud_bottom=cloud_bottom_val,
        cloud_position=cloud_position,
        tk_state=tk_state,
        poc=poc if not np.isnan(poc) else 0.0,
        vah=vah if not np.isnan(vah) else 0.0,
        val=val if not np.isnan(val) else 0.0,
        profile_bias=profile_bias,
        volume=volume_val,
        volume_sma_5=vol_sma_5_val,
        volume_sma_20=vol_sma_20_val,
        atr=atr_val,
    )


def build_all_snapshots(
    df: pd.DataFrame,
    timeframe: Timeframe,
    ichimoku_params: dict | None = None,
    atr_period: int = 14,
    profile_window: int | None = None,
    min_bars: int = 60,
) -> dict:
    """Batch-compute TimeframeSnapshots for every bar in the DataFrame.

    Computes ichimoku, ATR, volume SMAs ONCE for the entire DataFrame,
    then extracts per-bar snapshots in a single pass. Returns
    {timestamp: TimeframeSnapshot} dict.

    This is O(N) total instead of O(N²) when calling build_timeframe_snapshot
    for each bar individually.
    """
    if ichimoku_params is None:
        ichimoku_params = {}

    # Compute indicators once on full DataFrame
    ichi_df = compute_ichimoku(
        df,
        tenkan=ichimoku_params.get("tenkan", 9),
        kijun=ichimoku_params.get("kijun", 26),
        senkou_b=ichimoku_params.get("senkou_b", 52),
    )
    atr_series = compute_atr(df, period=atr_period)
    vol_sma_5 = compute_volume_sma(df, period=5)
    vol_sma_20 = compute_volume_sma(df, period=20)

    # Volume profile: pre-compute at regular intervals (every profile_window bars)
    # to avoid O(N²) cost while keeping values current.
    vp_cache: dict[int, tuple[float, float, float]] = {}  # {bar_index: (poc, vah, val)}
    if profile_window is not None and len(df) >= profile_window:
        # Compute VP every profile_window//4 bars (sliding update)
        step = max(profile_window // 4, 1)
        for vp_i in range(profile_window, len(df), step):
            window_df = df.iloc[vp_i - profile_window:vp_i]
            try:
                p, vh, vl = compute_volume_profile(window_df, window=profile_window)
                vp_cache[vp_i] = (p, vh, vl)
            except (ValueError, IndexError):
                continue

    # Extract timestamp column
    if "timestamp" in df.columns:
        timestamps = df["timestamp"]
    elif "timestamp" in ichi_df.columns:
        timestamps = ichi_df["timestamp"]
    else:
        timestamps = ichi_df.index

    result: dict = {}
    n = len(ichi_df)
    current_poc, current_vah, current_val = 0.0, 0.0, 0.0

    for i in range(min_bars, n):
        # Update VP from cache if a new computation is available
        if i in vp_cache:
            current_poc, current_vah, current_val = vp_cache[i]
        elif not vp_cache and profile_window is not None and i >= profile_window:
            # Fallback: compute once at first eligible bar
            try:
                current_poc, current_vah, current_val = compute_volume_profile(
                    df.iloc[i - profile_window:i], window=profile_window
                )
            except (ValueError, IndexError):
                pass
        row = ichi_df.iloc[i]
        close = float(row["close"])
        tenkan_v = float(row["tenkan"])
        kijun_v = float(row["kijun"])
        ct = float(row["cloud_top"])
        cb = float(row["cloud_bottom"])
        vol = float(row["volume"])
        atr_v = float(atr_series.iloc[i]) if not pd.isna(atr_series.iloc[i]) else 0.0
        vs5 = float(vol_sma_5.iloc[i]) if not pd.isna(vol_sma_5.iloc[i]) else 0.0
        vs20 = float(vol_sma_20.iloc[i]) if not pd.isna(vol_sma_20.iloc[i]) else 0.0

        cp = classify_cloud_position(close, ct, cb)
        tk = classify_tk_state(tenkan_v, kijun_v)
        pb = classify_profile_bias(close, current_vah, current_val) if current_vah != 0.0 else ProfileBias.INSIDE_VA

        ts = timestamps.iloc[i] if hasattr(timestamps, "iloc") else timestamps[i]
        if not isinstance(ts, datetime):
            ts = pd.Timestamp(ts).to_pydatetime()

        result[ts] = TimeframeSnapshot(
            timeframe=timeframe,
            timestamp=ts,
            close=close,
            tenkan=tenkan_v,
            kijun=kijun_v,
            cloud_top=ct,
            cloud_bottom=cb,
            cloud_position=cp,
            tk_state=tk,
            poc=current_poc,
            vah=current_vah,
            val=current_val,
            profile_bias=pb,
            volume=vol,
            volume_sma_5=vs5,
            volume_sma_20=vs20,
            atr=atr_v,
        )

    return result


# ---------------------------------------------------------------------------
# 9. Fibonacci Extensions (spec v2)
# ---------------------------------------------------------------------------


def compute_fib_extensions(
    swing_low: float,
    swing_high: float,
    ratios: list[float] | None = None,
) -> list[float]:
    """Compute Fibonacci extension levels from a swing range.

    Default ratios: [1.618, 2.0, 2.618]
    Extension = swing_low + (swing_high - swing_low) * ratio
    """
    if ratios is None:
        ratios = [1.618, 2.0, 2.618]
    swing_range = swing_high - swing_low
    if swing_range <= 0:
        return []
    return [swing_low + swing_range * r for r in ratios]
