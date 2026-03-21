"""Regime classifier — determines HTF, H1, M30 market states.

Pure functions, no state, no side effects.
Implements spec v2 section 8 timeframe state classification.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .models import ProfileBias, RegimeState, Timeframe, TimeframeSnapshot


# ---------------------------------------------------------------------------
# H1 / M30 bias enums (not in models.py — HTF-only RegimeState lives there)
# ---------------------------------------------------------------------------


class H1Bias(StrEnum):
    H1_BULLISH = "H1_BULLISH"
    H1_NEUTRAL = "H1_NEUTRAL"
    H1_BEARISH = "H1_BEARISH"


class M30Bias(StrEnum):
    M30_BULLISH = "M30_BULLISH"
    M30_NEUTRAL = "M30_NEUTRAL"
    M30_BEARISH = "M30_BEARISH"


# ---------------------------------------------------------------------------
# HTF regime classification (spec v2 section 8.1)
# ---------------------------------------------------------------------------


def classify_htf_regime(snapshot_4h: TimeframeSnapshot) -> RegimeState:
    """Classify 4h higher timeframe regime per spec v2 section 8.1.

    HTF_BULLISH when ALL:
      1. 4h.close > 4h.cloud_top
      2. 4h.tenkan > 4h.kijun
      3. 4h.profile_bias != below_va

    HTF_BEARISH when ALL:
      1. 4h.close < 4h.cloud_bottom
      2. 4h.tenkan < 4h.kijun
      3. 4h.profile_bias == below_va

    Otherwise: HTF_NEUTRAL
    """
    if (
        snapshot_4h.close > snapshot_4h.cloud_top
        and snapshot_4h.tenkan > snapshot_4h.kijun
        and snapshot_4h.profile_bias != ProfileBias.BELOW_VA
    ):
        return RegimeState.HTF_BULLISH

    if (
        snapshot_4h.close < snapshot_4h.cloud_bottom
        and snapshot_4h.tenkan < snapshot_4h.kijun
        and snapshot_4h.profile_bias == ProfileBias.BELOW_VA
    ):
        return RegimeState.HTF_BEARISH

    return RegimeState.HTF_NEUTRAL


# ---------------------------------------------------------------------------
# H1 bias classification (spec v2 section 8.2)
# ---------------------------------------------------------------------------


def classify_h1_bias(snapshot_1h: TimeframeSnapshot) -> H1Bias:
    """Classify 1h directional bias per spec v2 section 8.2.

    H1_BULLISH when ALL:
      1. 1h.close > 1h.cloud_top
      2. 1h.tenkan >= 1h.kijun
      3. 1h.close >= 1h.kijun
      4. 1h.profile_bias != below_va

    H1_BEARISH when ALL:
      1. 1h.close < 1h.cloud_bottom
      2. 1h.tenkan <= 1h.kijun
      3. 1h.close <= 1h.kijun
      4. 1h.profile_bias == below_va

    Otherwise: H1_NEUTRAL
    """
    if (
        snapshot_1h.close > snapshot_1h.cloud_top
        and snapshot_1h.tenkan >= snapshot_1h.kijun
        and snapshot_1h.close >= snapshot_1h.kijun
        and snapshot_1h.profile_bias != ProfileBias.BELOW_VA
    ):
        return H1Bias.H1_BULLISH

    if (
        snapshot_1h.close < snapshot_1h.cloud_bottom
        and snapshot_1h.tenkan <= snapshot_1h.kijun
        and snapshot_1h.close <= snapshot_1h.kijun
        and snapshot_1h.profile_bias == ProfileBias.BELOW_VA
    ):
        return H1Bias.H1_BEARISH

    return H1Bias.H1_NEUTRAL


# ---------------------------------------------------------------------------
# M30 bias classification (spec v2 section 8.3)
# ---------------------------------------------------------------------------


def classify_m30_bias(snapshot_30m: TimeframeSnapshot) -> M30Bias:
    """Classify 30m execution regime per spec v2 section 8.3.

    M30_BULLISH when ALL:
      1. 30m.close > 30m.cloud_top
      2. 30m.tenkan > 30m.kijun
      3. 30m.close >= 30m.kijun

    M30_BEARISH when ALL:
      1. 30m.close < 30m.cloud_bottom
      2. 30m.tenkan < 30m.kijun
      3. 30m.close <= 30m.kijun

    Otherwise: M30_NEUTRAL
    """
    if (
        snapshot_30m.close > snapshot_30m.cloud_top
        and snapshot_30m.tenkan > snapshot_30m.kijun
        and snapshot_30m.close >= snapshot_30m.kijun
    ):
        return M30Bias.M30_BULLISH

    if (
        snapshot_30m.close < snapshot_30m.cloud_bottom
        and snapshot_30m.tenkan < snapshot_30m.kijun
        and snapshot_30m.close <= snapshot_30m.kijun
    ):
        return M30Bias.M30_BEARISH

    return M30Bias.M30_NEUTRAL


# ---------------------------------------------------------------------------
# Combined classifier
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RegimeSnapshot:
    """Complete regime classification at a point in time."""

    htf: RegimeState
    h1: H1Bias
    m30: M30Bias


def classify_regime(
    snapshots: dict[Timeframe, TimeframeSnapshot],
) -> RegimeSnapshot:
    """Classify all regime levels from timeframe snapshots.

    Requires at least Timeframe.H4, Timeframe.H1, Timeframe.M30 in snapshots.
    Raises KeyError if missing.
    """
    return RegimeSnapshot(
        htf=classify_htf_regime(snapshots[Timeframe.H4]),
        h1=classify_h1_bias(snapshots[Timeframe.H1]),
        m30=classify_m30_bias(snapshots[Timeframe.M30]),
    )
