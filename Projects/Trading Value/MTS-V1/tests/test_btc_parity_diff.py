from __future__ import annotations

from datetime import UTC, datetime, timedelta

from btc_parity_diff import (
    PyEvent,
    TvTrade,
    classify_unmatched_trade,
    closed_cycle_entries,
    exit_reason_summary,
    match_trades,
    matched_exit_cause_bucket,
    matched_exit_timing_bucket,
    matched_exit_timing_residuals,
    py_state2_trigger_source,
    render_report,
    state2_trigger_source_summary,
    worst_exit_price_residuals,
)


def _tv(trade_no: int, minute: int) -> TvTrade:
    return TvTrade(
        trade_no=trade_no,
        symbol="BTC",
        side="long",
        entry_event="ENTRY_L1",
        entry_ts=datetime(2026, 4, 24, 0, minute, tzinfo=UTC),
        exit_ts=None,
        entry_price=100.0,
        exit_price=None,
        net_pnl_pct=None,
    )


def _py(minute: int) -> PyEvent:
    return PyEvent(
        event="ENTRY_L1",
        symbol="BTC",
        side="long",
        ts=datetime(2026, 4, 24, 0, minute, tzinfo=UTC),
        price=100.0,
        reason="L1_FILL",
        rr=None,
        win=None,
    )


def _py_with(event: str, minute: int, side: str = "long") -> PyEvent:
    return PyEvent(
        event=event,
        symbol="BTC",
        side=side,
        ts=datetime(2026, 4, 24, 0, minute, tzinfo=UTC),
        price=100.0,
        reason=f"{event}_{side}",
        rr=None,
        win=None,
    )


def _event(event: str, minute: int) -> PyEvent:
    return PyEvent(
        event=event,
        symbol="BTC",
        side="long",
        ts=datetime(2026, 4, 24, 0, minute, tzinfo=UTC),
        price=100.0,
        reason=event,
        rr=None,
        win=None,
    )


def _exit(
    minute: int,
    price: float,
    reason: str = "HARD_SL",
    *,
    state2_trigger_source: str = "",
    state2_reverse_spike: bool | None = None,
    state2_htf_cross: bool | None = None,
) -> PyEvent:
    return PyEvent(
        event="EXIT",
        symbol="BTC",
        side="long",
        ts=datetime(2026, 4, 24, 0, minute, tzinfo=UTC),
        price=price,
        reason=reason,
        rr=None,
        win=None,
        state2_trigger_source=state2_trigger_source,
        state2_reverse_spike=state2_reverse_spike,
        state2_htf_cross=state2_htf_cross,
    )


def test_match_trades_prefers_global_closest_pair_over_first_tv_row() -> None:
    matches = match_trades(
        [_tv(1, 0), _tv(2, 10)],
        [_py(10)],
        tolerance=timedelta(minutes=15),
    )

    assert matches[0].py is None
    assert matches[1].py is not None
    assert matches[1].delta == timedelta(0)


def test_closed_cycle_entries_require_parent_exit_inside_tv_exit_window() -> None:
    tv = TvTrade(
        trade_no=1,
        symbol="BTC",
        side="long",
        entry_event="ENTRY_L1",
        entry_ts=datetime(2026, 4, 24, 0, 10, tzinfo=UTC),
        exit_ts=datetime(2026, 4, 24, 0, 30, tzinfo=UTC),
        entry_price=100.0,
        exit_price=101.0,
        net_pnl_pct=None,
    )

    entries = closed_cycle_entries(
        [
            _event("ENTRY_SIGNAL", 0),
            _event("ENTRY_L1", 10),
            _event("EXIT", 30),
            _event("ENTRY_SIGNAL", 40),
            _event("ENTRY_L1", 45),
            _event("EXIT", 59),
        ],
        [tv],
        tolerance=timedelta(minutes=5),
    )

    assert [entry.ts.minute for entry in entries] == [10]


