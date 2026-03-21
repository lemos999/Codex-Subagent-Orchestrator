"""Setup tracker for the Trading Value automated trading system.

Pure functions and dataclasses for setup state management.
No side effects, no API calls, no mutation.

Implements spec v2 section 11 (strategy details) and
state machine design section 5.5 / 9.2 (SetupState transitions).
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from .indicators import (
    check_hammer,
    check_support_hold,
    check_upper_rejection,
    compute_zone_width,
    make_zone,
    merge_overlapping_zones,
)
from .mode import ModeResult
from .models import (
    ModeState,
    SetupState,
    Side,
    Timeframe,
    TimeframeSnapshot,
    Zone,
)
from .regime import RegimeSnapshot


# ---------------------------------------------------------------------------
# 1. SetupContext
# ---------------------------------------------------------------------------


@dataclass
class SetupContext:
    """Mutable context for an active setup being tracked."""

    setup_version: int
    strategy: str  # "TREND_LONG", "PULLBACK_LONG", "REBOUND_SHORT"
    state: SetupState  # current setup state
    watch_zones: list[Zone]  # zones being monitored
    active_zone: Zone | None  # zone that was touched
    side: Side  # LONG or SHORT
    entry_price: float | None  # planned entry
    stop_price: float | None  # planned stop
    tp1_price: float | None
    tp2_price: float | None
    tp3_price: float | None  # for PULLBACK_LONG
    rr_to_tp1: float | None
    invalidation_reason: str | None


# ---------------------------------------------------------------------------
# 2. Watch zone selection per strategy (spec v2 section 11)
# ---------------------------------------------------------------------------


def select_watch_zones_trend_long(
    snapshots: dict[Timeframe, TimeframeSnapshot],
    atr_15m: float,
) -> list[Zone]:
    """Section 11.1: Watch zones for TREND_LONG = [30m Tenkan, 1h Tenkan]."""
    snap_30m = snapshots[Timeframe.M30]
    snap_1h = snapshots[Timeframe.H1]
    current_price = snap_30m.close
    width = compute_zone_width(current_price, atr_15m)

    zones = [
        make_zone("trend_30m_tenkan", snap_30m.tenkan, width, Timeframe.M30, "30m_Tenkan"),
        make_zone("trend_1h_tenkan", snap_1h.tenkan, width, Timeframe.H1, "1h_Tenkan"),
    ]
    return merge_overlapping_zones(zones)


def select_watch_zones_pullback_long(
    snapshots: dict[Timeframe, TimeframeSnapshot],
    atr_15m: float,
) -> list[Zone]:
    """Section 11.2: Priority: 30m Kijun, 1h Kijun, 30m POC, 30m VAL, 1h POC, 1h VAL, 4h Kijun."""
    snap_30m = snapshots[Timeframe.M30]
    snap_1h = snapshots[Timeframe.H1]
    snap_4h = snapshots[Timeframe.H4]
    current_price = snap_30m.close
    width = compute_zone_width(current_price, atr_15m)

    candidates = [
        ("pb_30m_kijun", snap_30m.kijun, Timeframe.M30, "30m_Kijun"),
        ("pb_1h_kijun", snap_1h.kijun, Timeframe.H1, "1h_Kijun"),
        ("pb_30m_poc", snap_30m.poc, Timeframe.M30, "30m_POC"),
        ("pb_30m_val", snap_30m.val, Timeframe.M30, "30m_VAL"),
        ("pb_1h_poc", snap_1h.poc, Timeframe.H1, "1h_POC"),
        ("pb_1h_val", snap_1h.val, Timeframe.H1, "1h_VAL"),
        ("pb_4h_kijun", snap_4h.kijun, Timeframe.H4, "4h_Kijun"),
    ]

    zones = [
        make_zone(zid, level, width, tf, source)
        for zid, level, tf, source in candidates
    ]
    return merge_overlapping_zones(zones)


def select_watch_zones_rebound_short(
    snapshots: dict[Timeframe, TimeframeSnapshot],
    atr_15m: float,
) -> list[Zone]:
    """Section 11.3: Priority: 15m Kijun, 30m Tenkan, 30m Kijun, 30m VAH, 30m POC, 1h Tenkan."""
    snap_30m = snapshots.get(Timeframe.M30)
    snap_15m = snapshots.get(Timeframe.M15)
    snap_1h = snapshots.get(Timeframe.H1)
    if snap_30m is None:
        return []
    current_price = snap_30m.close
    width = compute_zone_width(current_price, atr_15m)

    candidates = []
    if snap_15m is not None:
        candidates.append(("rb_15m_kijun", snap_15m.kijun, Timeframe.M15, "15m_Kijun"))
    candidates.extend([
        ("rb_30m_tenkan", snap_30m.tenkan, Timeframe.M30, "30m_Tenkan"),
        ("rb_30m_kijun", snap_30m.kijun, Timeframe.M30, "30m_Kijun"),
        ("rb_30m_vah", snap_30m.vah, Timeframe.M30, "30m_VAH"),
        ("rb_30m_poc", snap_30m.poc, Timeframe.M30, "30m_POC"),
    ])
    if snap_1h is not None:
        candidates.append(("rb_1h_tenkan", snap_1h.tenkan, Timeframe.H1, "1h_Tenkan"))

    zones = [
        make_zone(zid, level, width, tf, source)
        for zid, level, tf, source in candidates
    ]
    return merge_overlapping_zones(zones)


def select_watch_zones(
    strategy: str,
    snapshots: dict[Timeframe, TimeframeSnapshot],
    atr_15m: float,
) -> list[Zone]:
    """Route to the correct zone selector based on strategy."""
    if strategy == "TREND_LONG":
        return select_watch_zones_trend_long(snapshots, atr_15m)
    if strategy == "PULLBACK_LONG":
        return select_watch_zones_pullback_long(snapshots, atr_15m)
    if strategy == "REBOUND_SHORT":
        return select_watch_zones_rebound_short(snapshots, atr_15m)
    return []


# ---------------------------------------------------------------------------
# 3. Zone touch detection
# ---------------------------------------------------------------------------


def check_zone_touch(current_price: float, zones: list[Zone]) -> Zone | None:
    """Check if current price is within any watch zone. Returns the touched zone or None."""
    for zone in zones:
        if zone.low <= current_price <= zone.high:
            return zone
    return None


# ---------------------------------------------------------------------------
# 4. Trigger confirmation per strategy (spec v2 section 11 entry sequences)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TriggerInput:
    """Data needed to evaluate trigger conditions."""

    # 5m bar data
    close_5m: float
    high_5m: float
    low_5m: float
    open_5m: float
    volume_5m: float
    prev_5m_high: float
    prev_5m_low: float
    prev_5m_highs_3: list[float]  # last 3 5m highs (for PULLBACK_LONG)
    avg_volume_5m_5: float  # average of last 5 5m volumes
    # 15m bar data
    close_15m: float
    high_15m: float
    low_15m: float
    open_15m: float
    volume_15m: float
    prev_volume_15m: float
    # 30m close
    close_30m: float
    # Rebound short specific
    rebound_volume_5m: float | None = None  # volume during bounce
    decline_drop: float | None = None  # prior drop magnitude
    retracement_pct: float | None = None  # current retracement level


def check_trigger_trend_long(trigger: TriggerInput, zone: Zone) -> tuple[bool, str]:
    """Section 11.1 TREND_LONG entry sequence:
    1. Price touched zone (already checked)
    2. 5m: lower wick OR prev low not broken
    3. Same/next 5m close breaks prev 5m high
    4. Latest 15m close >= zone mid
    5. Latest 30m close > zone low
    6. Trigger 5m volume >= avg of last 5
    Returns (confirmed, reason).
    """
    # Step 2: lower wick check OR prev low not broken
    lower_wick = min(trigger.close_5m, trigger.open_5m) - trigger.low_5m
    body = abs(trigger.close_5m - trigger.open_5m)
    has_lower_wick = lower_wick > body if body > 0 else lower_wick > 0
    prev_low_not_broken = trigger.low_5m >= trigger.prev_5m_low

    if not has_lower_wick and not prev_low_not_broken:
        return (False, "no_lower_wick_and_prev_low_broken")

    # Step 3: 5m close breaks prev 5m high
    if trigger.close_5m <= trigger.prev_5m_high:
        return (False, "5m_close_did_not_break_prev_high")

    # Step 4: 15m close >= zone mid
    if trigger.close_15m < zone.mid:
        return (False, "15m_close_below_zone_mid")

    # Step 5: 30m close > zone low
    if trigger.close_30m <= zone.low:
        return (False, "30m_close_not_above_zone_low")

    # Step 6: volume filter
    if trigger.volume_5m < trigger.avg_volume_5m_5:
        return (False, "5m_volume_below_average")

    return (True, "trend_long_trigger_confirmed")


def check_trigger_pullback_long(trigger: TriggerInput, zone: Zone) -> tuple[bool, str]:
    """Section 11.2 PULLBACK_LONG entry sequence:
    1. Zone reached (already checked)
    2. 15m support_hold or hammer
    3. Next 5m close > max of last 3 5m highs
    4. Trigger 15m volume > prev 15m volume
    5. Latest 30m close >= zone mid
    Returns (confirmed, reason).
    """
    # Step 2: 15m support_hold OR hammer
    has_support = check_support_hold(
        low=trigger.low_15m,
        close=trigger.close_15m,
        open_price=trigger.open_15m,
        zone_low=zone.low,
        zone_mid=zone.mid,
    )
    has_hammer = check_hammer(
        open_price=trigger.open_15m,
        high=trigger.high_15m,
        low=trigger.low_15m,
        close=trigger.close_15m,
    )
    if not has_support and not has_hammer:
        return (False, "no_15m_support_hold_or_hammer")

    # Step 3: 5m close > max of last 3 5m highs
    if not trigger.prev_5m_highs_3:
        return (False, "no_prev_5m_highs_data")
    max_prev_3_highs = max(trigger.prev_5m_highs_3)
    if trigger.close_5m <= max_prev_3_highs:
        return (False, "5m_close_did_not_break_prev_3_highs")

    # Step 4: 15m volume > prev 15m volume
    if trigger.volume_15m <= trigger.prev_volume_15m:
        return (False, "15m_volume_not_increasing")

    # Step 5: 30m close >= zone mid
    if trigger.close_30m < zone.mid:
        return (False, "30m_close_below_zone_mid")

    return (True, "pullback_long_trigger_confirmed")


def check_trigger_rebound_short(
    trigger: TriggerInput, zone: Zone, atr_30m: float, current_price: float,
) -> tuple[bool, str]:
    """Section 11.3 REBOUND_SHORT entry sequence:
    1. Prior decline >= max(ATR_30m * 1.5, price * 0.005), retracement 38.2-61.8%
    2. 5m upper_rejection at zone
    3. Same/next 5m close breaks prev 5m low
    4. Latest 15m close < zone mid
    5. Decline 5m volume > rebound 5m volume
    Returns (confirmed, reason).
    """
    # Step 1: prior decline check
    min_decline = max(atr_30m * 1.5, current_price * 0.005)
    if trigger.decline_drop is None or trigger.decline_drop < min_decline:
        return (False, f"prior_decline_insufficient: need>={min_decline:.4f}")

    if trigger.retracement_pct is None:
        return (False, "no_retracement_data")
    if not (0.382 <= trigger.retracement_pct <= 0.618):
        return (False, f"retracement_out_of_range: {trigger.retracement_pct:.3f}")

    # Step 2: 5m upper_rejection at zone
    has_rejection = check_upper_rejection(
        high=trigger.high_5m,
        close=trigger.close_5m,
        open_price=trigger.open_5m,
        zone_high=zone.high,
        zone_mid=zone.mid,
    )
    if not has_rejection:
        return (False, "no_5m_upper_rejection")

    # Step 3: 5m close breaks prev 5m low
    if trigger.close_5m >= trigger.prev_5m_low:
        return (False, "5m_close_did_not_break_prev_low")

    # Step 4: 15m close < zone mid
    if trigger.close_15m >= zone.mid:
        return (False, "15m_close_not_below_zone_mid")

    # Step 5: decline volume > rebound volume
    if trigger.rebound_volume_5m is None:
        return (False, "no_rebound_volume_data")
    if trigger.volume_5m <= trigger.rebound_volume_5m:
        return (False, "decline_volume_not_greater_than_rebound")

    return (True, "rebound_short_trigger_confirmed")


# ---------------------------------------------------------------------------
# 5. Stop and target price computation (spec v2 section 11)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StopTarget:
    """Computed stop and target prices."""

    stop_price: float
    tp1_price: float | None
    tp2_price: float | None
    tp3_price: float | None  # PULLBACK_LONG only
    rr_to_tp1: float


def _first_above(entry: float, candidates: list[float]) -> float | None:
    """Return the nearest candidate strictly above entry, or None."""
    valid = sorted([c for c in candidates if c > entry])
    return valid[0] if valid else None


def _first_below(entry: float, candidates: list[float]) -> float | None:
    """Return the nearest candidate strictly below entry, or None."""
    valid = sorted([c for c in candidates if c < entry], reverse=True)
    return valid[0] if valid else None


def _compute_rr(entry: float, stop: float, target: float) -> float:
    """Compute risk-reward ratio. Returns 0.0 if risk is zero."""
    risk = abs(entry - stop)
    if risk == 0:
        return 0.0
    reward = abs(target - entry)
    return reward / risk


def compute_stop_target_trend_long(
    entry_price: float,
    zone: Zone,
    swing_low_5m: float,
    atr_5m: float,
    atr_15m: float,
    recent_swing_high: float,
    vah_30m: float,
    vah_1h: float,
    fib_extensions: list[float] | None,
) -> StopTarget:
    """Section 11.1: Stop = min(swing_low - 0.2*ATR_5m, zone.low - 0.2*ATR_15m)
    tp1 = nearest resistance above entry (swing high or 30m VAH)
    tp2 = next resistance (1h VAH or fib extension)
    """
    stop = min(swing_low_5m - 0.2 * atr_5m, zone.low - 0.2 * atr_15m)

    # tp1 candidates: recent swing high, 30m VAH
    tp1_candidates = [recent_swing_high, vah_30m]
    # tp2 candidates: 1h VAH + fib extensions
    tp2_candidates = [vah_1h]
    if fib_extensions:
        tp2_candidates.extend(fib_extensions)

    # All targets must be above entry for longs
    tp1 = _first_above(entry_price, tp1_candidates)
    # tp2 must be above tp1 (or above entry if no tp1)
    tp2_base = tp1 if tp1 is not None else entry_price
    tp2 = _first_above(tp2_base, tp2_candidates)

    rr = _compute_rr(entry_price, stop, tp1) if tp1 is not None else 0.0

    return StopTarget(
        stop_price=stop,
        tp1_price=tp1,
        tp2_price=tp2,
        tp3_price=None,
        rr_to_tp1=rr,
    )


def compute_stop_target_pullback_long(
    entry_price: float,
    zone: Zone,
    atr_15m: float,
    tenkan_30m: float,
    kijun_30m: float,
    tenkan_1h: float,
    kijun_1h: float,
    poc_1h: float,
) -> StopTarget:
    """Section 11.2: Stop = zone.low - 0.2*ATR_15m
    tp candidates: 30m Tenkan, 30m Kijun, 1h Tenkan, 1h Kijun, 1h POC
    """
    stop = zone.low - 0.2 * atr_15m

    all_candidates = [tenkan_30m, kijun_30m, tenkan_1h, kijun_1h, poc_1h]
    # Only values above entry are valid for longs
    valid = sorted([c for c in all_candidates if c > entry_price])

    tp1 = valid[0] if len(valid) >= 1 else None
    tp2 = valid[1] if len(valid) >= 2 else None
    tp3 = valid[2] if len(valid) >= 3 else None

    rr = _compute_rr(entry_price, stop, tp1) if tp1 is not None else 0.0

    return StopTarget(
        stop_price=stop,
        tp1_price=tp1,
        tp2_price=tp2,
        tp3_price=tp3,
        rr_to_tp1=rr,
    )


def compute_stop_target_rebound_short(
    entry_price: float,
    zone: Zone,
    atr_15m: float,
    recent_low: float,
    poc_30m: float,
    val_30m: float,
    val_1h: float,
    kijun_4h: float,
) -> StopTarget:
    """Section 11.3: Stop = zone.high + 0.2*ATR_15m
    tp candidates: recent low, 30m POC, 30m VAL, 1h VAL, 4h Kijun
    """
    stop = zone.high + 0.2 * atr_15m

    all_candidates = [recent_low, poc_30m, val_30m, val_1h, kijun_4h]
    # Only values below entry are valid for shorts
    valid = sorted([c for c in all_candidates if c < entry_price], reverse=True)

    tp1 = valid[0] if len(valid) >= 1 else None
    tp2 = valid[1] if len(valid) >= 2 else None

    rr = _compute_rr(entry_price, stop, tp1) if tp1 is not None else 0.0

    return StopTarget(
        stop_price=stop,
        tp1_price=tp1,
        tp2_price=tp2,
        tp3_price=None,
        rr_to_tp1=rr,
    )


# ---------------------------------------------------------------------------
# 6. Invalidation check (spec v2 section 11 invalidation per strategy)
# ---------------------------------------------------------------------------


def check_invalidation_trend_long(
    close_15m: float,
    close_1h: float,
    zone: Zone,
    upper_support_low: float,
    m30_below_cloud: bool,
    m15_below_cloud_tk_bear: bool,
    m5_below_cloud_tk_bear: bool,
) -> tuple[bool, str]:
    """Section 11.1 invalidation:
    - 15m close < zone.low
    - 1h close < upper support
    - 30m+15m+5m all below_cloud + TK bearish
    """
    if close_15m < zone.low:
        return (True, "15m_close_below_zone_low")

    if close_1h < upper_support_low:
        return (True, "1h_close_below_upper_support")

    if m30_below_cloud and m15_below_cloud_tk_bear and m5_below_cloud_tk_bear:
        return (True, "30m_15m_5m_all_bearish_aligned")

    return (False, "")


def check_invalidation_pullback_long(
    close_15m: float,
    close_1h: float,
    zone: Zone,
    upper_support_low: float,
) -> tuple[bool, str]:
    """Section 11.2 invalidation:
    - 15m close < zone.low
    - 1h close < upper support
    """
    if close_15m < zone.low:
        return (True, "15m_close_below_zone_low")

    if close_1h < upper_support_low:
        return (True, "1h_close_below_upper_support")

    return (False, "")


@dataclass(frozen=True)
class InvalidationInput:
    """Data needed to evaluate invalidation conditions per strategy."""

    close_15m: float
    close_1h: float
    zone: Zone | None
    upper_support_low: float | None  # for trend/pullback long
    m30_below_cloud: bool  # for trend long
    m15_below_cloud_tk_bear: bool  # for trend long
    m5_below_cloud_tk_bear: bool  # for trend long
    m30_above_cloud_tk_bull: bool  # for rebound short
    h1_above_poc_or_vah_2bars: bool  # for rebound short


def check_invalidation_rebound_short(
    close_15m: float,
    zone: Zone,
    m30_above_cloud_tk_bull: bool,
    h1_above_poc_or_vah_2bars: bool,
) -> tuple[bool, str]:
    """Section 11.3 invalidation:
    - 15m close > zone.high
    - 30m above cloud + TK bullish
    - 1h above POC/VAH for 2 consecutive bars
    """
    if close_15m > zone.high:
        return (True, "15m_close_above_zone_high")

    if m30_above_cloud_tk_bull:
        return (True, "30m_above_cloud_tk_bullish")

    if h1_above_poc_or_vah_2bars:
        return (True, "1h_above_poc_vah_2_consecutive_bars")

    return (False, "")


# ---------------------------------------------------------------------------
# 7. SetupState transition evaluator
# ---------------------------------------------------------------------------

# Minimum RR threshold from config/default.toml [order] min_rr
_MIN_RR = 1.5


def evaluate_setup_transition(
    ctx: SetupContext,
    current_price: float,
    trigger_input: TriggerInput | None,
    snapshots: dict[Timeframe, TimeframeSnapshot],
    mode_result: ModeResult | None = None,
    invalidation_input: InvalidationInput | None = None,
) -> SetupContext:
    """Evaluate and apply setup state transitions.

    Per section 9.2:
    - IDLE -> WAIT_ZONE_TOUCH: when mode allows trading + watch zones created
    - WAIT_ZONE_TOUCH -> WAIT_TRIGGER_CONFIRM: zone touched
    - WAIT_TRIGGER_CONFIRM -> ENTRY_READY: trigger confirmed + volume + RR >= 1.5
    - Any -> INVALIDATED: mode collapse, zone breach, event risk
    - INVALIDATED -> IDLE: new 30m evaluation cycle

    Returns updated SetupContext (new object, never mutates the input).
    """
    # --- INVALIDATED: preserve state, caller resets to IDLE on next 30m bar close ---
    if ctx.state == SetupState.INVALIDATED:
        return ctx

    # --- Check mode collapse (any state -> INVALIDATED) ---
    if mode_result is not None:
        if mode_result.mode == ModeState.MODE_NO_TRADE:
            return replace(
                ctx,
                state=SetupState.INVALIDATED,
                invalidation_reason=f"mode_collapse: {mode_result.blocked_reason}",
            )
        if ctx.strategy not in mode_result.allowed_setups:
            return replace(
                ctx,
                state=SetupState.INVALIDATED,
                invalidation_reason=f"strategy_not_allowed: {ctx.strategy}",
            )

    # --- Strategy-specific invalidation (WAIT_ZONE_TOUCH / WAIT_TRIGGER_CONFIRM / ENTRY_READY -> INVALIDATED) ---
    if ctx.state in (
        SetupState.WAIT_ZONE_TOUCH,
        SetupState.WAIT_TRIGGER_CONFIRM,
        SetupState.ENTRY_READY,
    ) and invalidation_input is not None:
        inv = invalidation_input
        zone = inv.zone or ctx.active_zone
        if zone is not None:
            invalidated = False
            inv_reason = ""

            if ctx.strategy == "TREND_LONG":
                if inv.upper_support_low is not None:
                    invalidated, inv_reason = check_invalidation_trend_long(
                        close_15m=inv.close_15m,
                        close_1h=inv.close_1h,
                        zone=zone,
                        upper_support_low=inv.upper_support_low,
                        m30_below_cloud=inv.m30_below_cloud,
                        m15_below_cloud_tk_bear=inv.m15_below_cloud_tk_bear,
                        m5_below_cloud_tk_bear=inv.m5_below_cloud_tk_bear,
                    )
            elif ctx.strategy == "PULLBACK_LONG":
                if inv.upper_support_low is not None:
                    invalidated, inv_reason = check_invalidation_pullback_long(
                        close_15m=inv.close_15m,
                        close_1h=inv.close_1h,
                        zone=zone,
                        upper_support_low=inv.upper_support_low,
                    )
            elif ctx.strategy == "REBOUND_SHORT":
                invalidated, inv_reason = check_invalidation_rebound_short(
                    close_15m=inv.close_15m,
                    zone=zone,
                    m30_above_cloud_tk_bull=inv.m30_above_cloud_tk_bull,
                    h1_above_poc_or_vah_2bars=inv.h1_above_poc_or_vah_2bars,
                )

            if invalidated:
                return replace(
                    ctx,
                    state=SetupState.INVALIDATED,
                    invalidation_reason=inv_reason,
                )

    # --- IDLE -> WAIT_ZONE_TOUCH ---
    if ctx.state == SetupState.IDLE:
        if mode_result is not None and mode_result.mode != ModeState.MODE_NO_TRADE:
            atr_15m = snapshots[Timeframe.M15].atr if Timeframe.M15 in snapshots else 0.0
            zones = select_watch_zones(ctx.strategy, snapshots, atr_15m)
            if zones:
                return replace(
                    ctx,
                    state=SetupState.WAIT_ZONE_TOUCH,
                    watch_zones=zones,
                    active_zone=None,
                )
        return ctx

    # --- WAIT_ZONE_TOUCH -> WAIT_TRIGGER_CONFIRM ---
    if ctx.state == SetupState.WAIT_ZONE_TOUCH:
        touched = check_zone_touch(current_price, ctx.watch_zones)
        if touched is not None:
            return replace(
                ctx,
                state=SetupState.WAIT_TRIGGER_CONFIRM,
                active_zone=touched,
            )
        return ctx

    # --- WAIT_TRIGGER_CONFIRM -> ENTRY_READY or INVALIDATED ---
    if ctx.state == SetupState.WAIT_TRIGGER_CONFIRM:
        zone = ctx.active_zone
        if zone is None:
            return replace(
                ctx,
                state=SetupState.INVALIDATED,
                invalidation_reason="active_zone_missing",
            )

        # Check trigger if input provided
        if trigger_input is not None:
            confirmed = False
            reason = ""

            if ctx.strategy == "TREND_LONG":
                confirmed, reason = check_trigger_trend_long(trigger_input, zone)
            elif ctx.strategy == "PULLBACK_LONG":
                confirmed, reason = check_trigger_pullback_long(trigger_input, zone)
            elif ctx.strategy == "REBOUND_SHORT":
                atr_30m = snapshots[Timeframe.M30].atr if Timeframe.M30 in snapshots else 0.0
                confirmed, reason = check_trigger_rebound_short(
                    trigger_input, zone, atr_30m, current_price,
                )

            if confirmed:
                # Use trigger close as entry price
                entry = trigger_input.close_5m

                # Check RR before transitioning to ENTRY_READY
                rr = ctx.rr_to_tp1
                if rr is not None and rr >= _MIN_RR:
                    return replace(
                        ctx,
                        state=SetupState.ENTRY_READY,
                        entry_price=entry,
                    )
                elif rr is not None:
                    return replace(
                        ctx,
                        state=SetupState.INVALIDATED,
                        invalidation_reason=f"rr_insufficient: {rr:.2f} < {_MIN_RR}",
                    )
                # rr not yet computed -- stay in WAIT_TRIGGER_CONFIRM
                # (caller should compute stop/target and set rr_to_tp1 first)
                return replace(ctx, entry_price=entry)

        return ctx

    # ENTRY_READY state -- no further transitions handled here
    return ctx
