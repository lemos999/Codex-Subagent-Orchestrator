"""Tests for trading_value.infra.state_store — Phase 4.

Covers: StateStore CRUD, versioning, check_state_consistency.
Uses tmp_path fixture for file isolation.
"""
from __future__ import annotations

import pytest

from trading_value.core.models import (
    EngineState,
    GlobalState,
    SymbolState,
    TradeLifecycleState,
    TradingState,
)
from trading_value.infra.state_store import (
    StateStore,
    check_state_consistency,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_state(**kwargs) -> TradingState:
    return TradingState(**kwargs)


def make_symbol_state(symbol: str, **kwargs) -> SymbolState:
    return SymbolState(symbol=symbol, **kwargs)


# ---------------------------------------------------------------------------
# StateStore — basic persistence
# ---------------------------------------------------------------------------

class TestStateStore:

    def test_save_and_load_latest_roundtrip(self, tmp_path):
        store = StateStore(base_dir=str(tmp_path))
        state = make_state()
        version = store.save(state)
        snapshot = store.load_latest()
        assert snapshot is not None
        assert snapshot.version == version
        assert snapshot.state.global_state.engine == state.global_state.engine

    def test_multiple_saves_increment_version(self, tmp_path):
        store = StateStore(base_dir=str(tmp_path))
        v1 = store.save(make_state())
        v2 = store.save(make_state())
        v3 = store.save(make_state())
        assert v1 == 1
        assert v2 == 2
        assert v3 == 3

    def test_load_version_specific(self, tmp_path):
        store = StateStore(base_dir=str(tmp_path))
        s1 = TradingState(global_state=GlobalState(engine=EngineState.BOOTSTRAPPING))
        s2 = TradingState(global_state=GlobalState(engine=EngineState.WARMUP))
        store.save(s1)
        store.save(s2)
        snap1 = store.load_version(1)
        snap2 = store.load_version(2)
        assert snap1 is not None
        assert snap2 is not None
        assert snap1.state.global_state.engine == EngineState.BOOTSTRAPPING
        assert snap2.state.global_state.engine == EngineState.WARMUP

    def test_list_versions(self, tmp_path):
        store = StateStore(base_dir=str(tmp_path))
        assert store.list_versions() == []
        store.save(make_state())
        store.save(make_state())
        assert store.list_versions() == [1, 2]

    def test_load_latest_no_data_returns_none(self, tmp_path):
        store = StateStore(base_dir=str(tmp_path))
        assert store.load_latest() is None

    def test_load_version_missing_returns_none(self, tmp_path):
        store = StateStore(base_dir=str(tmp_path))
        assert store.load_version(99) is None

    def test_save_preserves_symbols(self, tmp_path):
        store = StateStore(base_dir=str(tmp_path))
        sym = make_symbol_state("BTCUSDT")
        state = TradingState(symbols={"BTCUSDT": sym})
        store.save(state)
        loaded = store.load_latest()
        assert loaded is not None
        assert "BTCUSDT" in loaded.state.symbols

    def test_snapshot_timestamp_is_set(self, tmp_path):
        store = StateStore(base_dir=str(tmp_path))
        store.save(make_state())
        snap = store.load_latest()
        assert snap is not None
        assert snap.timestamp != ""

    def test_load_latest_returns_most_recent(self, tmp_path):
        store = StateStore(base_dir=str(tmp_path))
        store.save(TradingState(global_state=GlobalState(engine=EngineState.BOOTSTRAPPING)))
        store.save(TradingState(global_state=GlobalState(engine=EngineState.READY)))
        snap = store.load_latest()
        assert snap is not None
        assert snap.version == 2
        assert snap.state.global_state.engine == EngineState.READY


# ---------------------------------------------------------------------------
# check_state_consistency
# ---------------------------------------------------------------------------

class TestCheckStateConsistency:

    def test_matching_state_ready(self):
        state = TradingState()
        result = check_state_consistency(state, {}, {})
        assert result.engine_state == EngineState.READY
        assert result.success is True
        assert result.mismatches == []

    def test_flat_local_exchange_position_halted(self):
        sym = make_symbol_state("BTCUSDT", lifecycle=TradeLifecycleState.FLAT)
        state = TradingState(symbols={"BTCUSDT": sym})
        exchange_positions = {"BTCUSDT": {"side": "LONG", "qty": 0.5}}
        result = check_state_consistency(state, exchange_positions, {})
        assert result.engine_state == EngineState.HALTED
        assert result.success is False
        assert any("BTCUSDT" in m for m in result.mismatches)

    def test_open_local_no_exchange_position_halted(self):
        sym = make_symbol_state(
            "BTCUSDT",
            lifecycle=TradeLifecycleState.OPEN_STAGE0,
            stop_price=40000.0,
            filled_qty=0.5,
        )
        state = TradingState(symbols={"BTCUSDT": sym})
        exchange_positions = {"BTCUSDT": {"side": "LONG", "qty": 0.0}}
        result = check_state_consistency(state, exchange_positions, {})
        assert result.engine_state == EngineState.HALTED

    def test_open_stop_price_none_halted(self):
        sym = make_symbol_state(
            "BTCUSDT",
            lifecycle=TradeLifecycleState.OPEN_STAGE0,
            stop_price=None,
            filled_qty=0.5,
        )
        state = TradingState(symbols={"BTCUSDT": sym})
        exchange_positions = {"BTCUSDT": {"side": "LONG", "qty": 0.5}}
        result = check_state_consistency(state, exchange_positions, {})
        assert result.engine_state == EngineState.HALTED
        assert any("stop_price" in m for m in result.mismatches)

    def test_qty_mismatch_degraded(self):
        sym = make_symbol_state(
            "BTCUSDT",
            lifecycle=TradeLifecycleState.OPEN_STAGE1,
            stop_price=40000.0,
            filled_qty=1.0,
        )
        state = TradingState(symbols={"BTCUSDT": sym})
        exchange_positions = {"BTCUSDT": {"side": "LONG", "qty": 0.5}}
        # Provide a stop order so the stop check passes
        exchange_orders = {"BTCUSDT": [{"type": "STOP_MARKET", "price": 40000}]}
        result = check_state_consistency(state, exchange_positions, exchange_orders)
        assert result.engine_state == EngineState.DEGRADED
        assert any("qty mismatch" in m for m in result.mismatches)

    def test_empty_state_and_positions_ready(self):
        state = TradingState()
        result = check_state_consistency(state, {}, {})
        assert result.engine_state == EngineState.READY

    def test_cooldown_lifecycle_treated_as_flat(self):
        sym = make_symbol_state("ETHUSDT", lifecycle=TradeLifecycleState.COOLDOWN)
        state = TradingState(symbols={"ETHUSDT": sym})
        # No exchange position -> matches FLAT/COOLDOWN -> READY
        result = check_state_consistency(state, {}, {})
        assert result.engine_state == EngineState.READY

    def test_multiple_symbols_worst_wins(self):
        sym_ok = make_symbol_state("ETHUSDT", lifecycle=TradeLifecycleState.FLAT)
        sym_bad = make_symbol_state("BTCUSDT", lifecycle=TradeLifecycleState.FLAT)
        state = TradingState(symbols={"ETHUSDT": sym_ok, "BTCUSDT": sym_bad})
        # BTCUSDT has exchange position but local is FLAT -> HALTED
        exchange_positions = {"BTCUSDT": {"side": "LONG", "qty": 1.0}}
        result = check_state_consistency(state, exchange_positions, {})
        assert result.engine_state == EngineState.HALTED
