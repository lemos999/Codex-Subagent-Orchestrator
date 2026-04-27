from __future__ import annotations

from datetime import UTC, datetime

from strategy import (
    OrderIntent,
    StateCode,
    StateMachine,
    StrategyStateSnapshot,
    SubState,
    TakeProfitInputs,
    TradeSide,
)


def _fixed_now() -> datetime:
    return datetime(2026, 4, 24, 0, 0, tzinfo=UTC)


def _machine() -> StateMachine:
    snapshot = StrategyStateSnapshot(
        symbol="BTC/USDT:USDT",
        state=int(StateCode.FILLED_FULL),
        side=TradeSide.LONG.value,
        remaining_position_fraction=1.0,
        avg_entry=100.0,
        hard_sl=90.0,
    )
    return StateMachine(
        snapshot,
        now_fn=_fixed_now,
        client_order_id_fn=lambda layer, state_from, state_to: (
            f"test_{layer}_{state_from}_{state_to}"
        ),
    )


def _short_machine() -> StateMachine:
    snapshot = StrategyStateSnapshot(
        symbol="BTC/USDT:USDT",
        state=int(StateCode.FILLED_FULL),
        side=TradeSide.SHORT.value,
        remaining_position_fraction=1.0,
        avg_entry=100.0,
        hard_sl=110.0,
    )
    return StateMachine(
        snapshot,
        now_fn=_fixed_now,
        client_order_id_fn=lambda layer, state_from, state_to: (
            f"test_{layer}_{state_from}_{state_to}"
        ),
    )


def _inputs(
    *,
    a: bool = False,
    b: bool = False,
    c: bool = False,
    use_runner: bool = True,
    price: float | None = None,
    rsi: float | None = None,
    kijun_series: list[float] | None = None,
    fibo_1_0: float = 120.0,
    fibo_1_5: float = 150.0,
    bar_id: int | None = None,
) -> TakeProfitInputs:
    return TakeProfitInputs(
        price=price if price is not None else 160.0 if c else 130.0 if b else 100.0,
        rsi=rsi if rsi is not None else 50.0 if a else 60.0,
        kijun_series=(
            kijun_series
            if kijun_series is not None
            else [103.0, 102.0, 101.0] if a else [101.0, 102.0, 103.0]
        ),
        fibo_1_0=fibo_1_0,
        fibo_1_5=fibo_1_5,
        volume=2000.0 if c else 1000.0,
        volume_sma_20=1000.0,
        use_runner=use_runner,
        bar_id=bar_id,
    )


def test_tp_a_triggers_state_3_to_3a() -> None:
    machine = _machine()

    action = machine.evaluate_take_profit_bar(_inputs(a=True))

    assert action is not None
    assert action.reason == "TP_A"
    assert action.intent == OrderIntent.CLOSE_MARKET
    assert machine.snapshot.state == int(StateCode.FILLED_FULL)
    assert machine.snapshot.sub_state == SubState.A.value
    assert machine.snapshot.remaining_position_fraction == 0.5
    assert action.order is not None
    assert action.order.equity_fraction == 0.5


def test_tp_b_from_3_skips_a() -> None:
    machine = _machine()

    action = machine.evaluate_take_profit_bar(_inputs(b=True))

    assert action is not None
    assert action.reason == "TP_B"
    assert machine.snapshot.sub_state == SubState.AB.value
    assert machine.snapshot.remaining_position_fraction == 0.5


def test_tp_b_from_3a_closes_half_remaining() -> None:
    machine = _machine()
    machine.on_tp_a()

    action = machine.evaluate_take_profit_bar(_inputs(b=True))

    assert action is not None
    assert action.reason == "TP_B"
    assert machine.snapshot.sub_state == SubState.AB.value
    assert machine.snapshot.remaining_position_fraction == 0.25
    assert action.order is not None
    assert action.order.equity_fraction == 0.25


