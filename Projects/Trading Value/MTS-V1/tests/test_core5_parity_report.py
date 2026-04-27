from __future__ import annotations

import json
from pathlib import Path

from datetime import timedelta

from core5_parity_report import (
    BTC_BASELINE_ENTRY_MATCHES,
    BTC_BASELINE_EXIT_PRICE_WITHIN_0_15,
    BTC_BASELINE_EXIT_PRICE_WITHIN_1_0,
    BTC_BASELINE_EXIT_TIME_MATCHES,
    BTC_BASELINE_SHA256,
    SymbolParitySummary,
    apply_gate,
    classify_status,
    detail_paths,
    exact_py_path_for_symbol,
    mismatch_class_for_summary,
    parse_symbols,
    render_report,
    summarize_symbol,
    tv_capture_kind,
    tv_raw_path_for_symbol,
    write_detail_reports,
)


def test_classify_status_distinguishes_partial_and_exit_mismatches() -> None:
    assert classify_status(
        tv_count=0,
        entry_matches=0,
        exit_time_matches=0,
        exit_price_matches=0,
    ) == "no_tv_rows"
    assert classify_status(
        tv_count=10,
        entry_matches=0,
        exit_time_matches=0,
        exit_price_matches=0,
    ) == "no_entry_matches"
    assert classify_status(
        tv_count=10,
        entry_matches=4,
        exit_time_matches=4,
        exit_price_matches=4,
    ) == "partial_entry_match"
    assert classify_status(
        tv_count=10,
        entry_matches=10,
        exit_time_matches=9,
        exit_price_matches=9,
    ) == "exit_time_mismatch"
    assert classify_status(
        tv_count=10,
        entry_matches=10,
        exit_time_matches=10,
        exit_price_matches=9,
    ) == "exit_price_mismatch"
    assert classify_status(
        tv_count=10,
        entry_matches=10,
        exit_time_matches=10,
        exit_price_matches=10,
    ) == "exact_match"


def test_tv_raw_path_prefers_entry15_raw_export(tmp_path: Path) -> None:
    older = tmp_path / "tradingview_mtsv1_BTC_raw.csv"
    preferred = tmp_path / "tradingview_mtsv1_BTC_entry15_raw.csv"
    older.write_text("", encoding="utf-8")
    preferred.write_text("", encoding="utf-8")

    assert tv_raw_path_for_symbol(tmp_path, "BTC") == preferred
    assert tv_capture_kind(preferred, "BTC") == "entry15_raw"
    assert tv_capture_kind(older, "BTC") == "raw_fallback"


def test_exact_py_path_prefers_symbol_specific_binanceusdm_artifact(tmp_path: Path) -> None:
    path = tmp_path / "mtsv1_tv_btc_15m_binanceusdm_profile" / "trades.jsonl"
    path.parent.mkdir()
    path.write_text("", encoding="utf-8")

    assert exact_py_path_for_symbol(tmp_path, "BTC") == path


def test_detail_paths_use_symbol_specific_report_names(tmp_path: Path) -> None:
    diff_path, trace_path = detail_paths(tmp_path, "ETH")

    assert diff_path == tmp_path / "eth_diff_entry15.md"
    assert trace_path == tmp_path / "eth_trace_entry15.md"


def test_mismatch_class_distinguishes_data_and_semantic_mismatches() -> None:
    assert mismatch_class_for_summary(
        status="missing_exact_cache",
        tv_count=10,
        py_entry_count=0,
        py_candidate_count=0,
    ) == "data_window_mismatch"
    assert mismatch_class_for_summary(
        status="no_entry_matches",
        tv_count=10,
        py_entry_count=20,
        py_candidate_count=20,
        tv_capture="raw_fallback",
    ) == "profile_input_mismatch"
    assert mismatch_class_for_summary(
        status="no_entry_matches",
        tv_count=10,
        py_entry_count=20,
        py_candidate_count=20,
        tv_capture="entry15_raw",
    ) == "semantic_replay_mismatch"
    assert mismatch_class_for_summary(
        status="exact_match",
        tv_count=10,
        py_entry_count=10,
        py_candidate_count=10,
    ) == "none"


