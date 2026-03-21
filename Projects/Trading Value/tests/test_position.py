"""Tests for trading_value.core.position — Phase 3 module.

At least 20 tests covering:
- Position sizing
- Entry splits (50/30/20)
- Exit plan (30/30/40)
- Trailing stop per strategy
- Cooldown logic
- Max hold evaluation
- Risk budget checks
- Position invariants
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from trading_value.core.models import (
    GlobalState,
    Side,
    SymbolState,
    TradeLifecycleState,
    TradingState,
)
from trading_value.core.position import (
    EntrySplits,
    ExitPlan,
    MaxHoldAction,
    TrailingAction,
    check_risk_budget,
    compute_cooldown_end,
    compute_entry_splits,
    compute_exit_plan,
    compute_position_size,
    evaluate_max_hold,
    evaluate_trailing_pullback_long,
    evaluate_trailing_rebound_short,
    evaluate_trailing_trend_long,
    is_cooldown_active,
    validate_position_invariants,
)


_NOW = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# 1. Position sizing
# ---------------------------------------------------------------------------


def test_position_size_basic_formula():
    """TargetQty = (Balance * Risk%) / |Entry - Stop|"""
    qty = compute_position_size(
        account_balance=10000.0,
        risk_pct=0.01,     # 1%
        entry_price=100.0,
        stop_price=98.0,   # distance = 2
        min_qty=0.001,
    )
    # raw = (10000 * 0.01) / 2 = 50
    # floored to min_qty=0.001 => 50.0
    assert abs(qty - 50.0) < 1e-6


def test_position_size_rounds_down_to_min_qty():
    """Ensure floor-to-min_qty is applied (never rounds up)."""
    qty = compute_position_size(
        account_balance=10000.0,
        risk_pct=0.01,
        entry_price=100.0,
        stop_price=99.67,  # distance=0.33 => raw ~ 303.03
        min_qty=0.1,
    )
    # raw ~303.03 => floor(303.03 / 0.1) * 0.1 = 303.0
    assert qty == pytest.approx(303.0, abs=1e-6)


def test_position_size_zero_distance_returns_zero():
    """If entry == stop, distance is 0 → return 0."""
    qty = compute_position_size(
        account_balance=10000.0,
        risk_pct=0.01,
        entry_price=100.0,
        stop_price=100.0,  # zero distance
        min_qty=0.001,
    )
    assert qty == 0.0


# ---------------------------------------------------------------------------
# 2. Entry splits
# ---------------------------------------------------------------------------


def test_entry_splits_50_30_20_percentages():
    """Standard splits: 50 / 30 / 20 percent."""
    splits = compute_entry_splits(total_qty=1.0, min_qty=0.001)
    assert abs(splits.stage1_qty - 0.5) < 1e-6
    assert abs(splits.stage2_qty - 0.3) < 1e-6
    assert abs(splits.stage3_qty - 0.2) < 1e-6


def test_entry_splits_total_is_sum_of_stages():
    splits = compute_entry_splits(total_qty=1.0, min_qty=0.001)
    assert abs(splits.total_qty - (splits.stage1_qty + splits.stage2_qty + splits.stage3_qty)) < 1e-9


def test_entry_splits_small_qty_rounds_down():
    """With very small qty, each split should be floored, not rounded up."""
    splits = compute_entry_splits(total_qty=0.003, min_qty=0.001)
    # 0.003 * 0.5 = 0.0015 -> floor to 0.001
    # 0.003 * 0.3 = 0.0009 -> floor to 0.000 (rounds down)
    assert splits.stage1_qty >= 0.0
    # Ensure no split exceeds total
    assert splits.total_qty <= 0.003 + 1e-9


# ---------------------------------------------------------------------------
# 3. Exit plan
# ---------------------------------------------------------------------------


def test_exit_plan_30_30_40_correct():
    """Standard exit: tp1=30%, tp2=30%, trailing=40%."""
    plan = compute_exit_plan(total_qty=1.0, min_qty=0.001)
    assert abs(plan.tp1_qty - 0.3) < 1e-6
    assert abs(plan.tp2_qty - 0.3) < 1e-6
    assert abs(plan.trailing_qty - 0.4) < 1e-6


def test_exit_plan_total_is_sum():
    plan = compute_exit_plan(total_qty=1.0, min_qty=0.001)
    total = plan.tp1_qty + plan.tp2_qty + plan.trailing_qty
    assert abs(total - 1.0) < 1e-6


# ---------------------------------------------------------------------------
# 4. Trailing stop — TREND_LONG
# ---------------------------------------------------------------------------


def test_trailing_trend_long_5m_below_kijun_reduce_half():
    """5m close < 5m Kijun → reduce_half."""
    action = evaluate_trailing_trend_long(
        close_5m=99.0,   # below kijun 100
        kijun_5m=100.0,
        close_15m=102.0,  # above tenkan 101 (OK)
        tenkan_15m=101.0,
    )
    assert action.action == "reduce_half"


def test_trailing_trend_long_15m_below_tenkan_close_all():
    """15m close < 15m Tenkan → close_all (takes priority over 5m check)."""
    action = evaluate_trailing_trend_long(
        close_5m=99.0,
        kijun_5m=100.0,
        close_15m=99.0,   # below tenkan 100
        tenkan_15m=100.0,
    )
    assert action.action == "close_all"


def test_trailing_trend_long_both_above_hold():
    """5m >= Kijun and 15m >= Tenkan → hold."""
    action = evaluate_trailing_trend_long(
        close_5m=101.0,
        kijun_5m=100.0,
        close_15m=102.0,
        tenkan_15m=100.0,
    )
    assert action.action == "hold"


# ---------------------------------------------------------------------------
# 5. Trailing stop — PULLBACK_LONG
# ---------------------------------------------------------------------------


def test_trailing_pullback_long_15m_below_kijun_reduce_half():
    """15m close < 15m Kijun → reduce_half."""
    action = evaluate_trailing_pullback_long(
        close_15m=99.0,   # below kijun 100
        kijun_15m=100.0,
        close_30m=101.0,  # above zone_mid 100
        zone_mid=100.0,
    )
    assert action.action == "reduce_half"


def test_trailing_pullback_long_30m_below_zone_mid_close_all():
    """30m close < zone_mid → close_all."""
    action = evaluate_trailing_pullback_long(
        close_15m=101.0,
        kijun_15m=100.0,
        close_30m=99.0,   # below zone_mid 100
        zone_mid=100.0,
    )
    assert action.action == "close_all"


# ---------------------------------------------------------------------------
# 6. Trailing stop — REBOUND_SHORT
# ---------------------------------------------------------------------------


def test_trailing_rebound_short_5m_above_kijun_reduce_30pct():
    """5m close > 5m Kijun → reduce_30pct."""
    action = evaluate_trailing_rebound_short(
        close_5m=101.0,   # above kijun 100
        kijun_5m=100.0,
        close_15m=99.0,   # below tenkan 100 (OK, no stronger signal)
        tenkan_15m=100.0,
        kijun_15m=102.0,  # 15m still below kijun
    )
    assert action.action == "reduce_30pct"


def test_trailing_rebound_short_15m_above_tenkan_reduce_half():
    """15m close > 15m Tenkan → reduce_half."""
    action = evaluate_trailing_rebound_short(
        close_5m=99.0,
        kijun_5m=100.0,
        close_15m=101.0,  # above tenkan 100
        tenkan_15m=100.0,
        kijun_15m=103.0,  # 15m still below kijun
    )
    assert action.action == "reduce_half"


def test_trailing_rebound_short_15m_above_kijun_close_all():
    """15m close > 15m Kijun → close_all (highest priority)."""
    action = evaluate_trailing_rebound_short(
        close_5m=102.0,
        kijun_5m=100.0,
        close_15m=104.0,  # above kijun 103
        tenkan_15m=101.0,
        kijun_15m=103.0,
    )
    assert action.action == "close_all"


# ---------------------------------------------------------------------------
# 7. Cooldown
# ---------------------------------------------------------------------------


def test_cooldown_normal_is_1_hour():
    """Normal exit cooldown = 2 bars * 30m = 60 minutes."""
    exit_ts = _NOW
    end = compute_cooldown_end(exit_ts, was_stop_loss=False, normal_bars=2, bar_minutes=30)
    assert end == exit_ts + timedelta(hours=1)


def test_cooldown_stop_loss_is_2_hours():
    """Stop-loss exit cooldown = 4 bars * 30m = 120 minutes."""
    exit_ts = _NOW
    end = compute_cooldown_end(exit_ts, was_stop_loss=True, stop_loss_bars=4, bar_minutes=30)
    assert end == exit_ts + timedelta(hours=2)


def test_cooldown_active_check():
    """is_cooldown_active returns True during and False after cooldown."""
    exit_ts = _NOW
    end = exit_ts + timedelta(hours=1)
    assert is_cooldown_active(end, exit_ts + timedelta(minutes=30)) is True
    assert is_cooldown_active(end, exit_ts + timedelta(hours=1, seconds=1)) is False


# ---------------------------------------------------------------------------
# 8. Max hold
# ---------------------------------------------------------------------------


def test_max_hold_under_48_bars_hold():
    """Under 48 bars → hold regardless of PnL."""
    entry = _NOW
    current = entry + timedelta(hours=10)  # 20 bars (30m each)
    action = evaluate_max_hold(entry, current, unrealized_pnl_r=0.1, max_bars=48)
    assert action.action == "hold"


def test_max_hold_over_48_bars_low_pnl_close_all():
    """Over 48 bars + PnL < min_profit_r → close_all."""
    entry = _NOW
    current = entry + timedelta(hours=25)  # 50 bars
    action = evaluate_max_hold(entry, current, unrealized_pnl_r=0.1, max_bars=48, min_profit_r=0.5)
    assert action.action == "close_all"


def test_max_hold_over_48_bars_high_pnl_tighten_trailing():
    """Over 48 bars + PnL >= min_profit_r → tighten_trailing."""
    entry = _NOW
    current = entry + timedelta(hours=25)  # 50 bars
    action = evaluate_max_hold(entry, current, unrealized_pnl_r=1.0, max_bars=48, min_profit_r=0.5)
    assert action.action == "tighten_trailing"


# ---------------------------------------------------------------------------
# 9. Risk budget
# ---------------------------------------------------------------------------


def _make_global_state(total_risk: float = 0.0) -> GlobalState:
    gs = GlobalState(engine="READY", risk_gate="ALLOW")
    gs.total_risk_exposure_pct = total_risk
    return gs


def test_risk_budget_within_limits_allowed():
    gs = _make_global_state(total_risk=0.003)
    allowed, reason = check_risk_budget(
        global_state=gs,
        candidate_risk_pct=0.002,
        symbol_risk_pct=0.001,
        max_total=0.01,
        max_symbol=0.005,
    )
    assert allowed is True


def test_risk_budget_exceeds_total_blocked():
    gs = _make_global_state(total_risk=0.009)
    allowed, reason = check_risk_budget(
        global_state=gs,
        candidate_risk_pct=0.003,  # 0.009 + 0.003 = 0.012 > 0.01
        symbol_risk_pct=0.0,
        max_total=0.01,
        max_symbol=0.005,
    )
    assert allowed is False
    assert "total risk" in reason


def test_risk_budget_exceeds_symbol_blocked():
    gs = _make_global_state(total_risk=0.001)
    allowed, reason = check_risk_budget(
        global_state=gs,
        candidate_risk_pct=0.004,  # symbol: 0.002 + 0.004 = 0.006 > 0.005
        symbol_risk_pct=0.002,
        max_total=0.01,
        max_symbol=0.005,
    )
    assert allowed is False
    assert "symbol risk" in reason


# ---------------------------------------------------------------------------
# 10. Position invariants
# ---------------------------------------------------------------------------


def _make_open_state(
    symbol: str = "ETHUSDT",
    lifecycle: TradeLifecycleState = TradeLifecycleState.OPEN_STAGE0,
    side: Side = Side.LONG,
    stop_price: float | None = 95.0,
    setup_version: int = 1,
) -> SymbolState:
    s = SymbolState(symbol=symbol)
    s.lifecycle = lifecycle
    s.side = side
    s.stop_price = stop_price
    s.setup_version = setup_version
    return s


def test_invariants_open_without_stop_violation():
    """OPEN_STAGE0 without stop_price → violation."""
    state = _make_open_state(stop_price=None)
    violations = validate_position_invariants(state)
    assert len(violations) > 0
    assert any("stop_price" in v for v in violations)


def test_invariants_flat_with_no_stop_valid():
    """FLAT state with side=NONE and no stop → no violations."""
    state = SymbolState(symbol="ETHUSDT")
    state.lifecycle = TradeLifecycleState.FLAT
    state.side = Side.NONE
    state.stop_price = None
    violations = validate_position_invariants(state)
    assert len(violations) == 0
