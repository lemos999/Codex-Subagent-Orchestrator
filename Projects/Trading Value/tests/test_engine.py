"""Tests for trading_value.core.engine — Phase 4.

Covers: TradingEngine, transition_engine_state, detect_bar_closes.
"""
from __future__ import annotations

from datetime import datetime

import pytest

from trading_value.core.engine import (
    TradingEngine,
    detect_bar_closes,
    transition_engine_state,
)
from trading_value.core.events import EngineEvent, EventType
from trading_value.core.models import EngineState, Timeframe
from trading_value.infra.state_store import StateStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def engine_event(event_type: EventType) -> EngineEvent:
    return EngineEvent(
        event_type=event_type,
        timestamp=datetime.utcnow(),
    )


def ts(hour: int, minute: int) -> datetime:
    return datetime(2024, 1, 1, hour, minute, 0)


# ---------------------------------------------------------------------------
# transition_engine_state — pure function
# ---------------------------------------------------------------------------

class TestTransitionEngineState:

    def test_bootstrapping_to_warmup(self):
        new_state, reason = transition_engine_state(
            EngineState.BOOTSTRAPPING, engine_event(EventType.BOOT_COMPLETED)
        )
        assert new_state == EngineState.WARMUP
        assert "warmup" in reason.lower()

    def test_warmup_to_ready(self):
        new_state, reason = transition_engine_state(
            EngineState.WARMUP,
            engine_event(EventType.HISTORY_READY),
            data_ready=True,
        )
        assert new_state == EngineState.READY

    def test_warmup_history_ready_but_not_data_ready_stays_warmup(self):
        new_state, _ = transition_engine_state(
            EngineState.WARMUP,
            engine_event(EventType.HISTORY_READY),
            data_ready=False,
        )
        assert new_state == EngineState.WARMUP

    def test_ready_to_degraded(self):
        new_state, reason = transition_engine_state(
            EngineState.READY, engine_event(EventType.API_DEGRADED)
        )
        assert new_state == EngineState.DEGRADED

    def test_degraded_to_ready(self):
        new_state, reason = transition_engine_state(
            EngineState.DEGRADED, engine_event(EventType.API_RECOVERED)
        )
        assert new_state == EngineState.READY

    def test_any_to_halted_manual(self):
        for current in [EngineState.BOOTSTRAPPING, EngineState.WARMUP,
                        EngineState.READY, EngineState.DEGRADED]:
            new_state, _ = transition_engine_state(
                current, engine_event(EventType.MANUAL_HALT)
            )
            assert new_state == EngineState.HALTED

    def test_halted_to_warmup(self):
        new_state, reason = transition_engine_state(
            EngineState.HALTED, engine_event(EventType.MANUAL_RESUME)
        )
        assert new_state == EngineState.WARMUP

    def test_risk_limit_breach_halts(self):
        from trading_value.core.events import RiskEvent
        risk_ev = RiskEvent(
            event_type=EventType.RISK_LIMIT_BREACHED,
            timestamp=datetime.utcnow(),
            rule_name="daily_loss",
            current_value=-3.5,
            threshold=-3.0,
        )
        new_state, reason = transition_engine_state(EngineState.READY, risk_ev)
        assert new_state == EngineState.HALTED

    def test_no_matching_transition_returns_current(self):
        # BOOTSTRAPPING + API_DEGRADED -> no transition
        new_state, _ = transition_engine_state(
            EngineState.BOOTSTRAPPING, engine_event(EventType.API_DEGRADED)
        )
        assert new_state == EngineState.BOOTSTRAPPING


# ---------------------------------------------------------------------------
# detect_bar_closes
# ---------------------------------------------------------------------------

