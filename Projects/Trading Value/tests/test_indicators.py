"""Tests for trading_value.core.indicators — spec v2 §5, §6, §7, §8, §11."""
from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from trading_value.core.indicators import (
    build_timeframe_snapshot,
    check_abnormal_volatility,
    check_box_center,
    check_hammer,
    check_maintain_above,
    check_maintain_below,
    check_support_hold,
    check_upper_rejection,
    classify_cloud_position,
    classify_profile_bias,
    classify_tk_state,
    compute_atr,
    compute_ichimoku,
    compute_retracement,
    compute_volume_profile,
    compute_volume_sma,
    detect_swings,
    make_zone,
    merge_overlapping_zones,
    compute_zone_width,
)
from trading_value.core.models import (
    CloudPosition,
    ProfileBias,
    Timeframe,
    TimeframeSnapshot,
    TkState,
    Zone,
)

NOW = datetime(2026, 3, 20, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_flat_ohlcv(n: int, price: float = 100.0, volume: float = 1000.0) -> pd.DataFrame:
    """Create a DataFrame with n identical OHLCV bars at ``price``."""
    timestamps = pd.date_range("2026-01-01", periods=n, freq="1h")
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": price,
            "high": price + 1.0,
            "low": price - 1.0,
            "close": price,
            "volume": volume,
        }
    )


def make_ohlcv(n: int, highs, lows, closes=None, opens=None, volume: float = 1000.0) -> pd.DataFrame:
    """Create a DataFrame from explicit arrays."""
    highs = list(highs)
    lows = list(lows)
    if closes is None:
        closes = [(h + l) / 2 for h, l in zip(highs, lows)]
    if opens is None:
        opens = closes
    timestamps = pd.date_range("2026-01-01", periods=n, freq="1h")
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": opens[:n],
            "high": highs[:n],
            "low": lows[:n],
            "close": closes[:n],
            "volume": volume,
        }
    )


def make_zone_obj(
    low: float,
    high: float,
    zone_id: str = "z1",
    timeframe: Timeframe = Timeframe.M30,
    source: str = "test",
) -> Zone:
    mid = (low + high) / 2
    return Zone(id=zone_id, level=mid, low=low, mid=mid, high=high, timeframe=timeframe, source=source)


# ---------------------------------------------------------------------------
# 1. Ichimoku
# ---------------------------------------------------------------------------

class TestIchimoku:

    def test_ichimoku_raises_if_too_few_rows(self):
        df = make_flat_ohlcv(51)
        with pytest.raises(ValueError, match="52"):
            compute_ichimoku(df)

    def test_ichimoku_columns_present(self):
        df = make_flat_ohlcv(60)
        result = compute_ichimoku(df)
        for col in ("tenkan", "kijun", "senkou_a", "senkou_b", "cloud_top", "cloud_bottom"):
            assert col in result.columns

    def test_ichimoku_flat_data_tenkan_kijun_equal(self):
        """Flat price => tenkan == kijun == price (midpoint of flat H/L)."""
        df = make_flat_ohlcv(60, price=100.0)
        result = compute_ichimoku(df)
        last = result.iloc[-1]
        # high=101, low=99 -> midpoint=100
        assert last["tenkan"] == pytest.approx(100.0)
        assert last["kijun"] == pytest.approx(100.0)

    def test_ichimoku_cloud_top_is_max_senkou(self):
        df = make_flat_ohlcv(60)
        result = compute_ichimoku(df)
        valid = result.dropna(subset=["senkou_a", "senkou_b"])
        for _, row in valid.iterrows():
            assert row["cloud_top"] == pytest.approx(max(row["senkou_a"], row["senkou_b"]))
            assert row["cloud_bottom"] == pytest.approx(min(row["senkou_a"], row["senkou_b"]))

    def test_ichimoku_custom_periods(self):
        """Shorter periods should produce valid output with fewer NaN rows."""
        df = make_flat_ohlcv(60)
        result = compute_ichimoku(df, tenkan=5, kijun=13, senkou_b=26)
        # With period=26, all rows from index 25 onward should have senkou_b
        assert result["senkou_b"].iloc[25:].notna().all()


