"""Tests for state machine invariants — design doc §11.

These tests define the contract that the engine must enforce.
Helper functions here are pure checks on the state model;
actual enforcement will live in the engine layer.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from trading_value.core.models import (
    EngineState,
    GlobalState,
    ModeState,
    RegimeState,
    RiskGate,
    SetupState,
    Side,
    SymbolState,
    TradeLifecycleState,
    TradingState,
)

NOW = datetime(2026, 3, 20, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Invariant helper functions (pure, no engine dependency)
# ---------------------------------------------------------------------------

def check_invariant_stop_price(state: SymbolState) -> bool:
    """Returns True if the stop-price invariant holds.

    §11: 'TradeLifecycleState != FLAT이면 반드시 보호 손절 가격이 존재해야 한다.'
    FLAT and COOLDOWN are exempt; all other lifecycle states require stop_price.
    """
    exempt = {TradeLifecycleState.FLAT, TradeLifecycleState.COOLDOWN}
    if state.lifecycle in exempt or state.lifecycle == "FLAT" or state.lifecycle == "COOLDOWN":
        return True
    return state.stop_price is not None


def check_invariant_no_opposite(trading_state: TradingState, symbol: str, new_side: Side) -> bool:
    """Returns True if submitting new_side does not create an opposite-direction conflict.

    §11: '반대 방향 주문과 포지션은 동시에 존재할 수 없다.'
    A new entry is allowed only if the symbol is FLAT (no open position).
    """
    sym_state = trading_state.symbols.get(symbol)
    if sym_state is None:
        return True  # symbol not tracked yet — no conflict
    if sym_state.lifecycle in (TradeLifecycleState.FLAT, "FLAT"):
        return True
    # Position is open: opposite direction is a conflict
    current_side = sym_state.side
    if current_side in (Side.NONE, "NONE"):
        return True
    opposite = {Side.LONG: Side.SHORT, Side.SHORT: Side.LONG}
    return opposite.get(current_side) != new_side


def check_invariant_engine_ready_for_entry(global_state: GlobalState) -> bool:
    """Returns True if the engine is READY to submit entry orders.

    §11: 'ENTRY_READY 상태라도 EngineState != READY면 주문을 내지 않는다.'
    """
    return global_state.engine in (EngineState.READY, "READY")


def check_invariant_no_duplicate_setup_version(
    trading_state: TradingState,
    symbol: str,
    new_setup_version: int,
) -> bool:
    """Returns True if this setup_version has not yet submitted an order.

    §11: '동일 setup_version에 대해 중복 주문 제출은 1회만 허용한다.'
    A duplicate is detected when the current symbol's lifecycle is NOT FLAT/IDLE
    and setup_version matches.
    """
    sym_state = trading_state.symbols.get(symbol)
    if sym_state is None:
        return True
    flat_states = {TradeLifecycleState.FLAT, "FLAT"}
    if sym_state.lifecycle in flat_states:
        return True  # no active order for this setup_version
    return sym_state.setup_version != new_setup_version


def check_invariant_risk_gate_block_forces_no_trade(
    global_state: GlobalState,
    effective_mode: ModeState | str,
) -> bool:
    """Returns True if RiskGate==BLOCK is correctly enforced as MODE_NO_TRADE.

    §6: 'RiskGate == BLOCK이면 ModeState를 내부적으로 MODE_NO_TRADE로 강등'
    """
    if global_state.risk_gate in (RiskGate.BLOCK, "BLOCK"):
        return effective_mode in (ModeState.MODE_NO_TRADE, "MODE_NO_TRADE")
    return True  # ALLOW or REDUCE — no constraint


def check_invariant_htf_bullish_rebound_short_risk(risk_pct: float) -> bool:
    """Returns True if REBOUND_SHORT in HTF_BULLISH uses at most 0.25% risk.

    Spec v2 §13.1: 'REBOUND_SHORT in HTF_BULLISH uses reduced risk (0.25% not 0.35%).'
    """
    return risk_pct <= 0.0025


def check_invariant_reboot_mismatch(
    local_lifecycle: TradeLifecycleState | str,
    exchange_has_position: bool,
) -> bool:
    """Returns True if local state matches exchange reality after reboot.

    §11: '재기동 후 로컬 상태와 거래소 실포지션이 다르면 즉시 DEGRADED 또는 HALTED로 간다.'
    Mismatch: local says FLAT but exchange has a position, or vice versa.
    """
    local_flat = local_lifecycle in (TradeLifecycleState.FLAT, "FLAT")
    if local_flat and exchange_has_position:
        return False  # mismatch: must go DEGRADED/HALTED
    if not local_flat and not exchange_has_position:
        return False  # mismatch: must go DEGRADED/HALTED
    return True


# ---------------------------------------------------------------------------
# §11 Invariant tests
# ---------------------------------------------------------------------------

def test_flat_has_no_stop_price():
    """§11: If lifecycle is FLAT, stop_price must be None — invariant holds by default."""
    state = SymbolState(symbol="ETHUSDT")
    assert state.lifecycle == TradeLifecycleState.FLAT
    assert state.stop_price is None
    assert check_invariant_stop_price(state) is True


def test_open_position_requires_stop_price_invariant_fails_when_missing():
    """§11: If lifecycle is OPEN_STAGE0/1/2, stop_price must exist.

    Creating an OPEN state without stop_price violates the invariant.
    The check function returns False (engine must enforce this).
    """
    state = SymbolState(
        symbol="ETHUSDT",
        lifecycle=TradeLifecycleState.OPEN_STAGE0,
        stop_price=None,  # invariant violation
    )
    assert not check_invariant_stop_price(state)


def test_open_position_with_stop_price_invariant_passes():
    """§11: OPEN_STAGE0 with stop_price present satisfies the invariant."""
    state = SymbolState(
        symbol="ETHUSDT",
        lifecycle=TradeLifecycleState.OPEN_STAGE0,
        stop_price=3400.0,
        side=Side.LONG,
    )
    assert check_invariant_stop_price(state) is True


def test_all_open_stages_require_stop_price():
    """§11: All OPEN_STAGE* and ENTRY_WORKING states fail invariant without stop_price."""
    open_states = [
        TradeLifecycleState.OPEN_STAGE0,
        TradeLifecycleState.OPEN_STAGE1,
        TradeLifecycleState.OPEN_STAGE2,
        TradeLifecycleState.ENTRY_WORKING,
        TradeLifecycleState.EXIT_WORKING,
    ]
    for lc in open_states:
        state = SymbolState(symbol="ETHUSDT", lifecycle=lc, stop_price=None)
        assert not check_invariant_stop_price(state), f"{lc} without stop_price should fail"


def test_cooldown_exempt_from_stop_price_invariant():
    """§11: COOLDOWN state is exempt from the stop_price requirement."""
    state = SymbolState(
        symbol="ETHUSDT",
        lifecycle=TradeLifecycleState.COOLDOWN,
        stop_price=None,
        cooldown_until=NOW + timedelta(minutes=30),
    )
    assert check_invariant_stop_price(state) is True


def test_no_opposite_direction_same_symbol():
    """§11: '반대 방향 주문과 포지션은 동시에 존재할 수 없다.'

    An open LONG position must block a new SHORT entry on the same symbol.
    """
    ts = TradingState(
        global_state=GlobalState(),
        symbols={
            "ETHUSDT": SymbolState(
                symbol="ETHUSDT",
                lifecycle=TradeLifecycleState.OPEN_STAGE1,
                side=Side.LONG,
                stop_price=3400.0,
            )
        },
    )
    # Attempting a SHORT entry must be detected as a conflict
    assert check_invariant_no_opposite(ts, "ETHUSDT", Side.SHORT) is False
    # Attempting another LONG is not an opposite-direction conflict
    assert check_invariant_no_opposite(ts, "ETHUSDT", Side.LONG) is True


def test_no_opposite_direction_when_flat():
    """§11: When FLAT, both directions are permitted (no conflict)."""
    ts = TradingState(
        global_state=GlobalState(),
        symbols={"ETHUSDT": SymbolState(symbol="ETHUSDT")},
    )
    assert check_invariant_no_opposite(ts, "ETHUSDT", Side.LONG) is True
    assert check_invariant_no_opposite(ts, "ETHUSDT", Side.SHORT) is True


def test_mode_only_changes_on_bar_close():
    """§11: 'ModeState는 봉 마감에서만 바뀌며 틱 단위로 뒤집지 않는다.'

    This invariant is behavioral (engine-level). We verify the model itself
    does not change mode autonomously — mode is only changed by explicit assignment.
    Two SymbolState instances with the same parameters retain their mode.
    """
    state1 = SymbolState(symbol="ETHUSDT", mode=ModeState.MODE_TREND_LONG)
    state2 = SymbolState(symbol="ETHUSDT", mode=ModeState.MODE_TREND_LONG)
    # Model does not self-modify mode between ticks
    assert state1.mode == state2.mode == "MODE_TREND_LONG"
    # Simulated bar-close: engine assigns new mode explicitly
    data = state1.model_dump()
    data["mode"] = ModeState.MODE_NO_TRADE
    updated = SymbolState.model_validate(data)
    assert updated.mode == "MODE_NO_TRADE"
    # Original state unchanged
    assert state1.mode == "MODE_TREND_LONG"


def test_no_entry_when_engine_not_ready():
    """§11: 'ENTRY_READY 상태라도 EngineState != READY면 주문을 내지 않는다.'"""
    non_ready_states = [
        EngineState.BOOTSTRAPPING,
        EngineState.WARMUP,
        EngineState.DEGRADED,
        EngineState.HALTED,
    ]
    for es in non_ready_states:
        gs = GlobalState(engine=es)
        assert check_invariant_engine_ready_for_entry(gs) is False, f"{es} should block entry"

    gs_ready = GlobalState(engine=EngineState.READY)
    assert check_invariant_engine_ready_for_entry(gs_ready) is True


def test_duplicate_setup_version_blocked():
    """§11: '동일 setup_version에 대해 중복 주문 제출은 1회만 허용한다.'

    If symbol is already in a non-FLAT state with setup_version=5,
    submitting another order with setup_version=5 must be blocked.
    """
    ts = TradingState(
        global_state=GlobalState(engine=EngineState.READY, risk_gate=RiskGate.ALLOW),
        symbols={
            "ETHUSDT": SymbolState(
                symbol="ETHUSDT",
                lifecycle=TradeLifecycleState.ENTRY_WORKING,
                setup_version=5,
                side=Side.LONG,
            )
        },
    )
    # Same setup_version → duplicate → blocked
    assert check_invariant_no_duplicate_setup_version(ts, "ETHUSDT", 5) is False
    # Different setup_version → allowed
    assert check_invariant_no_duplicate_setup_version(ts, "ETHUSDT", 6) is True


def test_reboot_mismatch_halts():
    """§11: '재기동 후 로컬 상태와 거래소 실포지션이 다르면 즉시 DEGRADED 또는 HALTED'."""
    # Case 1: local=FLAT but exchange has a position → mismatch
    assert check_invariant_reboot_mismatch(TradeLifecycleState.FLAT, exchange_has_position=True) is False

    # Case 2: local=OPEN_STAGE1 but exchange has no position → mismatch
    assert check_invariant_reboot_mismatch(TradeLifecycleState.OPEN_STAGE1, exchange_has_position=False) is False

    # Case 3: both agree — FLAT with no exchange position → ok
    assert check_invariant_reboot_mismatch(TradeLifecycleState.FLAT, exchange_has_position=False) is True

    # Case 4: both agree — open locally and exchange has position → ok
    assert check_invariant_reboot_mismatch(TradeLifecycleState.OPEN_STAGE0, exchange_has_position=True) is True


def test_htf_bullish_short_reduced_risk():
    """Spec v2 §13.1: REBOUND_SHORT in HTF_BULLISH uses reduced risk (0.25% not 0.35%)."""
    # 0.25% expressed as decimal
    assert check_invariant_htf_bullish_rebound_short_risk(0.0025) is True
    # At the limit
    assert check_invariant_htf_bullish_rebound_short_risk(0.0024) is True
    # Standard 0.35% must fail when HTF_BULLISH + REBOUND_SHORT
    assert check_invariant_htf_bullish_rebound_short_risk(0.0035) is False
    # Verify that 0.26% also fails (above 0.25% limit)
    assert check_invariant_htf_bullish_rebound_short_risk(0.0026) is False


def test_risk_gate_block_forces_no_trade():
    """§6: 'RiskGate == BLOCK이면 ModeState를 내부적으로 MODE_NO_TRADE로 강등.'"""
    gs_block = GlobalState(engine=EngineState.READY, risk_gate=RiskGate.BLOCK)

    # BLOCK + MODE_NO_TRADE → valid
    assert check_invariant_risk_gate_block_forces_no_trade(gs_block, ModeState.MODE_NO_TRADE) is True
    # BLOCK + any active mode → invariant violation
    assert check_invariant_risk_gate_block_forces_no_trade(gs_block, ModeState.MODE_TREND_LONG) is False
    assert check_invariant_risk_gate_block_forces_no_trade(gs_block, ModeState.MODE_PULLBACK_LONG) is False
    assert check_invariant_risk_gate_block_forces_no_trade(gs_block, ModeState.MODE_REBOUND_SHORT) is False

    # ALLOW + any mode → no constraint from this invariant
    gs_allow = GlobalState(engine=EngineState.READY, risk_gate=RiskGate.ALLOW)
    assert check_invariant_risk_gate_block_forces_no_trade(gs_allow, ModeState.MODE_TREND_LONG) is True
    assert check_invariant_risk_gate_block_forces_no_trade(gs_allow, ModeState.MODE_NO_TRADE) is True


def test_entry_blocked_when_risk_gate_block_and_engine_ready():
    """Combined invariant: even with EngineState=READY, BLOCK gate prevents entry.

    §11 + §6: Both conditions must be met for entry to proceed.
    """
    gs = GlobalState(engine=EngineState.READY, risk_gate=RiskGate.BLOCK)
    # Engine IS ready
    assert check_invariant_engine_ready_for_entry(gs) is True
    # But risk gate forces no-trade — effective mode must be NO_TRADE
    assert check_invariant_risk_gate_block_forces_no_trade(gs, ModeState.MODE_TREND_LONG) is False

    # With ALLOW gate, both pass
    gs_ok = GlobalState(engine=EngineState.READY, risk_gate=RiskGate.ALLOW)
    assert check_invariant_engine_ready_for_entry(gs_ok) is True
    assert check_invariant_risk_gate_block_forces_no_trade(gs_ok, ModeState.MODE_TREND_LONG) is True
