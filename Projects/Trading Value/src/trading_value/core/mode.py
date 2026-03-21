"""Mode selector — determines allowed strategies and entry filters.

Pure functions, no state, no side effects.
Implements spec v2 section 10 (strategy matrix) and section 12 (entry block filters).
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import ModeState, RegimeState
from .regime import H1Bias, M30Bias, RegimeSnapshot


# ---------------------------------------------------------------------------
# ModeResult
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ModeResult:
    """Result of mode selection."""

    mode: ModeState
    allowed_setups: list[str]  # e.g. ["TREND_LONG"], ["PULLBACK_LONG"], []
    blocked_reason: str | None = None  # reason if MODE_NO_TRADE
    enhanced_conditions: dict[str, object] | None = None  # e.g. {"min_volume_factor": 1.5, "min_rr": 2.0}


# ---------------------------------------------------------------------------
# EntryFilterInput
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EntryFilterInput:
    """Input data for entry filter evaluation."""

    is_box_center: bool
    is_abnormal_volatility: bool
    rr_to_tp1: float
    volume_30m: float
    volume_sma_20: float
    is_high_impact_event: bool
    has_position_same_symbol: bool
    total_risk_exposure_pct: float
    pending_risk_pct: float
    candidate_risk_pct: float
    max_total_risk: float  # default 1.0%
    max_symbol_risk: float  # default 0.5%
    symbol_risk_exposure_pct: float
    consecutive_losses: int
    daily_loss_r: float
    weekly_loss_exceeded: bool
    min_rr: float  # default 1.5
    volume_low_factor: float  # default 0.6


# ---------------------------------------------------------------------------
# Strategy matrix (spec v2 section 10)
# ---------------------------------------------------------------------------

# Risk stop-rule defaults from config/default.toml
_DEFAULT_CONSECUTIVE_LOSS_LIMIT = 4
_DEFAULT_DAILY_LOSS_R_LIMIT = -3.0


def select_mode(regime: RegimeSnapshot) -> ModeResult:
    """Select trading mode based on regime classification per spec v2 section 10.

    The complete matrix:

    | HTF        | H1          | M30                    | Allowed         | Notes |
    |------------|-------------|------------------------|-----------------|-------|
    | BULLISH    | H1_BULLISH  | M30_BULLISH            | TREND_LONG      | |
    | BULLISH    | H1_BULLISH  | M30_NEUTRAL            | TREND_LONG      | enhanced: vol>=1.5*sma5, RR>=2.0 |
    | BULLISH    | H1_BULLISH  | M30_BEARISH            | PULLBACK_LONG   | 30m correction buy |
    | BULLISH    | H1_NEUTRAL  | M30_BULLISH            | TREND_LONG      | |
    | BULLISH    | H1_NEUTRAL  | M30_NEUTRAL/BEARISH    | PULLBACK_LONG   | |
    | BULLISH    | H1_BEARISH  | M30_BEARISH            | REBOUND_SHORT   | reduced risk only |
    | BULLISH    | H1_BEARISH  | M30_NEUTRAL/BULLISH    | NO_TRADE        | direction conflict |
    | NEUTRAL    | H1_BEARISH  | M30_BEARISH            | REBOUND_SHORT   | |
    | NEUTRAL    | (other)     | (other)                | NO_TRADE        | |
    | BEARISH    | any         | M30_BEARISH/NEUTRAL    | REBOUND_SHORT   | |
    | BEARISH    | any         | M30_BULLISH            | NO_TRADE        | observe bounce only |
    """
    htf = regime.htf
    h1 = regime.h1
    m30 = regime.m30

    # --- HTF_BULLISH ---
    if htf == RegimeState.HTF_BULLISH:
        if h1 == H1Bias.H1_BULLISH:
            if m30 == M30Bias.M30_BULLISH:
                return ModeResult(
                    mode=ModeState.MODE_TREND_LONG,
                    allowed_setups=["TREND_LONG"],
                )
            if m30 == M30Bias.M30_NEUTRAL:
                return ModeResult(
                    mode=ModeState.MODE_TREND_LONG,
                    allowed_setups=["TREND_LONG"],
                    enhanced_conditions={"min_volume_factor": 1.5, "min_rr": 2.0},
                )
            # m30 == M30_BEARISH
            return ModeResult(
                mode=ModeState.MODE_PULLBACK_LONG,
                allowed_setups=["PULLBACK_LONG"],
            )

        if h1 == H1Bias.H1_NEUTRAL:
            if m30 == M30Bias.M30_BULLISH:
                return ModeResult(
                    mode=ModeState.MODE_TREND_LONG,
                    allowed_setups=["TREND_LONG"],
                )
            # m30 == M30_NEUTRAL or M30_BEARISH
            return ModeResult(
                mode=ModeState.MODE_PULLBACK_LONG,
                allowed_setups=["PULLBACK_LONG"],
            )

        # h1 == H1_BEARISH
        if m30 == M30Bias.M30_BEARISH:
            return ModeResult(
                mode=ModeState.MODE_REBOUND_SHORT,
                allowed_setups=["REBOUND_SHORT"],
                enhanced_conditions={"reduced_risk": True, "max_risk_pct": 0.0025},
            )
        # m30 == M30_NEUTRAL or M30_BULLISH
        return ModeResult(
            mode=ModeState.MODE_NO_TRADE,
            allowed_setups=[],
            blocked_reason="direction_conflict: HTF_BULLISH + H1_BEARISH + M30 not bearish",
        )

    # --- HTF_NEUTRAL ---
    if htf == RegimeState.HTF_NEUTRAL:
        if h1 == H1Bias.H1_BEARISH and m30 == M30Bias.M30_BEARISH:
            return ModeResult(
                mode=ModeState.MODE_REBOUND_SHORT,
                allowed_setups=["REBOUND_SHORT"],
            )
        return ModeResult(
            mode=ModeState.MODE_NO_TRADE,
            allowed_setups=[],
            blocked_reason="no_valid_setup: HTF_NEUTRAL without full bearish alignment",
        )

    # --- HTF_BEARISH ---
    # htf == RegimeState.HTF_BEARISH
    if m30 in (M30Bias.M30_BEARISH, M30Bias.M30_NEUTRAL):
        return ModeResult(
            mode=ModeState.MODE_REBOUND_SHORT,
            allowed_setups=["REBOUND_SHORT"],
        )
    # m30 == M30_BULLISH
    return ModeResult(
        mode=ModeState.MODE_NO_TRADE,
        allowed_setups=[],
        blocked_reason="observe_bounce_only: HTF_BEARISH + M30_BULLISH",
    )


# ---------------------------------------------------------------------------
# Entry block filters (spec v2 section 12)
# ---------------------------------------------------------------------------


def check_entry_filters(filter_input: EntryFilterInput) -> tuple[bool, str]:
    """Check all section 12 entry block filters.

    Returns (is_blocked, reason).

    Filters (any one blocks):
    1. box_center_30m == true
    2. abnormal_volatility == true
    3. RR < min_rr (1.5)
    4. volume_30m < volume_sma_20 * volume_low_factor (0.6)
    5. high impact event within 30min
    6. already has position in same symbol
    7. total risk exposure + pending + candidate > max_total_risk (1.0%)
    8. daily loss, weekly loss, or consecutive losses exceeded
    """
    # Filter 1: box center
    if filter_input.is_box_center:
        return (True, "box_center_30m: price in 40-60% range of recent 48-bar box")

    # Filter 2: abnormal volatility
    if filter_input.is_abnormal_volatility:
        return (True, "abnormal_volatility: amplitude exceeds ATR threshold")

    # Filter 3: insufficient risk-reward
    if filter_input.rr_to_tp1 < filter_input.min_rr:
        return (
            True,
            f"rr_insufficient: RR {filter_input.rr_to_tp1:.2f} < min {filter_input.min_rr:.2f}",
        )

    # Filter 4: low volume
    volume_threshold = filter_input.volume_sma_20 * filter_input.volume_low_factor
    if filter_input.volume_30m < volume_threshold:
        return (
            True,
            f"low_volume: volume_30m {filter_input.volume_30m:.2f} < threshold {volume_threshold:.2f}",
        )

    # Filter 5: high impact economic event
    if filter_input.is_high_impact_event:
        return (True, "high_impact_event: within 30min of scheduled event")

    # Filter 6: existing position in same symbol
    if filter_input.has_position_same_symbol:
        return (True, "existing_position: already has position in same symbol")

    # Filter 7: total risk exposure exceeded
    combined_risk = (
        filter_input.total_risk_exposure_pct
        + filter_input.pending_risk_pct
        + filter_input.candidate_risk_pct
    )
    if combined_risk >= filter_input.max_total_risk:
        return (
            True,
            f"risk_exposure_exceeded: combined {combined_risk:.4f}% >= max {filter_input.max_total_risk:.4f}%",
        )

    # Also check per-symbol risk
    symbol_combined = filter_input.symbol_risk_exposure_pct + filter_input.candidate_risk_pct
    if symbol_combined > filter_input.max_symbol_risk:
        return (
            True,
            f"symbol_risk_exceeded: {symbol_combined:.4f}% > max {filter_input.max_symbol_risk:.4f}%",
        )

    # Filter 8: loss limits exceeded
    if filter_input.consecutive_losses >= _DEFAULT_CONSECUTIVE_LOSS_LIMIT:
        return (
            True,
            f"consecutive_losses: {filter_input.consecutive_losses} >= {_DEFAULT_CONSECUTIVE_LOSS_LIMIT}",
        )

    if filter_input.daily_loss_r <= _DEFAULT_DAILY_LOSS_R_LIMIT:
        return (
            True,
            f"daily_loss_exceeded: {filter_input.daily_loss_r:.1f}R <= {_DEFAULT_DAILY_LOSS_R_LIMIT:.1f}R",
        )

    if filter_input.weekly_loss_exceeded:
        return (True, "weekly_loss_exceeded: weekly loss limit breached")

    return (False, "")


# ---------------------------------------------------------------------------
# Combined selector (state machine doc section 6)
# ---------------------------------------------------------------------------


def evaluate_mode(
    regime: RegimeSnapshot,
    filter_input: EntryFilterInput | None = None,
    engine_ready: bool = True,
    risk_gate_blocked: bool = False,
) -> ModeResult:
    """Full mode evaluation with filters.

    Per state machine doc section 6:
    - If engine not ready -> MODE_NO_TRADE
    - If risk_gate blocked -> MODE_NO_TRADE
    - Select mode from matrix
    - If mode allows trading and filter_input provided, check entry filters
    - If any filter blocks -> MODE_NO_TRADE with reason
    """
    # Pre-check: engine readiness
    if not engine_ready:
        return ModeResult(
            mode=ModeState.MODE_NO_TRADE,
            allowed_setups=[],
            blocked_reason="engine_not_ready",
        )

    # Pre-check: risk gate
    if risk_gate_blocked:
        return ModeResult(
            mode=ModeState.MODE_NO_TRADE,
            allowed_setups=[],
            blocked_reason="risk_gate_blocked",
        )

    # Select mode from strategy matrix
    mode_result = select_mode(regime)

    # If already NO_TRADE, return as-is
    if mode_result.mode == ModeState.MODE_NO_TRADE:
        return mode_result

    # If filter_input provided, check entry filters
    if filter_input is not None:
        is_blocked, reason = check_entry_filters(filter_input)
        if is_blocked:
            return ModeResult(
                mode=ModeState.MODE_NO_TRADE,
                allowed_setups=[],
                blocked_reason=reason,
                enhanced_conditions=mode_result.enhanced_conditions,
            )

    return mode_result