# ---------------------------------------------------------------------------
# 2. ATR
# ---------------------------------------------------------------------------

class TestATR:

    def test_atr_raises_if_too_few_rows(self):
        df = make_flat_ohlcv(14)
        with pytest.raises(ValueError):
            compute_atr(df, period=14)

    def test_atr_wilder_smoothing_manual(self):
        """Manually verify Wilder's ATR for simple known TR sequence.

        Implementation: tr[0] = high[0] - low[0] (no prev close for bar 0).
        For bars 1+: TR = max(H-L, |H-prev_C|, |L-prev_C|).
        With flat data: high=102, low=98, close=100 → H-L=4, |H-prevC|=2, |L-prevC|=2
        so TR[i>=1] = 4.0 for all bars.
        atr[period] = mean(TR[1:period+1]) = 4.0
        Subsequent ATR = (prev*(period-1) + 4) / period = 4.0 (stable).
        """
        n = 20
        highs = [102.0] * n
        lows = [98.0] * n
        closes = [100.0] * n
        opens = [100.0] * n
        df = make_ohlcv(n, highs, lows, closes, opens)
        atr = compute_atr(df, period=5)
        # First ATR at index 5 = mean(TR[1:6]) = mean([4]*5) = 4.0
        assert atr.iloc[5] == pytest.approx(4.0)
        # Stable because (4*(5-1) + 4)/5 = 4.0
        assert atr.iloc[-1] == pytest.approx(4.0, rel=1e-4)

    def test_atr_increases_with_higher_ranges(self):
        """ATR should be larger when bars have larger ranges."""
        n = 20
        # narrow range
        df_narrow = make_ohlcv(n, highs=[101.0] * n, lows=[99.0] * n)
        # wide range
        df_wide = make_ohlcv(n, highs=[110.0] * n, lows=[90.0] * n)
        atr_narrow = compute_atr(df_narrow, period=5).iloc[-1]
        atr_wide = compute_atr(df_wide, period=5).iloc[-1]
        assert atr_wide > atr_narrow

    def test_atr_length_matches_input(self):
        df = make_flat_ohlcv(30)
        atr = compute_atr(df, period=14)
        assert len(atr) == 30


# ---------------------------------------------------------------------------
# 3. Volume Profile
# ---------------------------------------------------------------------------

class TestVolumeProfile:

    def test_volume_profile_poc_in_range(self):
        df = make_flat_ohlcv(100)
        poc, vah, val = compute_volume_profile(df, window=100)
        assert df["low"].min() <= poc <= df["high"].max()

    def test_volume_profile_vah_above_val(self):
        df = make_flat_ohlcv(100)
        poc, vah, val = compute_volume_profile(df, window=100)
        assert vah >= val

    def test_volume_profile_raises_insufficient_data(self):
        df = make_flat_ohlcv(50)
        with pytest.raises(ValueError):
            compute_volume_profile(df, window=96)

    def test_volume_profile_concentrated_volume(self):
        """All volume at high prices => POC near the top."""
        n = 100
        highs = [90.0] * 50 + [110.0] * 50
        lows = [88.0] * 50 + [108.0] * 50
        closes = [89.0] * 50 + [109.0] * 50
        # give top half 100x more volume
        volumes = [1.0] * 50 + [100.0] * 50
        timestamps = pd.date_range("2026-01-01", periods=n, freq="30min")
        df = pd.DataFrame({
            "timestamp": timestamps,
            "open": closes,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes,
        })
        poc, vah, val = compute_volume_profile(df, window=100)
        assert poc > 100.0  # POC should be in upper half


# ---------------------------------------------------------------------------
# 4. Swing Detection
# ---------------------------------------------------------------------------