def test_summarize_symbol_reports_missing_tv_csv(tmp_path: Path) -> None:
    py_path = tmp_path / "trades.jsonl"
    py_path.write_text("", encoding="utf-8")

    result = summarize_symbol(
        symbol="ETH",
        samples_dir=tmp_path,
        py_path=py_path,
        tolerance=timedelta(minutes=15),
        exit_price_tolerance=0.15,
    )

    assert result.status == "missing_tv_csv"
    assert result.tv_path is None


def test_summarize_symbol_reports_missing_exact_cache(tmp_path: Path) -> None:
    samples_dir = tmp_path / "samples"
    samples_dir.mkdir()
    (samples_dir / "tradingview_mtsv1_ETH_raw.csv").write_text(
        "\n".join(
            [
                "symbol,entry_signal,trade_no,side,entry_time_utc,exit_time_utc,entry_price,exit_price,net_pnl_pct",
                "ETHUSDT,L1,1,long,2026-04-24T00:00:00Z,2026-04-24T01:00:00Z,100,101,1",
            ]
        ),
        encoding="utf-8",
    )

    result = summarize_symbol(
        symbol="ETH",
        samples_dir=samples_dir,
        exact_runs_dir=tmp_path / "runs",
        tolerance=timedelta(minutes=15),
        exit_price_tolerance=0.15,
    )

    assert result.status == "missing_exact_cache"
    assert result.py_path is None
    assert result.tv_count == 1


def test_summarize_symbol_counts_entry_and_exit_matches(tmp_path: Path) -> None:
    samples_dir = tmp_path / "samples"
    samples_dir.mkdir()
    tv_path = samples_dir / "tradingview_mtsv1_BTC_raw.csv"
    tv_path.write_text(
        "\n".join(
            [
                "symbol,entry_signal,trade_no,side,entry_time_utc,exit_time_utc,entry_price,exit_price,net_pnl_pct",
                "BTCUSDT,L1,1,long,2026-04-24T00:00:00Z,2026-04-24T01:00:00Z,100,101,1",
            ]
        ),
        encoding="utf-8",
    )
    py_path = tmp_path / "trades.jsonl"
    events = [
        {"event": "ENTRY_SIGNAL", "symbol": "BTC/USDT:USDT", "side": "long", "ts": "2026-04-23T23:45:00Z", "price": 99},
        {"event": "ENTRY_L1", "symbol": "BTC/USDT:USDT", "side": "long", "ts": "2026-04-24T00:00:00Z", "price": 100},
        {"event": "EXIT", "symbol": "BTC/USDT:USDT", "side": "long", "ts": "2026-04-24T01:00:00Z", "price": 101.1},
    ]
    py_path.write_text(
        "\n".join(json.dumps(event) for event in events),
        encoding="utf-8",
    )

    result = summarize_symbol(
        symbol="BTC",
        samples_dir=samples_dir,
        py_path=py_path,
        tolerance=timedelta(minutes=15),
        exit_price_tolerance=0.15,
    )

    assert result.status == "exact_match"
    assert result.tv_common_rows == 1
    assert result.tv_before_py_rows == 0
    assert result.tv_tail_after_py_rows == 0
    assert result.entry_matches == 1
    assert result.exit_time_matches == 1
    assert result.exit_price_within_0_15 == 1
    assert result.exit_price_within_1_0 == 1


