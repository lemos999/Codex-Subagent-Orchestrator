from __future__ import annotations

from datetime import UTC, datetime

from strategy import (
    BASE_SIZING_FRAME,
    PROMOTED_SIZING_FRAME,
    STATE_1_TIMEOUT_BARS,
    EntrySignalBar,
    StateCode,
    StateMachine,
    StrategyStateSnapshot,
    TradeSide,
    triple_confluence_active,
)


def _fixed_now() -> datetime:
    return datetime(2026, 4, 24, 0, 0, tzinfo=UTC)


def _machine() -> StateMachine:
    snapshot = StrategyStateSnapshot(symbol="BTC/USDT:USDT")
    return StateMachine(
        snapshot,
        now_fn=_fixed_now,
        client_order_id_fn=lambda layer, state_from, state_to: (
            f"test_{layer}_{state_from}_{state_to}"
        ),
    )


def _start_entry(machine: StateMachine) -> None:
    orders = machine.place_layers(
        avg_fill_fn=None,
        atr_value=10.0,
        poc=100.0,
        kijun=101.0,
        fibo_0618=96.0,
        fibo_0786=94.0,
        val=93.0,
        side=TradeSide.LONG,
        bar_index=11,
    )
    assert len(orders) == 1
    assert orders[0].layer == "L1"


def _fill_l1(machine: StateMachine) -> None:
    actions = machine.on_l1_fill(fill_price=101.5, fill_qty=1.0)
    assert len(actions) == 1
    assert actions[0].layer == "L2"


def test_entry_trigger_long() -> None:
    machine = _machine()

    signal = machine.evaluate_entry_trigger(
        bar=EntrySignalBar(close=101.0, kijun=100.0),
        prev_bar=EntrySignalBar(close=99.0, kijun=100.0),
        htf_bar=EntrySignalBar(close=110.0, kijun=100.0),
        btc_ema_htf=105.0,
        cvd_30m=10.0,
        side=TradeSide.LONG,
    )
    assert signal

    _start_entry(machine)

    assert machine.snapshot.state == int(StateCode.PENDING)
    assert machine.snapshot.entry_prices["L1"] == 101.5
    assert machine.snapshot.sizing_frame == BASE_SIZING_FRAME
    assert machine.snapshot.client_order_ids["L1"] == "test_L1_0_1"
    assert machine.snapshot.client_order_ids["L2"] is None
    assert machine.snapshot.client_order_ids["L3"] is None


def test_entry_trigger_blocks_during_cooldown() -> None:
    machine = _machine()
    machine.snapshot.cooldown_until = "2026-04-24T01:00:00+00:00"

    assert not machine.evaluate_entry_trigger(
        bar=EntrySignalBar(close=101.0, kijun=100.0),
        prev_bar=EntrySignalBar(close=99.0, kijun=100.0),
        htf_bar=EntrySignalBar(close=110.0, kijun=100.0),
        btc_ema_htf=105.0,
        cvd_30m=10.0,
        side=TradeSide.LONG,
    )


def test_triple_confluence_gate_rare() -> None:
    assert triple_confluence_active(poc=100.0, kijun=101.0, fibo_0618=100.5, atr_value=10.0)
    assert not triple_confluence_active(
        poc=100.0,
        kijun=103.0,
        fibo_0618=100.5,
        atr_value=10.0,
    )

    machine = _machine()
    _start_entry(machine)
    _fill_l1(machine)

    actions = machine.on_l2_fill(
        fill_price=96.0,
        fill_qty=1.0,
        atr_value=10.0,
        poc=100.0,
        kijun=101.0,
        fibo_0618=100.5,
    )

    assert machine.snapshot.triple_confluence
    assert machine.snapshot.triple_confluence_evaluated
    assert machine.snapshot.sizing_frame == PROMOTED_SIZING_FRAME
    assert [action.reason for action in actions] == [
        "HARD_SL_REPLACE",
        "TRIPLE_CONFLUENCE_RESIZE_L2",
        "TRIPLE_CONFLUENCE_RESIZE_L3",
        "ENTRY_L3",
    ]


def test_l2_promo_fill_updates_average_without_replacing_hard_sl() -> None:
    machine = _machine()
    _start_entry(machine)
    _fill_l1(machine)
    machine.on_l2_fill(
        fill_price=96.0,
        fill_qty=1.0,
        atr_value=10.0,
        poc=100.0,
        kijun=101.0,
        fibo_0618=100.5,
    )
    hard_sl_after_base_l2 = machine.snapshot.hard_sl

    machine.on_l2_promo_fill(fill_price=96.0, fill_qty=2.0)

    assert machine.snapshot.state == int(StateCode.FILLED_PARTIAL)
    assert machine.snapshot.fill_qtys["L2"] == 3.0
    assert machine.snapshot.avg_entry == ((101.5 * 1.0) + (96.0 * 3.0)) / 4.0
    assert machine.snapshot.hard_sl == hard_sl_after_base_l2


def test_state_2_abort_reverse_spike() -> None:
    machine = _machine()
    _start_entry(machine)
    _fill_l1(machine)

    assert machine.snapshot.state == int(StateCode.FILLED_PARTIAL)
    assert machine.check_state_2_abort(reverse_spike=True, htf_cross=False)

    assert machine.snapshot.state == int(StateCode.IDLE)
    assert machine.snapshot.cooldown_until is None
    assert machine.snapshot.fill_qtys == {"L1": 0.0, "L2": 0.0, "L3": 0.0}


def test_l3_fill_reaches_filled_full() -> None:
    machine = _machine()
    _start_entry(machine)
    _fill_l1(machine)
    machine.on_l2_fill(
        fill_price=96.0,
        fill_qty=1.0,
        atr_value=10.0,
        poc=100.0,
        kijun=103.0,
        fibo_0618=100.5,
    )

    actions = machine.on_l3_fill(fill_price=93.0, fill_qty=1.0)

    assert machine.snapshot.state == int(StateCode.FILLED_FULL)
    assert machine.snapshot.avg_entry == (101.5 + 96.0 + 93.0) / 3.0
    assert actions[0].reason == "FILLED_FULL"


def test_evasion_peak_and_reverse() -> None:
    machine = _machine()
    _start_entry(machine)
    _fill_l1(machine)

    assert machine.check_evasion(
        peak_mfe=0.5,
        atr_value=10.0,
        reverse_spike=True,
        htf_cross=False,
        hours_since_fill=12.0,
    )

    assert machine.snapshot.state == int(StateCode.IDLE)
    assert machine.snapshot.cooldown_until == "2026-04-25T00:00:00+00:00"


def test_evasion_requires_dead_signal_and_48h_window() -> None:
    machine = _machine()
    _start_entry(machine)
    _fill_l1(machine)

    assert not machine.check_evasion(
        peak_mfe=2.0,
        atr_value=10.0,
        reverse_spike=True,
        htf_cross=False,
        hours_since_fill=12.0,
    )
    assert not machine.check_evasion(
        peak_mfe=0.5,
        atr_value=10.0,
        reverse_spike=True,
        htf_cross=False,
        hours_since_fill=49.0,
    )


def test_state_1_timeout_48h() -> None:
    machine = _machine()
    _start_entry(machine)

    assert not machine.check_state_1_timeout(STATE_1_TIMEOUT_BARS - 1)
    assert machine.snapshot.state == int(StateCode.PENDING)

    assert machine.check_state_1_timeout(STATE_1_TIMEOUT_BARS)
    assert machine.snapshot.state == int(StateCode.IDLE)
    assert machine.snapshot.entry_prices == {"L1": 0.0, "L2": 0.0, "L3": None}
