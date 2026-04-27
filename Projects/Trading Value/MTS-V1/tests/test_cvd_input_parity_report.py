from __future__ import annotations

from datetime import UTC, datetime, timedelta

from btc_parity_diff import MatchedExitTimingResidual, PyEvent, TvTrade
from cvd_input_parity_report import (
    CvdBar,
    build_cvd_bars,
    build_diagnostics,
    pulse_for_side,
    ratio_for_side,
    reverse_spike_residuals,
)
from strategy import Candle


def _candle(index: int, *, open_: float = 100.0, close: float = 101.0) -> Candle:
    return Candle(
        timestamp=datetime(2026, 4, 1, tzinfo=UTC) + timedelta(minutes=15 * index),
        open=open_,
        high=max(open_, close),
        low=min(open_, close),
        close=close,
        volume=10.0,
    )


def _tv_trade(trade_no: int, *, side: str = "long") -> TvTrade:
    return TvTrade(
        trade_no=trade_no,
        symbol="SOL",
        side=side,
        entry_event="ENTRY_L1",
        entry_ts=datetime(2026, 4, 1, 1, tzinfo=UTC),
        exit_ts=datetime(2026, 4, 1, 6, tzinfo=UTC),
        entry_price=100.0,
        exit_price=99.0,
        net_pnl_pct=None,
    )


def _py_event(
    event: str,
    minutes: int,
    *,
    reason: str = "",
    side: str = "long",
) -> PyEvent:
    return PyEvent(
        event=event,
        symbol="SOL",
        side=side,
        ts=datetime(2026, 4, 1, tzinfo=UTC) + timedelta(minutes=minutes),
        price=100.0,
        reason=reason,
        rr=None,
        win=None,
    )


def test_build_cvd_bars_reconstructs_pine_ltf_formula() -> None:
    candles = [_candle(index) for index in range(19)]
    candles.append(_candle(19, open_=100.0, close=90.0))

    bars = build_cvd_bars(candles, multiplier=2.0)
    last = bars[-1]

    assert last.delta == -100.0
    assert last.abs_sma20 == 14.5
    assert last.threshold == 29.0
    assert pulse_for_side(last, "long") is True
    assert ratio_for_side(last, "long") == 100.0 / 29.0


def test_reverse_spike_residuals_filters_state2_reverse_spike() -> None:
    reverse_residual = MatchedExitTimingResidual(
        tv=_tv_trade(1),
        py_entry=_py_event("ENTRY_L1", 60),
        py_exit=_py_event("EXIT", 120, reason="STATE_2_ABORT"),
        signed_exit_delta=timedelta(minutes=-60),
        timing_bucket="python_exit_early",
        cause_bucket="state2_reverse_spike",
        trigger_source="reverse_spike",
    )
    hard_sl_residual = MatchedExitTimingResidual(
        tv=_tv_trade(2),
        py_entry=_py_event("ENTRY_L1", 60),
        py_exit=_py_event("EXIT", 120, reason="HARD_SL"),
        signed_exit_delta=timedelta(minutes=-60),
        timing_bucket="python_exit_early",
        cause_bucket="non_state2_abort",
        trigger_source="",
    )

    assert reverse_spike_residuals([reverse_residual, hard_sl_residual]) == [
        reverse_residual
    ]


def test_build_diagnostics_labels_isolated_python_pulse() -> None:
    start = datetime(2026, 4, 1, tzinfo=UTC)
    bars = [
        CvdBar(
            index=index,
            ts=start + timedelta(minutes=15 * index),
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.0,
            volume=10.0,
            delta=-5.0 if index == 8 else 0.0,
            abs_sma20=1.0,
            threshold=4.0,
            long_pulse=index == 8,
            short_pulse=False,
        )
        for index in range(30)
    ]
    residual = MatchedExitTimingResidual(
        tv=_tv_trade(1),
        py_entry=_py_event("ENTRY_L1", 60),
        py_exit=_py_event("EXIT", 120, reason="STATE_2_ABORT"),
        signed_exit_delta=timedelta(minutes=-240),
        timing_bucket="python_exit_early",
        cause_bucket="state2_reverse_spike",
        trigger_source="reverse_spike",
    )

    diagnostics = build_diagnostics([residual], bars)

    assert len(diagnostics) == 1
    assert diagnostics[0].classification == "isolated_python_pulse_no_tv_exit_pulse"
