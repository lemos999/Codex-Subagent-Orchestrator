from __future__ import annotations

import argparse
import json
import math
import statistics
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from strategy import DEFAULT_CONFIG_PATH, AppConfig, load_config, parse_symbol_override


@dataclass(slots=True, frozen=True)
class TradeRecord:
    ts: datetime
    symbol: str
    rr: float

    @property
    def win(self) -> bool:
        return self.rr > 0.0


@dataclass(slots=True, frozen=True)
class CoverageWindow:
    start: datetime
    end: datetime


@dataclass(slots=True, frozen=True)
class TradeInputBundle:
    trades: list[TradeRecord]
    sources: list[str]
    coverage: CoverageWindow | None


@dataclass(slots=True, frozen=True)
class MetricRow:
    symbol: str
    sharpe: float
    profit_factor: float
    max_drawdown: float
    trades: int
    wilson_lower: float
    avg_rr: float
    passed: bool
    reason: str


@dataclass(slots=True, frozen=True)
class WindowMetricRow:
    sharpe: float
    profit_factor: float
    max_drawdown: float
    trades: int
    wilson_lower: float
    avg_rr: float
    passed: bool


def parse_timestamp(raw: str) -> datetime:
    parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def load_trades(path: Path) -> list[TradeRecord]:
    trades, _coverage = load_trades_with_coverage(path)
    return trades


def load_trades_with_coverage(path: Path) -> tuple[list[TradeRecord], CoverageWindow | None]:
    trades: list[TradeRecord] = []
    coverage: CoverageWindow | None = None
    with path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError(f"Trade row must be a JSON object: {line!r}")
            if raw.get("event") == "REPLAY_META":
                coverage = CoverageWindow(
                    start=parse_timestamp(str(raw["coverage_start"])),
                    end=parse_timestamp(str(raw["coverage_end"])),
                )
                continue
            rr_value = raw.get("rr", raw.get("pnl_r", raw.get("r_multiple")))
            if rr_value is None:
                continue
            trades.append(
                TradeRecord(
                    ts=parse_timestamp(str(raw["ts"])),
                    symbol=str(raw["symbol"]),
                    rr=float(rr_value),
                )
            )
    return trades, coverage


def load_trade_inputs(trades_path: Path | None, logs_dir: Path) -> tuple[list[TradeRecord], list[str]]:
    bundle = load_trade_input_bundle(trades_path, logs_dir)
    return bundle.trades, bundle.sources


def load_trade_input_bundle(trades_path: Path | None, logs_dir: Path) -> TradeInputBundle:
    if trades_path is not None:
        trades, coverage = load_trades_with_coverage(trades_path)
        return TradeInputBundle(trades, [str(trades_path)], coverage)

    paths = sorted(logs_dir.glob("trades_*.jsonl"))
    trades: list[TradeRecord] = []
    coverage_windows: list[CoverageWindow] = []
    for path in paths:
        path_trades, path_coverage = load_trades_with_coverage(path)
        trades.extend(path_trades)
        if path_coverage is not None:
            coverage_windows.append(path_coverage)
    coverage = combine_coverage_windows(coverage_windows)
    return TradeInputBundle(trades, [str(path) for path in paths], coverage)


def combine_coverage_windows(windows: list[CoverageWindow]) -> CoverageWindow | None:
    if not windows:
        return None
    return CoverageWindow(
        start=min(window.start for window in windows),
        end=max(window.end for window in windows),
    )


def wilson_lower_bound(wins: int, total: int, z: float = 1.96) -> float:
    if total <= 0:
        return 0.0
    n = float(total)
    p_hat = wins / n
    denominator = 1.0 + (z * z / n)
    centre = p_hat + (z * z / (2.0 * n))
    margin = z * math.sqrt((p_hat * (1.0 - p_hat) + z * z / (4.0 * n)) / n)
    return (centre - margin) / denominator


def compute_sharpe(rr_values: list[float]) -> float:
    if len(rr_values) < 2:
        return 0.0
    stdev = statistics.pstdev(rr_values)
    if math.isclose(stdev, 0.0):
        return 0.0
    return statistics.fmean(rr_values) / stdev * math.sqrt(len(rr_values))


def compute_profit_factor(rr_values: list[float]) -> float:
    wins = sum(value for value in rr_values if value > 0.0)
    losses = abs(sum(value for value in rr_values if value < 0.0))
    if math.isclose(losses, 0.0):
        return float("inf") if wins > 0.0 else 0.0
    return wins / losses


def compute_max_drawdown(rr_values: list[float]) -> float:
    equity = 1.0
    peak = equity
    worst = 0.0
    for rr in rr_values:
        equity += rr * 0.01
        peak = max(peak, equity)
        if peak > 0.0:
            worst = min(worst, (equity - peak) / peak)
    return abs(worst)


