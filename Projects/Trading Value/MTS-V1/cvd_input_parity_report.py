from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from btc_parity_diff import (
    MatchedExitTimingResidual,
    closed_cycle_entries,
    format_dt,
    format_float,
    format_signed_delta,
    load_python_events,
    load_tv_raw,
    match_trades,
    matched_exit_timing_residuals,
    normalize_symbol,
)
from offline_replay import (
    candles_from_frame,
    load_15m_cache,
    pandas_timeframe,
    resample_ohlcv,
)
from strategy import Candle, cvd_abs_sma, cvd_proxy_series


ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_CACHE_DIR = ROOT_DIR.parent / "predictive_runner_paper" / "cache_180d"
DEFAULT_SYMBOL = "SOL"
DEFAULT_RSM = 5.5


@dataclass(slots=True, frozen=True)
class CvdBar:
    index: int
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    delta: float
    abs_sma20: float | None
    threshold: float | None
    long_pulse: bool
    short_pulse: bool


@dataclass(slots=True, frozen=True)
class CvdResidualDiagnostic:
    residual: MatchedExitTimingResidual
    py_exit_bar: CvdBar | None
    previous_bar: CvdBar | None
    tv_exit_bar: CvdBar | None
    interval_pulse_bar: CvdBar | None
    classification: str


def build_cvd_bars(candles: list[Candle], *, multiplier: float) -> list[CvdBar]:
    deltas, _cumulative = cvd_proxy_series(candles)
    bars: list[CvdBar] = []
    for index, candle in enumerate(candles):
        delta = deltas[index]
        abs_sma20: float | None = None
        threshold: float | None = None
        long_pulse = False
        short_pulse = False
        if index + 1 >= 20:
            abs_sma20 = cvd_abs_sma(deltas[: index + 1], 20)
            threshold = abs_sma20 * multiplier
            long_pulse = delta < -threshold
            short_pulse = delta > threshold
        bars.append(
            CvdBar(
                index=index,
                ts=candle.timestamp,
                open=candle.open,
                high=candle.high,
                low=candle.low,
                close=candle.close,
                volume=candle.volume,
                delta=delta,
                abs_sma20=abs_sma20,
                threshold=threshold,
                long_pulse=long_pulse,
                short_pulse=short_pulse,
            )
        )
    return bars


def load_symbol_cvd_bars(
    *,
    cache_dir: Path,
    symbol: str,
    ltf: str,
    multiplier: float,
) -> list[CvdBar]:
    asset = normalize_symbol(symbol)
    frame = load_15m_cache(cache_dir, asset)
    timeframe = pandas_timeframe(ltf)
    if timeframe != "15min":
        frame = resample_ohlcv(frame, timeframe)
    return build_cvd_bars(candles_from_frame(frame), multiplier=multiplier)


def ratio_for_side(bar: CvdBar | None, side: str) -> float | None:
    if bar is None or bar.threshold is None or bar.threshold <= 0.0:
        return None
    if side == "long":
        return -bar.delta / bar.threshold
    if side == "short":
        return bar.delta / bar.threshold
    return None


def pulse_for_side(bar: CvdBar | None, side: str) -> bool | None:
    if bar is None:
        return None
    if side == "long":
        return bar.long_pulse
    if side == "short":
        return bar.short_pulse
    return None


def reverse_spike_residuals(
    residuals: list[MatchedExitTimingResidual],
) -> list[MatchedExitTimingResidual]:
    result: list[MatchedExitTimingResidual] = []
    for residual in residuals:
        py_exit = residual.py_exit
        if py_exit is None:
            continue
        if py_exit.reason != "STATE_2_ABORT":
            continue
        if residual.trigger_source not in {"reverse_spike", "both"}:
            continue
        result.append(residual)
    return result


def first_pulse_between(
    bars: list[CvdBar],
    *,
    start: datetime,
    end: datetime | None,
    side: str,
) -> CvdBar | None:
    if end is None:
        return None
    low, high = sorted((start, end))
    for bar in bars:
        if low < bar.ts <= high and pulse_for_side(bar, side):
            return bar
    return None


def classify_diagnostic(
    *,
    py_exit_bar: CvdBar | None,
    previous_bar: CvdBar | None,
    tv_exit_bar: CvdBar | None,
    interval_pulse_bar: CvdBar | None,
    side: str,
) -> str:
    py_pulse = pulse_for_side(py_exit_bar, side)
    previous_pulse = pulse_for_side(previous_bar, side)
    tv_pulse = pulse_for_side(tv_exit_bar, side)
    if py_exit_bar is None or tv_exit_bar is None:
        return "missing_cache_bar"
    if tv_pulse:
        return "python_formula_pulses_at_tv_exit"
    if interval_pulse_bar is not None:
        return "python_formula_has_later_pulse_between_exits"
    if py_pulse and previous_pulse is False:
        return "isolated_python_pulse_no_tv_exit_pulse"
    if py_pulse:
        return "python_pulse_no_tv_exit_pulse"
    return "non_python_pulse_residual"