class TestSwingDetection:

    def _zigzag_df(self) -> pd.DataFrame:
        """Clear zigzag: 100, 110, 100, 110, 100, 110, 100, 110, 100, 110."""
        highs = [102, 112, 102, 112, 102, 112, 102, 112, 102, 112]
        lows  = [ 98, 108,  98, 108,  98, 108,  98, 108,  98, 108]
        return make_ohlcv(10, highs, lows)

    def test_detect_swings_returns_two_lists(self):
        df = self._zigzag_df()
        result = detect_swings(df)
        assert isinstance(result, tuple) and len(result) == 2

    def test_detect_swings_highs_detected(self):
        df = self._zigzag_df()
        highs, lows = detect_swings(df, left=1, right=1)
        assert len(highs) > 0

    def test_detect_swings_lows_detected(self):
        df = self._zigzag_df()
        highs, lows = detect_swings(df, left=1, right=1)
        assert len(lows) > 0

    def test_detect_swings_unconfirmed_excluded(self):
        """The last ``right`` bars cannot be confirmed swings."""
        highs = [100, 105, 100, 105, 100, 200]  # last bar is potential high but unconfirmed
        lows  = [ 98, 103,  98, 103,  98, 195]
        df = make_ohlcv(6, highs, lows)
        sh, _ = detect_swings(df, left=1, right=1)
        # Index 5 (last) should NOT appear in confirmed highs
        confirmed_indices = [idx for idx, _ in sh]
        assert 5 not in confirmed_indices

    def test_detect_swings_price_values_correct(self):
        """Verify the price in the returned tuple matches the DataFrame high/low."""
        highs = [100, 110, 100, 105, 100, 105, 100]
        lows  = [ 98, 108,  98, 103,  98, 103,  98]
        df = make_ohlcv(7, highs, lows)
        sh, sl = detect_swings(df, left=1, right=1)
        for idx, price in sh:
            assert price == pytest.approx(df["high"].iloc[idx])
        for idx, price in sl:
            assert price == pytest.approx(df["low"].iloc[idx])


# ---------------------------------------------------------------------------
# 5. Volume SMA
# ---------------------------------------------------------------------------

class TestVolumeSMA:

    def test_volume_sma_basic(self):
        df = make_flat_ohlcv(10, volume=200.0)
        sma = compute_volume_sma(df, period=5)
        assert sma.iloc[-1] == pytest.approx(200.0)

    def test_volume_sma_respects_period(self):
        """First period-1 values should be NaN."""
        df = make_flat_ohlcv(10, volume=100.0)
        sma = compute_volume_sma(df, period=5)
        assert sma.iloc[:4].isna().all()
        assert sma.iloc[4:].notna().all()


# ---------------------------------------------------------------------------
# 6. Cloud Position
# ---------------------------------------------------------------------------

class TestCloudPosition:

    def test_above_cloud(self):
        assert classify_cloud_position(110.0, 100.0, 90.0) == CloudPosition.ABOVE

    def test_below_cloud(self):
        assert classify_cloud_position(80.0, 100.0, 90.0) == CloudPosition.BELOW

    def test_in_cloud(self):
        assert classify_cloud_position(95.0, 100.0, 90.0) == CloudPosition.IN

    def test_boundary_at_cloud_top_is_in(self):
        """close == cloud_top → IN, not ABOVE (strictly >)."""
        assert classify_cloud_position(100.0, 100.0, 90.0) == CloudPosition.IN

    def test_boundary_at_cloud_bottom_is_in(self):
        """close == cloud_bottom → IN, not BELOW (strictly <)."""
        assert classify_cloud_position(90.0, 100.0, 90.0) == CloudPosition.IN


# ---------------------------------------------------------------------------
# 7. TK State
# ---------------------------------------------------------------------------

class TestTkState:

    def test_bullish_when_tenkan_above_kijun(self):
        assert classify_tk_state(105.0, 100.0) == TkState.BULLISH

    def test_bearish_when_tenkan_below_kijun(self):
        assert classify_tk_state(95.0, 100.0) == TkState.BEARISH

    def test_bullish_when_tenkan_equals_kijun(self):
        """Spec: tenkan >= kijun → BULLISH (boundary inclusive)."""
        assert classify_tk_state(100.0, 100.0) == TkState.BULLISH


