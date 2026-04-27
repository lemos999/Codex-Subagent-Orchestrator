from __future__ import annotations

import argparse
import csv
import json
import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parent
ENTRY_EVENTS = {"ENTRY_L1", "ENTRY_L2", "ENTRY_L3"}


@dataclass(slots=True, frozen=True)
class TvTrade:
    trade_no: int
    symbol: str
    side: str
    entry_event: str
    entry_ts: datetime
    exit_ts: datetime | None
    entry_price: float | None
    exit_price: float | None
    net_pnl_pct: float | None


@dataclass(slots=True, frozen=True)
class PyEvent:
    event: str
    symbol: str
    side: str
    ts: datetime
    price: float | None
    reason: str
    rr: float | None
    win: bool | None
    state2_trigger_source: str = ""
    state2_reverse_spike: bool | None = None
    state2_htf_cross: bool | None = None
    state2_current_r: float | None = None
    state2_peak_mfe: float | None = None
    state2_atr: float | None = None
    state2_hours_since_fill: float | None = None
    state2_active_rsm: float | None = None
    state2_reverse_spike_confirm_bars: int | None = None
    state2_reverse_spike_prev: bool | None = None
    state2_last_fill_event: str = ""
    state2_last_fill_reason: str = ""
    state2_minutes_since_last_fill: float | None = None
    state2_l2_filled: bool | None = None
    state2_l3_filled: bool | None = None
    state2_cvd_delta: float | None = None
    state2_cvd_delta_prev: float | None = None
    state2_reverse_spike_abs_sma_20: float | None = None
    state2_reverse_spike_abs_sma_20_prev: float | None = None
    state2_reverse_spike_threshold: float | None = None
    state2_reverse_spike_threshold_prev: float | None = None
    state2_reverse_spike_ratio: float | None = None
    state2_reverse_spike_ratio_prev: float | None = None
    state2_reverse_spike_margin: float | None = None


@dataclass(slots=True, frozen=True)
class Match:
    tv: TvTrade
    py: PyEvent | None
    delta: timedelta | None
    price_delta_pct: float | None


@dataclass(slots=True, frozen=True)
class PyCycle:
    entries: tuple[PyEvent, ...]
    exit: PyEvent | None


@dataclass(slots=True, frozen=True)
class ExitResidual:
    tv: TvTrade
    py_entry: PyEvent
    py_exit: PyEvent
    abs_exit_price_delta: float


@dataclass(slots=True, frozen=True)
class MatchedExitTimingResidual:
    tv: TvTrade
    py_entry: PyEvent
    py_exit: PyEvent | None
    signed_exit_delta: timedelta | None
    timing_bucket: str
    cause_bucket: str
    trigger_source: str


@dataclass(slots=True, frozen=True)
class UnmatchedClassification:
    tv: TvTrade
    bucket: str
    nearest: PyEvent | None
    nearest_delta: timedelta | None


def normalize_symbol(raw: str) -> str:
    symbol = raw.strip().upper()
    symbol = symbol.replace("BINANCE:", "").replace(".P", "")
    if "/" in symbol:
        return symbol.split("/", 1)[0]
    if symbol.endswith("USDT"):
        return symbol[:-4]
    return symbol


def parse_timestamp(raw: str) -> datetime:
    parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def parse_float(raw: Any) -> float | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    text = text.replace("\u202f", " ").replace("\xa0", " ")
    text = text.replace("−", "-")
    match = re.search(r"[-+]?\d[\d,]*(?:\.\d+)?", text)
    if match is None:
        return None
    return float(match.group(0).replace(",", ""))


def parse_pct(raw: Any) -> float | None:
    value = parse_float(raw)
    if value is None:
        return None
    return value / 100.0


def parse_int(raw: Any) -> int | None:
    value = parse_float(raw)
    if value is None:
        return None
    return int(value)


def parse_bool(raw: Any) -> bool | None:
    if isinstance(raw, bool):
        return raw
    if raw is None:
        return None
    lowered = str(raw).strip().lower()
    if lowered in {"true", "1", "yes", "win"}:
        return True
    if lowered in {"false", "0", "no", "loss"}:
        return False
    return None


def load_tv_raw(path: Path, symbol: str) -> list[TvTrade]:
    rows: list[TvTrade] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if normalize_symbol(row.get("symbol", "")) != symbol:
                continue
            entry_signal = str(row.get("entry_signal") or "").strip().upper()
            if entry_signal not in {"L1", "L2", "L3"}:
                continue
            rows.append(
                TvTrade(
                    trade_no=int(row.get("trade_no") or 0),
                    symbol=symbol,
                    side=str(row.get("side") or "").strip().lower(),
                    entry_event=f"ENTRY_{entry_signal}",
                    entry_ts=parse_timestamp(str(row["entry_time_utc"])),
                    exit_ts=parse_timestamp(str(row["exit_time_utc"])) if row.get("exit_time_utc") else None,
                    entry_price=parse_float(row.get("entry_price")),
                    exit_price=parse_float(row.get("exit_price")),
                    net_pnl_pct=parse_pct(row.get("net_pnl_pct")),
                )
            )
    return sorted(rows, key=lambda trade: trade.entry_ts)