def test_tp_c_runner_enabled() -> None:
    machine = _machine()

    action = machine.evaluate_take_profit_bar(
        _inputs(c=True, use_runner=True, fibo_1_0=170.0)
    )

    assert action is not None
    assert action.reason == "TP_C_RUNNER_START"
    assert action.intent == OrderIntent.TRANSITION
    assert machine.snapshot.state == int(StateCode.RUNNER)
    assert machine.snapshot.remaining_position_fraction == 1.0


def test_tp_c_runner_disabled() -> None:
    machine = _machine()

    action = machine.evaluate_take_profit_bar(
        _inputs(c=True, use_runner=False, fibo_1_0=170.0)
    )

    assert action is not None
    assert action.reason == "TP_C_EXIT"
    assert action.intent == OrderIntent.CLOSE_MARKET
    assert machine.snapshot.state == int(StateCode.IDLE)
    assert machine.snapshot.remaining_position_fraction == 0.0
    assert action.order is not None
    assert action.order.equity_fraction == 1.0


def test_tp_priority_same_bar() -> None:
    machine = _machine()

    action = machine.evaluate_take_profit_bar(_inputs(a=True, b=True, c=True))

    assert action is not None
    assert action.reason == "TP_A"
    assert machine.snapshot.sub_state == SubState.A.value
    assert machine.snapshot.remaining_position_fraction == 0.5


def test_tp_priority_same_bar_repeated_evaluation_does_not_chain() -> None:
    machine = _machine()

    first = machine.evaluate_take_profit_bar(_inputs(a=True, b=True, c=True, bar_id=100))
    second = machine.evaluate_take_profit_bar(_inputs(a=True, b=True, c=True, bar_id=100))

    assert first is not None
    assert first.reason == "TP_A"
    assert second is None
    assert machine.snapshot.sub_state == SubState.A.value
    assert machine.snapshot.remaining_position_fraction == 0.5


def test_hard_sl_priority_guard() -> None:
    machine = _machine()

    action = machine.evaluate_exit_bar(
        bar_low=89.0,
        bar_high=160.0,
        take_profit=_inputs(a=True, b=True, c=True),
    )

    assert action is not None
    assert action.reason == "HARD_SL"
    assert machine.snapshot.state == int(StateCode.IDLE)
    assert machine.snapshot.cooldown_until == "2026-04-25T00:00:00+00:00"


def test_runner_boundary_ignores_tp_abc() -> None:
    machine = _machine()
    machine.snapshot.state = int(StateCode.RUNNER)

    action = machine.evaluate_take_profit_bar(_inputs(a=True, b=True, c=True))

    assert action is None
    assert machine.snapshot.state == int(StateCode.RUNNER)
    assert machine.snapshot.remaining_position_fraction == 1.0


def test_short_tp_b_uses_downside_fibo_threshold() -> None:
    machine = _short_machine()

    action = machine.evaluate_take_profit_bar(_inputs(b=True, price=80.0, rsi=40.0))

    assert action is not None
    assert action.reason == "TP_B"
    assert action.order is not None
    assert action.order.side == TradeSide.LONG


def test_short_tp_a_uses_mirrored_rsi_and_kijun_condition() -> None:
    machine = _short_machine()

    action = machine.evaluate_take_profit_bar(
        _inputs(price=130.0, rsi=50.0, kijun_series=[101.0, 102.0, 103.0])
    )

    assert action is not None
    assert action.reason == "TP_A"
    assert action.order is not None
    assert action.order.side == TradeSide.LONG


def test_short_tp_a_rejects_long_side_bearish_condition() -> None:
    machine = _short_machine()

    action = machine.evaluate_take_profit_bar(
        _inputs(price=130.0, rsi=50.0, kijun_series=[103.0, 102.0, 101.0])
    )

    assert action is None
    assert machine.snapshot.sub_state is None
    assert machine.snapshot.remaining_position_fraction == 1.0


def test_short_tp_c_runner_uses_downside_fibo_threshold() -> None:
    machine = _short_machine()

    action = machine.evaluate_take_profit_bar(
        _inputs(c=True, price=40.0, rsi=40.0, fibo_1_0=30.0, fibo_1_5=50.0)
    )

    assert action is not None
    assert action.reason == "TP_C_RUNNER_START"
    assert machine.snapshot.state == int(StateCode.RUNNER)