# ---------------------------------------------------------------------------
# 8. Profile Bias
# ---------------------------------------------------------------------------

class TestProfileBias:

    def test_above_va(self):
        assert classify_profile_bias(110.0, 100.0, 90.0) == ProfileBias.ABOVE_VA

    def test_below_va(self):
        assert classify_profile_bias(80.0, 100.0, 90.0) == ProfileBias.BELOW_VA

    def test_inside_va(self):
        assert classify_profile_bias(95.0, 100.0, 90.0) == ProfileBias.INSIDE_VA

    def test_boundary_at_vah_is_inside(self):
        """close == vah → INSIDE (strictly >)."""
        assert classify_profile_bias(100.0, 100.0, 90.0) == ProfileBias.INSIDE_VA

    def test_boundary_at_val_is_inside(self):
        """close == val → INSIDE (strictly <)."""
        assert classify_profile_bias(90.0, 100.0, 90.0) == ProfileBias.INSIDE_VA


# ---------------------------------------------------------------------------
# 9. Zone Width
# ---------------------------------------------------------------------------

class TestZoneWidth:

    def test_zone_width_uses_price_factor(self):
        """When price*pct dominates ATR term."""
        width = compute_zone_width(current_price=10000.0, atr_15m=1.0)
        assert width == pytest.approx(max(10000 * 0.0015, 1.0 * 0.25))

    def test_zone_width_uses_atr_factor(self):
        """When ATR term dominates price*pct."""
        width = compute_zone_width(current_price=1.0, atr_15m=1000.0)
        assert width == pytest.approx(max(1.0 * 0.0015, 1000.0 * 0.25))

    def test_zone_width_max_semantics(self):
        price = 100.0
        atr = 200.0
        width = compute_zone_width(price, atr)
        assert width == pytest.approx(max(price * 0.0015, atr * 0.25))


# ---------------------------------------------------------------------------
# 10. Make Zone
# ---------------------------------------------------------------------------

class TestMakeZone:

    def test_make_zone_structure(self):
        z = make_zone("z1", level=100.0, zone_width=5.0, timeframe=Timeframe.H1, source="swing")
        assert z.low == pytest.approx(95.0)
        assert z.mid == pytest.approx(100.0)
        assert z.high == pytest.approx(105.0)
        assert z.level == pytest.approx(100.0)

    def test_make_zone_id_and_source(self):
        z = make_zone("test_id", level=50.0, zone_width=2.0, timeframe=Timeframe.M30, source="profile")
        assert z.id == "test_id"
        assert z.source == "profile"


# ---------------------------------------------------------------------------
# 11. Merge Overlapping Zones
# ---------------------------------------------------------------------------

class TestMergeOverlappingZones:

    def test_merge_empty_list(self):
        assert merge_overlapping_zones([]) == []

    def test_merge_single_zone(self):
        z = make_zone_obj(90.0, 110.0)
        result = merge_overlapping_zones([z])
        assert len(result) == 1

    def test_no_overlap_returns_two_zones(self):
        z1 = make_zone_obj(90.0, 95.0, "z1")
        z2 = make_zone_obj(100.0, 105.0, "z2")
        result = merge_overlapping_zones([z1, z2])
        assert len(result) == 2

    def test_partial_overlap_merges(self):
        z1 = make_zone_obj(90.0, 102.0, "z1")
        z2 = make_zone_obj(100.0, 110.0, "z2")
        result = merge_overlapping_zones([z1, z2])
        assert len(result) == 1
        assert result[0].low == pytest.approx(90.0)
        assert result[0].high == pytest.approx(110.0)

    def test_full_containment_merges(self):
        z1 = make_zone_obj(80.0, 120.0, "z1")
        z2 = make_zone_obj(90.0, 110.0, "z2")
        result = merge_overlapping_zones([z1, z2])
        assert len(result) == 1

    def test_merge_ids_joined(self):
        z1 = make_zone_obj(90.0, 102.0, "A")
        z2 = make_zone_obj(100.0, 110.0, "B")
        result = merge_overlapping_zones([z1, z2])
        assert "A" in result[0].id and "B" in result[0].id


