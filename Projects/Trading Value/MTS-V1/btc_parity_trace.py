from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from btc_parity_diff import (
    ENTRY_EVENTS,
    PyEvent,
    TvTrade,
    closed_cycle_entries,
    format_delta,
    format_dt,
    format_float,
    exit_comparison_summary,
    load_python_events,
    load_tv_raw,
    match_trades,
    normalize_symbol,
    py_state2_trigger_source,
)


ROOT_DIR = Path(__file__).resolve().parent


@dataclass(slots=True)
class PyCycle:
    cycle_id: int
    signal: PyEvent
    entries: list[PyEvent]
    exit: PyEvent | None


def build_cycles(events: list[PyEvent]) -> list[PyCycle]:
    cycles: list[PyCycle] = []
    current_signal: PyEvent | None = None
    current_entries: list[PyEvent] = []
    cycle_id = 0

    for event in events:
        if event.event == "ENTRY_SIGNAL":
            if current_signal is not None:
                cycles.append(PyCycle(cycle_id, current_signal, current_entries, None))
            cycle_id += 1
            current_signal = event
            current_entries = []
            continue

        if current_signal is None:
            continue
        if event.event in ENTRY_EVENTS:
            current_entries.append(event)
            continue
        if event.event == "EXIT":
            cycles.append(PyCycle(cycle_id, current_signal, current_entries, event))
            current_signal = None
            current_entries = []

    if current_signal is not None:
        cycles.append(PyCycle(cycle_id, current_signal, current_entries, None))
    return cycles


def active_cycle_at(cycles: list[PyCycle], ts: datetime) -> PyCycle | None:
    for index, cycle in enumerate(cycles):
        next_start = cycles[index + 1].signal.ts if index + 1 < len(cycles) else None
        end_ts = cycle.exit.ts if cycle.exit is not None else next_start
        if end_ts is None:
            end_ts = datetime.max.replace(tzinfo=ts.tzinfo)
        if cycle.signal.ts <= ts <= end_ts:
            return cycle
    return None


def nearest_entry(
    cycles: list[PyCycle],
    tv: TvTrade,
) -> tuple[PyCycle | None, PyEvent | None, timedelta | None]:
    candidates: list[tuple[timedelta, PyCycle, PyEvent]] = []
    for cycle in cycles:
        for entry in cycle.entries:
            if entry.event == tv.entry_event and entry.side == tv.side:
                candidates.append((abs(entry.ts - tv.entry_ts), cycle, entry))
    if not candidates:
        return None, None, None
    delta, cycle, entry = min(candidates, key=lambda item: item[0])
    return cycle, entry, delta


def cycle_by_entry(cycles: list[PyCycle]) -> dict[PyEvent, PyCycle]:
    result: dict[PyEvent, PyCycle] = {}
    for cycle in cycles:
        for entry in cycle.entries:
            result[entry] = cycle
    return result


def cycle_summary(cycle: PyCycle | None) -> str:
    if cycle is None:
        return ""
    exit_text = ""
    if cycle.exit is not None:
        exit_text = f"{format_dt(cycle.exit.ts)} {cycle.exit.reason} {format_float(cycle.exit.price, 4)}"
    entries = ", ".join(
        f"{entry.event}@{format_dt(entry.ts)} {format_float(entry.price, 4)} {entry.reason}"
        for entry in cycle.entries
    )
    return (
        f"#{cycle.cycle_id} {cycle.signal.side} sig {format_dt(cycle.signal.ts)} "
        f"{format_float(cycle.signal.price, 4)} entries [{entries}] exit [{exit_text}]"
    )