def test_worst_exit_price_residuals_sort_by_abs_delta() -> None:
    tv_1 = TvTrade(
        trade_no=1,
        symbol="BTC",
        side="long",
        entry_event="ENTRY_L1",
        entry_ts=datetime(2026, 4, 24, 0, 10, tzinfo=UTC),
        exit_ts=datetime(2026, 4, 24, 0, 30, tzinfo=UTC),
        entry_price=100.0,
        exit_price=101.0,
        net_pnl_pct=None,
    )
    tv_2 = TvTrade(
        trade_no=2,
        symbol="BTC",
        side="long",
        entry_event="ENTRY_L1",
        entry_ts=datetime(2026, 4, 24, 0, 40, tzinfo=UTC),
        exit_ts=datetime(2026, 4, 24, 0, 55, tzinfo=UTC),
        entry_price=100.0,
        exit_price=103.0,
        net_pnl_pct=None,
    )
    py_1 = _py(10)
    py_2 = _py(40)

    residuals = worst_exit_price_residuals(
        match_trades([tv_1, tv_2], [py_1, py_2], tolerance=timedelta(minutes=1)),
        [
            _event("ENTRY_SIGNAL", 0),
            py_1,
            _exit(30, 101.2, "HARD_SL"),
            _event("ENTRY_SIGNAL", 35),
            py_2,
            _exit(55, 104.5, "STATE_2_ABORT"),
        ],
        limit=2,
    )

    assert [residual.tv.trade_no for residual in residuals] == [2, 1]
    assert residuals[0].abs_exit_price_delta == 1.5
    assert residuals[0].py_exit.reason == "STATE_2_ABORT"


def test_classify_unmatched_trade_splits_drift_buckets() -> None:
    tv = _tv(1, 10)

    event_layer = classify_unmatched_trade(
        tv,
        [_py_with("ENTRY_L2", 10)],
        tolerance=timedelta(minutes=15),
    )
    side_drift = classify_unmatched_trade(
        tv,
        [_py_with("ENTRY_L1", 10, side="short")],
        tolerance=timedelta(minutes=15),
    )
    shifted = classify_unmatched_trade(
        _tv(1, 20),
        [_py_with("ENTRY_L3", 0), _py_with("ENTRY_L1", 50)],
        tolerance=timedelta(minutes=15),
    )
    outside = classify_unmatched_trade(
        tv,
        [_py_with("ENTRY_L1", 50)],
        tolerance=timedelta(minutes=5),
    )

    assert event_layer.bucket == "event-layer-drift"
    assert side_drift.bucket == "side-drift"
    assert shifted.bucket == "same-cycle-shift"
    assert outside.bucket == "outside_python_artifact"


def test_exit_reason_summary_groups_matched_python_exit_reasons() -> None:
    tv_1 = TvTrade(
        trade_no=1,
        symbol="BTC",
        side="long",
        entry_event="ENTRY_L1",
        entry_ts=datetime(2026, 4, 24, 0, 10, tzinfo=UTC),
        exit_ts=datetime(2026, 4, 24, 0, 30, tzinfo=UTC),
        entry_price=100.0,
        exit_price=101.0,
        net_pnl_pct=None,
    )
    tv_2 = TvTrade(
        trade_no=2,
        symbol="BTC",
        side="long",
        entry_event="ENTRY_L1",
        entry_ts=datetime(2026, 4, 24, 0, 40, tzinfo=UTC),
        exit_ts=datetime(2026, 4, 24, 0, 55, tzinfo=UTC),
        entry_price=100.0,
        exit_price=103.0,
        net_pnl_pct=None,
    )
    py_1 = _py(10)
    py_2 = _py(40)
    matches = match_trades([tv_1, tv_2], [py_1, py_2], tolerance=timedelta(minutes=1))

    summary = exit_reason_summary(
        matches,
        [
            _event("ENTRY_SIGNAL", 0),
            py_1,
            _exit(30, 101.0, "HARD_SL"),
            _event("ENTRY_SIGNAL", 35),
            py_2,
            _exit(55, 104.5, "STATE_2_ABORT"),
        ],
        tolerance=timedelta(minutes=1),
    )

    assert summary["HARD_SL"]["matched_entries"] == 1
    assert summary["HARD_SL"]["exit_price_within_0_15"] == 1
    assert summary["STATE_2_ABORT"]["matched_entries"] == 1
    assert summary["STATE_2_ABORT"]["exit_price_within_1_0"] == 0


