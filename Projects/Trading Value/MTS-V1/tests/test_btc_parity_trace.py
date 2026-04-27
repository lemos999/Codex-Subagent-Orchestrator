from __future__ import annotations

from datetime import UTC, datetime, timedelta

from btc_parity_diff import PyEvent, TvTrade
from btc_parity_trace import active_cycle_at, build_cycles, render_trace


def _event(
    event: str,
    minute: int,
    *,
    reason: str | None = None,
    state2_trigger_source: str = "",
) -> PyEvent:
    return PyEvent(
        event=event,
        symbol="BTC",
        side="long",
        ts=datetime(2026, 4, 24, 0, minute, tzinfo=UTC),
        price=100.0,
        reason=reason or event,
        rr=None,
        win=None,
        state2_trigger_source=state2_trigger_source,
    )


def test_build_cycles_groups_signal_entries_and_exit() -> None:
    cycles = build_cycles(
        [
            _event("ENTRY_SIGNAL", 0),
            _event("ENTRY_L1", 5),
            _event("ENTRY_L2", 10),
            _event("EXIT", 15),
        ],
    )

    assert len(cycles) == 1
    assert cycles[0].signal.event == "ENTRY_SIGNAL"
    assert [entry.event for entry in cycles[0].entries] == ["ENTRY_L1", "ENTRY_L2"]
    assert cycles[0].exit is not None
    assert cycles[0].exit.ts.minute == 15


def test_active_cycle_at_finds_blocking_cycle() -> None:
    cycles = build_cycles(
        [
            _event("ENTRY_SIGNAL", 0),
            _event("ENTRY_L1", 5),
            _event("EXIT", 30),
        ],
    )

    assert active_cycle_at(cycles, datetime(2026, 4, 24, 0, 20, tzinfo=UTC)) is cycles[0]
    assert active_cycle_at(cycles, datetime(2026, 4, 24, 0, 40, tzinfo=UTC)) is None


def test_render_trace_includes_matched_cycle_alignment() -> None:
    tv_trade = TvTrade(
        trade_no=1,
        symbol="BTC",
        side="long",
        entry_event="ENTRY_L1",
        entry_ts=datetime(2026, 4, 24, 0, 5, tzinfo=UTC),
        exit_ts=datetime(2026, 4, 24, 0, 15, tzinfo=UTC),
        entry_price=100.0,
        exit_price=101.0,
        net_pnl_pct=0.01,
    )
    report = render_trace(
        symbol="BTC",
        tv_trades=[tv_trade],
        py_events=[
            _event("ENTRY_SIGNAL", 0),
            _event("ENTRY_L1", 5),
            _event("EXIT", 15),
        ],
        tolerance=timedelta(minutes=15),
        examples=4,
    )

    assert "## Matched Cycle Alignment" in report
    assert "| 1 | ENTRY_L1 | long | 1 |" in report
    assert "| true |" in report


def test_render_trace_displays_state2_trigger_source() -> None:
    tv_trade = TvTrade(
        trade_no=1,
        symbol="BTC",
        side="long",
        entry_event="ENTRY_L1",
        entry_ts=datetime(2026, 4, 24, 0, 5, tzinfo=UTC),
        exit_ts=datetime(2026, 4, 24, 0, 45, tzinfo=UTC),
        entry_price=100.0,
        exit_price=101.0,
        net_pnl_pct=0.01,
    )
    report = render_trace(
        symbol="BTC",
        tv_trades=[tv_trade],
        py_events=[
            _event("ENTRY_SIGNAL", 0),
            _event("ENTRY_L1", 5),
            _event("EXIT", 45, reason="STATE_2_ABORT", state2_trigger_source="reverse_spike"),
        ],
        tolerance=timedelta(minutes=15),
        examples=4,
    )

    assert "Python State2 trigger" in report
    assert "reverse_spike" in report