# ---------------------------------------------------------------------------
# 12. Upper Rejection
# ---------------------------------------------------------------------------

class TestUpperRejection:

    def test_upper_rejection_pass(self):
        """High reaches zone.high, close < zone.mid, upper_wick >= body."""
        # zone_high=105, zone_mid=100
        # bar: open=98, high=106, close=97 → body=1, upper_wick=106-98=8 >= 1
        assert check_upper_rejection(
            high=106.0, close=97.0, open_price=98.0,
            zone_high=105.0, zone_mid=100.0
        ) is True

    def test_upper_rejection_fail_high_below_zone(self):
        assert check_upper_rejection(
            high=104.0, close=97.0, open_price=98.0,
            zone_high=105.0, zone_mid=100.0
        ) is False

    def test_upper_rejection_fail_close_above_mid(self):
        assert check_upper_rejection(
            high=106.0, close=101.0, open_price=98.0,
            zone_high=105.0, zone_mid=100.0
        ) is False

    def test_upper_rejection_fail_body_dominates(self):
        """Upper wick smaller than body → no rejection."""
        # open=90, close=97, high=98 → body=7, upper_wick=1 < 7
        assert check_upper_rejection(
            high=98.0, close=97.0, open_price=90.0,
            zone_high=97.0, zone_mid=95.0
        ) is False


# ---------------------------------------------------------------------------
# 13. Support Hold
# ---------------------------------------------------------------------------

class TestSupportHold:

    def test_support_hold_pass(self):
        """Low dips below zone.low, close > zone.mid, lower_wick >= body."""
        # zone_low=95, zone_mid=100
        # open=102, close=103, low=94 → body=1, lower_wick=94-min(103,102)=102-94=8 >= 1
        assert check_support_hold(
            low=94.0, close=103.0, open_price=102.0,
            zone_low=95.0, zone_mid=100.0
        ) is True

    def test_support_hold_fail_low_above_zone(self):
        assert check_support_hold(
            low=96.0, close=103.0, open_price=102.0,
            zone_low=95.0, zone_mid=100.0
        ) is False

    def test_support_hold_fail_close_below_mid(self):
        assert check_support_hold(
            low=94.0, close=99.0, open_price=98.0,
            zone_low=95.0, zone_mid=100.0
        ) is False

    def test_support_hold_fail_body_dominates(self):
        """Lower wick smaller than body → no hold."""
        # open=94, close=103, low=93 → body=9, lower_wick=94-93=1 < 9
        assert check_support_hold(
            low=93.0, close=103.0, open_price=94.0,
            zone_low=95.0, zone_mid=100.0
        ) is False


# ---------------------------------------------------------------------------
# 14. Maintain Above / Below
# ---------------------------------------------------------------------------

class TestMaintainAboveBelow:

    def test_maintain_above_pass(self):
        assert check_maintain_above([99.0, 101.0, 102.0], level=100.0) is True

    def test_maintain_above_fail_one_below(self):
        assert check_maintain_above([101.0, 99.0, 102.0], level=100.0) is False

    def test_maintain_above_fail_too_few(self):
        assert check_maintain_above([102.0], level=100.0) is False

    def test_maintain_below_pass(self):
        assert check_maintain_below([101.0, 99.0, 98.0], level=100.0) is True

    def test_maintain_below_fail_one_above(self):
        assert check_maintain_below([99.0, 101.0, 98.0], level=100.0) is False

    def test_maintain_below_fail_too_few(self):
        assert check_maintain_below([98.0], level=100.0) is False


# ---------------------------------------------------------------------------
# 15. Box Center
# ---------------------------------------------------------------------------