def test_matched_exit_timing_bucket_reports_signed_early_and_late() -> None:
    tv_exit = datetime(2026, 4, 24, 0, 30, tzinfo=UTC)

    early_bucket, early_delta = matched_exit_timing_bucket(
        tv_exit,
        datetime(2026, 4, 24, 0, 0, tzinfo=UTC),
        tolerance=timedelta(minutes=15),
    )
    late_bucket, late_delta = matched_exit_timing_bucket(
        tv_exit,
        datetime(2026, 4, 24, 1, 15, tzinfo=UTC),
        tolerance=timedelta(minutes=15),
    )
    matched_bucket, matched_delta = matched_exit_timing_bucket(
        tv_exit,
        datetime(2026, 4, 24, 0, 40, tzinfo=UTC),
        tolerance=timedelta(minutes=15),
    )

    assert early_bucket == "python_exit_early"
    assert early_delta == timedelta(minutes=-30)
    assert late_bucket == "python_exit_late"
    assert late_delta == timedelta(minutes=45)
    assert matched_bucket == "matched_within_tolerance"
    assert matched_delta == timedelta(minutes=10)


def test_matched_exit_cause_bucket_is_conservative_without_trigger_fields() -> None:
    tv = TvTrade(
        trade_no=1,
        symbol="BTC",
        side="long",
        entry_event="ENTRY_L1",
        entry_ts=datetime(2026, 4, 24, 0, 10, tzinfo=UTC),
        exit_ts=datetime(2026, 4, 24, 1, 30, tzinfo=UTC),
        entry_price=100.0,
        exit_price=101.0,
        net_pnl_pct=None,
    )
    py_entry = _py(10)
    match = match_trades([tv], [py_entry], tolerance=timedelta(minutes=15))[0]

    assert matched_exit_cause_bucket(
        match,
        _exit(10, 100.0, "STATE_2_ABORT"),
        tolerance=timedelta(minutes=15),
    ) == "same_bar_close_or_fill_ordering"
    assert matched_exit_cause_bucket(
        match,
        _exit(45, 100.0, "STATE_2_ABORT"),
        tolerance=timedelta(minutes=15),
    ) == "unknown_state2_abort"
    assert matched_exit_cause_bucket(
        match,
        _exit(45, 100.0, "STATE_2_ABORT", state2_trigger_source="reverse_spike"),
        tolerance=timedelta(minutes=15),
    ) == "state2_reverse_spike"
    assert matched_exit_cause_bucket(
        match,
        _exit(45, 100.0, "HTF_CROSS_ABORT"),
        tolerance=timedelta(minutes=15),
    ) == "htf_cross_pulse"
    assert matched_exit_cause_bucket(
        match,
        _exit(45, 100.0, "REVERSE_SPIKE_ABORT"),
        tolerance=timedelta(minutes=15),
    ) == "reverse_spike_pulse"


def test_py_state2_trigger_source_prefers_explicit_telemetry() -> None:
    assert (
        py_state2_trigger_source(
            _exit(
                45,
                100.0,
                "STATE_2_ABORT",
                state2_trigger_source="both",
                state2_reverse_spike=True,
                state2_htf_cross=True,
            )
        )
        == "both"
    )
    assert (
        py_state2_trigger_source(
            _exit(
                45,
                100.0,
                "STATE_2_ABORT",
                state2_reverse_spike=False,
                state2_htf_cross=True,
            )
        )
        == "htf_cross"
    )
    assert py_state2_trigger_source(_exit(45, 100.0, "STATE_2_ABORT")) == "unknown_state2_abort"


