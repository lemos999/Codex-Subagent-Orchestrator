"""Risk manager — pure functions + RiskTracker dataclass.

Implements spec v2 §13 risk management rules and state machine §5.2 RiskGate.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime

from .models import RiskGate


# ---------------------------------------------------------------------------
# 1. RiskTracker — mutable risk tracking state
# ---------------------------------------------------------------------------


@dataclass
class RiskTracker:
    """Tracks cumulative risk state across trades."""

    consecutive_losses: int = 0
    daily_pnl_r: float = 0.0  # cumulative R for today
    weekly_pnl_r: float = 0.0
    daily_loss_limit_r: float = -3.0
    weekly_loss_limit_r: float = -10.0  # configurable
    api_failure_count: int = 0
    max_api_failures: int = 3
    slippage_history: list[float] = field(default_factory=list)  # last 20
    slippage_max_entries: int = 20
    slippage_alert_multiplier: float = 2.0
    max_consecutive_losses: int = 4
    current_date: str = ""  # YYYY-MM-DD for daily reset
    current_week: str = ""  # YYYY-Wxx for weekly reset


# ---------------------------------------------------------------------------
# 2. RiskGate evaluation
# ---------------------------------------------------------------------------


def evaluate_risk_gate(
    tracker: RiskTracker,
    is_counter_trend: bool = False,
    is_abnormal_volatility: bool = False,
) -> RiskGate:
    """Evaluate current RiskGate level.

    BLOCK when ANY:
    - consecutive_losses >= max_consecutive_losses (default 4)
    - daily_pnl_r <= daily_loss_limit_r (default -3R)
    - weekly_pnl_r <= weekly_loss_limit_r (weekly loss exceeded)
    - api_failure_count >= max_api_failures (default 3)
    - slippage alert triggered

    REDUCE when ANY (and not BLOCK):
    - is_counter_trend (HTF_BULLISH rebound short)
    - is_abnormal_volatility
    - consecutive_losses >= 2 (warning level)

    ALLOW otherwise.
    """
    # --- BLOCK conditions ---
    if tracker.consecutive_losses >= tracker.max_consecutive_losses:
        return RiskGate.BLOCK

    if tracker.daily_pnl_r <= tracker.daily_loss_limit_r:
        return RiskGate.BLOCK

    if tracker.weekly_pnl_r <= tracker.weekly_loss_limit_r:
        return RiskGate.BLOCK

    if tracker.api_failure_count >= tracker.max_api_failures:
        return RiskGate.BLOCK

    if is_slippage_alert(tracker):
        return RiskGate.BLOCK

    # --- REDUCE conditions ---
    if is_counter_trend:
        return RiskGate.REDUCE

    if is_abnormal_volatility:
        return RiskGate.REDUCE

    if tracker.consecutive_losses >= 2:
        return RiskGate.REDUCE

    return RiskGate.ALLOW


# ---------------------------------------------------------------------------
# 3. Trade result recording
# ---------------------------------------------------------------------------


def record_trade_result(
    tracker: RiskTracker, pnl_r: float, timestamp: datetime
) -> RiskTracker:
    """Record a completed trade's PnL in R units.

    - Update consecutive_losses (reset on win)
    - Update daily_pnl_r
    - Update weekly_pnl_r
    - Handle date/week rollover (reset daily on new date, weekly on new week)
    Returns new RiskTracker.
    """
    new_date = timestamp.strftime("%Y-%m-%d")
    new_week = timestamp.strftime("%Y-W%W")

    daily_pnl = tracker.daily_pnl_r
    weekly_pnl = tracker.weekly_pnl_r
    current_date = tracker.current_date
    current_week = tracker.current_week

    # Handle date rollover
    if new_date != current_date:
        daily_pnl = 0.0
        current_date = new_date

    # Handle week rollover
    if new_week != current_week:
        weekly_pnl = 0.0
        current_week = new_week

    # Update PnL
    daily_pnl += pnl_r
    weekly_pnl += pnl_r

    # Update consecutive losses
    if pnl_r < 0:
        consecutive = tracker.consecutive_losses + 1
    else:
        consecutive = 0

    return replace(
        tracker,
        consecutive_losses=consecutive,
        daily_pnl_r=daily_pnl,
        weekly_pnl_r=weekly_pnl,
        current_date=current_date,
        current_week=current_week,
    )


# ---------------------------------------------------------------------------
# 4. API failure tracking
# ---------------------------------------------------------------------------


def record_api_failure(tracker: RiskTracker) -> RiskTracker:
    """Increment API failure count."""
    return replace(tracker, api_failure_count=tracker.api_failure_count + 1)


def record_api_success(tracker: RiskTracker) -> RiskTracker:
    """Reset API failure count on success."""
    return replace(tracker, api_failure_count=0)


# ---------------------------------------------------------------------------
# 5. Slippage monitoring (§13.3)
# ---------------------------------------------------------------------------


def record_slippage(tracker: RiskTracker, slippage: float) -> RiskTracker:
    """Record a slippage observation. Maintains rolling window.

    If latest slippage > avg(last N) * multiplier, this will trigger
    BLOCK via evaluate_risk_gate.
    """
    history = list(tracker.slippage_history)
    history.append(slippage)
    # Keep only the most recent entries
    if len(history) > tracker.slippage_max_entries:
        history = history[-tracker.slippage_max_entries :]
    return replace(tracker, slippage_history=history)


def is_slippage_alert(tracker: RiskTracker) -> bool:
    """Check if latest slippage exceeds multiplier of recent average."""
    if len(tracker.slippage_history) < 2:
        return False

    latest = tracker.slippage_history[-1]
    # Average of all entries except the latest
    previous = tracker.slippage_history[:-1]
    avg = sum(previous) / len(previous)

    if avg <= 0:
        return False

    return latest >= avg * tracker.slippage_alert_multiplier


# ---------------------------------------------------------------------------
# 6. Risk reset
# ---------------------------------------------------------------------------


def reset_daily(tracker: RiskTracker, new_date: str) -> RiskTracker:
    """Reset daily PnL counter. Called at day boundary."""
    return replace(tracker, daily_pnl_r=0.0, current_date=new_date)


def reset_weekly(tracker: RiskTracker, new_week: str) -> RiskTracker:
    """Reset weekly PnL counter. Called at week boundary."""
    return replace(tracker, weekly_pnl_r=0.0, current_week=new_week)


def manual_reset(tracker: RiskTracker) -> RiskTracker:
    """Operator manual reset — clears consecutive losses, API failures.

    Does NOT reset PnL.
    """
    return replace(tracker, consecutive_losses=0, api_failure_count=0)


# ---------------------------------------------------------------------------
# 7. Risk budget helpers (complement position.py)
# ---------------------------------------------------------------------------


def select_risk_pct(
    risk_gate: RiskGate,
    is_counter_trend: bool,
    default_pct: float = 0.0035,
    max_pct: float = 0.005,
    counter_trend_pct: float = 0.0025,
) -> float:
    """Select the appropriate risk percentage.

    - BLOCK -> 0 (no trading)
    - REDUCE -> min(default, counter_trend_pct)
    - Counter-trend -> counter_trend_pct
    - Normal -> default_pct
    """
    if risk_gate == RiskGate.BLOCK:
        return 0.0

    if risk_gate == RiskGate.REDUCE:
        return min(default_pct, counter_trend_pct)

    if is_counter_trend:
        return counter_trend_pct

    return default_pct
