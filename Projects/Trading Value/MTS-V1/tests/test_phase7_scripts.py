from __future__ import annotations

from datetime import UTC, datetime, timedelta

from backtest_runner import (
    CoverageWindow,
    TradeRecord,
    evaluate_symbol,
    evaluate_window,
    load_trade_inputs,
    load_trades_with_coverage,
    main as backtest_main,
    portfolio_avg_r,
    portfolio_total_r,
    split_walk_forward,
    validate_backtest_scope,
    walk_forward_pass_count,
)
from parity_check import TradeEvent, build_metrics, filter_events_by_symbol, main as parity_main


def test_parity_empty_or_incomplete_data_fails() -> None:
    metrics = build_metrics([], [], bar_seconds=3600)

    assert all(not metric.passed for metric in metrics)
    assert all(metric.comparable_count == 0 for metric in metrics)


def test_parity_requires_comparable_cvd_rows() -> None:
    ts = datetime(2026, 4, 24, tzinfo=UTC)

    metrics = build_metrics(
        [TradeEvent(ts=ts, event="ENTRY_L1")],
        [TradeEvent(ts=ts, event="ENTRY_L1")],
        bar_seconds=3600,
    )

    cvd_metric = next(metric for metric in metrics if metric.name == "cvd_sign_match")
    assert cvd_metric.passed is False
    assert cvd_metric.comparable_count == 0


def test_parity_symbol_filter_keeps_unspecified_pine_rows() -> None:
    ts = datetime(2026, 4, 24, tzinfo=UTC)
    events = [
        TradeEvent(ts=ts, event="ENTRY_L1", symbol=None),
        TradeEvent(ts=ts, event="ENTRY_L1", symbol="BTC"),
        TradeEvent(ts=ts, event="ENTRY_L1", symbol="ETH"),
    ]

    filtered = filter_events_by_symbol(events, "BTC")

    assert [event.symbol for event in filtered] == [None, "BTC"]


def test_parity_batch_writes_symbol_reports_and_summary(tmp_path) -> None:  # type: ignore[no-untyped-def]
    pine_dir = tmp_path / "pine"
    pine_dir.mkdir()
    pine_csv = (
        "ts,event,symbol,rr,win,cvd_sign\n"
        "2026-04-24T00:00:00Z,ENTRY_L1,BTCUSDT,,,+1\n"
        "2026-04-24T01:00:00Z,EXIT,BTCUSDT,1.0,true,+1\n"
    )
    (pine_dir / "tradingview_mtsv1_BTC.csv").write_text(pine_csv, encoding="utf-8")
    py_path = tmp_path / "trades.jsonl"
    py_path.write_text(
        "\n".join(
            [
                '{"ts":"2026-04-24T00:00:00Z","event":"ENTRY_L1","symbol":"BTC/USDT:USDT","cvd_sign":1}',
                '{"ts":"2026-04-24T01:00:00Z","event":"EXIT","symbol":"BTC/USDT:USDT","rr":1.0,"win":true,"cvd_sign":1}',
            ]
        ),
        encoding="utf-8",
    )
    report_path = tmp_path / "summary.md"
    report_dir = tmp_path / "reports"

    assert (
        parity_main(
            [
                "--pine-dir",
                str(pine_dir),
                "--py",
                str(py_path),
                "--symbols",
                "BTC",
                "--report",
                str(report_path),
                "--report-dir",
                str(report_dir),
            ]
        )
        == 0
    )

    assert "# MTS-V1 Parity Summary" in report_path.read_text(encoding="utf-8")
    assert (report_dir / "parity_BTC.md").exists()


def test_parity_winrate_requires_matching_24h_windows() -> None:
    pine_ts = datetime(2026, 4, 24, 1, tzinfo=UTC)
    py_ts = datetime(2026, 4, 25, 1, tzinfo=UTC)

    metrics = build_metrics(
        [TradeEvent(ts=pine_ts, event="HARD_SL", win=False)],
        [TradeEvent(ts=py_ts, event="HARD_SL", win=False)],
        bar_seconds=3600,
    )

    winrate_metric = next(metric for metric in metrics if metric.name == "winrate_delta_24h")
    assert winrate_metric.passed is False


def test_backtest_walk_forward_uses_time_windows() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    trades = [
        TradeRecord(ts=start + timedelta(days=day), symbol="BTC/USDT:USDT", rr=3.0)
        for day in (0, 10, 50, 89)
    ]

    windows = split_walk_forward(trades)

    assert [len(window) for window in windows] == [2, 0, 1, 1]


def test_backtest_scope_requires_all_symbols_and_days() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    trades = [
        TradeRecord(ts=start, symbol="BTC/USDT:USDT", rr=3.0),
        TradeRecord(ts=start + timedelta(days=10), symbol="BTC/USDT:USDT", rr=-1.0),
    ]

    errors = validate_backtest_scope(
        trades,
        ["BTC/USDT:USDT", "ETH/USDT:USDT"],
        90,
    )

    assert "missing symbols=['ETH/USDT:USDT']" in errors
    assert any(error.startswith("time span") for error in errors)