def build_diagnostics(
    residuals: list[MatchedExitTimingResidual],
    bars: list[CvdBar],
) -> list[CvdResidualDiagnostic]:
    bars_by_ts = {bar.ts: bar for bar in bars}
    diagnostics: list[CvdResidualDiagnostic] = []
    for residual in reverse_spike_residuals(residuals):
        if residual.py_exit is None:
            continue
        py_exit_bar = bars_by_ts.get(residual.py_exit.ts)
        previous_bar = (
            bars[py_exit_bar.index - 1]
            if py_exit_bar is not None and py_exit_bar.index > 0
            else None
        )
        tv_exit_bar = (
            bars_by_ts.get(residual.tv.exit_ts)
            if residual.tv.exit_ts is not None
            else None
        )
        interval_pulse_bar = first_pulse_between(
            bars,
            start=residual.py_exit.ts,
            end=residual.tv.exit_ts,
            side=residual.tv.side,
        )
        diagnostics.append(
            CvdResidualDiagnostic(
                residual=residual,
                py_exit_bar=py_exit_bar,
                previous_bar=previous_bar,
                tv_exit_bar=tv_exit_bar,
                interval_pulse_bar=interval_pulse_bar,
                classification=classify_diagnostic(
                    py_exit_bar=py_exit_bar,
                    previous_bar=previous_bar,
                    tv_exit_bar=tv_exit_bar,
                    interval_pulse_bar=interval_pulse_bar,
                    side=residual.tv.side,
                ),
            )
        )
    return diagnostics


