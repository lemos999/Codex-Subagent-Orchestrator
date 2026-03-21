"""Tests for trading_value.core.models — serialization roundtrip and default values."""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from trading_value.core.models import (
    OHLCV,
    CloudPosition,
    EngineState,
    GlobalState,
    MarketSnapshot,
    ModeState,
    ProfileBias,
    RegimeState,
    RiskGate,
    SetupState,
    Side,
    SymbolState,
    Timeframe,
    TimeframeSnapshot,
    TkState,
    TradeLifecycleState,
    TradingState,
    Zone,
)

NOW = datetime(2026, 3, 20, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# StrEnum tests
# ---------------------------------------------------------------------------

def test_str_enum_engine_state_values():
    """Each EngineState member value matches its string representation."""
    assert EngineState.BOOTSTRAPPING == "BOOTSTRAPPING"
    assert EngineState.WARMUP == "WARMUP"
    assert EngineState.READY == "READY"
    assert EngineState.DEGRADED == "DEGRADED"
    assert EngineState.HALTED == "HALTED"
    assert len(EngineState) == 5


def test_str_enum_risk_gate_values():
    assert RiskGate.ALLOW == "ALLOW"
    assert RiskGate.REDUCE == "REDUCE"
    assert RiskGate.BLOCK == "BLOCK"
    assert len(RiskGate) == 3


def test_str_enum_regime_state_values():
    assert RegimeState.HTF_BULLISH == "HTF_BULLISH"
    assert RegimeState.HTF_NEUTRAL == "HTF_NEUTRAL"
    assert RegimeState.HTF_BEARISH == "HTF_BEARISH"
    assert len(RegimeState) == 3


def test_str_enum_mode_state_values():
    assert ModeState.MODE_TREND_LONG == "MODE_TREND_LONG"
    assert ModeState.MODE_PULLBACK_LONG == "MODE_PULLBACK_LONG"
    assert ModeState.MODE_REBOUND_SHORT == "MODE_REBOUND_SHORT"
    assert ModeState.MODE_NO_TRADE == "MODE_NO_TRADE"
    assert len(ModeState) == 4


def test_str_enum_setup_state_values():
    assert SetupState.IDLE == "IDLE"
    assert SetupState.WAIT_ZONE_TOUCH == "WAIT_ZONE_TOUCH"
    assert SetupState.WAIT_TRIGGER_CONFIRM == "WAIT_TRIGGER_CONFIRM"
    assert SetupState.ENTRY_READY == "ENTRY_READY"
    assert SetupState.INVALIDATED == "INVALIDATED"
    assert len(SetupState) == 5


def test_str_enum_trade_lifecycle_values():
    assert TradeLifecycleState.FLAT == "FLAT"
    assert TradeLifecycleState.ENTRY_WORKING == "ENTRY_WORKING"
    assert TradeLifecycleState.OPEN_STAGE0 == "OPEN_STAGE0"
    assert TradeLifecycleState.OPEN_STAGE1 == "OPEN_STAGE1"
    assert TradeLifecycleState.OPEN_STAGE2 == "OPEN_STAGE2"
    assert TradeLifecycleState.EXIT_WORKING == "EXIT_WORKING"
    assert TradeLifecycleState.COOLDOWN == "COOLDOWN"
    assert len(TradeLifecycleState) == 7


def test_str_enum_side_values():
    assert Side.NONE == "NONE"
    assert Side.LONG == "LONG"
    assert Side.SHORT == "SHORT"
    assert len(Side) == 3


def test_str_enum_timeframe_values():
    assert Timeframe.H4 == "4h"
    assert Timeframe.H1 == "1h"
    assert Timeframe.M30 == "30m"
    assert Timeframe.M15 == "15m"
    assert Timeframe.M5 == "5m"
    assert len(Timeframe) == 5


# ---------------------------------------------------------------------------
# TimeframeSnapshot roundtrip
# ---------------------------------------------------------------------------

def _make_timeframe_snapshot(tf: Timeframe = Timeframe.H1) -> TimeframeSnapshot:
    return TimeframeSnapshot(
        timeframe=tf,
        timestamp=NOW,
        close=3500.0,
        tenkan=3490.0,
        kijun=3480.0,
        cloud_top=3520.0,
        cloud_bottom=3460.0,
        cloud_position=CloudPosition.ABOVE,
        tk_state=TkState.BULLISH,
        poc=3495.0,
        vah=3510.0,
        val=3470.0,
        profile_bias=ProfileBias.ABOVE_VA,
        volume=1500.0,
        volume_sma_5=1400.0,
        volume_sma_20=1300.0,
        atr=45.0,
    )


def test_timeframe_snapshot_all_17_fields():
    """TimeframeSnapshot can be created with all 17 fields."""
    snap = _make_timeframe_snapshot()
    assert snap.timeframe == "1h"  # use_enum_values=True serializes to str
    assert snap.close == 3500.0
    assert snap.cloud_position == "above"
    assert snap.tk_state == "bullish"
    assert snap.profile_bias == "above_va"


def test_timeframe_snapshot_roundtrip():
    """TimeframeSnapshot: model_dump() -> model_validate() roundtrip."""
    snap = _make_timeframe_snapshot()
    data = snap.model_dump()
    restored = TimeframeSnapshot.model_validate(data)
    assert restored.close == snap.close
    assert restored.timeframe == snap.timeframe
    assert restored.cloud_position == snap.cloud_position
    assert restored.atr == snap.atr


def test_timeframe_snapshot_all_timeframes():
    """TimeframeSnapshot can be created for each of the 5 timeframes."""
    for tf in Timeframe:
        snap = _make_timeframe_snapshot(tf)
        assert snap.timeframe == tf.value


# ---------------------------------------------------------------------------
# Zone roundtrip
# ---------------------------------------------------------------------------

def test_zone_create_and_roundtrip():
    """Zone: create, serialize, deserialize."""
    zone = Zone(
        id="zone-001",
        level=3500.0,
        low=3480.0,
        mid=3500.0,
        high=3520.0,
        timeframe=Timeframe.H4,
        source="ichimoku_kijun",
    )
    data = zone.model_dump()
    restored = Zone.model_validate(data)
    assert restored.id == zone.id
    assert restored.level == zone.level
    assert restored.timeframe == "4h"
    assert restored.source == zone.source


# ---------------------------------------------------------------------------
# OHLCV roundtrip
# ---------------------------------------------------------------------------

def test_ohlcv_create_and_roundtrip():
    """OHLCV: create, serialize, deserialize."""
    candle = OHLCV(
        timestamp=NOW,
        open=3480.0,
        high=3530.0,
        low=3470.0,
        close=3510.0,
        volume=2000.0,
    )
    data = candle.model_dump()
    restored = OHLCV.model_validate(data)
    assert restored.open == candle.open
    assert restored.high == candle.high
    assert restored.close == candle.close
    assert restored.volume == candle.volume


# ---------------------------------------------------------------------------
# SymbolState tests
# ---------------------------------------------------------------------------

def test_symbol_state_defaults():
    """SymbolState defaults match spec: regime=HTF_NEUTRAL, mode=MODE_NO_TRADE, setup=IDLE, lifecycle=FLAT, side=NONE."""
    state = SymbolState(symbol="ETHUSDT")
    assert state.regime == "HTF_NEUTRAL"
    assert state.mode == "MODE_NO_TRADE"
    assert state.setup == "IDLE"
    assert state.lifecycle == "FLAT"
    assert state.side == "NONE"
    assert state.setup_version == 0
    assert state.active_zone_id is None
    assert state.avg_entry_price is None
    assert state.filled_qty is None
    assert state.stop_price is None
    assert state.tp1_price is None
    assert state.tp2_price is None
    assert state.tp3_price is None
    assert state.cooldown_until is None
    assert state.entry_timestamp is None
    assert state.last_transition_reason == ""


def test_symbol_state_fully_populated_roundtrip():
    """SymbolState with all fields populated: create and roundtrip."""
    state = SymbolState(
        symbol="ETHUSDT",
        regime=RegimeState.HTF_BULLISH,
        mode=ModeState.MODE_TREND_LONG,
        setup=SetupState.ENTRY_READY,
        lifecycle=TradeLifecycleState.OPEN_STAGE1,
        side=Side.LONG,
        setup_version=3,
        active_zone_id="zone-042",
        avg_entry_price=3450.0,
        filled_qty=0.5,
        stop_price=3400.0,
        tp1_price=3550.0,
        tp2_price=3650.0,
        tp3_price=3800.0,
        cooldown_until=NOW,
        entry_timestamp=NOW,
        last_transition_reason="trigger_confirmed",
    )
    data = state.model_dump()
    restored = SymbolState.model_validate(data)
    assert restored.symbol == "ETHUSDT"
    assert restored.regime == "HTF_BULLISH"
    assert restored.mode == "MODE_TREND_LONG"
    assert restored.lifecycle == "OPEN_STAGE1"
    assert restored.side == "LONG"
    assert restored.stop_price == 3400.0
    assert restored.tp1_price == 3550.0
    assert restored.setup_version == 3
    assert restored.active_zone_id == "zone-042"


# ---------------------------------------------------------------------------
# GlobalState tests
# ---------------------------------------------------------------------------

def test_global_state_defaults():
    """GlobalState defaults: engine=BOOTSTRAPPING, risk_gate=BLOCK."""
    gs = GlobalState()
    assert gs.engine == "BOOTSTRAPPING"
    assert gs.risk_gate == "BLOCK"
    assert gs.total_risk_exposure_pct == 0.0
    assert gs.pending_risk_pct == 0.0
    assert gs.consecutive_losses == 0


def test_global_state_roundtrip():
    """GlobalState: create with all fields, roundtrip."""
    gs = GlobalState(
        engine=EngineState.READY,
        risk_gate=RiskGate.ALLOW,
        total_risk_exposure_pct=0.5,
        pending_risk_pct=0.1,
        consecutive_losses=2,
    )
    data = gs.model_dump()
    restored = GlobalState.model_validate(data)
    assert restored.engine == "READY"
    assert restored.risk_gate == "ALLOW"
    assert restored.total_risk_exposure_pct == 0.5
    assert restored.consecutive_losses == 2


# ---------------------------------------------------------------------------
# TradingState tests
# ---------------------------------------------------------------------------

def test_trading_state_with_two_symbols_roundtrip():
    """TradingState with GlobalState + ETHUSDT + BTCUSDT: roundtrip."""
    ts = TradingState(
        global_state=GlobalState(engine=EngineState.READY, risk_gate=RiskGate.ALLOW),
        symbols={
            "ETHUSDT": SymbolState(symbol="ETHUSDT"),
            "BTCUSDT": SymbolState(symbol="BTCUSDT"),
        },
    )
    data = ts.model_dump()
    restored = TradingState.model_validate(data)
    assert restored.global_state.engine == "READY"
    assert "ETHUSDT" in restored.symbols
    assert "BTCUSDT" in restored.symbols
    assert restored.symbols["ETHUSDT"].symbol == "ETHUSDT"


def test_trading_state_json_roundtrip():
    """TradingState: model_dump_json() -> model_validate_json() roundtrip."""
    ts = TradingState(
        global_state=GlobalState(engine=EngineState.READY, risk_gate=RiskGate.ALLOW),
        symbols={
            "ETHUSDT": SymbolState(
                symbol="ETHUSDT",
                lifecycle=TradeLifecycleState.OPEN_STAGE0,
                stop_price=3400.0,
                side=Side.LONG,
            ),
        },
    )
    json_str = ts.model_dump_json()
    restored = TradingState.model_validate_json(json_str)
    assert restored.symbols["ETHUSDT"].stop_price == 3400.0
    assert restored.global_state.risk_gate == "ALLOW"


# ---------------------------------------------------------------------------
# MarketSnapshot tests
# ---------------------------------------------------------------------------

def test_market_snapshot_roundtrip():
    """MarketSnapshot with multiple TimeframeSnapshots: create and roundtrip."""
    snaps = {
        tf: _make_timeframe_snapshot(tf)
        for tf in [Timeframe.H4, Timeframe.H1, Timeframe.M15]
    }
    ms = MarketSnapshot(
        symbol="ETHUSDT",
        timestamp=NOW,
        timeframes=snaps,
        zones=[
            Zone(
                id="z1",
                level=3500.0,
                low=3480.0,
                mid=3500.0,
                high=3520.0,
                timeframe=Timeframe.H1,
                source="kijun",
            )
        ],
    )
    data = ms.model_dump()
    restored = MarketSnapshot.model_validate(data)
    assert restored.symbol == "ETHUSDT"
    assert len(restored.timeframes) == 3
    assert len(restored.zones) == 1
    assert restored.zones[0].id == "z1"