class TestBoxCenter:

    def _make_highs_lows(self, n: int = 48, base: float = 100.0, span: float = 20.0):
        highs = [base + span / 2] * n
        lows = [base - span / 2] * n
        return highs, lows

    def test_box_center_pass_no_zones(self):
        highs, lows = self._make_highs_lows(48, 100.0, 20.0)
        # range = 20, center = 100, close=100 → position=0.50 ∈ [0.40, 0.60]
        result = check_box_center(
            highs_48=highs, lows_48=lows, current_close=100.0,
            atr_30m=1.0, zones=[]
        )
        assert result is True

    def test_box_center_fail_close_at_top(self):
        highs, lows = self._make_highs_lows(48, 100.0, 20.0)
        # close=109 → position=0.95 > 0.60
        result = check_box_center(
            highs_48=highs, lows_48=lows, current_close=109.0,
            atr_30m=1.0, zones=[]
        )
        assert result is False

    def test_box_center_fail_zone_nearby(self):
        highs, lows = self._make_highs_lows(48, 100.0, 20.0)
        # close=100, zone at 100 → distance=0 < 0.5*atr
        zone = make_zone_obj(99.0, 101.0)
        result = check_box_center(
            highs_48=highs, lows_48=lows, current_close=100.0,
            atr_30m=10.0, zones=[zone]
        )
        assert result is False

    def test_box_center_fail_insufficient_bars(self):
        highs = [110.0] * 30
        lows = [90.0] * 30
        result = check_box_center(
            highs_48=highs, lows_48=lows, current_close=100.0,
            atr_30m=1.0, zones=[]
        )
        assert result is False

    def test_box_center_uses_highs_lows_not_closes(self):
        """Verify function uses highs_48/lows_48 parameters (not close-based range)."""
        # range from H/L = 20
        highs = [110.0] * 48
        lows = [90.0] * 48
        # close in center
        result = check_box_center(
            highs_48=highs, lows_48=lows, current_close=100.0,
            atr_30m=1.0, zones=[]
        )
        assert result is True


# ---------------------------------------------------------------------------
# 16. Retracement
# ---------------------------------------------------------------------------

class TestRetracement:

    def test_retracement_at_midpoint(self):
        # swing_high=110, swing_low=90, close=100 → 0.50
        assert compute_retracement(110.0, 90.0, 100.0) == pytest.approx(0.50)

    def test_retracement_at_swing_low(self):
        assert compute_retracement(110.0, 90.0, 90.0) == pytest.approx(0.0)

    def test_retracement_at_swing_high(self):
        assert compute_retracement(110.0, 90.0, 110.0) == pytest.approx(1.0)

    def test_retracement_zero_range(self):
        assert compute_retracement(100.0, 100.0, 100.0) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# 17. Abnormal Volatility
# ---------------------------------------------------------------------------

class TestAbnormalVolatility:

    def test_abnormal_via_15m(self):
        """15m range > 2.5 * atr_15m → True."""
        assert check_abnormal_volatility(
            range_15m=10.0, atr_15m=3.0,
            range_30m=1.0, atr_30m=2.0
        ) is True

    def test_abnormal_via_30m(self):
        """30m range > 2.0 * atr_30m → True."""
        assert check_abnormal_volatility(
            range_15m=1.0, atr_15m=3.0,
            range_30m=10.0, atr_30m=4.0
        ) is True

    def test_normal_volatility(self):
        assert check_abnormal_volatility(
            range_15m=2.0, atr_15m=3.0,
            range_30m=3.0, atr_30m=4.0
        ) is False

    def test_boundary_not_exceeded(self):
        """Exactly at threshold is NOT abnormal (strictly >)."""
        assert check_abnormal_volatility(
            range_15m=7.5, atr_15m=3.0,   # 7.5 == 2.5*3.0, not >
            range_30m=8.0, atr_30m=4.0    # 8.0 == 2.0*4.0, not >
        ) is False