def test_state2_trigger_source_summary_groups_matched_exits() -> None:
    tv_1 = TvTrade(
        trade_no=1,
        symbol="BTC",
        side="long",
        entry_event="ENTRY_L1",
        entry_ts=datetime(2026, 4, 24, 0, 10, tzinfo=UTC),
        exit_ts=datetime(2026, 4, 24, 0, 30, tzinfo=UTC),
        entry_price=100.0,
        exit_price=101.0,
        net_pnl_pct=None,
    )
    tv_2 = TvTrade(
        trade_no=2,
        symbol="BTC",
        side="long",
        entry_event="ENTRY_L1",
        entry_ts=datetime(2026, 4, 24, 0, 40, tzinfo=UTC),
        exit_ts=datetime(2026, 4, 24, 1, 10, tzinfo=UTC),
        entry_price=100.0,
        exit_price=101.0,
        net_pnl_pct=None,
    )
    py_1 = _py(10)
    py_2 = _py(40)

    summary = state2_trigger_source_summary(
        match_trades([tv_1, tv_2], [py_1, py_2], tolerance=timedelta(minutes=15)),
        [
            _event("ENTRY_SIGNAL", 0),
            py_1,
            _exit(30, 101.0, "STATE_2_ABORT", state2_trigger_source="reverse_spike"),
            _event("ENTRY_SIGNAL", 35),
            py_2,
            _exit(50, 101.0, "STATE_2_ABORT", state2_trigger_source="htf_cross"),
        ],
        tolerance=timedelta(minutes=15),
    )

    assert summary["reverse_spike"] == {
        "matched_state2_exits": 1,
        "exit_timestamp_matches": 1,
        "python_exit_early": 0,
        "python_exit_late": 0,
    }
    assert summary["htf_cross"] == {
        "matched_state2_exits": 1,
        "exit_timestamp_matches": 0,
        "python_exit_early": 1,
        "python_exit_late": 0,
    }


def test_matched_exit_timing_residuals_omit_within_tolerance_rows() -> None:
    tv_1 = TvTrade(
        trade_no=1,
        symbol="BTC",
        side="long",
        entry_event="ENTRY_L1",
        entry_ts=datetime(2026, 4, 24, 0, 10, tzinfo=UTC),
        exit_ts=datetime(2026, 4, 24, 0, 30, tzinfo=UTC),
        entry_price=100.0,
        exit_price=101.0,
        net_pnl_pct=None,
    )
    tv_2 = TvTrade(
        trade_no=2,
        symbol="BTC",
        side="long",
        entry_event="ENTRY_L1",
        entry_ts=datetime(2026, 4, 24, 0, 40, tzinfo=UTC),
        exit_ts=datetime(2026, 4, 24, 0, 55, tzinfo=UTC),
        entry_price=100.0,
        exit_price=103.0,
        net_pnl_pct=None,
    )
    py_1 = _py(10)
    py_2 = _py(40)

    residuals = matched_exit_timing_residuals(
        match_trades([tv_1, tv_2], [py_1, py_2], tolerance=timedelta(minutes=1)),
        [
            _event("ENTRY_SIGNAL", 0),
            py_1,
            _exit(30, 101.0, "HARD_SL"),
            _event("ENTRY_SIGNAL", 35),
            py_2,
            _exit(25, 104.5, "STATE_2_ABORT"),
        ],
        tolerance=timedelta(minutes=1),
    )

    assert len(residuals) == 1
    assert residuals[0].tv.trade_no == 2
    assert residuals[0].timing_bucket == "python_exit_early"
    assert residuals[0].signed_exit_delta == timedelta(minutes=-30)
    assert residuals[0].cause_bucket == "unknown_state2_abort"
    assert residuals[0].trigger_source == "unknown_state2_abort"


def test_render_report_includes_exit_residual_section() -> None:
    tv = TvTrade(
        trade_no=1,
        symbol="BTC",
        side="long",
        entry_event="ENTRY_L1",
        entry_ts=datetime(2026, 4, 24, 0, 10, tzinfo=UTC),
        exit_ts=datetime(2026, 4, 24, 0, 30, tzinfo=UTC),
        entry_price=100.0,
        exit_price=101.0,
        net_pnl_pct=None,
    )
    py_entry = _py(10)
    py_events = [_event("ENTRY_SIGNAL", 0), py_entry, _exit(30, 101.2, "HARD_SL")]
    matches = match_trades([tv], [py_entry], tolerance=timedelta(minutes=1))

    report = render_report(
        symbol="BTC",
        tv_path="tv.csv",  # type: ignore[arg-type]
        py_path="py.jsonl",  # type: ignore[arg-type]
        tv_trades=[tv],
        py_entries=[py_entry],
        py_entries_in_window=[py_entry],
        matches=matches,
        tolerance=timedelta(minutes=1),
        examples=3,
        py_events=py_events,
    )

    assert "## Worst Matched Exit Price Residuals" in report
    assert "## Matched Exit Timing Residuals" in report
    assert "matched_exit_timing_residuals" in report
    assert "## Exit Reason Summary" in report
    assert "## Unmatched Classification" in report
    assert "HARD_SL" in report