def count_by_class(diagnostics: list[CvdResidualDiagnostic]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for diagnostic in diagnostics:
        counts[diagnostic.classification] = counts.get(diagnostic.classification, 0) + 1
    return dict(sorted(counts.items()))


def render_report(
    *,
    symbol: str,
    tv_path: Path,
    py_path: Path,
    cache_dir: Path,
    ltf: str,
    multiplier: float,
    tolerance: timedelta,
    diagnostics: list[CvdResidualDiagnostic],
    examples: int,
) -> str:
    isolated_count = sum(
        1
        for diagnostic in diagnostics
        if diagnostic.classification == "isolated_python_pulse_no_tv_exit_pulse"
    )
    tv_exit_pulse_count = sum(
        1
        for diagnostic in diagnostics
        if diagnostic.classification == "python_formula_pulses_at_tv_exit"
    )
    interval_pulse_count = sum(
        1 for diagnostic in diagnostics if diagnostic.interval_pulse_bar is not None
    )
    lines = [
        f"# MTS-V1 {symbol} CVD Input Parity Diagnostic",
        "",
        "## Inputs",
        f"- TradingView raw CSV: `{tv_path}`",
        f"- Python JSONL: `{py_path}`",
        f"- OHLCV cache: `{cache_dir}`",
        f"- LTF / `request.security()` timeframe: `{ltf}`",
        f"- Reverse spike multiplier: `{multiplier}`",
        f"- Match tolerance: `{tolerance.total_seconds() / 60:.1f}m`",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| reverse_spike_exit_timing_residuals | {len(diagnostics)} |",
        f"| isolated_python_pulse_no_tv_exit_pulse | {isolated_count} |",
        f"| python_formula_pulses_at_tv_exit | {tv_exit_pulse_count} |",
        f"| python_formula_interval_pulses_between_exits | {interval_pulse_count} |",
        f"| classifications | `{count_by_class(diagnostics)}` |",
        "",
        "## Residual CVD Inputs",
        "",
        "| Trade | Class | Side | TV exit UTC | Python exit UTC | Exit delta | Py delta | Py threshold | Py ratio | Prev ratio | Prev pulse | TV-exit delta | TV-exit threshold | TV-exit ratio | TV-exit pulse | Other pulse between exits | Other pulse ratio |",
        "|---:|---|---|---|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---|---|---:|",
    ]
    for diagnostic in diagnostics[:examples]:
        residual = diagnostic.residual
        side = residual.tv.side
        py_exit_bar = diagnostic.py_exit_bar
        previous_bar = diagnostic.previous_bar
        tv_exit_bar = diagnostic.tv_exit_bar
        interval_bar = diagnostic.interval_pulse_bar
        lines.append(
            f"| {residual.tv.trade_no} | {diagnostic.classification} | {side} | "
            f"{format_dt(residual.tv.exit_ts)} | "
            f"{format_dt(residual.py_exit.ts if residual.py_exit is not None else None)} | "
            f"{format_signed_delta(residual.signed_exit_delta)} | "
            f"{format_float(py_exit_bar.delta if py_exit_bar is not None else None, 4)} | "
            f"{format_float(py_exit_bar.threshold if py_exit_bar is not None else None, 4)} | "
            f"{format_float(ratio_for_side(py_exit_bar, side), 4)} | "
            f"{format_float(ratio_for_side(previous_bar, side), 4)} | "
            f"{format_bool(pulse_for_side(previous_bar, side))} | "
            f"{format_float(tv_exit_bar.delta if tv_exit_bar is not None else None, 4)} | "
            f"{format_float(tv_exit_bar.threshold if tv_exit_bar is not None else None, 4)} | "
            f"{format_float(ratio_for_side(tv_exit_bar, side), 4)} | "
            f"{format_bool(pulse_for_side(tv_exit_bar, side))} | "
            f"{format_dt(interval_bar.ts if interval_bar is not None else None)} | "
            f"{format_float(ratio_for_side(interval_bar, side), 4)} |"
        )

    lines.extend(
        [
            "",
            "## CVD Bar Inputs",
            "",
            "| Trade | Anchor | UTC | Open | Close | Volume | Delta | Abs SMA20 | Threshold | Ratio | Pulse |",
            "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for diagnostic in diagnostics[:examples]:
        residual = diagnostic.residual
        side = residual.tv.side
        for anchor, bar in (
            ("python_exit", diagnostic.py_exit_bar),
            ("tv_exit", diagnostic.tv_exit_bar),
        ):
            lines.append(
                f"| {residual.tv.trade_no} | {anchor} | {format_dt(bar.ts if bar else None)} | "
                f"{format_float(bar.open if bar else None, 4)} | "
                f"{format_float(bar.close if bar else None, 4)} | "
                f"{format_float(bar.volume if bar else None, 4)} | "
                f"{format_float(bar.delta if bar else None, 4)} | "
                f"{format_float(bar.abs_sma20 if bar else None, 4)} | "
                f"{format_float(bar.threshold if bar else None, 4)} | "
                f"{format_float(ratio_for_side(bar, side), 4)} | "
                f"{format_bool(pulse_for_side(bar, side))} |"
            )

    lines.extend(
        [
            "",
            "## Python CVD Formula",
            "- Pine source uses `delta_bar = request.security(syminfo.tickerid, ltf, (close - open) * volume, barmerge.gaps_off, barmerge.lookahead_off)`.",
            "- This report reconstructs the same formula from the local OHLCV cache and the accepted symbol RSM.",
            "- TradingView Strategy Report CSV exports do not include `delta_bar`, `cvd_abs_sma_20`, or reverse-spike plot values, so this is a Python-side input reconstruction, not a direct TV plot export comparison.",
            "- If `python_formula_pulses_at_tv_exit` is zero, the remaining mismatch needs either a TradingView CVD plot export or another non-CVD order/state timing explanation before changing replay semantics.",
            "",
        ]
    )
    return "\n".join(lines)


def format_bool(value: bool | None) -> str:
    if value is None:
        return ""
    return "true" if value else "false"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate CVD input diagnostics for parity residuals.")
    parser.add_argument("--symbol", default=DEFAULT_SYMBOL)
    parser.add_argument(
        "--tv-raw",
        type=Path,
        default=ROOT_DIR / "samples" / "tradingview_mtsv1_SOL_entry15_raw.csv",
    )
    parser.add_argument(
        "--py",
        type=Path,
        default=ROOT_DIR / "runs" / "mtsv1_tv_sol_15m_binanceusdm_profile" / "trades.jsonl",
    )
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT_DIR / "parity_reports" / "sol_cvd_input_parity.md",
    )
    parser.add_argument("--ltf", default="15m")
    parser.add_argument("--reverse-spike-multiplier", type=float, default=DEFAULT_RSM)
    parser.add_argument("--bar-seconds", type=int, default=900)
    parser.add_argument("--examples", type=int, default=32)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    symbol = normalize_symbol(args.symbol)
    tolerance = timedelta(seconds=args.bar_seconds)
    tv_trades = load_tv_raw(args.tv_raw, symbol)
    py_events = load_python_events(args.py, symbol)
    py_entries_in_window = closed_cycle_entries(
        py_events,
        tv_trades,
        tolerance=tolerance,
    )
    matches = match_trades(tv_trades, py_entries_in_window, tolerance=tolerance)
    residuals = matched_exit_timing_residuals(matches, py_events, tolerance=tolerance)
    bars = load_symbol_cvd_bars(
        cache_dir=args.cache_dir,
        symbol=symbol,
        ltf=args.ltf,
        multiplier=args.reverse_spike_multiplier,
    )
    diagnostics = build_diagnostics(residuals, bars)
    report = render_report(
        symbol=symbol,
        tv_path=args.tv_raw,
        py_path=args.py,
        cache_dir=args.cache_dir,
        ltf=args.ltf,
        multiplier=args.reverse_spike_multiplier,
        tolerance=tolerance,
        diagnostics=diagnostics,
        examples=args.examples,
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
