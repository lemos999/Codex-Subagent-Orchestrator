from __future__ import annotations

import argparse
import hashlib
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

from btc_parity_diff import (
    ENTRY_EVENTS,
    Match,
    PyEvent,
    TvTrade,
    closed_cycle_entries,
    format_dt,
    format_float,
    load_python_events,
    load_tv_raw,
    match_trades,
    normalize_symbol,
    render_report as render_diff_report,
)
from btc_parity_trace import render_trace
from mts_profile import (
    ACCEPTED_ENTRY_TIMEFRAME,
    ACCEPTED_EXECUTION_TIMEFRAME,
    ACCEPTED_HTF_TIMEFRAME,
    ACCEPTED_RSM,
)


ROOT_DIR = Path(__file__).resolve().parent
CORE5_SYMBOLS = tuple(ACCEPTED_RSM)
BTC_BASELINE_SHA256 = "BE6FDFE9CD6A853D7983B51DCDA4D61DA41EEFE546FF8FCEDB84114630AFB41D"
BTC_BASELINE_ENTRY_MATCHES = 64
BTC_BASELINE_EXIT_TIME_MATCHES = 64
BTC_BASELINE_EXIT_PRICE_WITHIN_0_15 = 62
BTC_BASELINE_EXIT_PRICE_WITHIN_1_0 = 64
STRICT_TARGETS = {
    "SOL": {"entry_match_rate": 0.80, "exit_time_match_rate": 0.70, "exit_price_within_1_0_rate": 1.0},
    "XRP": {"entry_match_rate": 0.70, "exit_time_match_rate": 0.60, "exit_price_within_0_15_rate": 1.0},
}


@dataclass(slots=True, frozen=True)
class PyCycle:
    entries: tuple[PyEvent, ...]
    exit: PyEvent | None


@dataclass(slots=True, frozen=True)
class SymbolParitySummary:
    symbol: str
    status: str
    tv_path: Path | None
    py_path: Path | None = None
    detail_diff_path: Path | None = None
    detail_trace_path: Path | None = None
    mismatch_class: str = ""
    tv_capture: str = ""
    tv_mtime: datetime | None = None
    py_mtime: datetime | None = None
    py_sha256: str = ""
    tv_count: int = 0
    tv_start: datetime | None = None
    tv_end: datetime | None = None
    tv_common_rows: int = 0
    tv_tail_after_py_rows: int = 0
    tv_before_py_rows: int = 0
    py_entry_count: int = 0
    py_entry_start: datetime | None = None
    py_entry_end: datetime | None = None
    py_candidate_count: int = 0
    entry_matches: int = 0
    exit_time_matches: int = 0
    exit_price_within_0_15: int = 0
    exit_price_within_1_0: int = 0
    avg_abs_exit_price_delta: float | None = None
    max_abs_exit_price_delta: float | None = None
    trade_no_contiguous: bool = True
    gate_status: str = "not_run"
    gate_failures: tuple[str, ...] = ()


def parse_symbols(raw: str) -> list[str]:
    return [normalize_symbol(part) for part in raw.split(",") if normalize_symbol(part)]


def tv_raw_path_for_symbol(samples_dir: Path, symbol: str) -> Path | None:
    candidates = [
        samples_dir / f"tradingview_mtsv1_{symbol}_entry15_raw.csv",
        samples_dir / f"tradingview_mtsv1_{symbol}_raw.csv",
        samples_dir / f"tradingview_mtsv1_{symbol}.csv",
        samples_dir / f"{symbol}_raw.csv",
        samples_dir / f"{symbol}.csv",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def tv_capture_kind(path: Path | None, symbol: str) -> str:
    if path is None:
        return ""
    if path.name == f"tradingview_mtsv1_{symbol}_entry15_raw.csv":
        return "entry15_raw"
    return "raw_fallback"


def path_mtime(path: Path | None) -> datetime | None:
    if path is None or not path.exists():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)


