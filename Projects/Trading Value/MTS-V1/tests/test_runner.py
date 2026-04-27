from __future__ import annotations

from datetime import UTC, datetime

from strategy import (
    OrderIntent,
    RunnerInputs,
    StateCode,
    StateMachine,
    StrategyStateSnapshot,
    TakeProfitInputs,
    TradeSide,
)


def _fixed_now() -> datetime:
    return datetime(2026, 4, 24, 0, 0, tzinfo=UTC)


def _machine(*, state: StateCode = StateCode.RUNNER, side: TradeSide = TradeSide.LONG) -> StateMachine:
    snapshot = StrategyStateSnapshot(
        symbol="BTC/USDT:USDT",
        state=int(state),
        side=side.value,
        remaining_position_fraction=0.30,
        avg_entry=100.0,
        hard_sl=90.0 if side == TradeSide.LONG else 110.0,
        client_order_ids={"L1": None, "L2": None, "L3": None, "HARD_SL": "hsl_1"},
    )
    return StateMachine(
        snapshot,
        now_fn=_fixed_now,
        client_order_id_fn=lambda layer, state_from, state_to: (
            f"test_{layer}_{state_from}_{state_to}"
        ),
    )


def _tp_inputs() -> TakeProfitInputs:
    return TakeProfitInputs(
        price=160.0,
        rsi=50.0,
        kijun_series=[103.0, 102.0, 101.0],
        fibo_1_0=120.0,
        fibo_1_5=150.0,
        volume=2000.0,
        volume_sma_20=1000.0,
        use_runner=True,
    )


def test_enter_runner_from_tp_c_cancels_hard_sl_and_preserves_remaining() -> None:
    machine = _machine(state=StateCode.FILLED_FULL)

    action = machine.on_tp_c(use_runner=True)

    assert action is not None
    assert action.reason == "TP_C_RUNNER_START"
    assert action.intent == OrderIntent.TRANSITION
    assert action.cancel_order_ids == ("hsl_1",)
    assert action.stop_order is not None
    assert action.stop_order.client_order_id == "hsl_1"
    assert machine.snapshot.state == int(StateCode.RUNNER)
    assert machine.snapshot.remaining_position_fraction == 0.30
    assert machine.snapshot.hard_sl == 0.0
    assert machine.snapshot.client_order_ids["HARD_SL"] is None


def test_runner_ignores_tp_abc() -> None:
    machine = _machine()

    action = machine.evaluate_take_profit_bar(_tp_inputs())

    assert action is None
    assert machine.snapshot.state == int(StateCode.RUNNER)
    assert machine.snapshot.remaining_position_fraction == 0.30


def test_runner_ignores_hard_sl() -> None:
    machine = _machine()

    hit = machine.check_hard_sl_hit(bar_low=1.0, bar_high=200.0)

    assert hit is False
    assert machine.snapshot.state == int(StateCode.RUNNER)
    assert machine.snapshot.cooldown_until is None


def test_kijun_2bar_break_closes_and_sets_cooldown() -> None:
    machine = _machine()

    action = machine.tick(
        runner=RunnerInputs(
            close_prev=95.0,
            open_cur=94.0,
            kijun_prev=100.0,
            kijun_cur=100.0,
        )
    )

    assert action is not None
    assert action.reason == "RUNNER_KIJUN_BREAK"
    assert action.intent == OrderIntent.CLOSE_MARKET
    assert action.order is not None
    assert action.order.side == TradeSide.SHORT
    assert action.order.equity_fraction == 0.30
    assert machine.snapshot.state == int(StateCode.IDLE)
    assert machine.snapshot.cooldown_until == "2026-04-25T00:00:00+00:00"


def test_kijun_1bar_break_no_exit() -> None:
    machine = _machine()

    action = machine.tick(
        runner=RunnerInputs(
            close_prev=101.0,
            open_cur=94.0,
            kijun_prev=100.0,
            kijun_cur=100.0,
        )
    )

    assert action is None
    assert machine.snapshot.state == int(StateCode.RUNNER)
    assert machine.snapshot.cooldown_until is None


def test_short_runner_kijun_2bar_upside_break_closes() -> None:
    machine = _machine(side=TradeSide.SHORT)

    action = machine.tick(
        runner=RunnerInputs(
            close_prev=105.0,
            open_cur=106.0,
            kijun_prev=100.0,
            kijun_cur=100.0,
        )
    )

    assert action is not None
    assert action.reason == "RUNNER_KIJUN_BREAK"
    assert action.order is not None
    assert action.order.side == TradeSide.LONG
    assert machine.snapshot.state == int(StateCode.IDLE)
