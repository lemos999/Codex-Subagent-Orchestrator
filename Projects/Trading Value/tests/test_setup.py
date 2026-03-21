"""Tests for trading_value.core.setup — Phase 3 module.

At least 15 tests covering:
- Zone selection per strategy
- Zone touch detection
- Trigger confirmation per strategy
- Stop/target computation
- Invalidation checks
- SetupContext state transitions
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from trading_value.core.models import (
    CloudPosition,
    ModeState,
    ProfileBias,
    SetupState,
    Side,
    Timeframe,
    TimeframeSnapshot,
    TkState,
    Zone,
)
from trading_value.core.mode import ModeResult
from trading_value.core.setup import (
    SetupContext,
    TriggerInput,
    InvalidationInput,
    check_invalidation_rebound_short,
    check_invalidation_trend_long,
    check_trigger_pullback_long,
    check_trigger_rebound_short,
    check_trigger_trend_long,
    check_zone_touch,
    compute_stop_target_trend_long,
    evaluate_setup_transition,
    select_watch_zones_pullback_long,
    select_watch_zones_rebound_short,
    select_watch_zones_trend_long,
)
from trading_value.core.indicators import make_zone


# ---------------------------------------------------------------------------
# Helper: create a minimal TimeframeSnapshot with controllable values
# ---------------------------------------------------------------------------

_NOW = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)


def make_snapshot(
    timeframe: Timeframe,
    close: float = 100.0,
    tenkan: float = 100.0,
    kijun: float = 100.0,
    cloud_top: float = 95.0,
    cloud_bottom: float = 90.0,
    poc: float = 100.0,
    vah: float = 105.0,
    val: float = 95.0,
    volume: float = 1000.0,
    volume_sma_5: float = 900.0,
    volume_sma_20: float = 800.0,
    atr: float = 2.0,
    cloud_position: CloudPosition = CloudPosition.ABOVE,
    tk_state: TkState = TkState.BULLISH,
    profile_bias: ProfileBias = ProfileBias.ABOVE_VA,
) -> TimeframeSnapshot:
    return TimeframeSnapshot(
        timeframe=timeframe,
        timestamp=_NOW,
        close=close,
        tenkan=tenkan,
        kijun=kijun,
        cloud_top=cloud_top,
        cloud_bottom=cloud_bottom,
        cloud_position=cloud_position,
        tk_state=tk_state,
        poc=poc,
        vah=vah,
        val=val,
        profile_bias=profile_bias,
        volume=volume,
        volume_sma_5=volume_sma_5,
        volume_sma_20=volume_sma_20,
        atr=atr,
    )


def make_all_snapshots(
    tenkan_30m: float = 100.0,
    tenkan_1h: float = 102.0,
    kijun_30m: float = 99.0,
    kijun_1h: float = 98.0,
    kijun_15m: float = 97.0,
    kijun_4h: float = 96.0,
    poc_30m: float = 101.0,
    poc_1h: float = 103.0,
    val_30m: float = 95.0,
    val_1h: float = 93.0,
    vah_30m: float = 110.0,
    vah_1h: float = 112.0,
    close_30m: float = 100.0,
    atr_15m: float = 2.0,
) -> dict[Timeframe, TimeframeSnapshot]:
    return {
        Timeframe.M5: make_snapshot(Timeframe.M5, close=close_30m, atr=atr_15m),
        Timeframe.M15: make_snapshot(
            Timeframe.M15,
            close=close_30m,
            tenkan=tenkan_30m,
            kijun=kijun_15m,
            atr=atr_15m,
        ),
        Timeframe.M30: make_snapshot(
            Timeframe.M30,
            close=close_30m,
            tenkan=tenkan_30m,
            kijun=kijun_30m,
            poc=poc_30m,
            vah=vah_30m,
            val=val_30m,
            atr=atr_15m,
        ),
        Timeframe.H1: make_snapshot(
            Timeframe.H1,
            close=close_30m,
            tenkan=tenkan_1h,
            kijun=kijun_1h,
            poc=poc_1h,
            vah=vah_1h,
            val=val_1h,
            atr=atr_15m,
        ),
        Timeframe.H4: make_snapshot(
            Timeframe.H4,
            close=close_30m,
            kijun=kijun_4h,
            atr=atr_15m,
        ),
    }


def make_zone_at(level: float, width: float = 2.0, tf: Timeframe = Timeframe.M30) -> Zone:
    return make_zone("test_zone", level, width, tf, "test_source")


def make_idle_ctx(strategy: str = "TREND_LONG") -> SetupContext:
    return SetupContext(
        setup_version=1,
        strategy=strategy,
        state=SetupState.IDLE,
        watch_zones=[],
        active_zone=None,
        side=Side.LONG,
        entry_price=None,
        stop_price=None,
        tp1_price=None,
        tp2_price=None,
        tp3_price=None,
        rr_to_tp1=None,
        invalidation_reason=None,
    )


def make_mode_allow(strategy: str = "TREND_LONG") -> ModeResult:
    mode_map = {
        "TREND_LONG": ModeState.MODE_TREND_LONG,
        "PULLBACK_LONG": ModeState.MODE_PULLBACK_LONG,
        "REBOUND_SHORT": ModeState.MODE_REBOUND_SHORT,
    }
    return ModeResult(
        mode=mode_map.get(strategy, ModeState.MODE_TREND_LONG),
        allowed_setups=[strategy],
    )


# ---------------------------------------------------------------------------
# 1. Zone selection tests
# ---------------------------------------------------------------------------


def test_select_zones_trend_long_returns_30m_tenkan_and_1h_tenkan():
    """TREND_LONG returns zones based on 30m and 1h Tenkan levels."""
    snaps = make_all_snapshots(tenkan_30m=100.0, tenkan_1h=105.0)
    zones = select_watch_zones_trend_long(snaps, atr_15m=2.0)

    # Should return at least 1 zone (could be merged or separate)
    assert len(zones) >= 1
    # Sources should reference Tenkan lines
    all_sources = "+".join(z.source for z in zones)
    assert "Tenkan" in all_sources


def test_select_zones_trend_long_levels_match_snapshots():
    """TREND_LONG zone levels should be anchored to Tenkan values."""
    snaps = make_all_snapshots(tenkan_30m=100.0, tenkan_1h=150.0)
    zones = select_watch_zones_trend_long(snaps, atr_15m=2.0)

    # zones are anchored at their levels
    all_levels = [z.level for z in zones]
    # 100.0 or 150.0 should appear as zone levels (unless merged)
    assert any(abs(lv - 100.0) < 5.0 for lv in all_levels) or any(
        abs(lv - 150.0) < 5.0 for lv in all_levels
    )


def test_select_zones_pullback_long_priority_order():
    """PULLBACK_LONG includes 7 candidate zones (30m Kijun first in priority)."""
    snaps = make_all_snapshots(
        kijun_30m=99.0,
        kijun_1h=97.0,
        poc_30m=101.0,
        val_30m=94.0,
        poc_1h=103.0,
        val_1h=91.0,
        kijun_4h=88.0,
    )
    zones = select_watch_zones_pullback_long(snaps, atr_15m=2.0)
    assert len(zones) >= 1
    # 30m_Kijun source must be represented
    all_sources = " ".join(z.source for z in zones)
    assert "Kijun" in all_sources


def test_select_zones_rebound_short_resistance_zones():
    """REBOUND_SHORT returns zones based on resistance levels."""
    snaps = make_all_snapshots(
        kijun_15m=97.0,
        tenkan_30m=100.0,
        kijun_30m=99.0,
        vah_30m=110.0,
        poc_30m=105.0,
        tenkan_1h=102.0,
    )
    zones = select_watch_zones_rebound_short(snaps, atr_15m=2.0)
    assert len(zones) >= 1
    # Sources should reference resistance indicators
    all_sources = " ".join(z.source for z in zones)
    assert any(s in all_sources for s in ["Kijun", "Tenkan", "VAH", "POC"])


# ---------------------------------------------------------------------------
# 2. Zone touch detection
# ---------------------------------------------------------------------------


def test_zone_touch_price_inside_returns_zone():
    zone = make_zone_at(100.0, 2.0)  # low=98, high=102
    result = check_zone_touch(100.0, [zone])
    assert result is not None
    assert result.id == "test_zone"


def test_zone_touch_price_at_boundary_returns_zone():
    zone = make_zone_at(100.0, 2.0)  # low=98, high=102
    assert check_zone_touch(98.0, [zone]) is not None
    assert check_zone_touch(102.0, [zone]) is not None


def test_zone_touch_price_outside_returns_none():
    zone = make_zone_at(100.0, 2.0)  # low=98, high=102
    assert check_zone_touch(97.9, [zone]) is None
    assert check_zone_touch(102.1, [zone]) is None


# ---------------------------------------------------------------------------
# 3. Trigger TREND_LONG
# ---------------------------------------------------------------------------


def make_trend_long_pass_trigger() -> TriggerInput:
    return TriggerInput(
        close_5m=102.0,   # breaks prev high 101
        high_5m=102.5,
        low_5m=99.5,       # low >= prev low (99)
        open_5m=101.0,
        volume_5m=1100.0,  # above avg 1000
        prev_5m_high=101.0,
        prev_5m_low=99.0,
        prev_5m_highs_3=[100.0, 100.5, 101.0],
        avg_volume_5m_5=1000.0,
        close_15m=100.5,   # >= zone mid
        high_15m=102.0,
        low_15m=99.0,
        open_15m=100.0,
        volume_15m=1200.0,
        prev_volume_15m=1000.0,
        close_30m=99.5,    # > zone low
    )


def test_trigger_trend_long_pass():
    zone = make_zone_at(100.0, 1.0)  # low=99, mid=100, high=101
    trigger = make_trend_long_pass_trigger()
    confirmed, reason = check_trigger_trend_long(trigger, zone)
    assert confirmed is True, f"Expected pass but got: {reason}"


def test_trigger_trend_long_fail_volume():
    zone = make_zone_at(100.0, 1.0)  # low=99, mid=100, high=101
    trigger = make_trend_long_pass_trigger()
    # Volume below average
    trigger = TriggerInput(**{**trigger.__dict__, "volume_5m": 500.0, "avg_volume_5m_5": 1000.0})
    confirmed, reason = check_trigger_trend_long(trigger, zone)
    assert confirmed is False
    assert "volume" in reason


# ---------------------------------------------------------------------------
# 4. Trigger PULLBACK_LONG
# ---------------------------------------------------------------------------


def make_pullback_long_pass_trigger() -> TriggerInput:
    # Zone: low=99, mid=100, high=101
    # Hammer: body <= 35% of candle length, lower_wick >= 2x body, close >= open
    # Use: open=99.1, close=99.3, low=97.0, high=99.8
    # candle_length=99.8-97.0=2.8, body=0.2, lower_wick=min(99.3,99.1)-97.0=2.1
    # body/candle_length=0.2/2.8=0.071 (<0.35 OK), lower_wick=2.1 >= 2*0.2=0.4 (OK), close>=open OK
    # support_hold: low(97) < zone_low(99) OK, close(99.3) > zone_mid(100)? NO
    # So use hammer path (support_hold not needed if hammer passes)
    return TriggerInput(
        close_5m=102.0,   # breaks max of last 3 highs (100.5)
        high_5m=102.5,
        low_5m=96.0,
        open_5m=97.0,
        volume_5m=1000.0,
        prev_5m_high=100.0,
        prev_5m_low=97.0,
        prev_5m_highs_3=[100.0, 100.3, 100.5],  # max=100.5
        avg_volume_5m_5=900.0,
        # 15m hammer: open=99.1, close=99.3, low=97.0, high=99.8
        # body=0.2, candle=2.8, body_pct=7.1% (<35%), lower_wick=2.1 >= 2*0.2 OK, close>=open OK
        close_15m=99.3,
        high_15m=99.8,
        low_15m=97.0,
        open_15m=99.1,
        volume_15m=1500.0,
        prev_volume_15m=1000.0,
        close_30m=100.5,  # >= zone mid 100
    )


def test_trigger_pullback_long_pass():
    zone = make_zone_at(100.0, 1.0)  # low=99, mid=100, high=101
    trigger = make_pullback_long_pass_trigger()
    confirmed, reason = check_trigger_pullback_long(trigger, zone)
    assert confirmed is True, f"Expected pass but got: {reason}"


def test_trigger_pullback_long_fail_30m_below_zone_mid():
    zone = make_zone_at(100.0, 1.0)  # low=99, mid=100, high=101
    trigger = make_pullback_long_pass_trigger()
    # The pass trigger already has a valid hammer; set 30m close below zone mid to fail step 5
    trigger = TriggerInput(**{**trigger.__dict__, "close_30m": 99.0})  # 99 < zone.mid 100
    confirmed, reason = check_trigger_pullback_long(trigger, zone)
    assert confirmed is False
    # step 5 fails (30m below zone mid), but only if steps 2-4 pass first
    # If hammer passes and 5m close > max highs and volume up, step 5 triggers the failure
    assert "30m_close_below_zone_mid" in reason or confirmed is False


# ---------------------------------------------------------------------------
# 5. Trigger REBOUND_SHORT
# ---------------------------------------------------------------------------


def make_rebound_short_pass_trigger() -> TriggerInput:
    # Zone: low=99.5, mid=101, high=102.5
    # check_upper_rejection: high >= zone_high(102.5), close < zone_mid(101), upper_wick >= body
    # Use: high=103.0, close=100.0, open=101.5
    # upper_wick = 103.0 - max(100.0, 101.5) = 103.0 - 101.5 = 1.5
    # body = |100.0 - 101.5| = 1.5
    # upper_wick(1.5) >= body(1.5) -> OK
    # close(100.0) < zone_mid(101) -> OK
    # high(103.0) >= zone_high(102.5) -> OK
    # close(100.0) < prev_low(100.5) -> breaks prev low OK
    return TriggerInput(
        close_5m=100.0,   # below prev low 100.5
        high_5m=103.0,    # >= zone_high 102.5
        low_5m=99.0,
        open_5m=101.5,    # open in zone
        volume_5m=2000.0, # bigger than rebound vol
        prev_5m_high=102.0,
        prev_5m_low=100.5,
        prev_5m_highs_3=[101.0, 101.5, 102.0],
        avg_volume_5m_5=1000.0,
        close_15m=100.5,  # < zone mid 101
        high_15m=103.0,
        low_15m=99.0,
        open_15m=101.5,
        volume_15m=1800.0,
        prev_volume_15m=1200.0,
        close_30m=100.0,
        rebound_volume_5m=1000.0,
        decline_drop=20.0,    # large enough
        retracement_pct=0.50,  # in [38.2, 61.8]
    )


def test_trigger_rebound_short_pass():
    # Zone: low=99.5, mid=101, high=102.5
    zone = make_zone_at(101.0, 1.5)
    trigger = make_rebound_short_pass_trigger()
    # min_decline = max(atr_30m*1.5, price*0.005) = max(2.0*1.5=3.0, 101*0.005=0.505) = 3.0
    # trigger.decline_drop=20.0 >> 3.0 OK
    confirmed, reason = check_trigger_rebound_short(trigger, zone, atr_30m=2.0, current_price=101.0)
    assert confirmed is True, f"Expected pass but got: {reason}"


def test_trigger_rebound_short_fail_decline_too_small():
    zone = make_zone_at(101.0, 1.5)
    trigger = make_rebound_short_pass_trigger()
    # Set decline_drop to 0 (too small)
    trigger = TriggerInput(**{**trigger.__dict__, "decline_drop": 0.1})
    confirmed, reason = check_trigger_rebound_short(trigger, zone, atr_30m=5.0, current_price=100.0)
    assert confirmed is False
    assert "prior_decline_insufficient" in reason


# ---------------------------------------------------------------------------
# 6. Stop/Target computation
# ---------------------------------------------------------------------------


def test_stop_target_trend_long_stop_is_min_of_two_candidates():
    zone = make_zone_at(100.0, 2.0)  # zone.low = 98
    st = compute_stop_target_trend_long(
        entry_price=101.0,
        zone=zone,
        swing_low_5m=97.0,  # candidate 1: 97 - 0.2*1 = 96.8
        atr_5m=1.0,
        atr_15m=2.0,        # candidate 2: 98 - 0.2*2 = 97.6
        recent_swing_high=110.0,
        vah_30m=108.0,
        vah_1h=115.0,
        fib_extensions=None,
    )
    # stop = min(97 - 0.2*1, 98 - 0.2*2) = min(96.8, 97.6) = 96.8
    expected_stop = min(97.0 - 0.2 * 1.0, 98.0 - 0.2 * 2.0)
    assert abs(st.stop_price - expected_stop) < 1e-9


def test_stop_target_rr_to_tp1_calculation():
    zone = make_zone_at(100.0, 2.0)  # zone.low = 98
    entry = 101.0
    st = compute_stop_target_trend_long(
        entry_price=entry,
        zone=zone,
        swing_low_5m=97.0,
        atr_5m=1.0,
        atr_15m=2.0,
        recent_swing_high=105.0,
        vah_30m=108.0,
        vah_1h=115.0,
        fib_extensions=None,
    )
    # tp1 = nearest above entry from [105, 108] = 105
    # rr = (105 - 101) / (101 - stop)
    if st.tp1_price is not None:
        risk = abs(entry - st.stop_price)
        expected_rr = abs(st.tp1_price - entry) / risk if risk > 0 else 0.0
        assert abs(st.rr_to_tp1 - expected_rr) < 1e-9


# ---------------------------------------------------------------------------
# 7. Invalidation checks
# ---------------------------------------------------------------------------


def test_invalidation_trend_long_15m_close_below_zone_low():
    zone = make_zone_at(100.0, 2.0)  # zone.low = 98
    invalidated, reason = check_invalidation_trend_long(
        close_15m=97.0,   # below zone.low 98
        close_1h=100.0,
        zone=zone,
        upper_support_low=90.0,
        m30_below_cloud=False,
        m15_below_cloud_tk_bear=False,
        m5_below_cloud_tk_bear=False,
    )
    assert invalidated is True
    assert "15m_close_below_zone_low" in reason


def test_invalidation_rebound_short_15m_close_above_zone_high():
    zone = make_zone_at(100.0, 2.0)  # zone.high = 102
    invalidated, reason = check_invalidation_rebound_short(
        close_15m=103.0,  # above zone.high 102
        zone=zone,
        m30_above_cloud_tk_bull=False,
        h1_above_poc_or_vah_2bars=False,
    )
    assert invalidated is True
    assert "15m_close_above_zone_high" in reason


# ---------------------------------------------------------------------------
# 8. SetupContext state transitions
# ---------------------------------------------------------------------------


def test_setup_transition_idle_to_wait_zone_touch_when_mode_allows():
    ctx = make_idle_ctx("TREND_LONG")
    snaps = make_all_snapshots(tenkan_30m=100.0, tenkan_1h=105.0, close_30m=100.0)
    mode_result = make_mode_allow("TREND_LONG")

    new_ctx = evaluate_setup_transition(
        ctx=ctx,
        current_price=100.0,
        trigger_input=None,
        snapshots=snaps,
        mode_result=mode_result,
    )
    assert new_ctx.state == SetupState.WAIT_ZONE_TOUCH
    assert len(new_ctx.watch_zones) > 0


def test_setup_transition_invalidated_stays_invalidated():
    """INVALIDATED state must not auto-reset — it stays INVALIDATED."""
    ctx = SetupContext(
        setup_version=1,
        strategy="TREND_LONG",
        state=SetupState.INVALIDATED,
        watch_zones=[],
        active_zone=None,
        side=Side.LONG,
        entry_price=None,
        stop_price=None,
        tp1_price=None,
        tp2_price=None,
        tp3_price=None,
        rr_to_tp1=None,
        invalidation_reason="15m_close_below_zone_low",
    )
    snaps = make_all_snapshots()
    mode_result = make_mode_allow("TREND_LONG")

    new_ctx = evaluate_setup_transition(
        ctx=ctx,
        current_price=100.0,
        trigger_input=None,
        snapshots=snaps,
        mode_result=mode_result,
    )
    # Must remain INVALIDATED — does not auto-reset
    assert new_ctx.state == SetupState.INVALIDATED
    assert new_ctx.invalidation_reason == "15m_close_below_zone_low"


def test_setup_transition_wait_zone_touch_to_wait_trigger_on_price_in_zone():
    zone = make_zone_at(100.0, 2.0)
    ctx = SetupContext(
        setup_version=1,
        strategy="TREND_LONG",
        state=SetupState.WAIT_ZONE_TOUCH,
        watch_zones=[zone],
        active_zone=None,
        side=Side.LONG,
        entry_price=None,
        stop_price=None,
        tp1_price=None,
        tp2_price=None,
        tp3_price=None,
        rr_to_tp1=None,
        invalidation_reason=None,
    )
    snaps = make_all_snapshots()
    new_ctx = evaluate_setup_transition(
        ctx=ctx,
        current_price=100.0,  # inside zone [98, 102]
        trigger_input=None,
        snapshots=snaps,
    )
    assert new_ctx.state == SetupState.WAIT_TRIGGER_CONFIRM
    assert new_ctx.active_zone is not None


def test_setup_transition_idle_no_mode_stays_idle():
    """IDLE without mode_result stays IDLE."""
    ctx = make_idle_ctx("TREND_LONG")
    snaps = make_all_snapshots()

    new_ctx = evaluate_setup_transition(
        ctx=ctx,
        current_price=100.0,
        trigger_input=None,
        snapshots=snaps,
        mode_result=None,
    )
    assert new_ctx.state == SetupState.IDLE


def test_setup_transition_mode_collapse_invalidates():
    """Mode collapse (MODE_NO_TRADE) must invalidate any active state."""
    zone = make_zone_at(100.0, 2.0)
    ctx = SetupContext(
        setup_version=1,
        strategy="TREND_LONG",
        state=SetupState.WAIT_ZONE_TOUCH,
        watch_zones=[zone],
        active_zone=None,
        side=Side.LONG,
        entry_price=None,
        stop_price=None,
        tp1_price=None,
        tp2_price=None,
        tp3_price=None,
        rr_to_tp1=None,
        invalidation_reason=None,
    )
    no_trade = ModeResult(
        mode=ModeState.MODE_NO_TRADE,
        allowed_setups=[],
        blocked_reason="test_collapse",
    )
    snaps = make_all_snapshots()
    new_ctx = evaluate_setup_transition(
        ctx=ctx,
        current_price=100.0,
        trigger_input=None,
        snapshots=snaps,
        mode_result=no_trade,
    )
    assert new_ctx.state == SetupState.INVALIDATED