class TestDetectBarCloses:

    def test_midnight_all_timeframes(self):
        # 00:00 -> 240min % all = 0 -> all 5 timeframes
        result = detect_bar_closes(ts(0, 0))
        assert Timeframe.H4 in result
        assert Timeframe.H1 in result
        assert Timeframe.M30 in result
        assert Timeframe.M15 in result
        assert Timeframe.M5 in result

    def test_5m_only(self):
        # 00:05 -> only M5 closes
        result = detect_bar_closes(ts(0, 5))
        assert result == [Timeframe.M5]

    def test_15m_and_5m(self):
        # 00:15 -> M15 and M5
        result = detect_bar_closes(ts(0, 15))
        assert Timeframe.M15 in result
        assert Timeframe.M5 in result
        assert Timeframe.M30 not in result

    def test_30m_15m_5m(self):
        # 00:30 -> M30, (15min: 30%15=0 yes), M5
        result = detect_bar_closes(ts(0, 30))
        assert Timeframe.M30 in result
        assert Timeframe.M15 in result
        assert Timeframe.M5 in result

    def test_1h_closes(self):
        # 01:00 -> H1, M30, M15, M5 (but not H4)
        result = detect_bar_closes(ts(1, 0))
        assert Timeframe.H1 in result
        assert Timeframe.H4 not in result

    def test_4h_closes(self):
        # 04:00 -> H4 + H1 + M30 + M15 + M5
        result = detect_bar_closes(ts(4, 0))
        assert Timeframe.H4 in result

    def test_no_close_at_odd_minute(self):
        # 00:07 -> no standard bar closes
        result = detect_bar_closes(ts(0, 7))
        assert result == []

    def test_order_higher_first(self):
        # 04:00 -> [H4, H1, M30, M15, M5]
        result = detect_bar_closes(ts(4, 0))
        assert result[0] == Timeframe.H4
        assert result[-1] == Timeframe.M5


# ---------------------------------------------------------------------------
# TradingEngine
# ---------------------------------------------------------------------------

class TestTradingEngine:

    def test_initialization_with_symbols(self):
        engine = TradingEngine(symbols=["BTCUSDT", "ETHUSDT"])
        assert "BTCUSDT" in engine.symbols
        assert "ETHUSDT" in engine.symbols
        assert engine.engine_state == EngineState.BOOTSTRAPPING

    def test_symbols_in_state(self):
        engine = TradingEngine(symbols=["BTCUSDT"])
        assert "BTCUSDT" in engine.state.symbols

    def test_boot_sets_engine_state_to_warmup(self, tmp_path):
        store = StateStore(base_dir=str(tmp_path))
        engine = TradingEngine(symbols=["BTCUSDT"], state_store=store)
        engine.boot()
        assert engine.engine_state == EngineState.WARMUP

    def test_boot_without_state_store(self):
        engine = TradingEngine(symbols=["BTCUSDT"])
        engine.boot()
        assert engine.engine_state == EngineState.WARMUP

    def test_boot_saves_state(self, tmp_path):
        store = StateStore(base_dir=str(tmp_path))
        engine = TradingEngine(symbols=["BTCUSDT"], state_store=store)
        engine.boot()
        snap = store.load_latest()
        assert snap is not None
        assert snap.state.global_state.engine == EngineState.WARMUP

    def test_get_status_returns_expected_fields(self):
        engine = TradingEngine(symbols=["BTCUSDT", "ETHUSDT"])
        status = engine.get_status()
        assert "engine_state" in status
        assert "risk_gate" in status
        assert "total_risk_exposure_pct" in status
        assert "consecutive_losses" in status
        assert "symbols" in status
        assert "BTCUSDT" in status["symbols"]
        assert "ETHUSDT" in status["symbols"]

    def test_get_status_symbol_has_expected_keys(self):
        engine = TradingEngine(symbols=["BTCUSDT"])
        status = engine.get_status()
        sym = status["symbols"]["BTCUSDT"]
        for key in ("regime", "mode", "setup", "lifecycle", "side", "setup_version"):
            assert key in sym

    def test_initial_engine_state_in_status(self):
        engine = TradingEngine(symbols=["BTCUSDT"])
        status = engine.get_status()
        assert status["engine_state"] == str(EngineState.BOOTSTRAPPING)

    def test_process_system_event_manual_halt(self):
        engine = TradingEngine(symbols=["BTCUSDT"])
        engine.boot()  # -> WARMUP
        engine.process_event(engine_event(EventType.MANUAL_HALT))
        assert engine.engine_state == EngineState.HALTED

    def test_process_system_event_resume_after_halt(self):
        engine = TradingEngine(symbols=["BTCUSDT"])
        engine.boot()
        engine.process_event(engine_event(EventType.MANUAL_HALT))
        engine.process_event(engine_event(EventType.MANUAL_RESUME))
        assert engine.engine_state == EngineState.WARMUP
