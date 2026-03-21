from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field

from .models import Side, Timeframe


# ---------------------------------------------------------------------------
# 1. EventType StrEnum — 23 members, grouped by category
# ---------------------------------------------------------------------------

class EventType(StrEnum):
    # System/Engine events
    BOOT_COMPLETED = "BOOT_COMPLETED"
    HISTORY_READY = "HISTORY_READY"
    API_DEGRADED = "API_DEGRADED"
    API_RECOVERED = "API_RECOVERED"
    MANUAL_HALT = "MANUAL_HALT"
    MANUAL_RESUME = "MANUAL_RESUME"
    # Bar close events
    BAR_CLOSED_4H = "BAR_CLOSED_4H"
    BAR_CLOSED_1H = "BAR_CLOSED_1H"
    BAR_CLOSED_30M = "BAR_CLOSED_30M"
    BAR_CLOSED_15M = "BAR_CLOSED_15M"
    BAR_CLOSED_5M = "BAR_CLOSED_5M"
    # Setup events
    ZONE_TOUCHED = "ZONE_TOUCHED"
    TRIGGER_CONFIRMED = "TRIGGER_CONFIRMED"
    TRIGGER_INVALIDATED = "TRIGGER_INVALIDATED"
    # Order events
    ENTRY_ORDER_SUBMITTED = "ENTRY_ORDER_SUBMITTED"
    ENTRY_ORDER_PARTIAL_FILL = "ENTRY_ORDER_PARTIAL_FILL"
    ENTRY_ORDER_FILLED = "ENTRY_ORDER_FILLED"
    STOP_ORDER_ATTACHED = "STOP_ORDER_ATTACHED"
    TP1_FILLED = "TP1_FILLED"
    TP2_FILLED = "TP2_FILLED"
    STOP_FILLED = "STOP_FILLED"
    EXIT_ORDER_FILLED = "EXIT_ORDER_FILLED"
    # Risk events
    RISK_LIMIT_BREACHED = "RISK_LIMIT_BREACHED"


# ---------------------------------------------------------------------------
# 2. Base Event model
# ---------------------------------------------------------------------------

class Event(BaseModel):
    """Base event. All events carry these fields."""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: EventType
    timestamp: datetime
    symbol: str | None = None  # None for system-level events


# ---------------------------------------------------------------------------
# 3. Specialized event models
# ---------------------------------------------------------------------------

class BarClosedEvent(Event):
    """Candle close event -- carries OHLCV data for the closed bar."""

    timeframe: Timeframe
    open: float
    high: float
    low: float
    close: float
    volume: float


class ZoneTouchedEvent(Event):
    """Price reached a monitored support/resistance zone."""

    zone_id: str
    zone_level: float
    zone_low: float
    zone_high: float
    touch_price: float


class TriggerEvent(Event):
    """Trigger confirmed or invalidated on lower timeframe."""

    setup_version: int
    zone_id: str
    trigger_timeframe: Timeframe
    trigger_price: float | None = None
    reason: str = ""


class EntryOrderEvent(Event):
    """Entry order lifecycle events."""

    order_id: str
    setup_version: int
    side: Side
    price: float
    qty: float
    filled_qty: float = 0.0
    avg_fill_price: float | None = None


class StopOrderEvent(Event):
    """Stop order attached confirmation."""

    order_id: str
    stop_price: float
    qty: float


class TpFilledEvent(Event):
    """Take-profit level filled."""

    tp_level: int  # 1 or 2
    fill_price: float
    fill_qty: float
    remaining_qty: float


class StopFilledEvent(Event):
    """Stop loss filled."""

    fill_price: float
    fill_qty: float
    pnl: float


class ExitOrderFilledEvent(Event):
    """Full exit (manual, trailing, forced)."""

    fill_price: float
    fill_qty: float
    pnl: float
    reason: str = ""


class EngineEvent(Event):
    """System/engine state change events."""

    reason: str = ""
    details: str = ""


class RiskEvent(Event):
    """Risk limit breached."""

    rule_name: str  # e.g. "consecutive_losses", "daily_loss", "api_failures"
    current_value: float
    threshold: float
    action: str = ""  # e.g. "BLOCK", "REDUCE"


# ---------------------------------------------------------------------------
# 4. Factory mapping — EventType -> event class (all 23 covered)
# ---------------------------------------------------------------------------

EVENT_TYPE_MAP: dict[EventType, type[Event]] = {
    EventType.BAR_CLOSED_4H: BarClosedEvent,
    EventType.BAR_CLOSED_1H: BarClosedEvent,
    EventType.BAR_CLOSED_30M: BarClosedEvent,
    EventType.BAR_CLOSED_15M: BarClosedEvent,
    EventType.BAR_CLOSED_5M: BarClosedEvent,
    EventType.ZONE_TOUCHED: ZoneTouchedEvent,
    EventType.TRIGGER_CONFIRMED: TriggerEvent,
    EventType.TRIGGER_INVALIDATED: TriggerEvent,
    EventType.ENTRY_ORDER_SUBMITTED: EntryOrderEvent,
    EventType.ENTRY_ORDER_PARTIAL_FILL: EntryOrderEvent,
    EventType.ENTRY_ORDER_FILLED: EntryOrderEvent,
    EventType.STOP_ORDER_ATTACHED: StopOrderEvent,
    EventType.TP1_FILLED: TpFilledEvent,
    EventType.TP2_FILLED: TpFilledEvent,
    EventType.STOP_FILLED: StopFilledEvent,
    EventType.EXIT_ORDER_FILLED: ExitOrderFilledEvent,
    EventType.BOOT_COMPLETED: EngineEvent,
    EventType.HISTORY_READY: EngineEvent,
    EventType.API_DEGRADED: EngineEvent,
    EventType.API_RECOVERED: EngineEvent,
    EventType.MANUAL_HALT: EngineEvent,
    EventType.MANUAL_RESUME: EngineEvent,
    EventType.RISK_LIMIT_BREACHED: RiskEvent,
}
