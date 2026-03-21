"""Tests for trading_value.core.regime — spec v2 §8 regime classification.

Tests all conditions from the spec, including operator boundaries.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from trading_value.core.models import (
    CloudPosition,
    ProfileBias,
    RegimeState,
    Timeframe,
    TimeframeSnapshot,
    TkState,
)
from trading_value.core.regime import (
    H1Bias,
    M30Bias,
    RegimeSnapshot,
    classify_h1_bias,
    classify_htf_regime,
    classify_m30_bias,
    classify_regime,
)

NOW = datetime(2026, 3, 20, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def make_snapshot(
    timeframe: Timeframe,
    close: float,
    cloud_top: float,
    cloud_bottom: float,
    tenkan: float,
    kijun: float,
    profile_bias: ProfileBias = ProfileBias.INSIDE_VA,
    **kwargs,
) -> TimeframeSnapshot:
    """Create a TimeframeSnapshot with controllable regime-relevant values."""
    return TimeframeSnapshot(
        timeframe=timeframe,
        timestamp=NOW,
        close=close,
        tenkan=tenkan,
        kijun=kijun,
        cloud_top=cloud_top,
        cloud_bottom=cloud_bottom,
        cloud_position=CloudPosition.ABOVE if close > cloud_top else (
            CloudPosition.BELOW if close < cloud_bottom else CloudPosition.IN
        ),
        tk_state=TkState.BULLISH if tenkan >= kijun else TkState.BEARISH,
        poc=kwargs.get("poc", 0.0),
        vah=kwargs.get("vah", 0.0),
        val=kwargs.get("val", 0.0),
        profile_bias=profile_bias,
        volume=kwargs.get("volume", 1000.0),
        volume_sma_5=kwargs.get("volume_sma_5", 1000.0),
        volume_sma_20=kwargs.get("volume_sma_20", 1000.0),
        atr=kwargs.get("atr", 10.0),
    )


# ---------------------------------------------------------------------------
# 1. HTF regime classification (spec v2 §8.1)
# ---------------------------------------------------------------------------

class TestHTFRegime:

    def test_htf_bullish_all_conditions_met(self):
        """close > cloud_top AND tenkan > kijun AND profile_bias != BELOW_VA → BULLISH."""
        snap = make_snapshot(
            Timeframe.H4,
            close=110.0, cloud_top=100.0, cloud_bottom=90.0,
            tenkan=105.0, kijun=100.0,
            profile_bias=ProfileBias.ABOVE_VA,
        )
        assert classify_htf_regime(snap) == RegimeState.HTF_BULLISH

    def test_htf_bullish_with_inside_va_bias(self):
        """profile_bias=INSIDE_VA is not BELOW_VA → still BULLISH."""
        snap = make_snapshot(
            Timeframe.H4,
            close=110.0, cloud_top=100.0, cloud_bottom=90.0,
            tenkan=105.0, kijun=100.0,
            profile_bias=ProfileBias.INSIDE_VA,
        )
        assert classify_htf_regime(snap) == RegimeState.HTF_BULLISH

    def test_htf_bearish_all_conditions_met(self):
        """close < cloud_bottom AND tenkan < kijun AND profile_bias == BELOW_VA → BEARISH."""
        snap = make_snapshot(
            Timeframe.H4,
            close=80.0, cloud_top=100.0, cloud_bottom=90.0,
            tenkan=85.0, kijun=95.0,
            profile_bias=ProfileBias.BELOW_VA,
        )
        assert classify_htf_regime(snap) == RegimeState.HTF_BEARISH

    def test_htf_neutral_mixed_bullish_bias_but_below_cloud(self):
        """Below cloud but tenkan > kijun and inside_va → NEUTRAL."""
        snap = make_snapshot(
            Timeframe.H4,
            close=80.0, cloud_top=100.0, cloud_bottom=90.0,
            tenkan=95.0, kijun=90.0,
            profile_bias=ProfileBias.INSIDE_VA,
        )
        assert classify_htf_regime(snap) == RegimeState.HTF_NEUTRAL

    def test_htf_neutral_above_cloud_but_tk_bearish(self):
        """Above cloud but tenkan < kijun → NEUTRAL."""
        snap = make_snapshot(
            Timeframe.H4,
            close=110.0, cloud_top=100.0, cloud_bottom=90.0,
            tenkan=95.0, kijun=100.0,
            profile_bias=ProfileBias.ABOVE_VA,
        )
        assert classify_htf_regime(snap) == RegimeState.HTF_NEUTRAL

    def test_htf_neutral_all_bearish_except_bias_is_above(self):
        """All bearish conditions except profile_bias is ABOVE_VA → NEUTRAL (not BEARISH)."""
        snap = make_snapshot(
            Timeframe.H4,
            close=80.0, cloud_top=100.0, cloud_bottom=90.0,
            tenkan=85.0, kijun=95.0,
            profile_bias=ProfileBias.ABOVE_VA,
        )
        assert classify_htf_regime(snap) == RegimeState.HTF_NEUTRAL

    def test_htf_operator_boundary_close_eq_cloud_top_not_bullish(self):
        """Spec: close > cloud_top (strictly). close == cloud_top → NOT BULLISH."""
        snap = make_snapshot(
            Timeframe.H4,
            close=100.0, cloud_top=100.0, cloud_bottom=90.0,
            tenkan=105.0, kijun=100.0,
            profile_bias=ProfileBias.ABOVE_VA,
        )
        assert classify_htf_regime(snap) != RegimeState.HTF_BULLISH

    def test_htf_operator_boundary_close_eq_cloud_bottom_not_bearish(self):
        """Spec: close < cloud_bottom (strictly). close == cloud_bottom → NOT BEARISH."""
        snap = make_snapshot(
            Timeframe.H4,
            close=90.0, cloud_top=100.0, cloud_bottom=90.0,
            tenkan=85.0, kijun=95.0,
            profile_bias=ProfileBias.BELOW_VA,
        )
        assert classify_htf_regime(snap) != RegimeState.HTF_BEARISH


# ---------------------------------------------------------------------------
# 2. H1 bias classification (spec v2 §8.2)
# ---------------------------------------------------------------------------

class TestH1Bias:

    def test_h1_bullish_all_conditions_met(self):
        """close > cloud_top AND tenkan >= kijun AND close >= kijun AND bias != BELOW_VA."""
        snap = make_snapshot(
            Timeframe.H1,
            close=110.0, cloud_top=100.0, cloud_bottom=90.0,
            tenkan=105.0, kijun=104.0,
            profile_bias=ProfileBias.ABOVE_VA,
        )
        assert classify_h1_bias(snap) == H1Bias.H1_BULLISH

    def test_h1_bullish_tenkan_equals_kijun(self):
        """tenkan >= kijun includes equality → BULLISH when other conditions met."""
        snap = make_snapshot(
            Timeframe.H1,
            close=110.0, cloud_top=100.0, cloud_bottom=90.0,
            tenkan=104.0, kijun=104.0,
            profile_bias=ProfileBias.INSIDE_VA,
        )
        assert classify_h1_bias(snap) == H1Bias.H1_BULLISH

    def test_h1_bearish_all_conditions_met(self):
        """close < cloud_bottom AND tenkan <= kijun AND close <= kijun AND bias == BELOW_VA."""
        snap = make_snapshot(
            Timeframe.H1,
            close=80.0, cloud_top=100.0, cloud_bottom=90.0,
            tenkan=85.0, kijun=86.0,
            profile_bias=ProfileBias.BELOW_VA,
        )
        assert classify_h1_bias(snap) == H1Bias.H1_BEARISH

    def test_h1_bearish_tenkan_equals_kijun(self):
        """tenkan <= kijun includes equality in bearish path."""
        snap = make_snapshot(
            Timeframe.H1,
            close=80.0, cloud_top=100.0, cloud_bottom=90.0,
            tenkan=86.0, kijun=86.0,
            profile_bias=ProfileBias.BELOW_VA,
        )
        assert classify_h1_bias(snap) == H1Bias.H1_BEARISH

    def test_h1_neutral_in_cloud(self):
        """Price inside cloud → NEUTRAL."""
        snap = make_snapshot(
            Timeframe.H1,
            close=95.0, cloud_top=100.0, cloud_bottom=90.0,
            tenkan=95.0, kijun=94.0,
            profile_bias=ProfileBias.INSIDE_VA,
        )
        assert classify_h1_bias(snap) == H1Bias.H1_NEUTRAL

    def test_h1_neutral_above_cloud_but_below_va(self):
        """profile_bias=BELOW_VA blocks BULLISH → NEUTRAL."""
        snap = make_snapshot(
            Timeframe.H1,
            close=110.0, cloud_top=100.0, cloud_bottom=90.0,
            tenkan=105.0, kijun=104.0,
            profile_bias=ProfileBias.BELOW_VA,
        )
        assert classify_h1_bias(snap) == H1Bias.H1_NEUTRAL


# ---------------------------------------------------------------------------
# 3. M30 bias classification (spec v2 §8.3)
# ---------------------------------------------------------------------------

class TestM30Bias:

    def test_m30_bullish_all_conditions_met(self):
        """close > cloud_top AND tenkan > kijun AND close >= kijun."""
        snap = make_snapshot(
            Timeframe.M30,
            close=110.0, cloud_top=100.0, cloud_bottom=90.0,
            tenkan=105.0, kijun=103.0,
        )
        assert classify_m30_bias(snap) == M30Bias.M30_BULLISH

    def test_m30_bearish_all_conditions_met(self):
        """close < cloud_bottom AND tenkan < kijun AND close <= kijun."""
        snap = make_snapshot(
            Timeframe.M30,
            close=80.0, cloud_top=100.0, cloud_bottom=90.0,
            tenkan=85.0, kijun=87.0,
        )
        assert classify_m30_bias(snap) == M30Bias.M30_BEARISH

    def test_m30_neutral_fallback(self):
        """Mixed conditions → NEUTRAL."""
        snap = make_snapshot(
            Timeframe.M30,
            close=95.0, cloud_top=100.0, cloud_bottom=90.0,
            tenkan=95.0, kijun=94.0,
        )
        assert classify_m30_bias(snap) == M30Bias.M30_NEUTRAL

    def test_m30_not_bullish_when_tenkan_equals_kijun(self):
        """M30_BULLISH requires tenkan > kijun (strictly). Equal → not bullish."""
        snap = make_snapshot(
            Timeframe.M30,
            close=110.0, cloud_top=100.0, cloud_bottom=90.0,
            tenkan=104.0, kijun=104.0,
        )
        assert classify_m30_bias(snap) != M30Bias.M30_BULLISH

    def test_m30_bearish_close_equals_kijun_boundary(self):
        """close <= kijun includes equality → can be BEARISH when other conditions met."""
        snap = make_snapshot(
            Timeframe.M30,
            close=80.0, cloud_top=100.0, cloud_bottom=90.0,
            tenkan=79.0, kijun=80.0,  # close == kijun
        )
        assert classify_m30_bias(snap) == M30Bias.M30_BEARISH


# ---------------------------------------------------------------------------
# 4. classify_regime (combined)
# ---------------------------------------------------------------------------

class TestClassifyRegime:

    def test_classify_regime_returns_regime_snapshot(self):
        snaps = {
            Timeframe.H4: make_snapshot(
                Timeframe.H4, close=110.0, cloud_top=100.0, cloud_bottom=90.0,
                tenkan=105.0, kijun=100.0, profile_bias=ProfileBias.ABOVE_VA,
            ),
            Timeframe.H1: make_snapshot(
                Timeframe.H1, close=108.0, cloud_top=100.0, cloud_bottom=90.0,
                tenkan=104.0, kijun=103.0, profile_bias=ProfileBias.ABOVE_VA,
            ),
            Timeframe.M30: make_snapshot(
                Timeframe.M30, close=107.0, cloud_top=100.0, cloud_bottom=90.0,
                tenkan=103.0, kijun=102.0, profile_bias=ProfileBias.ABOVE_VA,
            ),
        }
        result = classify_regime(snaps)
        assert isinstance(result, RegimeSnapshot)

    def test_classify_regime_fully_bullish(self):
        snaps = {
            Timeframe.H4: make_snapshot(
                Timeframe.H4, close=110.0, cloud_top=100.0, cloud_bottom=90.0,
                tenkan=105.0, kijun=100.0, profile_bias=ProfileBias.ABOVE_VA,
            ),
            Timeframe.H1: make_snapshot(
                Timeframe.H1, close=108.0, cloud_top=100.0, cloud_bottom=90.0,
                tenkan=104.0, kijun=103.0, profile_bias=ProfileBias.ABOVE_VA,
            ),
            Timeframe.M30: make_snapshot(
                Timeframe.M30, close=107.0, cloud_top=100.0, cloud_bottom=90.0,
                tenkan=103.0, kijun=102.0, profile_bias=ProfileBias.ABOVE_VA,
            ),
        }
        result = classify_regime(snaps)
        assert result.htf == RegimeState.HTF_BULLISH
        assert result.h1 == H1Bias.H1_BULLISH
        assert result.m30 == M30Bias.M30_BULLISH

    def test_classify_regime_fully_bearish(self):
        snaps = {
            Timeframe.H4: make_snapshot(
                Timeframe.H4, close=80.0, cloud_top=100.0, cloud_bottom=90.0,
                tenkan=85.0, kijun=88.0, profile_bias=ProfileBias.BELOW_VA,
            ),
            Timeframe.H1: make_snapshot(
                Timeframe.H1, close=82.0, cloud_top=100.0, cloud_bottom=90.0,
                tenkan=83.0, kijun=85.0, profile_bias=ProfileBias.BELOW_VA,
            ),
            Timeframe.M30: make_snapshot(
                Timeframe.M30, close=81.0, cloud_top=100.0, cloud_bottom=90.0,
                tenkan=82.0, kijun=84.0, profile_bias=ProfileBias.BELOW_VA,
            ),
        }
        result = classify_regime(snaps)
        assert result.htf == RegimeState.HTF_BEARISH
        assert result.h1 == H1Bias.H1_BEARISH
        assert result.m30 == M30Bias.M30_BEARISH

    def test_classify_regime_missing_timeframe_raises(self):
        """Missing required timeframe → KeyError."""
        snaps = {
            Timeframe.H4: make_snapshot(
                Timeframe.H4, close=110.0, cloud_top=100.0, cloud_bottom=90.0,
                tenkan=105.0, kijun=100.0,
            ),
        }
        with pytest.raises(KeyError):
            classify_regime(snaps)

    def test_classify_regime_mixed_neutral(self):
        """HTF NEUTRAL, H1 NEUTRAL, M30 NEUTRAL."""
        snaps = {
            Timeframe.H4: make_snapshot(
                Timeframe.H4, close=95.0, cloud_top=100.0, cloud_bottom=90.0,
                tenkan=95.0, kijun=94.0, profile_bias=ProfileBias.INSIDE_VA,
            ),
            Timeframe.H1: make_snapshot(
                Timeframe.H1, close=94.0, cloud_top=100.0, cloud_bottom=90.0,
                tenkan=93.0, kijun=94.0, profile_bias=ProfileBias.INSIDE_VA,
            ),
            Timeframe.M30: make_snapshot(
                Timeframe.M30, close=93.0, cloud_top=100.0, cloud_bottom=90.0,
                tenkan=92.0, kijun=93.0, profile_bias=ProfileBias.INSIDE_VA,
            ),
        }
        result = classify_regime(snaps)
        assert result.htf == RegimeState.HTF_NEUTRAL
        assert result.h1 == H1Bias.H1_NEUTRAL
        assert result.m30 == M30Bias.M30_NEUTRAL


# ---------------------------------------------------------------------------
# 5. Operator boundary tests (watchdog findings)
# ---------------------------------------------------------------------------


class TestHTFBoundaryOperators:

    def test_htf_tenkan_eq_kijun_not_bullish(self):
        """Finding 1: HTF_BULLISH requires tenkan > kijun (strict). tenkan == kijun → NOT HTF_BULLISH."""
        snap = make_snapshot(
            Timeframe.H4,
            close=110.0, cloud_top=100.0, cloud_bottom=90.0,
            tenkan=105.0, kijun=105.0,  # tenkan == kijun
            profile_bias=ProfileBias.ABOVE_VA,
        )
        assert classify_htf_regime(snap) != RegimeState.HTF_BULLISH

    def test_htf_tenkan_eq_kijun_not_bearish(self):
        """Finding 2: HTF_BEARISH requires tenkan < kijun (strict). tenkan == kijun → NOT HTF_BEARISH."""
        snap = make_snapshot(
            Timeframe.H4,
            close=80.0, cloud_top=100.0, cloud_bottom=90.0,
            tenkan=86.0, kijun=86.0,  # tenkan == kijun
            profile_bias=ProfileBias.BELOW_VA,
        )
        assert classify_htf_regime(snap) != RegimeState.HTF_BEARISH


class TestH1BoundaryOperators:

    def test_h1_close_eq_cloud_top_not_bullish(self):
        """Finding 3: H1_BULLISH requires close > cloud_top (strict). close == cloud_top → NOT H1_BULLISH."""
        snap = make_snapshot(
            Timeframe.H1,
            close=100.0, cloud_top=100.0, cloud_bottom=90.0,  # close == cloud_top
            tenkan=105.0, kijun=104.0,
            profile_bias=ProfileBias.ABOVE_VA,
        )
        assert classify_h1_bias(snap) != H1Bias.H1_BULLISH

    def test_h1_close_eq_cloud_bottom_not_bearish(self):
        """Finding 4: H1_BEARISH requires close < cloud_bottom (strict). close == cloud_bottom → NOT H1_BEARISH."""
        snap = make_snapshot(
            Timeframe.H1,
            close=90.0, cloud_top=100.0, cloud_bottom=90.0,  # close == cloud_bottom
            tenkan=85.0, kijun=86.0,
            profile_bias=ProfileBias.BELOW_VA,
        )
        assert classify_h1_bias(snap) != H1Bias.H1_BEARISH

    def test_h1_close_eq_kijun_bullish_boundary(self):
        """Finding 5: H1_BULLISH uses close >= kijun. close == kijun with all other bullish conditions → H1_BULLISH."""
        snap = make_snapshot(
            Timeframe.H1,
            close=110.0, cloud_top=100.0, cloud_bottom=90.0,
            tenkan=110.0, kijun=110.0,  # close == kijun, tenkan >= kijun satisfied
            profile_bias=ProfileBias.ABOVE_VA,
        )
        assert classify_h1_bias(snap) == H1Bias.H1_BULLISH

    def test_h1_close_eq_kijun_bearish_boundary(self):
        """Finding 6: H1_BEARISH uses close <= kijun. close == kijun with all other bearish conditions → H1_BEARISH."""
        snap = make_snapshot(
            Timeframe.H1,
            close=80.0, cloud_top=100.0, cloud_bottom=90.0,
            tenkan=80.0, kijun=80.0,  # close == kijun, tenkan <= kijun satisfied
            profile_bias=ProfileBias.BELOW_VA,
        )
        assert classify_h1_bias(snap) == H1Bias.H1_BEARISH


class TestM30BoundaryOperators:

    def test_m30_close_eq_cloud_top_not_bullish(self):
        """Finding 7: M30_BULLISH requires close > cloud_top (strict). close == cloud_top → NOT M30_BULLISH."""
        snap = make_snapshot(
            Timeframe.M30,
            close=100.0, cloud_top=100.0, cloud_bottom=90.0,  # close == cloud_top
            tenkan=105.0, kijun=103.0,
        )
        assert classify_m30_bias(snap) != M30Bias.M30_BULLISH

    def test_m30_close_eq_cloud_bottom_not_bearish(self):
        """Finding 8: M30_BEARISH requires close < cloud_bottom (strict). close == cloud_bottom → NOT M30_BEARISH."""
        snap = make_snapshot(
            Timeframe.M30,
            close=90.0, cloud_top=100.0, cloud_bottom=90.0,  # close == cloud_bottom
            tenkan=85.0, kijun=87.0,
        )
        assert classify_m30_bias(snap) != M30Bias.M30_BEARISH

    def test_m30_close_eq_kijun_bullish_boundary(self):
        """Finding 9: M30_BULLISH uses close >= kijun. close == kijun with all other bullish conditions → M30_BULLISH."""
        snap = make_snapshot(
            Timeframe.M30,
            close=110.0, cloud_top=100.0, cloud_bottom=90.0,
            tenkan=110.0, kijun=110.0,  # close == kijun, tenkan > kijun? No: tenkan==kijun fails strict >
        )
        # tenkan == kijun does NOT satisfy tenkan > kijun (strict), so result is M30_NEUTRAL not M30_BULLISH.
        # To test close==kijun boundary independently, use tenkan strictly > kijun and close==kijun.
        snap2 = make_snapshot(
            Timeframe.M30,
            close=110.0, cloud_top=100.0, cloud_bottom=90.0,
            tenkan=111.0, kijun=110.0,  # close == kijun (110), tenkan (111) > kijun (110) strict
        )
        assert classify_m30_bias(snap2) == M30Bias.M30_BULLISH

    def test_m30_tenkan_eq_kijun_neutral(self):
        """Finding 10: M30_BULLISH requires tenkan > kijun (strict). tenkan == kijun → NOT M30_BULLISH.
        Also NOT M30_BEARISH (close is above cloud). Result is M30_NEUTRAL."""
        snap = make_snapshot(
            Timeframe.M30,
            close=110.0, cloud_top=100.0, cloud_bottom=90.0,
            tenkan=104.0, kijun=104.0,  # tenkan == kijun
        )
        assert classify_m30_bias(snap) != M30Bias.M30_BULLISH
        assert classify_m30_bias(snap) == M30Bias.M30_NEUTRAL
