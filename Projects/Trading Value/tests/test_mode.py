"""Tests for trading_value.core.mode — spec v2 §10 matrix and §12 entry filters.

Tests all 11 rows of the strategy matrix and all 8 entry filters.
"""
from __future__ import annotations

import pytest

from trading_value.core.mode import (
    EntryFilterInput,
    ModeResult,
    check_entry_filters,
    evaluate_mode,
    select_mode,
)
from trading_value.core.models import ModeState, RegimeState
from trading_value.core.regime import H1Bias, M30Bias, RegimeSnapshot


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_regime(
    htf: RegimeState = RegimeState.HTF_BULLISH,
    h1: H1Bias = H1Bias.H1_BULLISH,
    m30: M30Bias = M30Bias.M30_BULLISH,
) -> RegimeSnapshot:
    return RegimeSnapshot(htf=htf, h1=h1, m30=m30)


def make_filter_input(
    is_box_center: bool = False,
    is_abnormal_volatility: bool = False,
    rr_to_tp1: float = 2.0,
    volume_30m: float = 1000.0,
    volume_sma_20: float = 1000.0,
    is_high_impact_event: bool = False,
    has_position_same_symbol: bool = False,
    total_risk_exposure_pct: float = 0.0,
    pending_risk_pct: float = 0.0,
    candidate_risk_pct: float = 0.3,
    max_total_risk: float = 1.0,
    max_symbol_risk: float = 0.5,
    symbol_risk_exposure_pct: float = 0.0,
    consecutive_losses: int = 0,
    daily_loss_r: float = 0.0,
    weekly_loss_exceeded: bool = False,
    min_rr: float = 1.5,
    volume_low_factor: float = 0.6,
) -> EntryFilterInput:
    return EntryFilterInput(
        is_box_center=is_box_center,
        is_abnormal_volatility=is_abnormal_volatility,
        rr_to_tp1=rr_to_tp1,
        volume_30m=volume_30m,
        volume_sma_20=volume_sma_20,
        is_high_impact_event=is_high_impact_event,
        has_position_same_symbol=has_position_same_symbol,
        total_risk_exposure_pct=total_risk_exposure_pct,
        pending_risk_pct=pending_risk_pct,
        candidate_risk_pct=candidate_risk_pct,
        max_total_risk=max_total_risk,
        max_symbol_risk=max_symbol_risk,
        symbol_risk_exposure_pct=symbol_risk_exposure_pct,
        consecutive_losses=consecutive_losses,
        daily_loss_r=daily_loss_r,
        weekly_loss_exceeded=weekly_loss_exceeded,
        min_rr=min_rr,
        volume_low_factor=volume_low_factor,
    )


# ---------------------------------------------------------------------------
# 1. Strategy matrix rows (spec v2 §10)
# ---------------------------------------------------------------------------