def path_sha256(path: Path | None) -> str:
    if path is None or not path.exists():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def exact_py_path_for_symbol(runs_dir: Path, symbol: str) -> Path | None:
    lower = symbol.lower()
    candidates = [
        runs_dir / f"mtsv1_tv_{lower}_15m_binanceusdm_profile" / "trades.jsonl",
        runs_dir / f"mtsv1_tv_{symbol}_15m_binanceusdm_profile" / "trades.jsonl",
        runs_dir / f"mtsv1_tv_{lower}_15m_profile" / "trades.jsonl",
        runs_dir / f"mtsv1_tv_{symbol}_15m_profile" / "trades.jsonl",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def build_cycles(events: list[PyEvent]) -> list[PyCycle]:
    cycles: list[PyCycle] = []
    current_entries: list[PyEvent] = []
    for event in events:
        if event.event == "ENTRY_SIGNAL":
            if current_entries:
                cycles.append(PyCycle(tuple(current_entries), None))
            current_entries = []
            continue
        if event.event in ENTRY_EVENTS:
            current_entries.append(event)
            continue
        if event.event == "EXIT":
            cycles.append(PyCycle(tuple(current_entries), event))
            current_entries = []
    if current_entries:
        cycles.append(PyCycle(tuple(current_entries), None))
    return cycles


def cycle_exit_by_entry(events: list[PyEvent]) -> dict[PyEvent, PyEvent | None]:
    mapping: dict[PyEvent, PyEvent | None] = {}
    for cycle in build_cycles(events):
        for entry in cycle.entries:
            mapping[entry] = cycle.exit
    return mapping


def trade_numbers_contiguous(tv_trades: list[TvTrade]) -> bool:
    trade_numbers = sorted(
        int(getattr(trade, "trade_no"))
        for trade in tv_trades
        if int(getattr(trade, "trade_no")) > 0
    )
    if not trade_numbers:
        return True
    expected = list(range(trade_numbers[0], trade_numbers[-1] + 1))
    return trade_numbers == expected


def tv_trades_in_python_coverage(
    tv_trades: list[TvTrade],
    *,
    py_entry_start: datetime | None,
    py_entry_end: datetime | None,
    tolerance: timedelta,
) -> tuple[list[TvTrade], int, int]:
    if py_entry_start is None or py_entry_end is None:
        return [], len(tv_trades), 0
    common: list[TvTrade] = []
    before = 0
    after = 0
    for trade in tv_trades:
        entry_ts = trade.entry_ts
        if entry_ts < py_entry_start - tolerance:
            before += 1
        elif entry_ts > py_entry_end + tolerance:
            after += 1
        else:
            common.append(trade)
    return common, before, after


def mismatch_class_for_summary(
    *,
    status: str,
    tv_count: int,
    py_entry_count: int,
    py_candidate_count: int,
    tv_capture: str = "entry15_raw",
) -> str:
    if status in {"exact_match", "exit_price_mismatch"}:
        return "semantic_replay_mismatch" if status != "exact_match" else "none"
    if status in {"missing_tv_csv", "missing_exact_cache", "no_tv_rows", "no_common_coverage"}:
        return "data_window_mismatch"
    if tv_capture != "entry15_raw":
        return "profile_input_mismatch"
    if py_entry_count == 0 or py_candidate_count == 0:
        return "data_window_mismatch"
    return "semantic_replay_mismatch"


def detail_paths(detail_dir: Path | None, symbol: str) -> tuple[Path | None, Path | None]:
    if detail_dir is None:
        return None, None
    lower = symbol.lower()
    return (
        detail_dir / f"{lower}_diff_entry15.md",
        detail_dir / f"{lower}_trace_entry15.md",
    )


def summarize_symbol(
    *,
    symbol: str,
    samples_dir: Path,
    tolerance: timedelta,
    exit_price_tolerance: float,
    py_path: Path | None = None,
    exact_runs_dir: Path | None = None,
    detail_dir: Path | None = None,
) -> SymbolParitySummary:
    tv_path = tv_raw_path_for_symbol(samples_dir, symbol)
    diff_path, trace_path = detail_paths(detail_dir, symbol)
    capture = tv_capture_kind(tv_path, symbol)
    if tv_path is None:
        return SymbolParitySummary(
            symbol=symbol,
            status="missing_tv_csv",
            tv_path=None,
            detail_diff_path=diff_path,
            detail_trace_path=trace_path,
            mismatch_class="data_window_mismatch",
            tv_capture=capture,
        )
    tv_trades = load_tv_raw(tv_path, symbol)
    tv_start = min((trade.entry_ts for trade in tv_trades), default=None)
    tv_end = max((trade.entry_ts for trade in tv_trades), default=None)
    selected_py_path = (
        exact_py_path_for_symbol(exact_runs_dir, symbol)
        if exact_runs_dir is not None
        else py_path
    )
    if selected_py_path is None:
        return SymbolParitySummary(
            symbol=symbol,
            status="missing_exact_cache",
            tv_path=tv_path,
            py_path=None,
            detail_diff_path=diff_path,
            detail_trace_path=trace_path,
            mismatch_class="data_window_mismatch",
            tv_capture=capture,
            tv_mtime=path_mtime(tv_path),
            tv_count=len(tv_trades),
            tv_start=tv_start,
            tv_end=tv_end,
            tv_before_py_rows=len(tv_trades),
            trade_no_contiguous=trade_numbers_contiguous(tv_trades),
        )

    py_events = load_python_events(selected_py_path, symbol)
    py_entries = [event for event in py_events if event.event in ENTRY_EVENTS]
    py_entry_start = min((event.ts for event in py_entries), default=None)
    py_entry_end = max((event.ts for event in py_entries), default=None)
    tv_common_trades_raw, tv_before_py_rows, tv_tail_after_py_rows = tv_trades_in_python_coverage(
        tv_trades,
        py_entry_start=py_entry_start,
        py_entry_end=py_entry_end,
        tolerance=tolerance,
    )
    tv_common_trades = list(tv_common_trades_raw)
    py_candidates = closed_cycle_entries(py_events, tv_common_trades, tolerance=tolerance)
    matches = match_trades(tv_common_trades, py_candidates, tolerance=tolerance)
    matched = [match for match in matches if match.py is not None]
    py_exit_by_entry = cycle_exit_by_entry(py_events)
    exit_stats = compare_exits(
        matched,
        py_exit_by_entry,
        tolerance=tolerance,
        exit_price_tolerance=exit_price_tolerance,
    )
    if len(tv_trades) == 0:
        status = "no_tv_rows"
    elif len(tv_common_trades) == 0:
        status = "no_common_coverage"
    else:
        status = classify_status(
            tv_count=len(tv_common_trades),
            entry_matches=len(matched),
            exit_time_matches=int(exit_stats["exit_time_matches"] or 0),
            exit_price_matches=int(exit_stats["exit_price_within_0_15"] or 0),
        )
    mismatch_class = mismatch_class_for_summary(
        status=status,
        tv_count=len(tv_trades),
        py_entry_count=len(py_entries),
        py_candidate_count=len(py_candidates),
        tv_capture=capture,
    )
    return SymbolParitySummary(
        symbol=symbol,
        status=status,
        tv_path=tv_path,
        py_path=selected_py_path,
        detail_diff_path=diff_path,
        detail_trace_path=trace_path,
        mismatch_class=mismatch_class,
        tv_count=len(tv_trades),
        tv_capture=capture,
        tv_mtime=path_mtime(tv_path),
        py_mtime=path_mtime(selected_py_path),
        py_sha256=path_sha256(selected_py_path),
        tv_start=tv_start,
        tv_end=tv_end,
        tv_common_rows=len(tv_common_trades),
        tv_tail_after_py_rows=tv_tail_after_py_rows,
        tv_before_py_rows=tv_before_py_rows,
        py_entry_count=len(py_entries),
        py_entry_start=py_entry_start,
        py_entry_end=py_entry_end,
        py_candidate_count=len(py_candidates),
        entry_matches=len(matched),
        exit_time_matches=exit_stats["exit_time_matches"],
        exit_price_within_0_15=exit_stats["exit_price_within_0_15"],
        exit_price_within_1_0=exit_stats["exit_price_within_1_0"],
        avg_abs_exit_price_delta=exit_stats["avg_abs_exit_price_delta"],
        max_abs_exit_price_delta=exit_stats["max_abs_exit_price_delta"],
        trade_no_contiguous=trade_numbers_contiguous(tv_trades),
    )


def classify_status(
    *,
    tv_count: int,
    entry_matches: int,
    exit_time_matches: int,
    exit_price_matches: int,
) -> str:
    if tv_count == 0:
        return "no_tv_rows"
    if entry_matches == 0:
        return "no_entry_matches"
    if entry_matches < tv_count:
        return "partial_entry_match"
    if exit_time_matches < entry_matches:
        return "exit_time_mismatch"
    if exit_price_matches < entry_matches:
        return "exit_price_mismatch"
    return "exact_match"


def compare_exits(
    matches: list[Match],
    py_exit_by_entry: dict[PyEvent, PyEvent | None],
    *,
    tolerance: timedelta,
    exit_price_tolerance: float,
) -> dict[str, int | float | None]:
    time_matches = 0
    within_main = 0
    within_one = 0
    price_deltas: list[float] = []
    for match in matches:
        if match.py is None:
            continue
        py_exit = py_exit_by_entry.get(match.py)
        if py_exit is None or match.tv.exit_ts is None:
            continue
        if abs(py_exit.ts - match.tv.exit_ts) <= tolerance:
            time_matches += 1
        if py_exit.price is None or match.tv.exit_price is None:
            continue
        delta = abs(py_exit.price - match.tv.exit_price)
        price_deltas.append(delta)
        if delta <= exit_price_tolerance:
            within_main += 1
        if delta <= 1.0:
            within_one += 1
    return {
        "exit_time_matches": time_matches,
        "exit_price_within_0_15": within_main,
        "exit_price_within_1_0": within_one,
        "avg_abs_exit_price_delta": (
            sum(price_deltas) / len(price_deltas) if price_deltas else None
        ),
        "max_abs_exit_price_delta": max(price_deltas) if price_deltas else None,
    }


def format_failures(failures: tuple[str, ...]) -> str:
    if not failures:
        return ""
    return ", ".join(f"`{failure}`" for failure in failures)


def render_report(rows: list[SymbolParitySummary], *, py_path: Path | None = None) -> str:
    lines = [
        "# MTS-V1 Core5 Parity Report",
        "",
        "- Profile: `15m/core5/symbol-RSM`",
        f"- Timeframes: entry `{ACCEPTED_ENTRY_TIMEFRAME}`, execution `{ACCEPTED_EXECUTION_TIMEFRAME}`, HTF `{ACCEPTED_HTF_TIMEFRAME}`",
        f"- Symbol RSM: `{ACCEPTED_RSM}`",
        "- Python JSONL: per-symbol exact artifact"
        if py_path is None
        else f"- Python JSONL: `{py_path}`",
        "",
        "| Symbol | Status | Class | TV capture | TV CSV | Python artifact | Detail reports | TV rows | Common TV rows | Py entries | Py candidates | Entry matches | Exit time | Exit price <=0.15 | Exit price <=1.0 | Avg exit delta | Max exit delta |",
        "|---|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        tv_path = f"`{row.tv_path}`" if row.tv_path is not None else ""
        py_artifact = f"`{row.py_path}`" if row.py_path is not None else ""
        detail_reports = ""
        if row.detail_diff_path is not None and row.detail_trace_path is not None:
            detail_reports = f"`{row.detail_diff_path}` / `{row.detail_trace_path}`"
        lines.append(
            "| "
            f"{row.symbol} | {row.status} | {row.mismatch_class} | {row.tv_capture} | {tv_path} | "
            f"{py_artifact} | {detail_reports} | {row.tv_count} | {row.tv_common_rows} | "
            f"{row.py_entry_count} | {row.py_candidate_count} | {row.entry_matches} | "
            f"{row.exit_time_matches} | {row.exit_price_within_0_15} | "
            f"{row.exit_price_within_1_0} | "
            f"{format_float(row.avg_abs_exit_price_delta, 4)} | "
            f"{format_float(row.max_abs_exit_price_delta, 4)} |"
        )
    lines.extend(
        [
            "",
            "## Coverage / Gate",
            "",
            "| Symbol | TV rows | Common TV rows | TV before Python artifact | TV tail after Python artifact | Trade numbers contiguous | Python SHA256 | Gate | Gate failures |",
            "|---|---:|---:|---:|---:|---|---|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row.symbol} | {row.tv_count} | {row.tv_common_rows} | "
            f"{row.tv_before_py_rows} | {row.tv_tail_after_py_rows} | "
            f"{str(row.trade_no_contiguous).lower()} | {row.py_sha256} | "
            f"{row.gate_status} | {format_failures(row.gate_failures)} |"
        )
    lines.extend(
        [
            "",
            "## Ranges",
            "",
            "| Symbol | TV entry range | Python filled-entry range |",
            "|---|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row.symbol} | {format_dt(row.tv_start)} to {format_dt(row.tv_end)} | "
            f"{format_dt(row.py_entry_start)} to {format_dt(row.py_entry_end)} |"
        )
    lines.extend(
        [
            "",
            "## Capture Inventory",
            "",
            "| Symbol | TV capture | TV CSV mtime | Python artifact mtime | RSM | Entry TF | Execution TF | HTF |",
            "|---|---|---|---|---:|---|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row.symbol} | {row.tv_capture} | {format_dt(row.tv_mtime)} | "
            f"{format_dt(row.py_mtime)} | {ACCEPTED_RSM.get(row.symbol, 0.0)} | "
            f"{ACCEPTED_ENTRY_TIMEFRAME} | {ACCEPTED_EXECUTION_TIMEFRAME} | {ACCEPTED_HTF_TIMEFRAME} |"
        )
    lines.extend(
        [
            "",
            "## Criteria",
            "- This batch report classifies current Core5 mismatches against per-symbol exact artifacts.",
            "- Semantic match metrics use `Common TV rows` as the denominator; raw `TV rows` preserve the full capture inventory.",
            "- TV rows outside the Python artifact filled-entry range are counted as before/tail coverage, not semantic replay failures.",
            "- Detail reports are generated with the same diff/trace logic used for BTC parity.",
            "- ETH/SOL/XRP/BNB rows classify current mismatches; they are not PASS claims.",
            "- `missing_tv_csv` means no raw TradingView CSV was found for that symbol.",
            "- `missing_exact_cache` means no per-symbol exact Python artifact was found.",
            "- `data_window_mismatch` means the available TV/Python ranges or candidates are insufficient for semantic comparison.",
            "- `profile_input_mismatch` means the TV capture is not the verified `*_entry15_raw.csv` export, so semantic replay debugging is deferred until capture refresh.",
            "- `semantic_replay_mismatch` means comparable rows exist but entry/exit semantics still diverge.",
            "",
        ]
    )
    return "\n".join(lines)


def write_detail_reports(
    row: SymbolParitySummary,
    *,
    tolerance: timedelta,
    examples: int,
) -> None:
    if (
        row.tv_path is None
        or row.py_path is None
        or row.detail_diff_path is None
        or row.detail_trace_path is None
    ):
        return
    tv_trades = load_tv_raw(row.tv_path, row.symbol)
    py_events = load_python_events(row.py_path, row.symbol)
    py_entries = [event for event in py_events if event.event in ENTRY_EVENTS]
    py_entry_start = min((event.ts for event in py_entries), default=None)
    py_entry_end = max((event.ts for event in py_entries), default=None)
    tv_common_trades_raw, tv_before_py_rows, tv_tail_after_py_rows = tv_trades_in_python_coverage(
        tv_trades,
        py_entry_start=py_entry_start,
        py_entry_end=py_entry_end,
        tolerance=tolerance,
    )
    tv_common_trades = list(tv_common_trades_raw)
    py_entries_in_window = closed_cycle_entries(
        py_events,
        tv_common_trades,
        tolerance=tolerance,
    )
    matches = match_trades(tv_common_trades, py_entries_in_window, tolerance=tolerance)
    diff_report = render_diff_report(
        symbol=row.symbol,
        tv_path=row.tv_path,
        py_path=row.py_path,
        tv_trades=tv_common_trades,
        py_entries=py_entries,
        py_entries_in_window=py_entries_in_window,
        matches=matches,
        tolerance=tolerance,
        examples=examples,
        py_events=py_events,
        tv_total_rows=len(tv_trades),
        tv_before_python_rows=tv_before_py_rows,
        tv_tail_after_python_rows=tv_tail_after_py_rows,
    )
    trace_report = render_trace(
        symbol=row.symbol,
        tv_trades=tv_common_trades,
        py_events=py_events,
        tolerance=tolerance,
        examples=examples,
        tv_total_rows=len(tv_trades),
        tv_before_python_rows=tv_before_py_rows,
        tv_tail_after_python_rows=tv_tail_after_py_rows,
    )
    row.detail_diff_path.parent.mkdir(parents=True, exist_ok=True)
    row.detail_diff_path.write_text(diff_report, encoding="utf-8")
    row.detail_trace_path.write_text(trace_report, encoding="utf-8")


def detail_reports_exist(row: SymbolParitySummary) -> bool:
    if row.tv_path is None or row.py_path is None:
        return True
    if row.detail_diff_path is None or row.detail_trace_path is None:
        return False
    return row.detail_diff_path.exists() and row.detail_trace_path.exists()


def btc_baseline_failures(row: SymbolParitySummary) -> list[str]:
    failures: list[str] = []
    if row.entry_matches != BTC_BASELINE_ENTRY_MATCHES:
        failures.append(
            f"btc_entry_matches_regressed:{row.entry_matches}!={BTC_BASELINE_ENTRY_MATCHES}"
        )
    if row.exit_time_matches != BTC_BASELINE_EXIT_TIME_MATCHES:
        failures.append(
            f"btc_exit_time_regressed:{row.exit_time_matches}!={BTC_BASELINE_EXIT_TIME_MATCHES}"
        )
    if row.exit_price_within_0_15 < BTC_BASELINE_EXIT_PRICE_WITHIN_0_15:
        failures.append(
            "btc_exit_price_0_15_regressed:"
            f"{row.exit_price_within_0_15}<{BTC_BASELINE_EXIT_PRICE_WITHIN_0_15}"
        )
    if row.exit_price_within_1_0 != BTC_BASELINE_EXIT_PRICE_WITHIN_1_0:
        failures.append(
            "btc_exit_price_1_0_regressed:"
            f"{row.exit_price_within_1_0}!={BTC_BASELINE_EXIT_PRICE_WITHIN_1_0}"
        )
    if row.py_sha256 != BTC_BASELINE_SHA256:
        failures.append("btc_artifact_sha256_regressed")
    return failures


def strict_target_failures(row: SymbolParitySummary) -> list[str]:
    target = STRICT_TARGETS.get(row.symbol)
    if target is None:
        return []
    failures: list[str] = []
    denominator = row.tv_common_rows
    if denominator <= 0:
        return [f"{row.symbol.lower()}_strict_no_common_rows"]
    entry_rate = row.entry_matches / denominator
    exit_time_rate = row.exit_time_matches / row.entry_matches if row.entry_matches else 0.0
    price_0_15_rate = row.exit_price_within_0_15 / row.entry_matches if row.entry_matches else 0.0
    price_1_0_rate = row.exit_price_within_1_0 / row.entry_matches if row.entry_matches else 0.0
    if entry_rate < target.get("entry_match_rate", 0.0):
        failures.append(f"{row.symbol.lower()}_entry_rate:{entry_rate:.3f}")
    if exit_time_rate < target.get("exit_time_match_rate", 0.0):
        failures.append(f"{row.symbol.lower()}_exit_time_rate:{exit_time_rate:.3f}")
    if price_0_15_rate < target.get("exit_price_within_0_15_rate", 0.0):
        failures.append(f"{row.symbol.lower()}_exit_price_0_15_rate:{price_0_15_rate:.3f}")
    if price_1_0_rate < target.get("exit_price_within_1_0_rate", 0.0):
        failures.append(f"{row.symbol.lower()}_exit_price_1_0_rate:{price_1_0_rate:.3f}")
    return failures


def apply_gate(rows: list[SymbolParitySummary], *, mode: str) -> tuple[list[SymbolParitySummary], bool]:
    if mode == "off":
        return rows, True

    gated_rows: list[SymbolParitySummary] = []
    gate_passed = True
    for row in rows:
        failures: list[str] = []
        if row.status in {"missing_tv_csv", "missing_exact_cache"}:
            failures.append(row.status)
        if row.mismatch_class == "profile_input_mismatch":
            failures.append("profile_input_mismatch")
        if not row.trade_no_contiguous:
            failures.append("trade_no_discontinuity")
        if not detail_reports_exist(row):
            failures.append("detail_report_missing")
        if row.symbol == "BTC":
            failures.extend(btc_baseline_failures(row))
        if mode == "strict":
            failures.extend(strict_target_failures(row))

        if failures:
            gate_passed = False
        gated_rows.append(
            replace(
                row,
                gate_status="pass" if not failures else "fail",
                gate_failures=tuple(failures),
            )
        )
    return gated_rows, gate_passed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate an MTS-V1 Core5 TradingView/Python parity matrix.")
    parser.add_argument("--py", type=Path, help="Optional aggregate Python JSONL fallback for tests/manual diagnostics.")
    parser.add_argument("--runs-dir", type=Path, default=ROOT_DIR / "runs")
    parser.add_argument("--samples-dir", type=Path, default=ROOT_DIR / "samples")
    parser.add_argument("--symbols", default=",".join(CORE5_SYMBOLS))
    parser.add_argument("--report", type=Path, default=ROOT_DIR / "parity_reports" / "core5_parity.md")
    parser.add_argument("--detail-dir", type=Path)
    parser.add_argument("--examples", type=int, default=32)
    parser.add_argument("--no-detail-reports", action="store_true")
    parser.add_argument("--bar-seconds", type=int, default=900)
    parser.add_argument("--exit-price-tolerance", type=float, default=0.15)
    parser.add_argument("--gate", choices=("off", "baseline", "strict"), default="off")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    detail_dir = None if args.no_detail_reports else (args.detail_dir or args.report.parent)
    tolerance = timedelta(seconds=args.bar_seconds)
    rows = [
        summarize_symbol(
            symbol=symbol,
            samples_dir=args.samples_dir,
            py_path=args.py,
            exact_runs_dir=args.runs_dir,
            detail_dir=detail_dir,
            tolerance=tolerance,
            exit_price_tolerance=args.exit_price_tolerance,
        )
        for symbol in parse_symbols(args.symbols)
    ]
    if not args.no_detail_reports:
        for row in rows:
            write_detail_reports(row, tolerance=tolerance, examples=args.examples)
    rows, gate_passed = apply_gate(rows, mode=args.gate)
    report = render_report(rows, py_path=None)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(report)
    return 0 if gate_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