def row_to_py_event(row: dict[str, Any]) -> PyEvent | None:
    event = str(row.get("event") or "")
    symbol_raw = row.get("symbol")
    ts_raw = row.get("ts")
    if not event or symbol_raw is None or ts_raw is None:
        return None
    rr = parse_float(row.get("rr") if row.get("rr") is not None else row.get("r_multiple"))
    return PyEvent(
        event=event,
        symbol=normalize_symbol(str(symbol_raw)),
        side=str(row.get("side") or "").strip().lower(),
        ts=parse_timestamp(str(ts_raw)),
        price=parse_float(row.get("price")),
        reason=str(row.get("reason") or ""),
        rr=rr,
        win=parse_bool(row.get("win")),
        state2_trigger_source=str(row.get("state2_trigger_source") or ""),
        state2_reverse_spike=parse_bool(row.get("state2_reverse_spike")),
        state2_htf_cross=parse_bool(row.get("state2_htf_cross")),
        state2_current_r=parse_float(row.get("state2_current_r")),
        state2_peak_mfe=parse_float(row.get("state2_peak_mfe")),
        state2_atr=parse_float(row.get("state2_atr")),
        state2_hours_since_fill=parse_float(row.get("state2_hours_since_fill")),
        state2_active_rsm=parse_float(row.get("state2_active_rsm")),
        state2_reverse_spike_confirm_bars=parse_int(
            row.get("state2_reverse_spike_confirm_bars"),
        ),
        state2_reverse_spike_prev=parse_bool(row.get("state2_reverse_spike_prev")),
        state2_last_fill_event=str(row.get("state2_last_fill_event") or ""),
        state2_last_fill_reason=str(row.get("state2_last_fill_reason") or ""),
        state2_minutes_since_last_fill=parse_float(row.get("state2_minutes_since_last_fill")),
        state2_l2_filled=parse_bool(row.get("state2_l2_filled")),
        state2_l3_filled=parse_bool(row.get("state2_l3_filled")),
        state2_cvd_delta=parse_float(row.get("state2_cvd_delta")),
        state2_cvd_delta_prev=parse_float(row.get("state2_cvd_delta_prev")),
        state2_reverse_spike_abs_sma_20=parse_float(row.get("state2_reverse_spike_abs_sma_20")),
        state2_reverse_spike_abs_sma_20_prev=parse_float(
            row.get("state2_reverse_spike_abs_sma_20_prev"),
        ),
        state2_reverse_spike_threshold=parse_float(row.get("state2_reverse_spike_threshold")),
        state2_reverse_spike_threshold_prev=parse_float(
            row.get("state2_reverse_spike_threshold_prev"),
        ),
        state2_reverse_spike_ratio=parse_float(row.get("state2_reverse_spike_ratio")),
        state2_reverse_spike_ratio_prev=parse_float(row.get("state2_reverse_spike_ratio_prev")),
        state2_reverse_spike_margin=parse_float(row.get("state2_reverse_spike_margin")),
    )


def load_python_events(path: Path, symbol: str) -> list[PyEvent]:
    events: list[PyEvent] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                continue
            event = row_to_py_event(raw)
            if event is not None and event.symbol == symbol:
                events.append(event)
    return sorted(events, key=lambda event: event.ts)


def closed_cycle_entries(
    events: list[PyEvent],
    tv_trades: list[TvTrade],
    *,
    tolerance: timedelta,
) -> list[PyEvent]:
    tv_entry_start = min((trade.entry_ts for trade in tv_trades), default=None)
    tv_entry_end = max((trade.entry_ts for trade in tv_trades), default=None)
    tv_exit_start = min((trade.exit_ts for trade in tv_trades if trade.exit_ts is not None), default=None)
    tv_exit_end = max((trade.exit_ts for trade in tv_trades if trade.exit_ts is not None), default=None)
    if tv_entry_start is None or tv_entry_end is None:
        return []

    entries: list[PyEvent] = []
    current_entries: list[PyEvent] = []
    for event in events:
        if event.event == "ENTRY_SIGNAL":
            current_entries = []
            continue
        if event.event in ENTRY_EVENTS:
            current_entries.append(event)
            continue
        if event.event != "EXIT":
            continue

        exit_in_window = True
        if tv_exit_start is not None and tv_exit_end is not None:
            exit_in_window = tv_exit_start - tolerance <= event.ts <= tv_exit_end + tolerance
        if exit_in_window:
            entries.extend(
                entry
                for entry in current_entries
                if tv_entry_start - tolerance <= entry.ts <= tv_entry_end + tolerance
            )
        current_entries = []
    return entries


