from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


ENTRY_EVENTS = {"ENTRY_SIGNAL", "ENTRY_L1", "ENTRY_L2", "ENTRY_L3"}


@dataclass(slots=True, frozen=True)
class ParityMetric:
    name: str
    value: float
    threshold: str
    passed: bool
    detail: str
    comparable_count: int


@dataclass(slots=True, frozen=True)
class TradeEvent:
    ts: datetime
    event: str
    symbol: str | None = None
    rr: float | None = None
    win: bool | None = None
    cvd_sign: int | None = None


def parse_timestamp(raw: str) -> datetime:
    parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def parse_bool(raw: Any) -> bool | None:
    if isinstance(raw, bool):
        return raw
    if raw is None or raw == "":
        return None
    lowered = str(raw).strip().lower()
    if lowered in {"1", "true", "yes", "win"}:
        return True
    if lowered in {"0", "false", "no", "loss"}:
        return False
    return None


def parse_float(raw: Any) -> float | None:
    if raw is None or raw == "":
        return None
    return float(raw)


def parse_cvd_sign(raw: Any) -> int | None:
    value = parse_float(raw)
    if value is None or math.isclose(value, 0.0):
        return None
    return 1 if value > 0 else -1


def normalize_symbol(raw: str) -> str:
    symbol = raw.strip().upper()
    if not symbol:
        return ""
    symbol = symbol.replace("BINANCE:", "")
    symbol = symbol.replace(".P", "")
    if "/" in symbol:
        return symbol.split("/", 1)[0]
    if symbol.endswith("USDT"):
        return symbol[:-4]
    return symbol.split(":", 1)[0]


def row_to_event(row: dict[str, Any]) -> TradeEvent:
    ts_raw = str(row.get("ts") or row.get("timestamp") or row.get("time"))
    event = str(row.get("event") or row.get("type") or "")
    rr = parse_float(row.get("rr") or row.get("r_multiple") or row.get("pnl_r"))
    symbol_raw = row.get("symbol") or row.get("ticker") or row.get("asset")
    symbol = normalize_symbol(str(symbol_raw)) if symbol_raw is not None else None
    return TradeEvent(
        ts=parse_timestamp(ts_raw),
        event=event,
        symbol=symbol or None,
        rr=rr,
        win=parse_bool(row.get("win") if "win" in row else row.get("result")),
        cvd_sign=parse_cvd_sign(row.get("cvd_sign") or row.get("cvd")),
    )


def load_pine_csv(path: Path) -> list[TradeEvent]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [row_to_event(dict(row)) for row in csv.DictReader(handle)]


def load_jsonl(path: Path) -> list[TradeEvent]:
    events: list[TradeEvent] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError(f"JSONL row must be an object: {line!r}")
            events.append(row_to_event(raw))
    return events


def filter_events_by_symbol(events: list[TradeEvent], symbol: str | None) -> list[TradeEvent]:
    if symbol is None:
        return events
    normalized = normalize_symbol(symbol)
    return [
        event
        for event in events
        if event.symbol is None or normalize_symbol(event.symbol) == normalized
    ]


def entry_timing_match_rate(
    pine_events: list[TradeEvent],
    py_events: list[TradeEvent],
    *,
    tolerance: timedelta,
) -> tuple[float, int]:
    pine_entries = [event.ts for event in pine_events if event.event in ENTRY_EVENTS]
    py_entries = [event.ts for event in py_events if event.event in ENTRY_EVENTS]
    if not pine_entries and not py_entries:
        return 0.0, 0
    if not pine_entries or not py_entries:
        return 0.0, 0

    unused = set(range(len(pine_entries)))
    matches = 0
    for py_ts in py_entries:
        best_index: int | None = None
        best_delta: timedelta | None = None
        for index in unused:
            delta = abs(pine_entries[index] - py_ts)
            if delta <= tolerance and (best_delta is None or delta < best_delta):
                best_index = index
                best_delta = delta
        if best_index is not None:
            unused.remove(best_index)
            matches += 1
    return matches / max(len(pine_entries), len(py_entries)), max(len(pine_entries), len(py_entries))


def max_window_winrate_delta(
    pine_events: list[TradeEvent],
    py_events: list[TradeEvent],
) -> tuple[float, int]:
    pine_rates = win_rates_by_day(pine_events)
    py_rates = win_rates_by_day(py_events)
    pine_windows = set(pine_rates)
    py_windows = set(py_rates)
    windows = pine_windows & py_windows
    if not windows:
        return 1.0, 0
    if pine_windows != py_windows:
        return 1.0, len(windows)
    return (
        max(abs(pine_rates[window] - py_rates[window]) for window in windows),
        len(windows),
    )


