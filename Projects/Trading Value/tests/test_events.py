"""Tests for trading_value.core.events — event creation and serialization."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from trading_value.core.events import (
    EVENT_TYPE_MAP,
    BarClosedEvent,
    EngineEvent,
    EntryOrderEvent,
    Event,
    EventType,
    ExitOrderFilledEvent,
    RiskEvent,
    StopFilledEvent,
    StopOrderEvent,
    TpFilledEvent,
    TriggerEvent,
    ZoneTouchedEvent,
)
from trading_value.core.models import Side, Timeframe

NOW = datetime(2026, 3, 20, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# EventType enum
# ---------------------------------------------------------------------------

def test_event_type_has_exactly_23_members():
    """EventType enum must have exactly 23 members (spec §1)."""
    assert len(EventType) == 23


def test_event_type_all_member_values():
    """Spot-check critical EventType string values."""
    assert EventType.BOOT_COMPLETED == "BOOT_COMPLETED"
    assert EventType.BAR_CLOSED_4H == "BAR_CLOSED_4H"
    assert EventType.BAR_CLOSED_1H == "BAR_CLOSED_1H"
    assert EventType.BAR_CLOSED_30M == "BAR_CLOSED_30M"
    assert EventType.BAR_CLOSED_15M == "BAR_CLOSED_15M"
    assert EventType.BAR_CLOSED_5M == "BAR_CLOSED_5M"
    assert EventType.ZONE_TOUCHED == "ZONE_TOUCHED"
    assert EventType.TRIGGER_CONFIRMED == "TRIGGER_CONFIRMED"
    assert EventType.TRIGGER_INVALIDATED == "TRIGGER_INVALIDATED"
    assert EventType.ENTRY_ORDER_SUBMITTED == "ENTRY_ORDER_SUBMITTED"
    assert EventType.ENTRY_ORDER_PARTIAL_FILL == "ENTRY_ORDER_PARTIAL_FILL"
    assert EventType.ENTRY_ORDER_FILLED == "ENTRY_ORDER_FILLED"
    assert EventType.STOP_ORDER_ATTACHED == "STOP_ORDER_ATTACHED"
    assert EventType.TP1_FILLED == "TP1_FILLED"
    assert EventType.TP2_FILLED == "TP2_FILLED"
    assert EventType.STOP_FILLED == "STOP_FILLED"
    assert EventType.EXIT_ORDER_FILLED == "EXIT_ORDER_FILLED"
    assert EventType.RISK_LIMIT_BREACHED == "RISK_LIMIT_BREACHED"
    assert EventType.API_DEGRADED == "API_DEGRADED"
    assert EventType.API_RECOVERED == "API_RECOVERED"
    assert EventType.MANUAL_HALT == "MANUAL_HALT"
    assert EventType.MANUAL_RESUME == "MANUAL_RESUME"
    assert EventType.HISTORY_READY == "HISTORY_READY"


# ---------------------------------------------------------------------------
# Event base — auto-generated UUID
# ---------------------------------------------------------------------------

def test_event_base_auto_generates_uuid():
    """Event base: event_id is auto-generated as a valid UUID string."""
    evt = EngineEvent(
        event_type=EventType.BOOT_COMPLETED,
        timestamp=NOW,
    )
    # Should parse as a valid UUID (raises ValueError if not)
    parsed = UUID(evt.event_id)
    assert str(parsed) == evt.event_id


def test_event_base_unique_ids():
    """Each Event instance gets a different event_id."""
    e1 = EngineEvent(event_type=EventType.BOOT_COMPLETED, timestamp=NOW)
    e2 = EngineEvent(event_type=EventType.BOOT_COMPLETED, timestamp=NOW)
    assert e1.event_id != e2.event_id


def test_event_base_system_event_has_no_symbol():
    """System-level events may have symbol=None."""
    evt = EngineEvent(event_type=EventType.MANUAL_HALT, timestamp=NOW)
    assert evt.symbol is None


# ---------------------------------------------------------------------------
# BarClosedEvent
# ---------------------------------------------------------------------------

def test_bar_closed_event_for_each_timeframe():
    """BarClosedEvent: create for each of the 5 timeframes."""
    tf_event_map = {
        Timeframe.H4: EventType.BAR_CLOSED_4H,
        Timeframe.H1: EventType.BAR_CLOSED_1H,
        Timeframe.M30: EventType.BAR_CLOSED_30M,
        Timeframe.M15: EventType.BAR_CLOSED_15M,
        Timeframe.M5: EventType.BAR_CLOSED_5M,
    }
    for tf, et in tf_event_map.items():
        evt = BarClosedEvent(
            event_type=et,
            timestamp=NOW,
            symbol="ETHUSDT",
            timeframe=tf,
            open=3480.0,
            high=3530.0,
            low=3470.0,
            close=3510.0,
            volume=1500.0,
        )
        assert evt.timeframe == tf.value
        assert evt.event_type == et.value
        assert evt.symbol == "ETHUSDT"


def test_bar_closed_event_roundtrip():
    """BarClosedEvent: model_dump() -> model_validate() roundtrip."""
    evt = BarClosedEvent(
        event_type=EventType.BAR_CLOSED_1H,
        timestamp=NOW,
        symbol="BTCUSDT",
        timeframe=Timeframe.H1,
        open=85000.0,
        high=86000.0,
        low=84500.0,
        close=85500.0,
        volume=500.0,
    )
    data = evt.model_dump()
    restored = BarClosedEvent.model_validate(data)
    assert restored.close == 85500.0
    assert restored.timeframe == "1h"
    assert restored.symbol == "BTCUSDT"


# ---------------------------------------------------------------------------
# ZoneTouchedEvent
# ---------------------------------------------------------------------------

def test_zone_touched_event_create_and_roundtrip():
    """ZoneTouchedEvent: create and roundtrip."""
    evt = ZoneTouchedEvent(
        event_type=EventType.ZONE_TOUCHED,
        timestamp=NOW,
        symbol="ETHUSDT",
        zone_id="zone-007",
        zone_level=3500.0,
        zone_low=3480.0,
        zone_high=3520.0,
        touch_price=3501.0,
    )
    data = evt.model_dump()
    restored = ZoneTouchedEvent.model_validate(data)
    assert restored.zone_id == "zone-007"
    assert restored.touch_price == 3501.0
    assert restored.zone_level == 3500.0


# ---------------------------------------------------------------------------
# TriggerEvent
# ---------------------------------------------------------------------------

def test_trigger_confirmed_event():
    """TriggerEvent: TRIGGER_CONFIRMED variant."""
    evt = TriggerEvent(
        event_type=EventType.TRIGGER_CONFIRMED,
        timestamp=NOW,
        symbol="ETHUSDT",
        setup_version=5,
        zone_id="zone-007",
        trigger_timeframe=Timeframe.M5,
        trigger_price=3498.0,
        reason="bullish_engulfing",
    )
    assert evt.event_type == "TRIGGER_CONFIRMED"
    assert evt.setup_version == 5
    assert evt.trigger_price == 3498.0


def test_trigger_invalidated_event():
    """TriggerEvent: TRIGGER_INVALIDATED variant."""
    evt = TriggerEvent(
        event_type=EventType.TRIGGER_INVALIDATED,
        timestamp=NOW,
        symbol="ETHUSDT",
        setup_version=5,
        zone_id="zone-007",
        trigger_timeframe=Timeframe.M15,
        trigger_price=None,
        reason="zone_broken",
    )
    assert evt.event_type == "TRIGGER_INVALIDATED"
    assert evt.trigger_price is None
    assert evt.reason == "zone_broken"


# ---------------------------------------------------------------------------
# EntryOrderEvent — partial fill
# ---------------------------------------------------------------------------

def test_entry_order_event_partial_fill():
    """EntryOrderEvent: create with partial fill data."""
    evt = EntryOrderEvent(
        event_type=EventType.ENTRY_ORDER_PARTIAL_FILL,
        timestamp=NOW,
        symbol="ETHUSDT",
        order_id="ord-001",
        setup_version=3,
        side=Side.LONG,
        price=3450.0,
        qty=1.0,
        filled_qty=0.4,
        avg_fill_price=3449.5,
    )
    assert evt.filled_qty == 0.4
    assert evt.avg_fill_price == 3449.5
    assert evt.side == "LONG"

    data = evt.model_dump()
    restored = EntryOrderEvent.model_validate(data)
    assert restored.order_id == "ord-001"
    assert restored.filled_qty == 0.4


# ---------------------------------------------------------------------------
# StopOrderEvent
# ---------------------------------------------------------------------------

def test_stop_order_event():
    """StopOrderEvent: create and verify fields."""
    evt = StopOrderEvent(
        event_type=EventType.STOP_ORDER_ATTACHED,
        timestamp=NOW,
        symbol="ETHUSDT",
        order_id="stop-001",
        stop_price=3400.0,
        qty=1.0,
    )
    assert evt.stop_price == 3400.0
    assert evt.order_id == "stop-001"
    data = evt.model_dump()
    restored = StopOrderEvent.model_validate(data)
    assert restored.stop_price == 3400.0


# ---------------------------------------------------------------------------
# TpFilledEvent
# ---------------------------------------------------------------------------

def test_tp1_filled_event():
    """TpFilledEvent: TP1 fill."""
    evt = TpFilledEvent(
        event_type=EventType.TP1_FILLED,
        timestamp=NOW,
        symbol="ETHUSDT",
        tp_level=1,
        fill_price=3550.0,
        fill_qty=0.5,
        remaining_qty=0.5,
    )
    assert evt.tp_level == 1
    assert evt.fill_price == 3550.0
    assert evt.remaining_qty == 0.5


def test_tp2_filled_event():
    """TpFilledEvent: TP2 fill."""
    evt = TpFilledEvent(
        event_type=EventType.TP2_FILLED,
        timestamp=NOW,
        symbol="ETHUSDT",
        tp_level=2,
        fill_price=3650.0,
        fill_qty=0.3,
        remaining_qty=0.2,
    )
    assert evt.tp_level == 2
    data = evt.model_dump()
    restored = TpFilledEvent.model_validate(data)
    assert restored.tp_level == 2
    assert restored.fill_price == 3650.0


# ---------------------------------------------------------------------------
# StopFilledEvent
# ---------------------------------------------------------------------------

def test_stop_filled_event():
    """StopFilledEvent: create and verify."""
    evt = StopFilledEvent(
        event_type=EventType.STOP_FILLED,
        timestamp=NOW,
        symbol="ETHUSDT",
        fill_price=3400.0,
        fill_qty=0.5,
        pnl=-25.0,
    )
    assert evt.pnl == -25.0
    data = evt.model_dump()
    restored = StopFilledEvent.model_validate(data)
    assert restored.fill_price == 3400.0
    assert restored.pnl == -25.0


# ---------------------------------------------------------------------------
# ExitOrderFilledEvent
# ---------------------------------------------------------------------------

def test_exit_order_filled_event():
    """ExitOrderFilledEvent: create and verify."""
    evt = ExitOrderFilledEvent(
        event_type=EventType.EXIT_ORDER_FILLED,
        timestamp=NOW,
        symbol="ETHUSDT",
        fill_price=3700.0,
        fill_qty=0.2,
        pnl=60.0,
        reason="manual_close",
    )
    assert evt.pnl == 60.0
    assert evt.reason == "manual_close"
    data = evt.model_dump()
    restored = ExitOrderFilledEvent.model_validate(data)
    assert restored.fill_price == 3700.0


# ---------------------------------------------------------------------------
# EngineEvent
# ---------------------------------------------------------------------------

def test_engine_event_boot_completed():
    """EngineEvent: BOOT_COMPLETED variant."""
    evt = EngineEvent(
        event_type=EventType.BOOT_COMPLETED,
        timestamp=NOW,
        reason="initial_startup",
        details="All feeds connected",
    )
    assert evt.event_type == "BOOT_COMPLETED"
    assert evt.reason == "initial_startup"
    assert evt.symbol is None


def test_engine_event_api_degraded():
    """EngineEvent: API_DEGRADED variant."""
    evt = EngineEvent(
        event_type=EventType.API_DEGRADED,
        timestamp=NOW,
        reason="websocket_disconnect",
        details="Feed lost for > 30s",
    )
    assert evt.event_type == "API_DEGRADED"
    assert evt.details == "Feed lost for > 30s"


# ---------------------------------------------------------------------------
# RiskEvent
# ---------------------------------------------------------------------------

def test_risk_event_with_rule_details():
    """RiskEvent: create with rule details."""
    evt = RiskEvent(
        event_type=EventType.RISK_LIMIT_BREACHED,
        timestamp=NOW,
        rule_name="consecutive_losses",
        current_value=3.0,
        threshold=3.0,
        action="BLOCK",
    )
    assert evt.rule_name == "consecutive_losses"
    assert evt.current_value == 3.0
    assert evt.threshold == 3.0
    assert evt.action == "BLOCK"

    data = evt.model_dump()
    restored = RiskEvent.model_validate(data)
    assert restored.rule_name == "consecutive_losses"


# ---------------------------------------------------------------------------
# EVENT_TYPE_MAP
# ---------------------------------------------------------------------------

def test_event_type_map_has_all_23_keys():
    """EVENT_TYPE_MAP must have a key for every EventType member."""
    for member in EventType:
        assert member in EVENT_TYPE_MAP, f"Missing mapping for {member}"
    assert len(EVENT_TYPE_MAP) == 23


def test_event_type_map_correct_classes():
    """EVENT_TYPE_MAP maps to correct event classes."""
    assert EVENT_TYPE_MAP[EventType.BAR_CLOSED_4H] is BarClosedEvent
    assert EVENT_TYPE_MAP[EventType.BAR_CLOSED_1H] is BarClosedEvent
    assert EVENT_TYPE_MAP[EventType.BAR_CLOSED_30M] is BarClosedEvent
    assert EVENT_TYPE_MAP[EventType.BAR_CLOSED_15M] is BarClosedEvent
    assert EVENT_TYPE_MAP[EventType.BAR_CLOSED_5M] is BarClosedEvent
    assert EVENT_TYPE_MAP[EventType.ZONE_TOUCHED] is ZoneTouchedEvent
    assert EVENT_TYPE_MAP[EventType.TRIGGER_CONFIRMED] is TriggerEvent
    assert EVENT_TYPE_MAP[EventType.TRIGGER_INVALIDATED] is TriggerEvent
    assert EVENT_TYPE_MAP[EventType.ENTRY_ORDER_SUBMITTED] is EntryOrderEvent
    assert EVENT_TYPE_MAP[EventType.ENTRY_ORDER_PARTIAL_FILL] is EntryOrderEvent
    assert EVENT_TYPE_MAP[EventType.ENTRY_ORDER_FILLED] is EntryOrderEvent
    assert EVENT_TYPE_MAP[EventType.STOP_ORDER_ATTACHED] is StopOrderEvent
    assert EVENT_TYPE_MAP[EventType.TP1_FILLED] is TpFilledEvent
    assert EVENT_TYPE_MAP[EventType.TP2_FILLED] is TpFilledEvent
    assert EVENT_TYPE_MAP[EventType.STOP_FILLED] is StopFilledEvent
    assert EVENT_TYPE_MAP[EventType.EXIT_ORDER_FILLED] is ExitOrderFilledEvent
    assert EVENT_TYPE_MAP[EventType.BOOT_COMPLETED] is EngineEvent
    assert EVENT_TYPE_MAP[EventType.HISTORY_READY] is EngineEvent
    assert EVENT_TYPE_MAP[EventType.API_DEGRADED] is EngineEvent
    assert EVENT_TYPE_MAP[EventType.API_RECOVERED] is EngineEvent
    assert EVENT_TYPE_MAP[EventType.MANUAL_HALT] is EngineEvent
    assert EVENT_TYPE_MAP[EventType.MANUAL_RESUME] is EngineEvent
    assert EVENT_TYPE_MAP[EventType.RISK_LIMIT_BREACHED] is RiskEvent


# ---------------------------------------------------------------------------
# Event serialization: event_type string in model_dump()
# ---------------------------------------------------------------------------

def test_event_serialization_event_type_string():
    """model_dump() produces correct event_type string for each event class."""
    evt = ZoneTouchedEvent(
        event_type=EventType.ZONE_TOUCHED,
        timestamp=NOW,
        symbol="ETHUSDT",
        zone_id="z1",
        zone_level=3500.0,
        zone_low=3480.0,
        zone_high=3520.0,
        touch_price=3500.5,
    )
    data = evt.model_dump()
    assert data["event_type"] == "ZONE_TOUCHED"


def test_event_serialization_bar_closed_event_type_string():
    """BarClosedEvent model_dump() produces correct event_type string."""
    evt = BarClosedEvent(
        event_type=EventType.BAR_CLOSED_4H,
        timestamp=NOW,
        symbol="BTCUSDT",
        timeframe=Timeframe.H4,
        open=85000.0,
        high=86000.0,
        low=84500.0,
        close=85800.0,
        volume=300.0,
    )
    data = evt.model_dump()
    assert data["event_type"] == "BAR_CLOSED_4H"
    assert data["timeframe"] == "4h"
