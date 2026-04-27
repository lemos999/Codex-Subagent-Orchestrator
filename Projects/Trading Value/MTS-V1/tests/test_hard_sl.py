from __future__ import annotations

from datetime import UTC, datetime

from strategy import (
    Position,
    StateCode,
    StateMachine,
    StrategyStateSnapshot,
    TradeSide,
)


def _fixed_now() -> datetime:
    return datetime(2026, 4, 24, 0, 0, tzinfo=UTC)


def _machine(side: TradeSide = TradeSide.LONG) -> StateMachine:
    snapshot = StrategyStateSnapshot(symbol="BTC/USDT:USDT", side=side.value)
    return StateMachine(
        snapshot,
        now_fn=_fixed_now,
        client_order_id_fn=lambda layer, state_from, state_to: (
            f"test_{layer}_{state_from}_{state_to}"
        ),
    )


def _start_and_fill_l1(machine: StateMachine, side: TradeSide = TradeSide.LONG) -> None:
    machine.snapshot.state = int(StateCode.PENDING)
    machine.snapshot.side = side.value
    machine.snapshot.entry_prices = {"L1": 101.0, "L2": 96.0, "L3": 92.0, "HARD_SL": None}
    machine.on_l1_fill(fill_price=101.0, fill_qty=1.0)


def test_avg_entry_after_l2_fill() -> None:
    machine = _machine()
    _start_and_fill_l1(machine)

    actions = machine.on_l2_fill(
        fill_price=95.0,
        fill_qty=2.0,
        atr_value=4.0,
        poc=100.0,
        kijun=103.0,
        fibo_0618=100.5,
    )

    assert machine.snapshot.avg_entry == (101.0 + 190.0) / 3.0
    assert machine.snapshot.hard_sl == machine.snapshot.avg_entry - 8.0
    assert actions[0].reason == "HARD_SL_REPLACE"
    assert actions[0].stop_order is not None
    assert actions[0].stop_order.stop_price == machine.snapshot.hard_sl


def test_hard_sl_recalc_after_l3() -> None:
    machine = _machine()
    _start_and_fill_l1(machine)
    machine.on_l2_fill(
        fill_price=96.0,
        fill_qty=1.0,
        atr_value=5.0,
        poc=100.0,
        kijun=103.0,
        fibo_0618=100.5,
    )
    hard_sl_after_l2 = machine.snapshot.hard_sl
    hard_sl_id_after_l2 = machine.snapshot.client_order_ids["HARD_SL"]

    actions = machine.on_l3_fill(fill_price=90.0, fill_qty=1.0, atr_value=5.0)

    assert machine.snapshot.state == int(StateCode.FILLED_FULL)
    assert machine.snapshot.avg_entry == (101.0 + 96.0 + 90.0) / 3.0
    assert machine.snapshot.hard_sl < hard_sl_after_l2
    assert [action.reason for action in actions[:2]] == [
        "HARD_SL_CANCEL_REPLACE",
        "HARD_SL_REPLACE",
    ]
    assert actions[0].stop_order is not None
    assert actions[0].stop_order.client_order_id == hard_sl_id_after_l2


def test_hard_sl_hit_triggers_cooldown() -> None:
    machine = _machine()
    _start_and_fill_l1(machine)
    machine.on_l2_fill(
        fill_price=96.0,
        fill_qty=1.0,
        atr_value=5.0,
        poc=100.0,
        kijun=103.0,
        fibo_0618=100.5,
    )
    machine.on_l3_fill(fill_price=90.0, fill_qty=1.0, atr_value=5.0)

    assert machine.check_hard_sl_hit(bar_low=85.0, bar_high=110.0)

    assert machine.snapshot.state == int(StateCode.IDLE)
    assert machine.snapshot.cooldown_until == "2026-04-25T00:00:00+00:00"
    assert machine.snapshot.hard_sl == 0.0


def test_rr_at_least_2_5() -> None:
    position = Position(
        side=TradeSide.LONG,
        entry_prices={"L1": 100.0, "L2": 96.0, "L3": 92.0},
        fill_qtys={"L1": 1.0, "L2": 1.0, "L3": 1.0},
    )
    avg_entry = position.compute_avg_entry()
    hard_sl = position.compute_hard_sl(atr_entry_tf=4.0)
    fibo_1000 = avg_entry + 20.0

    rr = (fibo_1000 - avg_entry) / (avg_entry - hard_sl)

    assert rr >= 2.5


def test_runner_state_ignores_hard_sl_hit() -> None:
    machine = _machine()
    machine.snapshot.state = int(StateCode.RUNNER)
    machine.snapshot.hard_sl = 100.0

    assert not machine.check_hard_sl_hit(bar_low=50.0, bar_high=150.0)
    assert machine.snapshot.state == int(StateCode.RUNNER)