def test_backtest_scope_can_use_replay_coverage_metadata() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    trades = [
        TradeRecord(ts=start + timedelta(days=10), symbol="BTC/USDT:USDT", rr=3.0),
        TradeRecord(ts=start + timedelta(days=20), symbol="ETH/USDT:USDT", rr=-1.0),
    ]

    errors = validate_backtest_scope(
        trades,
        ["BTC/USDT:USDT", "ETH/USDT:USDT"],
        90,
        CoverageWindow(start=start, end=start + timedelta(days=90)),
    )

    assert errors == []


def test_walk_forward_requires_portfolio_window_not_single_symbol() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    trades = [
        TradeRecord(
            ts=start + timedelta(minutes=index),
            symbol=("BTC/USDT:USDT" if index % 2 == 0 else "ETH/USDT:USDT"),
            rr=(3.0 if index % 4 else -1.0),
        )
        for index in range(80)
    ]

    assert evaluate_window(trades).passed is True
    assert walk_forward_pass_count(trades, ["BTC/USDT:USDT", "ETH/USDT:USDT"]) == 4


def test_portfolio_score_uses_selected_symbols() -> None:
    ts = datetime(2026, 1, 1, tzinfo=UTC)
    trades = [
        TradeRecord(ts=ts, symbol="BTC/USDT:USDT", rr=2.0),
        TradeRecord(ts=ts, symbol="ETH/USDT:USDT", rr=-1.0),
        TradeRecord(ts=ts, symbol="SOL/USDT:USDT", rr=10.0),
    ]

    assert portfolio_total_r(trades, ["BTC/USDT:USDT", "ETH/USDT:USDT"]) == 1.0
    assert portfolio_avg_r(trades, ["BTC/USDT:USDT", "ETH/USDT:USDT"]) == 0.5


def test_avg_rr_is_payoff_ratio_not_expectancy() -> None:
    ts = datetime(2026, 1, 1, tzinfo=UTC)
    trades = [
        TradeRecord(ts=ts, symbol="BTC/USDT:USDT", rr=3.0),
        TradeRecord(ts=ts, symbol="BTC/USDT:USDT", rr=-1.0),
    ]

    row = evaluate_symbol("BTC/USDT:USDT", trades)

    assert row.avg_rr == 3.0


def test_backtest_discovers_default_trade_logs(tmp_path) -> None:  # type: ignore[no-untyped-def]
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    (logs_dir / "trades_2026-04-24.jsonl").write_text(
        '{"ts":"2026-04-24T00:00:00+00:00","symbol":"BTC/USDT:USDT","rr":3.0}\n',
        encoding="utf-8",
    )

    trades, sources = load_trade_inputs(None, logs_dir)

    assert len(trades) == 1
    assert trades[0].symbol == "BTC/USDT:USDT"
    assert sources == [str(logs_dir / "trades_2026-04-24.jsonl")]


def test_backtest_loads_replay_coverage_metadata(tmp_path) -> None:  # type: ignore[no-untyped-def]
    trades_path = tmp_path / "trades.jsonl"
    trades_path.write_text(
        "\n".join(
            [
                '{"ts":"2026-01-01T00:00:00Z","event":"REPLAY_META",'
                '"coverage_start":"2026-01-01T00:00:00Z",'
                '"coverage_end":"2026-04-01T00:00:00Z"}',
                '{"ts":"2026-01-10T00:00:00Z","symbol":"BTC/USDT:USDT","rr":3.0}',
            ]
        ),
        encoding="utf-8",
    )

    trades, coverage = load_trades_with_coverage(trades_path)

    assert len(trades) == 1
    assert coverage == CoverageWindow(
        start=datetime(2026, 1, 1, tzinfo=UTC),
        end=datetime(2026, 4, 1, tzinfo=UTC),
    )


def test_backtest_main_creates_output_parent(tmp_path) -> None:  # type: ignore[no-untyped-def]
    trades_path = tmp_path / "trades.jsonl"
    trades_path.write_text(
        '{"ts":"2026-04-24T00:00:00Z","symbol":"BTC/USDT:USDT","rr":3.0}\n',
        encoding="utf-8",
    )
    output_path = tmp_path / "nested" / "BACKTEST_VERDICT.md"

    assert backtest_main(["--trades", str(trades_path), "--output", str(output_path)]) == 0

    assert output_path.exists()


def test_backtest_main_accepts_symbol_override(tmp_path, capsys) -> None:  # type: ignore[no-untyped-def]
    trades_path = tmp_path / "trades.jsonl"
    trades_path.write_text(
        "\n".join(
            [
                '{"ts":"2026-01-01T00:00:00Z","event":"REPLAY_META",'
                '"coverage_start":"2026-01-01T00:00:00Z",'
                '"coverage_end":"2026-04-01T00:00:00Z"}',
                '{"ts":"2026-01-10T00:00:00Z","symbol":"BTC/USDT:USDT","rr":3.0}',
            ]
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "BACKTEST_VERDICT.md"

    assert (
        backtest_main(
            [
                "--trades",
                str(trades_path),
                "--symbols",
                "BTC/USDT:USDT",
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    captured = capsys.readouterr()
    assert "Scope: 1 symbols x 90d" in captured.out
    assert "missing symbols" not in captured.out