# ---------------------------------------------------------------------------
# 18. Hammer
# ---------------------------------------------------------------------------

class TestHammer:

    def test_hammer_pass(self):
        """Classic hammer: small body, long lower wick, bullish close."""
        # candle: open=100, close=101, low=90, high=102
        # candle_length=12, body=1, lower_wick=90->100=10
        # body/candle=1/12≈0.08 < 0.35 ✓
        # lower_wick(10) >= 2*body(1) ✓, close(101)>=open(100) ✓
        assert check_hammer(open_price=100.0, high=102.0, low=90.0, close=101.0) is True

    def test_hammer_fail_large_body(self):
        """Body too large → fail."""
        # open=90, close=100, low=89, high=101
        # body=10, candle=12, body/candle≈0.83 > 0.35
        assert check_hammer(open_price=90.0, high=101.0, low=89.0, close=100.0) is False

    def test_hammer_fail_wick_too_small(self):
        """Lower wick < 2*body → fail."""
        # open=98, close=100, low=97, high=102
        # body=2, lower_wick=1 < 2*2
        assert check_hammer(open_price=98.0, high=102.0, low=97.0, close=100.0) is False

    def test_hammer_fail_bearish_close(self):
        """close < open → fail even with good wick."""
        # open=101, close=100, low=90, high=102
        assert check_hammer(open_price=101.0, high=102.0, low=90.0, close=100.0) is False

    def test_hammer_zero_length_candle(self):
        assert check_hammer(open_price=100.0, high=100.0, low=100.0, close=100.0) is False


# ---------------------------------------------------------------------------
# 19. build_timeframe_snapshot
# ---------------------------------------------------------------------------

class TestBuildTimeframeSnapshot:

    def _make_df_for_snapshot(self, n: int = 60) -> pd.DataFrame:
        return make_flat_ohlcv(n, price=100.0)

    def test_build_snapshot_returns_timeframe_snapshot(self):
        df = self._make_df_for_snapshot()
        snap = build_timeframe_snapshot(df, Timeframe.H1)
        assert isinstance(snap, TimeframeSnapshot)

    def test_build_snapshot_correct_timeframe(self):
        df = self._make_df_for_snapshot()
        snap = build_timeframe_snapshot(df, Timeframe.H4)
        assert snap.timeframe == Timeframe.H4

    def test_build_snapshot_close_matches_last_bar(self):
        df = self._make_df_for_snapshot()
        snap = build_timeframe_snapshot(df, Timeframe.H1)
        assert snap.close == pytest.approx(df["close"].iloc[-1])

    def test_build_snapshot_atr_positive(self):
        df = self._make_df_for_snapshot()
        snap = build_timeframe_snapshot(df, Timeframe.H1)
        assert snap.atr > 0

    def test_build_snapshot_with_profile_window(self):
        """Passing a profile_window should populate poc/vah/val."""
        df = self._make_df_for_snapshot(120)
        snap = build_timeframe_snapshot(df, Timeframe.H1, profile_window=96)
        assert snap.poc > 0
        assert snap.vah >= snap.val

    def test_build_snapshot_no_profile_window(self):
        """Without profile_window, poc/vah/val should be 0.0 (NaN converted)."""
        df = self._make_df_for_snapshot()
        snap = build_timeframe_snapshot(df, Timeframe.M15)
        assert snap.poc == 0.0
        assert snap.vah == 0.0
        assert snap.val == 0.0

    def test_build_snapshot_cloud_position_set(self):
        df = self._make_df_for_snapshot()
        snap = build_timeframe_snapshot(df, Timeframe.H1)
        assert snap.cloud_position in (CloudPosition.ABOVE, CloudPosition.IN, CloudPosition.BELOW)

    def test_build_snapshot_tk_state_set(self):
        df = self._make_df_for_snapshot()
        snap = build_timeframe_snapshot(df, Timeframe.H1)
        assert snap.tk_state in (TkState.BULLISH, TkState.BEARISH)