class TestStrategyMatrix:

    # Row 1: BULLISH | H1_BULL | M30_BULL → TREND_LONG
    def test_bullish_h1bull_m30bull_trend_long(self):
        result = select_mode(make_regime(
            RegimeState.HTF_BULLISH, H1Bias.H1_BULLISH, M30Bias.M30_BULLISH
        ))
        assert result.mode == ModeState.MODE_TREND_LONG
        assert "TREND_LONG" in result.allowed_setups
        assert result.enhanced_conditions is None

    # Row 2: BULLISH | H1_BULL | M30_NEUTRAL → TREND_LONG + enhanced
    def test_bullish_h1bull_m30neutral_trend_long_enhanced(self):
        result = select_mode(make_regime(
            RegimeState.HTF_BULLISH, H1Bias.H1_BULLISH, M30Bias.M30_NEUTRAL
        ))
        assert result.mode == ModeState.MODE_TREND_LONG
        assert "TREND_LONG" in result.allowed_setups
        assert result.enhanced_conditions is not None
        assert result.enhanced_conditions.get("min_volume_factor") == 1.5
        assert result.enhanced_conditions.get("min_rr") == 2.0

    # Row 3: BULLISH | H1_BULL | M30_BEAR → PULLBACK_LONG
    def test_bullish_h1bull_m30bear_pullback_long(self):
        result = select_mode(make_regime(
            RegimeState.HTF_BULLISH, H1Bias.H1_BULLISH, M30Bias.M30_BEARISH
        ))
        assert result.mode == ModeState.MODE_PULLBACK_LONG
        assert "PULLBACK_LONG" in result.allowed_setups

    # Row 4: BULLISH | H1_NEUTRAL | M30_BULL → TREND_LONG
    def test_bullish_h1neutral_m30bull_trend_long(self):
        result = select_mode(make_regime(
            RegimeState.HTF_BULLISH, H1Bias.H1_NEUTRAL, M30Bias.M30_BULLISH
        ))
        assert result.mode == ModeState.MODE_TREND_LONG
        assert "TREND_LONG" in result.allowed_setups

    # Row 5: BULLISH | H1_NEUTRAL | M30_NEUTRAL → PULLBACK_LONG
    def test_bullish_h1neutral_m30neutral_pullback_long(self):
        result = select_mode(make_regime(
            RegimeState.HTF_BULLISH, H1Bias.H1_NEUTRAL, M30Bias.M30_NEUTRAL
        ))
        assert result.mode == ModeState.MODE_PULLBACK_LONG
        assert "PULLBACK_LONG" in result.allowed_setups

    # Row 6: BULLISH | H1_NEUTRAL | M30_BEAR → PULLBACK_LONG
    def test_bullish_h1neutral_m30bear_pullback_long(self):
        result = select_mode(make_regime(
            RegimeState.HTF_BULLISH, H1Bias.H1_NEUTRAL, M30Bias.M30_BEARISH
        ))
        assert result.mode == ModeState.MODE_PULLBACK_LONG
        assert "PULLBACK_LONG" in result.allowed_setups

    # Row 7: BULLISH | H1_BEAR | M30_BEAR → REBOUND_SHORT (reduced risk)
    def test_bullish_h1bear_m30bear_rebound_short_reduced(self):
        result = select_mode(make_regime(
            RegimeState.HTF_BULLISH, H1Bias.H1_BEARISH, M30Bias.M30_BEARISH
        ))
        assert result.mode == ModeState.MODE_REBOUND_SHORT
        assert "REBOUND_SHORT" in result.allowed_setups
        assert result.enhanced_conditions is not None
        assert result.enhanced_conditions.get("reduced_risk") is True

    # Row 8: BULLISH | H1_BEAR | M30_NEUTRAL → NO_TRADE
    def test_bullish_h1bear_m30neutral_no_trade(self):
        result = select_mode(make_regime(
            RegimeState.HTF_BULLISH, H1Bias.H1_BEARISH, M30Bias.M30_NEUTRAL
        ))
        assert result.mode == ModeState.MODE_NO_TRADE
        assert result.allowed_setups == []

    # Row 9: BULLISH | H1_BEAR | M30_BULL → NO_TRADE
    def test_bullish_h1bear_m30bull_no_trade(self):
        result = select_mode(make_regime(
            RegimeState.HTF_BULLISH, H1Bias.H1_BEARISH, M30Bias.M30_BULLISH
        ))
        assert result.mode == ModeState.MODE_NO_TRADE
        assert result.allowed_setups == []

    # Row 10: NEUTRAL | H1_BEAR | M30_BEAR → REBOUND_SHORT
    def test_neutral_h1bear_m30bear_rebound_short(self):
        result = select_mode(make_regime(
            RegimeState.HTF_NEUTRAL, H1Bias.H1_BEARISH, M30Bias.M30_BEARISH
        ))
        assert result.mode == ModeState.MODE_REBOUND_SHORT
        assert "REBOUND_SHORT" in result.allowed_setups

    # Row 11: NEUTRAL | other → NO_TRADE
    def test_neutral_other_no_trade(self):
        result = select_mode(make_regime(
            RegimeState.HTF_NEUTRAL, H1Bias.H1_NEUTRAL, M30Bias.M30_NEUTRAL
        ))
        assert result.mode == ModeState.MODE_NO_TRADE

    # Row 12: BEARISH | M30_BEAR → REBOUND_SHORT
    def test_bearish_m30bear_rebound_short(self):
        result = select_mode(make_regime(
            RegimeState.HTF_BEARISH, H1Bias.H1_BEARISH, M30Bias.M30_BEARISH
        ))
        assert result.mode == ModeState.MODE_REBOUND_SHORT
        assert "REBOUND_SHORT" in result.allowed_setups

    # Row 13: BEARISH | M30_NEUTRAL → REBOUND_SHORT
    def test_bearish_m30neutral_rebound_short(self):
        result = select_mode(make_regime(
            RegimeState.HTF_BEARISH, H1Bias.H1_NEUTRAL, M30Bias.M30_NEUTRAL
        ))
        assert result.mode == ModeState.MODE_REBOUND_SHORT

    # Row 14: BEARISH | M30_BULL → NO_TRADE
    def test_bearish_m30bull_no_trade(self):
        result = select_mode(make_regime(
            RegimeState.HTF_BEARISH, H1Bias.H1_BULLISH, M30Bias.M30_BULLISH
        ))
        assert result.mode == ModeState.MODE_NO_TRADE
        assert result.allowed_setups == []


# ---------------------------------------------------------------------------
# 2. Enhanced / reduced risk conditions
# ---------------------------------------------------------------------------