def win_rates_by_day(events: list[TradeEvent]) -> dict[datetime, float]:
    grouped: dict[datetime, list[bool]] = {}
    for event in events:
        if event.win is None:
            continue
        window = event.ts.replace(hour=0, minute=0, second=0, microsecond=0)
        grouped.setdefault(window, []).append(event.win)
    return {
        window: sum(1 for value in values if value) / len(values)
        for window, values in grouped.items()
        if values
    }


def average_rr(events: list[TradeEvent]) -> float | None:
    values = [event.rr for event in events if event.rr is not None]
    if not values:
        return None
    return sum(values) / len(values)


def average_rr_delta(pine_events: list[TradeEvent], py_events: list[TradeEvent]) -> float:
    pine_rr = average_rr(pine_events)
    py_rr = average_rr(py_events)
    if pine_rr is None and py_rr is None:
        return 0.0
    if pine_rr is None or py_rr is None:
        return 1.0
    denominator = max(abs(pine_rr), 1e-9)
    return abs(py_rr - pine_rr) / denominator


def average_rr_delta_with_count(
    pine_events: list[TradeEvent],
    py_events: list[TradeEvent],
) -> tuple[float, int]:
    count = min(
        sum(1 for event in pine_events if event.rr is not None),
        sum(1 for event in py_events if event.rr is not None),
    )
    if count == 0:
        return 1.0, 0
    return average_rr_delta(pine_events, py_events), count


def cvd_sign_match_rate(pine_events: list[TradeEvent], py_events: list[TradeEvent]) -> tuple[float, int]:
    pine_by_ts = {event.ts: event.cvd_sign for event in pine_events if event.cvd_sign is not None}
    comparable = [
        event.cvd_sign == pine_by_ts[event.ts]
        for event in py_events
        if event.cvd_sign is not None and event.ts in pine_by_ts
    ]
    if not comparable:
        return 0.0, 0
    return sum(1 for matched in comparable if matched) / len(comparable), len(comparable)


def build_metrics(
    pine_events: list[TradeEvent],
    py_events: list[TradeEvent],
    *,
    bar_seconds: int,
) -> list[ParityMetric]:
    timing, timing_count = entry_timing_match_rate(
        pine_events,
        py_events,
        tolerance=timedelta(seconds=bar_seconds),
    )
    win_delta, win_count = max_window_winrate_delta(pine_events, py_events)
    rr_delta, rr_count = average_rr_delta_with_count(pine_events, py_events)
    cvd_match, cvd_count = cvd_sign_match_rate(pine_events, py_events)
    return [
        ParityMetric(
            "entry_timing_match",
            timing,
            ">= 0.85",
            timing_count > 0 and timing >= 0.85,
            "+/-1 bar",
            timing_count,
        ),
        ParityMetric(
            "winrate_delta_24h",
            win_delta,
            "<= 0.05",
            win_count > 0 and win_delta <= 0.05,
            "absolute",
            win_count,
        ),
        ParityMetric(
            "avg_rr_delta",
            rr_delta,
            "<= 0.15",
            rr_count > 0 and rr_delta <= 0.15,
            "relative",
            rr_count,
        ),
        ParityMetric(
            "cvd_sign_match",
            cvd_match,
            ">= 0.90",
            cvd_count > 0 and cvd_match >= 0.90,
            "bar timestamp",
            cvd_count,
        ),
    ]


def render_report(
    metrics: list[ParityMetric],
    pine_path: Path,
    py_path: Path,
    *,
    symbol: str | None = None,
) -> str:
    status = "PASS" if all(metric.passed for metric in metrics) else "FAIL"
    lines = [
        "# MTS-V1 Parity Report",
        "",
        f"- Status: {status}",
        f"- Symbol: `{normalize_symbol(symbol)}`" if symbol else "- Symbol: `ALL`",
        f"- Pine CSV: `{pine_path}`",
        f"- Python JSONL: `{py_path}`",
        "",
        "| Metric | Value | Comparable | Threshold | Pass | Detail |",
        "|---|---:|---:|---|:---:|---|",
    ]
    for metric in metrics:
        lines.append(
            f"| {metric.name} | {metric.value:.6f} | {metric.comparable_count} | {metric.threshold} | "
            f"{'yes' if metric.passed else 'no'} | {metric.detail} |"
        )
    failed = [metric for metric in metrics if not metric.passed]
    if failed:
        lines.extend(
            [
                "",
                "## Failure Candidates",
                "- Entry timing: Pine bar-close vs Python execution timestamp alignment.",
                "- Win/RR delta: fee, funding, partial-fill, or rounding differences.",
                "- CVD sign: Pine proxy vs Python tick-stream source mismatch.",
            ]
        )
    lines.append("")
    return "\n".join(lines)