def count_by(items: list[Any], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(getattr(item, key))
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def count_values(values: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def price_delta_pct(tv_price: float | None, py_price: float | None) -> float | None:
    if tv_price is None or py_price is None or math.isclose(tv_price, 0.0):
        return None
    return (py_price - tv_price) / tv_price


def match_trades(
    tv_trades: list[TvTrade],
    py_entries: list[PyEvent],
    *,
    tolerance: timedelta,
) -> list[Match]:
    candidate_pairs: list[tuple[timedelta, float, int, int]] = []
    for tv_index, tv in enumerate(tv_trades):
        for py_index, candidate in enumerate(py_entries):
            if candidate.event != tv.entry_event or candidate.side != tv.side:
                continue
            delta = abs(candidate.ts - tv.entry_ts)
            if delta > tolerance:
                continue
            price_delta = price_delta_pct(tv.entry_price, candidate.price)
            candidate_pairs.append(
                (
                    delta,
                    abs(price_delta) if price_delta is not None else math.inf,
                    tv_index,
                    py_index,
                )
            )

    assigned_tv: set[int] = set()
    assigned_py: set[int] = set()
    selected: dict[int, tuple[PyEvent, timedelta]] = {}
    for delta, _price_delta, tv_index, py_index in sorted(candidate_pairs):
        if tv_index in assigned_tv or py_index in assigned_py:
            continue
        assigned_tv.add(tv_index)
        assigned_py.add(py_index)
        selected[tv_index] = (py_entries[py_index], delta)

    matches: list[Match] = []
    for tv_index, tv in enumerate(tv_trades):
        selected_pair = selected.get(tv_index)
        if selected_pair is None:
            matches.append(Match(tv=tv, py=None, delta=None, price_delta_pct=None))
            continue
        py, delta = selected_pair
        matches.append(
            Match(
                tv=tv,
                py=py,
                delta=delta,
                price_delta_pct=price_delta_pct(tv.entry_price, py.price),
            )
        )
    return matches


def nearest_examples(tv_trades: list[TvTrade], py_entries: list[PyEvent], limit: int) -> list[tuple[TvTrade, PyEvent | None, timedelta | None]]:
    examples: list[tuple[TvTrade, PyEvent | None, timedelta | None]] = []
    for tv in tv_trades:
        candidates = [
            event
            for event in py_entries
            if event.event == tv.entry_event and event.side == tv.side
        ]
        if not candidates:
            examples.append((tv, None, None))
            continue
        nearest = min(candidates, key=lambda event: abs(event.ts - tv.entry_ts))
        examples.append((tv, nearest, abs(nearest.ts - tv.entry_ts)))
    return sorted(
        examples,
        key=lambda item: item[2] if item[2] is not None else timedelta.max,
        reverse=True,
    )[:limit]


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


def exit_by_entry(events: list[PyEvent]) -> dict[PyEvent, PyEvent | None]:
    result: dict[PyEvent, PyEvent | None] = {}
    for cycle in build_cycles(events):
        for entry in cycle.entries:
            result[entry] = cycle.exit
    return result


def exit_comparison_summary(
    matches: list[Match],
    py_events: list[PyEvent],
    *,
    tolerance: timedelta,
) -> dict[str, float | int | None]:
    exits = exit_by_entry(py_events)
    matched = [match for match in matches if match.py is not None]
    time_matches = 0
    price_deltas: list[float] = []
    for match in matched:
        assert match.py is not None
        py_exit = exits.get(match.py)
        if py_exit is None or match.tv.exit_ts is None:
            continue
        if abs(py_exit.ts - match.tv.exit_ts) <= tolerance:
            time_matches += 1
        if py_exit.price is not None and match.tv.exit_price is not None:
            price_deltas.append(abs(py_exit.price - match.tv.exit_price))
    return {
        "exit_timestamp_matches": time_matches,
        "exit_price_within_0_15": sum(1 for delta in price_deltas if delta <= 0.15),
        "exit_price_within_1_0": sum(1 for delta in price_deltas if delta <= 1.0),
        "avg_abs_exit_price_delta": (
            sum(price_deltas) / len(price_deltas) if price_deltas else None
        ),
        "max_abs_exit_price_delta": max(price_deltas) if price_deltas else None,
    }


def exit_reason_summary(
    matches: list[Match],
    py_events: list[PyEvent],
    *,
    tolerance: timedelta,
) -> dict[str, dict[str, int]]:
    exits = exit_by_entry(py_events)
    summary: dict[str, dict[str, int]] = {}
    for match in matches:
        if match.py is None:
            continue
        py_exit = exits.get(match.py)
        if py_exit is None:
            reason = "missing-python-exit"
        else:
            reason = py_exit.reason or "unknown"
        row = summary.setdefault(
            reason,
            {
                "matched_entries": 0,
                "exit_timestamp_matches": 0,
                "exit_price_within_0_15": 0,
                "exit_price_within_1_0": 0,
            },
        )
        row["matched_entries"] += 1
        if py_exit is None or match.tv.exit_ts is None:
            continue
        if abs(py_exit.ts - match.tv.exit_ts) <= tolerance:
            row["exit_timestamp_matches"] += 1
        if py_exit.price is None or match.tv.exit_price is None:
            continue
        delta = abs(py_exit.price - match.tv.exit_price)
        if delta <= 0.15:
            row["exit_price_within_0_15"] += 1
        if delta <= 1.0:
            row["exit_price_within_1_0"] += 1
    return dict(sorted(summary.items()))


def matched_exit_timing_bucket(
    tv_exit_ts: datetime | None,
    py_exit_ts: datetime | None,
    *,
    tolerance: timedelta,
) -> tuple[str, timedelta | None]:
    if tv_exit_ts is None:
        return "missing_tv_exit", None
    if py_exit_ts is None:
        return "missing_python_exit", None
    signed_delta = py_exit_ts - tv_exit_ts
    if abs(signed_delta) <= tolerance:
        return "matched_within_tolerance", signed_delta
    if signed_delta.total_seconds() < 0:
        return "python_exit_early", signed_delta
    return "python_exit_late", signed_delta


def matched_exit_cause_bucket(
    match: Match,
    py_exit: PyEvent | None,
    *,
    tolerance: timedelta,
) -> str:
    if py_exit is None:
        return "missing_python_exit"
    reason = py_exit.reason.upper()
    if "HTF" in reason or "CROSS" in reason:
        return "htf_cross_pulse"
    if "REVERSE" in reason or "SPIKE" in reason:
        return "reverse_spike_pulse"
    if py_exit.reason != "STATE_2_ABORT":
        return "non_state2_abort"
    trigger_source = py_state2_trigger_source(py_exit)
    if match.py is not None and abs(py_exit.ts - match.py.ts) <= tolerance:
        return "same_bar_close_or_fill_ordering"
    if match.delta is not None and match.delta > timedelta(0):
        return "entry_cycle_drift"
    if trigger_source in {"reverse_spike", "htf_cross", "both"}:
        return f"state2_{trigger_source}"
    return "unknown_state2_abort"


def py_state2_trigger_source(py_exit: PyEvent | None) -> str:
    if py_exit is None or py_exit.reason != "STATE_2_ABORT":
        return ""
    source = py_exit.state2_trigger_source.strip()
    if source:
        return source
    if py_exit.state2_reverse_spike is True and py_exit.state2_htf_cross is True:
        return "both"
    if py_exit.state2_reverse_spike is True:
        return "reverse_spike"
    if py_exit.state2_htf_cross is True:
        return "htf_cross"
    return "unknown_state2_abort"


def state2_trigger_source_summary(
    matches: list[Match],
    py_events: list[PyEvent],
    *,
    tolerance: timedelta,
) -> dict[str, dict[str, int]]:
    exits = exit_by_entry(py_events)
    summary: dict[str, dict[str, int]] = {}
    for match in matches:
        if match.py is None:
            continue
        py_exit = exits.get(match.py)
        source = py_state2_trigger_source(py_exit)
        if not source:
            continue
        timing_bucket, _ = matched_exit_timing_bucket(
            match.tv.exit_ts,
            py_exit.ts if py_exit is not None else None,
            tolerance=tolerance,
        )
        row = summary.setdefault(
            source,
            {
                "matched_state2_exits": 0,
                "exit_timestamp_matches": 0,
                "python_exit_early": 0,
                "python_exit_late": 0,
            },
        )
        row["matched_state2_exits"] += 1
        if timing_bucket == "matched_within_tolerance":
            row["exit_timestamp_matches"] += 1
        elif timing_bucket == "python_exit_early":
            row["python_exit_early"] += 1
        elif timing_bucket == "python_exit_late":
            row["python_exit_late"] += 1
    return dict(sorted(summary.items()))


def matched_exit_timing_residuals(
    matches: list[Match],
    py_events: list[PyEvent],
    *,
    tolerance: timedelta,
) -> list[MatchedExitTimingResidual]:
    exits = exit_by_entry(py_events)
    residuals: list[MatchedExitTimingResidual] = []
    for match in matches:
        if match.py is None:
            continue
        py_exit = exits.get(match.py)
        timing_bucket, signed_delta = matched_exit_timing_bucket(
            match.tv.exit_ts,
            py_exit.ts if py_exit is not None else None,
            tolerance=tolerance,
        )
        if timing_bucket == "matched_within_tolerance":
            continue
        residuals.append(
            MatchedExitTimingResidual(
                tv=match.tv,
                py_entry=match.py,
                py_exit=py_exit,
                signed_exit_delta=signed_delta,
                timing_bucket=timing_bucket,
                cause_bucket=matched_exit_cause_bucket(
                    match,
                    py_exit,
                    tolerance=tolerance,
                ),
                trigger_source=py_state2_trigger_source(py_exit),
            )
        )
    return sorted(
        residuals,
        key=lambda residual: (
            abs(residual.signed_exit_delta.total_seconds())
            if residual.signed_exit_delta is not None
            else float("inf")
        ),
        reverse=True,
    )


def worst_exit_price_residuals(
    matches: list[Match],
    py_events: list[PyEvent],
    limit: int,
) -> list[ExitResidual]:
    exits = exit_by_entry(py_events)
    residuals: list[ExitResidual] = []
    for match in matches:
        if match.py is None:
            continue
        py_exit = exits.get(match.py)
        if py_exit is None or py_exit.price is None or match.tv.exit_price is None:
            continue
        residuals.append(
            ExitResidual(
                tv=match.tv,
                py_entry=match.py,
                py_exit=py_exit,
                abs_exit_price_delta=abs(py_exit.price - match.tv.exit_price),
            )
        )
    return sorted(
        residuals,
        key=lambda residual: residual.abs_exit_price_delta,
        reverse=True,
    )[:limit]


def classify_unmatched_trade(
    tv: TvTrade,
    py_entries: list[PyEvent],
    *,
    tolerance: timedelta,
) -> UnmatchedClassification:
    if not py_entries:
        return UnmatchedClassification(tv, "missing-python-cycle", None, None)

    nearest = min(py_entries, key=lambda event: abs(event.ts - tv.entry_ts))
    nearest_delta = abs(nearest.ts - tv.entry_ts)
    py_start = min(event.ts for event in py_entries)
    py_end = max(event.ts for event in py_entries)
    if tv.entry_ts < py_start - tolerance or tv.entry_ts > py_end + tolerance:
        return UnmatchedClassification(tv, "outside_python_artifact", nearest, nearest_delta)

    same_bar = [
        event
        for event in py_entries
        if abs(event.ts - tv.entry_ts) <= tolerance
    ]
    if any(event.side == tv.side and event.event != tv.entry_event for event in same_bar):
        return UnmatchedClassification(tv, "event-layer-drift", nearest, nearest_delta)
    if any(event.event == tv.entry_event and event.side != tv.side for event in same_bar):
        return UnmatchedClassification(tv, "side-drift", nearest, nearest_delta)

    same_event_side = [
        event
        for event in py_entries
        if event.event == tv.entry_event and event.side == tv.side
    ]
    if same_event_side:
        nearest_same = min(same_event_side, key=lambda event: abs(event.ts - tv.entry_ts))
        same_delta = abs(nearest_same.ts - tv.entry_ts)
        if same_delta <= max(tolerance * 8, timedelta(hours=4)):
            return UnmatchedClassification(tv, "same-cycle-shift", nearest_same, same_delta)

    return UnmatchedClassification(tv, "missing-python-cycle", nearest, nearest_delta)


def classify_unmatched_trades(
    matches: list[Match],
    py_entries: list[PyEvent],
    *,
    tolerance: timedelta,
) -> list[UnmatchedClassification]:
    return [
        classify_unmatched_trade(match.tv, py_entries, tolerance=tolerance)
        for match in matches
        if match.py is None
    ]


def format_dt(ts: datetime | None) -> str:
    if ts is None:
        return ""
    return ts.isoformat().replace("+00:00", "Z")


def format_float(value: float | None, digits: int = 6) -> str:
    if value is None:
        return ""
    return f"{value:.{digits}f}"


def format_minutes(value: float | None, digits: int = 1) -> str:
    if value is None:
        return ""
    return f"{value:.{digits}f}m"


def format_bool(value: bool | None) -> str:
    if value is None:
        return ""
    return "true" if value else "false"


def format_delta(delta: timedelta | None) -> str:
    if delta is None:
        return ""
    return f"{delta.total_seconds() / 60:.1f}m"


def format_signed_delta(delta: timedelta | None) -> str:
    if delta is None:
        return ""
    return f"{delta.total_seconds() / 60:+.1f}m"


def render_report(
    *,
    symbol: str,
    tv_path: Path,
    py_path: Path,
    tv_trades: list[TvTrade],
    py_entries: list[PyEvent],
    py_entries_in_window: list[PyEvent],
    matches: list[Match],
    tolerance: timedelta,
    examples: int,
    py_events: list[PyEvent] | None = None,
    tv_total_rows: int | None = None,
    tv_before_python_rows: int = 0,
    tv_tail_after_python_rows: int = 0,
) -> str:
    matched = [match for match in matches if match.py is not None]
    unmatched = [match for match in matches if match.py is None]
    tv_start = min((trade.entry_ts for trade in tv_trades), default=None)
    tv_end = max((trade.entry_ts for trade in tv_trades), default=None)
    tv_total = tv_total_rows if tv_total_rows is not None else len(tv_trades)
    match_rate = len(matched) / len(tv_trades) if tv_trades else 0.0
    avg_delta = (
        sum(match.delta.total_seconds() for match in matched if match.delta is not None) / len(matched)
        if matched
        else None
    )
    avg_price_delta = (
        sum(abs(match.price_delta_pct) for match in matched if match.price_delta_pct is not None)
        / sum(1 for match in matched if match.price_delta_pct is not None)
        if any(match.price_delta_pct is not None for match in matched)
        else None
    )
    exit_summary = (
        exit_comparison_summary(matches, py_events, tolerance=tolerance)
        if py_events is not None
        else {}
    )
    exit_residuals = (
        worst_exit_price_residuals(matches, py_events, examples)
        if py_events is not None
        else []
    )
    unmatched_classifications = classify_unmatched_trades(
        matches,
        py_entries,
        tolerance=tolerance,
    )
    unmatched_by_trade_no = {
        classification.tv.trade_no: classification
        for classification in unmatched_classifications
    }
    unmatched_counts = count_values(
        [classification.bucket for classification in unmatched_classifications]
    )
    reason_summary = (
        exit_reason_summary(matches, py_events, tolerance=tolerance)
        if py_events is not None
        else {}
    )
    trigger_summary = (
        state2_trigger_source_summary(matches, py_events, tolerance=tolerance)
        if py_events is not None
        else {}
    )
    exit_timing_residuals = (
        matched_exit_timing_residuals(matches, py_events, tolerance=tolerance)
        if py_events is not None
        else []
    )
    timing_counts = count_values(
        [residual.timing_bucket for residual in exit_timing_residuals]
    )
    cause_counts = count_values(
        [residual.cause_bucket for residual in exit_timing_residuals]
    )

    lines = [
        f"# MTS-V1 {symbol} TradingView/Python Diff",
        "",
        "## Inputs",
        f"- TradingView raw CSV: `{tv_path}`",
        f"- Python JSONL: `{py_path}`",
        f"- Match tolerance: `{format_delta(tolerance)}`",
        f"- TradingView entry range: `{format_dt(tv_start)}` to `{format_dt(tv_end)}`",
        f"- TradingView raw rows: `{tv_total}`",
        f"- TradingView common-window rows: `{len(tv_trades)}`",
        f"- TradingView rows before Python artifact: `{tv_before_python_rows}`",
        f"- TradingView tail after Python artifact: `{tv_tail_after_python_rows}`",
        "",
        "## Counts",
        "",
        "| Source | Scope | Count | By event | By side |",
        "|---|---|---:|---|---|",
        f"| TradingView | common-window closed trades | {len(tv_trades)} | `{count_by(tv_trades, 'entry_event')}` | `{count_by(tv_trades, 'side')}` |",
        f"| TradingView | raw capture rows | {tv_total} | | |",
        f"| TradingView | outside Python artifact | {tv_before_python_rows + tv_tail_after_python_rows} | `{{'before': {tv_before_python_rows}, 'tail': {tv_tail_after_python_rows}}}` | |",
        f"| Python | all `{symbol}` filled entries | {len(py_entries)} | `{count_by(py_entries, 'event')}` | `{count_by(py_entries, 'side')}` |",
        f"| Python | TradingView date window | {len(py_entries_in_window)} | `{count_by(py_entries_in_window, 'event')}` | `{count_by(py_entries_in_window, 'side')}` |",
        "",
        "## Match Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| matched_common_window_tv_trades | {len(matched)} / {len(tv_trades)} |",
        f"| common_window_match_rate | {match_rate:.6f} |",
        f"| unmatched_tv_trades | {len(unmatched)} |",
        f"| avg_abs_time_delta_minutes | {avg_delta / 60:.3f} |"
        if avg_delta is not None
        else "| avg_abs_time_delta_minutes | |",
        f"| avg_abs_entry_price_delta_pct | {avg_price_delta:.6f} |"
        if avg_price_delta is not None
        else "| avg_abs_entry_price_delta_pct | |",
        f"| exit_timestamp_matches | {exit_summary.get('exit_timestamp_matches')} / {len(matched)} |"
        if exit_summary
        else "| exit_timestamp_matches | |",
        f"| exit_price_within_0_15 | {exit_summary.get('exit_price_within_0_15')} / {len(matched)} |"
        if exit_summary
        else "| exit_price_within_0_15 | |",
        f"| exit_price_within_1_0 | {exit_summary.get('exit_price_within_1_0')} / {len(matched)} |"
        if exit_summary
        else "| exit_price_within_1_0 | |",
        f"| avg_abs_exit_price_delta | {exit_summary.get('avg_abs_exit_price_delta'):.6f} |"
        if exit_summary and exit_summary.get("avg_abs_exit_price_delta") is not None
        else "| avg_abs_exit_price_delta | |",
        f"| max_abs_exit_price_delta | {exit_summary.get('max_abs_exit_price_delta'):.6f} |"
        if exit_summary and exit_summary.get("max_abs_exit_price_delta") is not None
        else "| max_abs_exit_price_delta | |",
        f"| unmatched_classification | `{unmatched_counts}` |",
        f"| matched_exit_timing_residuals | `{timing_counts}` |",
        f"| matched_exit_cause_buckets | `{cause_counts}` |",
        "",
        "## Exit Reason Summary",
        "",
        "| Python exit reason | Matched entries | Exit timestamp matches | Exit price <=0.15 | Exit price <=1.0 |",
        "|---|---:|---:|---:|---:|",
    ]
    for reason, counts in reason_summary.items():
        lines.append(
            f"| {reason} | {counts['matched_entries']} | "
            f"{counts['exit_timestamp_matches']} | "
            f"{counts['exit_price_within_0_15']} | "
            f"{counts['exit_price_within_1_0']} |"
        )

    lines.extend(
        [
            "",
            "## State2 Trigger Source Summary",
            "",
            "| Python State2 trigger | Matched State2 exits | Exit timestamp matches | Python exit early | Python exit late |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for source, counts in trigger_summary.items():
        lines.append(
            f"| {source} | {counts['matched_state2_exits']} | "
            f"{counts['exit_timestamp_matches']} | "
            f"{counts['python_exit_early']} | "
            f"{counts['python_exit_late']} |"
        )

    lines.extend(
        [
            "",
            "## Matched Exit Timing Residuals",
            "",
            "| Trade | Timing bucket | Cause bucket | Python State2 trigger | Event | Side | TV entry UTC | TV exit UTC | Python entry UTC | Python exit UTC | Signed exit delta | CVD delta | Reverse threshold | Reverse ratio | Prev ratio | Prev pulse | Confirm bars | Last fill | Last fill age | L2 filled | Python exit reason | Python entry reason |",
            "|---:|---|---|---|---|---|---|---|---|---|---:|---:|---:|---:|---:|---|---:|---|---:|---|---|---|",
        ]
    )
    for residual in exit_timing_residuals[:examples]:
        py_exit = residual.py_exit
        last_fill = ""
        if py_exit is not None and py_exit.state2_last_fill_event:
            last_fill = f"{py_exit.state2_last_fill_event}/{py_exit.state2_last_fill_reason}"
        lines.append(
            f"| {residual.tv.trade_no} | {residual.timing_bucket} | {residual.cause_bucket} | "
            f"{residual.trigger_source} | "
            f"{residual.tv.entry_event} | {residual.tv.side} | "
            f"{format_dt(residual.tv.entry_ts)} | {format_dt(residual.tv.exit_ts)} | "
            f"{format_dt(residual.py_entry.ts)} | "
            f"{format_dt(py_exit.ts if py_exit is not None else None)} | "
            f"{format_signed_delta(residual.signed_exit_delta)} | "
            f"{format_float(py_exit.state2_cvd_delta if py_exit is not None else None, 4)} | "
            f"{format_float(py_exit.state2_reverse_spike_threshold if py_exit is not None else None, 4)} | "
            f"{format_float(py_exit.state2_reverse_spike_ratio if py_exit is not None else None, 4)} | "
            f"{format_float(py_exit.state2_reverse_spike_ratio_prev if py_exit is not None else None, 4)} | "
            f"{format_bool(py_exit.state2_reverse_spike_prev if py_exit is not None else None)} | "
            f"{py_exit.state2_reverse_spike_confirm_bars if py_exit is not None and py_exit.state2_reverse_spike_confirm_bars is not None else ''} | "
            f"{last_fill} | "
            f"{format_minutes(py_exit.state2_minutes_since_last_fill if py_exit is not None else None)} | "
            f"{format_bool(py_exit.state2_l2_filled if py_exit is not None else None)} | "
            f"{py_exit.reason if py_exit is not None else ''} | "
            f"{residual.py_entry.reason} |"
        )

    lines.extend(
        [
            "",
            "## Worst Matched Exit Price Residuals",
            "",
            "| Trade | Event | Side | TV entry UTC | TV exit UTC | Python entry UTC | Python exit UTC | TV exit price | Python exit price | Abs delta | Python exit reason | Python entry reason |",
            "|---:|---|---|---|---|---|---|---:|---:|---:|---|---|",
        ]
    )
    for residual in exit_residuals:
        lines.append(
            f"| {residual.tv.trade_no} | {residual.tv.entry_event} | {residual.tv.side} | "
            f"{format_dt(residual.tv.entry_ts)} | {format_dt(residual.tv.exit_ts)} | "
            f"{format_dt(residual.py_entry.ts)} | {format_dt(residual.py_exit.ts)} | "
            f"{format_float(residual.tv.exit_price, 4)} | "
            f"{format_float(residual.py_exit.price, 4)} | "
            f"{format_float(residual.abs_exit_price_delta, 4)} | "
            f"{residual.py_exit.reason} | {residual.py_entry.reason} |"
        )
    lines.extend(
        [
            "",
            "## Unmatched Classification",
            "",
            "| Bucket | Count |",
            "|---|---:|",
        ]
    )
    for bucket, count in unmatched_counts.items():
        lines.append(f"| {bucket} | {count} |")

    lines.extend(
        [
            "",
            "## Unmatched TradingView Trades",
            "",
            "| Trade | Class | Event | Side | TV entry UTC | TV entry price | TV pnl pct | Nearest Python UTC | Nearest event | Nearest side | Delta | Python reason |",
            "|---:|---|---|---|---|---:|---:|---|---|---|---:|---|",
        ]
    )
    for match in unmatched[:examples]:
        tv = match.tv
        classification = unmatched_by_trade_no.get(tv.trade_no)
        nearest = classification.nearest if classification is not None else None
        lines.append(
            f"| {tv.trade_no} | {classification.bucket if classification is not None else ''} | "
            f"{tv.entry_event} | {tv.side} | {format_dt(tv.entry_ts)} | "
            f"{format_float(tv.entry_price, 4)} | {format_float(tv.net_pnl_pct, 6)} | "
            f"{format_dt(nearest.ts if nearest is not None else None)} | "
            f"{nearest.event if nearest is not None else ''} | "
            f"{nearest.side if nearest is not None else ''} | "
            f"{format_delta(classification.nearest_delta if classification is not None else None)} | "
            f"{nearest.reason if nearest is not None else ''} |"
        )

    lines.extend(
        [
            "",
            "## Worst Nearest Filled-Entry Deltas",
            "",
            "| Trade | Event | Side | TV entry UTC | Nearest Python UTC | Delta | TV price | Python price | Python reason |",
            "|---:|---|---|---|---|---:|---:|---:|---|",
        ]
    )
    for tv, py, delta in nearest_examples(tv_trades, py_entries_in_window or py_entries, examples):
        lines.append(
            f"| {tv.trade_no} | {tv.entry_event} | {tv.side} | {format_dt(tv.entry_ts)} | "
            f"{format_dt(py.ts if py else None)} | {format_delta(delta)} | "
            f"{format_float(tv.entry_price, 4)} | {format_float(py.price if py else None, 4)} | "
            f"{py.reason if py else ''} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation Notes",
            "- This report compares TradingView filled trade rows only against Python `ENTRY_L1/L2/L3` rows.",
            "- It intentionally does not compare TradingView rows to Python `ENTRY_SIGNAL`, because that is a pre-fill trigger.",
            "- TradingView `net_pnl_pct` is not the same unit as Python `r_multiple`; use price/time/side first, then handle PnL separately.",
            "- If Python date-window counts are much larger than TradingView counts, the next check is profile parity: chart timeframe, `entry_timeframe`, `execution_timeframe`, RSM overrides, and available TradingView history.",
            "",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a BTC TradingView/Python filled-entry diff report.")
    parser.add_argument("--symbol", default="BTC")
    parser.add_argument("--tv-raw", type=Path, default=ROOT_DIR / "samples" / "tradingview_mtsv1_BTC_raw.csv")
    parser.add_argument(
        "--py",
        type=Path,
        default=ROOT_DIR / "runs" / "mtsv1_improve_core5_symbol_rsm_best5_nol3cap" / "trades.jsonl",
    )
    parser.add_argument("--report", type=Path, default=ROOT_DIR / "parity_reports" / "btc_diff.md")
    parser.add_argument("--bar-seconds", type=int, default=900)
    parser.add_argument("--examples", type=int, default=12)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    symbol = normalize_symbol(args.symbol)
    tv_trades = load_tv_raw(args.tv_raw, symbol)
    py_events = load_python_events(args.py, symbol)
    py_entries = [event for event in py_events if event.event in ENTRY_EVENTS]
    py_entries_in_window = closed_cycle_entries(
        py_events,
        tv_trades,
        tolerance=timedelta(seconds=args.bar_seconds),
    )
    matches = match_trades(
        tv_trades,
        py_entries_in_window,
        tolerance=timedelta(seconds=args.bar_seconds),
    )
    report = render_report(
        symbol=symbol,
        tv_path=args.tv_raw,
        py_path=args.py,
        tv_trades=tv_trades,
        py_entries=py_entries,
        py_entries_in_window=py_entries_in_window,
        matches=matches,
        tolerance=timedelta(seconds=args.bar_seconds),
        examples=args.examples,
        py_events=py_events,
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