class TestEnhancedAndReducedRisk:

    def test_enhanced_conditions_recorded(self):
        """BULLISH + H1_BULLISH + M30_NEUTRAL → enhanced_conditions has min_volume_factor and min_rr."""
        result = select_mode(make_regime(
            RegimeState.HTF_BULLISH, H1Bias.H1_BULLISH, M30Bias.M30_NEUTRAL
        ))
        assert result.enhanced_conditions is not None
        assert "min_volume_factor" in result.enhanced_conditions
        assert "min_rr" in result.enhanced_conditions

    def test_reduced_risk_signal(self):
        """BULLISH + H1_BEARISH + M30_BEARISH → reduced_risk=True and max_risk_pct present."""
        result = select_mode(make_regime(
            RegimeState.HTF_BULLISH, H1Bias.H1_BEARISH, M30Bias.M30_BEARISH
        ))
        assert result.enhanced_conditions is not None
        assert result.enhanced_conditions.get("reduced_risk") is True
        assert "max_risk_pct" in result.enhanced_conditions


# ---------------------------------------------------------------------------
# 3. Entry filters (spec v2 §12)
# ---------------------------------------------------------------------------

class TestEntryFilters:

    def test_filter_all_pass(self):
        fi = make_filter_input()
        blocked, reason = check_entry_filters(fi)
        assert blocked is False
        assert reason == ""

    def test_filter_box_center_blocks(self):
        fi = make_filter_input(is_box_center=True)
        blocked, reason = check_entry_filters(fi)
        assert blocked is True
        assert "box_center" in reason

    def test_filter_abnormal_volatility_blocks(self):
        fi = make_filter_input(is_abnormal_volatility=True)
        blocked, reason = check_entry_filters(fi)
        assert blocked is True
        assert "abnormal_volatility" in reason

    def test_filter_rr_insufficient_blocks(self):
        fi = make_filter_input(rr_to_tp1=1.0, min_rr=1.5)
        blocked, reason = check_entry_filters(fi)
        assert blocked is True
        assert "rr_insufficient" in reason

    def test_filter_rr_exactly_at_min_passes(self):
        """RR == min_rr: not strictly <, so should pass."""
        fi = make_filter_input(rr_to_tp1=1.5, min_rr=1.5)
        blocked, _ = check_entry_filters(fi)
        assert blocked is False

    def test_filter_low_volume_blocks(self):
        """volume_30m < volume_sma_20 * 0.6."""
        fi = make_filter_input(volume_30m=500.0, volume_sma_20=1000.0, volume_low_factor=0.6)
        blocked, reason = check_entry_filters(fi)
        assert blocked is True
        assert "low_volume" in reason

    def test_filter_high_impact_event_blocks(self):
        fi = make_filter_input(is_high_impact_event=True)
        blocked, reason = check_entry_filters(fi)
        assert blocked is True
        assert "high_impact_event" in reason

    def test_filter_existing_position_blocks(self):
        fi = make_filter_input(has_position_same_symbol=True)
        blocked, reason = check_entry_filters(fi)
        assert blocked is True
        assert "existing_position" in reason

    def test_filter_total_risk_exceeded_blocks(self):
        """combined risk >= max_total_risk → blocked."""
        fi = make_filter_input(
            total_risk_exposure_pct=0.5,
            pending_risk_pct=0.3,
            candidate_risk_pct=0.2,
            max_total_risk=1.0,
        )
        blocked, reason = check_entry_filters(fi)
        assert blocked is True
        assert "risk_exposure_exceeded" in reason

    def test_filter_total_risk_boundary_blocks_at_equality(self):
        """combined == max_total_risk → blocked (>= operator)."""
        fi = make_filter_input(
            total_risk_exposure_pct=0.0,
            pending_risk_pct=0.0,
            candidate_risk_pct=1.0,
            max_total_risk=1.0,
        )
        blocked, _ = check_entry_filters(fi)
        assert blocked is True

    def test_filter_consecutive_losses_blocks(self):
        """4 consecutive losses → blocked (>= 4)."""
        fi = make_filter_input(consecutive_losses=4)
        blocked, reason = check_entry_filters(fi)
        assert blocked is True
        assert "consecutive_losses" in reason

    def test_filter_consecutive_losses_boundary_3_passes(self):
        """3 consecutive losses: < 4 limit → not blocked."""
        fi = make_filter_input(consecutive_losses=3)
        blocked, _ = check_entry_filters(fi)
        assert blocked is False

    def test_filter_daily_loss_blocks(self):
        """-3.0R daily loss → blocked (<= -3.0)."""
        fi = make_filter_input(daily_loss_r=-3.0)
        blocked, reason = check_entry_filters(fi)
        assert blocked is True
        assert "daily_loss_exceeded" in reason

    def test_filter_daily_loss_boundary_minus_2_9_passes(self):
        fi = make_filter_input(daily_loss_r=-2.9)
        blocked, _ = check_entry_filters(fi)
        assert blocked is False

    def test_filter_weekly_loss_blocks(self):
        fi = make_filter_input(weekly_loss_exceeded=True)
        blocked, reason = check_entry_filters(fi)
        assert blocked is True
        assert "weekly_loss_exceeded" in reason