def evaluate_symbol(symbol: str, trades: list[TradeRecord]) -> MetricRow:
    rr_values = [trade.rr for trade in trades if trade.symbol == symbol]
    if not rr_values:
        return MetricRow(symbol, 0.0, 0.0, 1.0, 0, 0.0, 0.0, False, "no trades")

    winning_values = [value for value in rr_values if value > 0.0]
    losing_values = [value for value in rr_values if value < 0.0]
    wins = len(winning_values)
    avg_win_r = statistics.fmean(winning_values) if winning_values else 0.0
    avg_loss_r = abs(statistics.fmean(losing_values)) if losing_values else 0.0
    if math.isclose(avg_loss_r, 0.0):
        avg_rr = float("inf") if avg_win_r > 0.0 else 0.0
    else:
        avg_rr = avg_win_r / avg_loss_r
    wilson = wilson_lower_bound(wins, len(rr_values))
    breakeven = 1.0 / (1.0 + avg_rr) if avg_rr > 0.0 else 1.0
    sharpe = compute_sharpe(rr_values)
    profit_factor = compute_profit_factor(rr_values)
    max_drawdown = compute_max_drawdown(rr_values)
    passed = (
        sharpe >= 1.0
        and profit_factor >= 1.3
        and max_drawdown <= 0.20
        and len(rr_values) >= 100
        and wilson > breakeven
        and avg_rr >= 2.5
    )
    failed: list[str] = []
    if sharpe < 1.0:
        failed.append("Sharpe < 1.0")
    if profit_factor < 1.3:
        failed.append("PF < 1.3")
    if max_drawdown > 0.20:
        failed.append("MDD > 20%")
    if len(rr_values) < 100:
        failed.append("trades < 100")
    if wilson <= breakeven:
        failed.append("Wilson <= BE")
    if avg_rr < 2.5:
        failed.append("avg RR < 2.5")
    return MetricRow(
        symbol,
        sharpe,
        profit_factor,
        max_drawdown,
        len(rr_values),
        wilson,
        avg_rr,
        passed,
        ", ".join(failed) if failed else "pass",
    )


def portfolio_total_r(trades: list[TradeRecord], symbols: list[str]) -> float:
    symbol_set = set(symbols)
    return sum(trade.rr for trade in trades if trade.symbol in symbol_set)


def portfolio_avg_r(trades: list[TradeRecord], symbols: list[str]) -> float:
    symbol_set = set(symbols)
    rr_values = [trade.rr for trade in trades if trade.symbol in symbol_set]
    if not rr_values:
        return 0.0
    return statistics.fmean(rr_values)