def test_summarize_symbol_uses_common_coverage_denominator(tmp_path: Path) -> None:
    samples_dir = tmp_path / "samples"
    samples_dir.mkdir()
    tv_path = samples_dir / "tradingview_mtsv1_SOL_entry15_raw.csv"
    tv_path.write_text(
        "\n".join(
            [
                "symbol,entry_signal,trade_no,side,entry_time_utc,exit_time_utc,entry_price,exit_price,net_pnl_pct",
                "SOLUSDT,L1,1,long,2026-04-24T00:00:00Z,2026-04-24T01:00:00Z,100,101,1",
                "SOLUSDT,L1,2,long,2026-04-25T00:00:00Z,2026-04-25T01:00:00Z,102,103,1",
            ]
        ),
        encoding="utf-8",
    )
    py_path = tmp_path / "trades.jsonl"
    events = [
        {"event": "ENTRY_SIGNAL", "symbol": "SOL/USDT:USDT", "side": "long", "ts": "2026-04-23T23:45:00Z", "price": 99},
        {"event": "ENTRY_L1", "symbol": "SOL/USDT:USDT", "side": "long", "ts": "2026-04-24T00:00:00Z", "price": 100},
        {"event": "EXIT", "symbol": "SOL/USDT:USDT", "side": "long", "ts": "2026-04-24T01:00:00Z", "price": 101},
    ]
    py_path.write_text("\n".join(json.dumps(event) for event in events), encoding="utf-8")

    result = summarize_symbol(
        symbol="SOL",
        samples_dir=samples_dir,
        py_path=py_path,
        tolerance=timedelta(minutes=15),
        exit_price_tolerance=0.15,
    )

    assert result.tv_count == 2
    assert result.tv_common_rows == 1
    assert result.tv_tail_after_py_rows == 1
    assert result.entry_matches == 1
    assert result.status == "exact_match"


def test_summarize_symbol_uses_exact_artifact_and_report_renders_path(tmp_path: Path) -> None:
    samples_dir = tmp_path / "samples"
    runs_dir = tmp_path / "runs"
    samples_dir.mkdir()
    tv_path = samples_dir / "tradingview_mtsv1_BTC_raw.csv"
    tv_path.write_text(
        "\n".join(
            [
                "symbol,entry_signal,trade_no,side,entry_time_utc,exit_time_utc,entry_price,exit_price,net_pnl_pct",
                "BTCUSDT,L1,1,long,2026-04-24T00:00:00Z,2026-04-24T01:00:00Z,100,101,1",
            ]
        ),
        encoding="utf-8",
    )
    py_path = runs_dir / "mtsv1_tv_btc_15m_binanceusdm_profile" / "trades.jsonl"
    py_path.parent.mkdir(parents=True)
    events = [
        {"event": "ENTRY_SIGNAL", "symbol": "BTC/USDT:USDT", "side": "long", "ts": "2026-04-23T23:45:00Z", "price": 99},
        {"event": "ENTRY_L1", "symbol": "BTC/USDT:USDT", "side": "long", "ts": "2026-04-24T00:00:00Z", "price": 100},
        {"event": "EXIT", "symbol": "BTC/USDT:USDT", "side": "long", "ts": "2026-04-24T01:00:00Z", "price": 101.1},
    ]
    py_path.write_text("\n".join(json.dumps(event) for event in events), encoding="utf-8")

    result = summarize_symbol(
        symbol="BTC",
        samples_dir=samples_dir,
        exact_runs_dir=runs_dir,
        detail_dir=tmp_path / "reports",
        tolerance=timedelta(minutes=15),
        exit_price_tolerance=0.15,
    )
    report = render_report([result])

    assert result.status == "exact_match"
    assert result.py_path == py_path
    assert result.detail_diff_path == tmp_path / "reports" / "btc_diff_entry15.md"
    assert str(py_path) in report
    assert "Detail reports" in report
    assert "TV entry range" in report
    assert "Coverage / Gate" in report
    assert "Common TV rows" in report
    assert "Capture Inventory" in report