# ---------------------------------------------------------------------------
# 4. evaluate_mode integration
# ---------------------------------------------------------------------------

class TestEvaluateMode:

    def test_evaluate_mode_engine_not_ready(self):
        regime = make_regime(RegimeState.HTF_BULLISH, H1Bias.H1_BULLISH, M30Bias.M30_BULLISH)
        result = evaluate_mode(regime, engine_ready=False)
        assert result.mode == ModeState.MODE_NO_TRADE
        assert result.blocked_reason == "engine_not_ready"

    def test_evaluate_mode_risk_gate_blocked(self):
        regime = make_regime(RegimeState.HTF_BULLISH, H1Bias.H1_BULLISH, M30Bias.M30_BULLISH)
        result = evaluate_mode(regime, engine_ready=True, risk_gate_blocked=True)
        assert result.mode == ModeState.MODE_NO_TRADE
        assert result.blocked_reason == "risk_gate_blocked"

    def test_evaluate_mode_with_filter_block(self):
        regime = make_regime(RegimeState.HTF_BULLISH, H1Bias.H1_BULLISH, M30Bias.M30_BULLISH)
        fi = make_filter_input(is_box_center=True)
        result = evaluate_mode(regime, filter_input=fi, engine_ready=True, risk_gate_blocked=False)
        assert result.mode == ModeState.MODE_NO_TRADE
        assert result.blocked_reason is not None
        assert "box_center" in result.blocked_reason

    def test_evaluate_mode_happy_path(self):
        regime = make_regime(RegimeState.HTF_BULLISH, H1Bias.H1_BULLISH, M30Bias.M30_BULLISH)
        fi = make_filter_input()  # all pass
        result = evaluate_mode(regime, filter_input=fi, engine_ready=True, risk_gate_blocked=False)
        assert result.mode == ModeState.MODE_TREND_LONG
        assert result.blocked_reason is None

    def test_evaluate_mode_no_filter_input_returns_mode(self):
        """Without filter_input, skips filter checks → returns matrix result."""
        regime = make_regime(RegimeState.HTF_BULLISH, H1Bias.H1_BULLISH, M30Bias.M30_BULLISH)
        result = evaluate_mode(regime, filter_input=None, engine_ready=True, risk_gate_blocked=False)
        assert result.mode == ModeState.MODE_TREND_LONG

    def test_evaluate_mode_no_trade_skips_filters(self):
        """If matrix returns NO_TRADE, filter_input should be skipped and NO_TRADE returned directly."""
        regime = make_regime(RegimeState.HTF_NEUTRAL, H1Bias.H1_BULLISH, M30Bias.M30_BULLISH)
        fi = make_filter_input()  # would pass filters
        result = evaluate_mode(regime, filter_input=fi, engine_ready=True, risk_gate_blocked=False)
        assert result.mode == ModeState.MODE_NO_TRADE

    def test_evaluate_mode_engine_check_before_risk_gate(self):
        """engine_not_ready takes priority over risk_gate_blocked."""
        regime = make_regime(RegimeState.HTF_BULLISH, H1Bias.H1_BULLISH, M30Bias.M30_BULLISH)
        result = evaluate_mode(regime, engine_ready=False, risk_gate_blocked=True)
        assert result.blocked_reason == "engine_not_ready"

    def test_evaluate_mode_bearish_m30neutral_returns_rebound_short(self):
        regime = make_regime(RegimeState.HTF_BEARISH, H1Bias.H1_BEARISH, M30Bias.M30_NEUTRAL)
        fi = make_filter_input()
        result = evaluate_mode(regime, filter_input=fi, engine_ready=True, risk_gate_blocked=False)
        assert result.mode == ModeState.MODE_REBOUND_SHORT

    def test_evaluate_mode_filter_preserves_enhanced_conditions(self):
        """Even when filter blocks, enhanced_conditions from matrix are preserved in result."""
        regime = make_regime(RegimeState.HTF_BULLISH, H1Bias.H1_BEARISH, M30Bias.M30_BEARISH)
        fi = make_filter_input(is_box_center=True)
        result = evaluate_mode(regime, filter_input=fi, engine_ready=True, risk_gate_blocked=False)
        assert result.mode == ModeState.MODE_NO_TRADE
        # enhanced_conditions from REBOUND_SHORT + reduced_risk should still be present
        assert result.enhanced_conditions is not None
        assert result.enhanced_conditions.get("reduced_risk") is True