def split_walk_forward(trades: list[TradeRecord], windows: int = 4) -> list[list[TradeRecord]]:
    if not trades:
        return [[] for _ in range(windows)]
    ordered = sorted(trades, key=lambda trade: trade.ts)
    start = ordered[0].ts
    end = ordered[-1].ts
    total_seconds = max((end - start).total_seconds(), 1.0)
    window_seconds = total_seconds / windows
    buckets: list[list[TradeRecord]] = [[] for _ in range(windows)]
    for trade in ordered:
        offset = (trade.ts - start).total_seconds()
        index = min(int(offset // window_seconds), windows - 1)
        buckets[index].append(trade)
    return buckets


def walk_forward_pass_count(trades: list[TradeRecord], symbols: list[str]) -> int:
    selected = [trade for trade in trades if trade.symbol in set(symbols)]
    pass_count = 0
    for window_trades in split_walk_forward(selected):
        if evaluate_window(window_trades).passed:
            pass_count += 1
    return pass_count


def evaluate_window(trades: list[TradeRecord]) -> WindowMetricRow:
    rr_values = [trade.rr for trade in trades]
    if not rr_values:
        return WindowMetricRow(0.0, 0.0, 1.0, 0, 0.0, 0.0, False)

    winning_values = [value for value in rr_values if value > 0.0]
    losing_values = [value for value in rr_values if value < 0.0]
    avg_win_r = statistics.fmean(winning_values) if winning_values else 0.0
    avg_loss_r = abs(statistics.fmean(losing_values)) if losing_values else 0.0
    if math.isclose(avg_loss_r, 0.0):
        avg_rr = float("inf") if avg_win_r > 0.0 else 0.0
    else:
        avg_rr = avg_win_r / avg_loss_r
    breakeven = 1.0 / (1.0 + avg_rr) if avg_rr > 0.0 else 1.0
    wilson = wilson_lower_bound(len(winning_values), len(rr_values))
    sharpe = compute_sharpe(rr_values)
    profit_factor = compute_profit_factor(rr_values)
    max_drawdown = compute_max_drawdown(rr_values)
    return WindowMetricRow(
        sharpe=sharpe,
        profit_factor=profit_factor,
        max_drawdown=max_drawdown,
        trades=len(rr_values),
        wilson_lower=wilson,
        avg_rr=avg_rr,
        passed=(
            sharpe >= 1.0
            and profit_factor >= 1.3
            and max_drawdown <= 0.20
            and wilson > breakeven
        ),
    )


def _window_core_passed(row: MetricRow) -> bool:
    breakeven = 1.0 / (1.0 + row.avg_rr) if row.avg_rr > 0.0 else 1.0
    return (
        row.sharpe >= 1.0
        and row.profit_factor >= 1.3
        and row.max_drawdown <= 0.20
        and row.wilson_lower > breakeven
    )


def validate_backtest_scope(
    trades: list[TradeRecord],
    symbols: list[str],
    days: int,
    coverage: CoverageWindow | None = None,
) -> list[str]:
    if not trades:
        return ["no local trade input"]

    errors: list[str] = []
    trade_symbols = {trade.symbol for trade in trades}
    missing_symbols = sorted(set(symbols) - trade_symbols)
    if missing_symbols:
        errors.append(f"missing symbols={missing_symbols}")

    required_span = timedelta(days=days)
    if coverage is not None:
        actual_span = coverage.end - coverage.start
    else:
        ordered = sorted(trades, key=lambda trade: trade.ts)
        actual_span = ordered[-1].ts - ordered[0].ts
    if actual_span < required_span:
        errors.append(
            f"time span {actual_span} < required {required_span}"
        )
    return errors


def render_verdict(
    config: AppConfig,
    trades: list[TradeRecord],
    days: int,
    *,
    input_sources: list[str] | None = None,
    coverage: CoverageWindow | None = None,
    symbols: list[str] | None = None,
) -> str:
    selected_symbols = symbols or config.symbols
    rows = [evaluate_symbol(symbol, trades) for symbol in selected_symbols]
    wf_pass = walk_forward_pass_count(trades, selected_symbols)
    scope_errors = validate_backtest_scope(trades, selected_symbols, days, coverage)
    overall_pass = not scope_errors and all(row.passed for row in rows) and wf_pass >= 2
    total_r = portfolio_total_r(trades, selected_symbols)
    avg_r = portfolio_avg_r(trades, selected_symbols)
    coverage_text = (
        f"{coverage.start.isoformat()} to {coverage.end.isoformat()}"
        if coverage is not None
        else "trade timestamps"
    )
    lines = [
        "# MTS-V1 Backtest Verdict",
        "",
        f"- Status: {'PASS' if overall_pass else 'FAIL'}",
        f"- Scope: {len(selected_symbols)} symbols x {days}d x entry_tf={config.timeframes.entry_tf}",
        f"- Coverage: {coverage_text}",
        f"- Walk-forward pass windows: {wf_pass}/4",
        f"- Portfolio total R: {total_r:.6f}",
        f"- Portfolio avg R/trade: {avg_r:.6f}",
        f"- Trade inputs: {', '.join(input_sources or ['none'])}",
        "",
        "| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |",
        "|---|---:|---:|---:|---:|---:|---:|:---:|---|",
    ]
    for row in rows:
        profit_factor = "inf" if math.isinf(row.profit_factor) else f"{row.profit_factor:.3f}"
        lines.append(
            f"| {row.symbol} | {row.sharpe:.3f} | {profit_factor} | "
            f"{row.max_drawdown:.3f} | {row.trades} | {row.wilson_lower:.3f} | "
            f"{row.avg_rr:.3f} | {'yes' if row.passed else 'no'} | {row.reason} |"
        )
    lines.extend(
        [
            "",
            "## Walk-Forward Windows",
            "",
            "| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |",
            "|---:|---:|---:|---:|---:|---:|---:|:---:|",
        ]
    )
    selected_trades = [trade for trade in trades if trade.symbol in set(selected_symbols)]
    for index, window_trades in enumerate(split_walk_forward(selected_trades), start=1):
        row = evaluate_window(window_trades)
        profit_factor = "inf" if math.isinf(row.profit_factor) else f"{row.profit_factor:.3f}"
        lines.append(
            f"| {index} | {row.sharpe:.3f} | {profit_factor} | "
            f"{row.max_drawdown:.3f} | {row.trades} | {row.wilson_lower:.3f} | "
            f"{row.avg_rr:.3f} | {'yes' if row.passed else 'no'} |"
        )
    if scope_errors:
        lines.extend(
            [
                "",
                "## Failure Cause",
            ]
        )
        lines.extend(f"- {error}" for error in scope_errors)
    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate MTS-V1 Phase 7 backtest verdict.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--trades", type=Path, help="Optional trade JSONL with ts/symbol/rr.")
    parser.add_argument("--symbols", help="Optional comma-separated symbol override for scoring.")
    parser.add_argument(
        "--logs-dir",
        type=Path,
        default=Path("logs"),
        help="Default trade log directory used when --trades is omitted.",
    )
    parser.add_argument("--output", type=Path, default=Path("BACKTEST_VERDICT.md"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config(args.config)
    bundle = load_trade_input_bundle(args.trades, args.logs_dir)
    verdict = render_verdict(
        config,
        bundle.trades,
        args.days,
        input_sources=bundle.sources,
        coverage=bundle.coverage,
        symbols=parse_symbol_override(args.symbols),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(verdict, encoding="utf-8")
    print(verdict)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