def test_write_detail_reports_generates_symbol_diff_and_trace(tmp_path: Path) -> None:
    samples_dir = tmp_path / "samples"
    runs_dir = tmp_path / "runs"
    reports_dir = tmp_path / "reports"
    samples_dir.mkdir()
    (samples_dir / "tradingview_mtsv1_BNB_raw.csv").write_text(
        "\n".join(
            [
                "symbol,entry_signal,trade_no,side,entry_time_utc,exit_time_utc,entry_price,exit_price,net_pnl_pct",
                "BNBUSDT,L1,1,long,2026-04-24T00:00:00Z,2026-04-24T01:00:00Z,100,101,1",
            ]
        ),
        encoding="utf-8",
    )
    py_path = runs_dir / "mtsv1_tv_bnb_15m_binanceusdm_profile" / "trades.jsonl"
    py_path.parent.mkdir(parents=True)
    events = [
        {"event": "ENTRY_SIGNAL", "symbol": "BNB/USDT:USDT", "side": "long", "ts": "2026-04-23T23:45:00Z", "price": 99},
        {"event": "ENTRY_L1", "symbol": "BNB/USDT:USDT", "side": "long", "ts": "2026-04-24T00:00:00Z", "price": 100},
        {"event": "EXIT", "symbol": "BNB/USDT:USDT", "side": "long", "ts": "2026-04-24T01:00:00Z", "price": 101},
    ]
    py_path.write_text("\n".join(json.dumps(event) for event in events), encoding="utf-8")
    result = summarize_symbol(
        symbol="BNB",
        samples_dir=samples_dir,
        exact_runs_dir=runs_dir,
        detail_dir=reports_dir,
        tolerance=timedelta(minutes=15),
        exit_price_tolerance=0.15,
    )

    write_detail_reports(result, tolerance=timedelta(minutes=15), examples=4)

    assert (reports_dir / "bnb_diff_entry15.md").read_text(encoding="utf-8").startswith(
        "# MTS-V1 BNB TradingView/Python Diff"
    )
    assert (reports_dir / "bnb_trace_entry15.md").read_text(encoding="utf-8").startswith(
        "# MTS-V1 BNB Parity Trace"
    )


def test_parse_symbols_normalizes_symbol_inputs() -> None:
    assert parse_symbols("BINANCE:BTCUSDT.P, ETH/USDT:USDT") == ["BTC", "ETH"]


def test_baseline_gate_enforces_btc_artifact_contract(tmp_path: Path) -> None:
    diff_path = tmp_path / "btc_diff.md"
    trace_path = tmp_path / "btc_trace.md"
    diff_path.write_text("diff", encoding="utf-8")
    trace_path.write_text("trace", encoding="utf-8")
    row = SymbolParitySummary(
        symbol="BTC",
        status="exit_price_mismatch",
        tv_path=Path("tv.csv"),
        py_path=Path("py.jsonl"),
        detail_diff_path=diff_path,
        detail_trace_path=trace_path,
        mismatch_class="semantic_replay_mismatch",
        py_sha256=BTC_BASELINE_SHA256,
        tv_count=BTC_BASELINE_ENTRY_MATCHES,
        tv_common_rows=BTC_BASELINE_ENTRY_MATCHES,
        entry_matches=BTC_BASELINE_ENTRY_MATCHES,
        exit_time_matches=BTC_BASELINE_EXIT_TIME_MATCHES,
        exit_price_within_0_15=BTC_BASELINE_EXIT_PRICE_WITHIN_0_15,
        exit_price_within_1_0=BTC_BASELINE_EXIT_PRICE_WITHIN_1_0,
    )

    gated, passed = apply_gate([row], mode="baseline")

    assert passed is True
    assert gated[0].gate_status == "pass"
    assert gated[0].gate_failures == ()


def test_baseline_gate_marks_btc_metric_regression() -> None:
    row = SymbolParitySummary(
        symbol="BTC",
        status="partial_entry_match",
        tv_path=None,
        py_path=None,
        mismatch_class="semantic_replay_mismatch",
        py_sha256="bad",
        tv_count=BTC_BASELINE_ENTRY_MATCHES,
        tv_common_rows=BTC_BASELINE_ENTRY_MATCHES,
        entry_matches=BTC_BASELINE_ENTRY_MATCHES - 1,
        exit_time_matches=BTC_BASELINE_EXIT_TIME_MATCHES,
        exit_price_within_0_15=BTC_BASELINE_EXIT_PRICE_WITHIN_0_15,
        exit_price_within_1_0=BTC_BASELINE_EXIT_PRICE_WITHIN_1_0,
    )

    gated, passed = apply_gate([row], mode="baseline")

    assert passed is False
    assert any(failure.startswith("btc_entry_matches_regressed") for failure in gated[0].gate_failures)
    assert "btc_artifact_sha256_regressed" in gated[0].gate_failures