def render_trace(
    *,
    symbol: str,
    tv_trades: list[TvTrade],
    py_events: list[PyEvent],
    tolerance: timedelta,
    examples: int,
    tv_total_rows: int | None = None,
    tv_before_python_rows: int = 0,
    tv_tail_after_python_rows: int = 0,
) -> str:
    cycles = build_cycles(py_events)
    py_entries = [event for event in py_events if event.event in ENTRY_EVENTS]
    py_entries_in_window = closed_cycle_entries(py_events, tv_trades, tolerance=tolerance)
    matches = match_trades(tv_trades, py_entries_in_window, tolerance=tolerance)
    unmatched = [match for match in matches if match.py is None]
    matched = [match for match in matches if match.py is not None]
    cycle_for_entry = cycle_by_entry(cycles)
    exit_summary = exit_comparison_summary(
        matches,
        py_events,
        tolerance=tolerance,
    )
    tv_total = tv_total_rows if tv_total_rows is not None else len(tv_trades)

    lines = [
        f"# MTS-V1 {symbol} Parity Trace",
        "",
        "## Summary",
        "",
        f"- TV raw closed trade rows: {tv_total}",
        f"- TV common-window closed trade rows: {len(tv_trades)}",
        f"- TV rows before Python artifact: {tv_before_python_rows}",
        f"- TV tail after Python artifact: {tv_tail_after_python_rows}",
        f"- Python cycles: {len(cycles)}",
        f"- Python filled entries: {len(py_entries)}",
        f"- Python closed-cycle candidate entries: {len(py_entries_in_window)}",
        f"- Matched common-window TV rows: {len(matches) - len(unmatched)} / {len(tv_trades)}",
        f"- Exit timestamp matches: {exit_summary['exit_timestamp_matches']} / {len(matches) - len(unmatched)}",
        f"- Exit price <= 0.15: {exit_summary['exit_price_within_0_15']} / {len(matches) - len(unmatched)}",
        f"- Exit price <= 1.0: {exit_summary['exit_price_within_1_0']} / {len(matches) - len(unmatched)}",
        "",
        "## Matched Cycle Alignment",
        "",
        "| TV | Event | Side | Python cycle | TV entry | Python entry | Entry delta | TV exit | Python exit | Exit delta | Python exit reason | Python State2 trigger | Same-cycle pass |",
        "|---:|---|---|---:|---|---|---:|---|---|---:|---|---|---|",
    ]
    for match in matched[:examples]:
        assert match.py is not None
        cycle = cycle_for_entry.get(match.py)
        py_exit = cycle.exit if cycle is not None else None
        entry_delta = abs(match.py.ts - match.tv.entry_ts)
        exit_delta = (
            abs(py_exit.ts - match.tv.exit_ts)
            if py_exit is not None and match.tv.exit_ts is not None
            else None
        )
        same_cycle_pass = bool(
            cycle is not None
            and entry_delta <= tolerance
            and exit_delta is not None
            and exit_delta <= tolerance
        )
        lines.append(
            f"| {match.tv.trade_no} | {match.tv.entry_event} | {match.tv.side} | "
            f"{cycle.cycle_id if cycle is not None else ''} | "
            f"{format_dt(match.tv.entry_ts)} | {format_dt(match.py.ts)} | {format_delta(entry_delta)} | "
            f"{format_dt(match.tv.exit_ts)} | {format_dt(py_exit.ts if py_exit is not None else None)} | "
            f"{format_delta(exit_delta)} | {py_exit.reason if py_exit is not None else ''} | "
            f"{py_state2_trigger_source(py_exit)} | "
            f"{str(same_cycle_pass).lower()} |"
        )

    lines.extend(
        [
            "",
        "## Unmatched Rows",
        "",
        "| TV | Event | Side | TV entry | TV exit | Active Python cycle at TV entry | Nearest same event/side Python entry | Nearest delta |",
        "|---:|---|---|---|---|---|---|---:|",
        ]
    )
    for match in unmatched[:examples]:
        tv = match.tv
        active = active_cycle_at(cycles, tv.entry_ts)
        nearest_cycle, nearest_py, nearest_delta = nearest_entry(cycles, tv)
        lines.append(
            f"| {tv.trade_no} | {tv.entry_event} | {tv.side} | {format_dt(tv.entry_ts)} "
            f"{format_float(tv.entry_price, 4)} | {format_dt(tv.exit_ts)} "
            f"{format_float(tv.exit_price, 4)} | {cycle_summary(active)} | "
            f"{cycle_summary(nearest_cycle) if nearest_py is not None else ''} | "
            f"{format_delta(nearest_delta)} |"
        )

    lines.extend(
        [
            "",
            "## Python Cycles In TV Entry Range",
            "",
            "| Cycle | Side | Signal | Entries | Exit |",
            "|---:|---|---|---|---|",
        ]
    )
    tv_start = min((trade.entry_ts for trade in tv_trades), default=None)
    tv_end = max((trade.entry_ts for trade in tv_trades), default=None)
    for cycle in cycles:
        if tv_start is not None and tv_end is not None and not (
            tv_start - tolerance <= cycle.signal.ts <= tv_end + tolerance
            or any(tv_start - tolerance <= entry.ts <= tv_end + tolerance for entry in cycle.entries)
        ):
            continue
        entries = "<br>".join(
            f"{entry.event} {format_dt(entry.ts)} {format_float(entry.price, 4)} {entry.reason}"
            for entry in cycle.entries
        )
        exit_text = ""
        if cycle.exit is not None:
            trigger = py_state2_trigger_source(cycle.exit)
            trigger_text = f" {trigger}" if trigger else ""
            exit_text = f"{format_dt(cycle.exit.ts)} {format_float(cycle.exit.price, 4)} {cycle.exit.reason}{trigger_text}"
        lines.append(
            f"| {cycle.cycle_id} | {cycle.signal.side} | {format_dt(cycle.signal.ts)} "
            f"{format_float(cycle.signal.price, 4)} | {entries} | {exit_text} |"
        )

    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a TradingView/Python cycle trace for MTS-V1 parity.")
    parser.add_argument("--symbol", default="BTC")
    parser.add_argument("--tv-raw", type=Path, default=ROOT_DIR / "samples" / "tradingview_mtsv1_BTC_entry15_raw.csv")
    parser.add_argument("--py", type=Path, default=ROOT_DIR / "runs" / "mtsv1_tv_btc_15m_binanceusdm_profile" / "trades.jsonl")
    parser.add_argument("--report", type=Path, default=ROOT_DIR / "parity_reports" / "btc_trace_entry15.md")
    parser.add_argument("--bar-seconds", type=int, default=900)
    parser.add_argument("--examples", type=int, default=32)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    symbol = normalize_symbol(args.symbol)
    tv_trades = load_tv_raw(args.tv_raw, symbol)
    py_events = load_python_events(args.py, symbol)
    report = render_trace(
        symbol=symbol,
        tv_trades=tv_trades,
        py_events=py_events,
        tolerance=timedelta(seconds=args.bar_seconds),
        examples=args.examples,
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