def render_summary(rows: list[tuple[str, list[ParityMetric], Path]]) -> str:
    status = "PASS" if rows and all(all(metric.passed for metric in metrics) for _, metrics, _ in rows) else "FAIL"
    lines = [
        "# MTS-V1 Parity Summary",
        "",
        f"- Status: {status}",
        "",
        "| Symbol | Report | Entry Timing | Winrate Delta | Avg RR Delta | CVD Sign | Pass |",
        "|---|---|---:|---:|---:|---:|:---:|",
    ]
    for symbol, metrics, report_path in rows:
        metric_by_name = {metric.name: metric for metric in metrics}
        passed = all(metric.passed for metric in metrics)
        lines.append(
            "| "
            f"{symbol} | `{report_path}` | "
            f"{metric_by_name['entry_timing_match'].value:.6f} | "
            f"{metric_by_name['winrate_delta_24h'].value:.6f} | "
            f"{metric_by_name['avg_rr_delta'].value:.6f} | "
            f"{metric_by_name['cvd_sign_match'].value:.6f} | "
            f"{'yes' if passed else 'no'} |"
        )
    lines.append("")
    return "\n".join(lines)


def parse_symbols(raw: str) -> list[str]:
    return [normalize_symbol(part) for part in raw.split(",") if normalize_symbol(part)]


def pine_path_for_symbol(pine_dir: Path, symbol: str) -> Path:
    candidates = [
        pine_dir / f"tradingview_mtsv1_{symbol}.csv",
        pine_dir / f"tradingview_mtsv1_{symbol.lower()}.csv",
        pine_dir / f"{symbol}.csv",
        pine_dir / f"{symbol.lower()}.csv",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"No TradingView CSV found for {symbol} in {pine_dir}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare Pine and Python MTS-V1 backtest outputs.")
    pine_group = parser.add_mutually_exclusive_group(required=True)
    pine_group.add_argument("--pine", type=Path, help="TradingView export CSV.")
    pine_group.add_argument("--pine-dir", type=Path, help="Directory containing per-symbol TradingView CSVs.")
    parser.add_argument("--py", type=Path, required=True, help="Python trade log JSONL.")
    parser.add_argument("--report", type=Path, default=Path("parity_report.md"))
    parser.add_argument("--report-dir", type=Path, default=Path("parity_reports"))
    parser.add_argument("--symbol", help="Single-symbol filter, e.g. BTC.")
    parser.add_argument("--symbols", default="BTC,ETH,SOL,XRP,BNB")
    parser.add_argument("--bar-seconds", type=int, default=3600)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    py_events = load_jsonl(args.py)

    if args.pine_dir is not None:
        args.report_dir.mkdir(parents=True, exist_ok=True)
        rows: list[tuple[str, list[ParityMetric], Path]] = []
        for symbol in parse_symbols(args.symbols):
            pine_path = pine_path_for_symbol(args.pine_dir, symbol)
            metrics = build_metrics(
                filter_events_by_symbol(load_pine_csv(pine_path), symbol),
                filter_events_by_symbol(py_events, symbol),
                bar_seconds=args.bar_seconds,
            )
            report_path = args.report_dir / f"parity_{symbol}.md"
            report_path.write_text(
                render_report(metrics, pine_path, args.py, symbol=symbol),
                encoding="utf-8",
            )
            rows.append((symbol, metrics, report_path))
        summary = render_summary(rows)
        args.report.write_text(summary, encoding="utf-8")
        print(summary)
        return 0

    assert args.pine is not None
    metrics = build_metrics(
        filter_events_by_symbol(load_pine_csv(args.pine), args.symbol),
        filter_events_by_symbol(py_events, args.symbol),
        bar_seconds=args.bar_seconds,
    )
    report = render_report(metrics, args.pine, args.py, symbol=args.symbol)
    args.report.write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
