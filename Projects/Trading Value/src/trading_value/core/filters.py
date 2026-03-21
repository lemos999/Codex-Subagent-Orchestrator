"""Conditional entry filters based on trade record pattern analysis.

Analyzes historical trade records to extract statistically significant
underperforming conditions, then converts them into entry block filters.

Pure functions -- no side effects.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

from ..adapters.backtest import TradeRecord


# ---------------------------------------------------------------------------
# 1. TradeAnalysis -- pattern extraction
# ---------------------------------------------------------------------------

@dataclass
class ConditionStats:
    """Statistics for a specific trading condition."""

    condition_name: str
    condition_value: str
    total_trades: int
    winning_trades: int
    win_rate: float
    avg_pnl: float
    avg_pnl_r: float
    is_significant: bool  # enough samples + statistically different from overall


@dataclass
class TradeAnalysis:
    """Complete analysis of trade record patterns."""

    overall_win_rate: float
    overall_avg_pnl: float
    total_trades: int
    by_session: list[ConditionStats] = field(default_factory=list)
    by_weekday: list[ConditionStats] = field(default_factory=list)
    by_strategy: list[ConditionStats] = field(default_factory=list)
    by_regime: list[ConditionStats] = field(default_factory=list)
    by_strategy_regime: list[ConditionStats] = field(default_factory=list)
    by_consecutive_loss: list[ConditionStats] = field(default_factory=list)
    by_hour_bucket: list[ConditionStats] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 2. Analysis functions
# ---------------------------------------------------------------------------

_WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

_HOUR_BUCKETS = [
    (0, 4, "00-04"),
    (4, 8, "04-08"),
    (8, 12, "08-12"),
    (12, 16, "12-16"),
    (16, 20, "16-20"),
    (20, 24, "20-24"),
]


def classify_session(hour_utc: int) -> str:
    """Classify a UTC hour into a trading session.

    Asia: 0-8, Europe: 8-16, US: 16-24.
    """
    if hour_utc < 8:
        return "Asia"
    if hour_utc < 16:
        return "Europe"
    return "US"


def _compute_stats(
    condition_name: str,
    condition_value: str,
    trades: list[TradeRecord],
    overall_win_rate: float,
    min_significant_sample: int = 20,
    significance_threshold: float = 0.10,
) -> ConditionStats:
    """Compute statistics for a group of trades."""
    total = len(trades)
    if total == 0:
        return ConditionStats(
            condition_name=condition_name,
            condition_value=condition_value,
            total_trades=0,
            winning_trades=0,
            win_rate=0.0,
            avg_pnl=0.0,
            avg_pnl_r=0.0,
            is_significant=False,
        )

    wins = sum(1 for t in trades if t.pnl > 0)
    win_rate = wins / total
    avg_pnl = sum(t.pnl for t in trades) / total
    avg_pnl_r = sum(t.pnl_r for t in trades) / total

    is_significant = (
        total >= min_significant_sample
        and abs(win_rate - overall_win_rate) > significance_threshold
    )

    return ConditionStats(
        condition_name=condition_name,
        condition_value=condition_value,
        total_trades=total,
        winning_trades=wins,
        win_rate=win_rate,
        avg_pnl=avg_pnl,
        avg_pnl_r=avg_pnl_r,
        is_significant=is_significant,
    )


def _classify_hour_bucket(hour_utc: int) -> str:
    """Return the 4-hour bucket label for a given UTC hour."""
    for start, end, label in _HOUR_BUCKETS:
        if start <= hour_utc < end:
            return label
    return "20-24"  # fallback


def _compute_consecutive_losses_at_entry(
    trades: list[TradeRecord],
) -> list[int]:
    """For each trade, compute how many consecutive losses preceded it."""
    result: list[int] = []
    consec = 0
    for t in trades:
        result.append(consec)
        if t.pnl < 0:
            consec += 1
        else:
            consec = 0
    return result


def analyze_trades(trades: list[TradeRecord]) -> TradeAnalysis:
    """Extract all condition patterns from trade records.

    Groups trades by session, weekday, strategy, regime, consecutive losses,
    hour bucket. Computes win rate and avg PnL for each group.
    Marks as significant if sample >= 20 and win_rate differs from overall by > 10%.
    """
    total = len(trades)
    if total == 0:
        return TradeAnalysis(
            overall_win_rate=0.0,
            overall_avg_pnl=0.0,
            total_trades=0,
        )

    overall_wins = sum(1 for t in trades if t.pnl > 0)
    overall_win_rate = overall_wins / total
    overall_avg_pnl = sum(t.pnl for t in trades) / total

    # Sort trades by exit_time for consecutive loss calculation
    # (consecutive losses are counted at trade closure, not entry)
    sorted_trades = sorted(trades, key=lambda t: t.exit_time)

    # --- Group by session ---
    session_groups: dict[str, list[TradeRecord]] = defaultdict(list)
    for t in sorted_trades:
        session = classify_session(t.entry_time.hour)
        session_groups[session].append(t)
    by_session = [
        _compute_stats("session", session, group, overall_win_rate)
        for session, group in sorted(session_groups.items())
    ]

    # --- Group by weekday ---
    weekday_groups: dict[str, list[TradeRecord]] = defaultdict(list)
    for t in sorted_trades:
        day_name = _WEEKDAY_NAMES[t.entry_time.weekday()]
        weekday_groups[day_name].append(t)
    by_weekday = [
        _compute_stats("weekday", day, group, overall_win_rate)
        for day, group in sorted(weekday_groups.items(), key=lambda x: _WEEKDAY_NAMES.index(x[0]))
    ]

    # --- Group by strategy ---
    strategy_groups: dict[str, list[TradeRecord]] = defaultdict(list)
    for t in sorted_trades:
        strategy_groups[t.strategy].append(t)
    by_strategy = [
        _compute_stats("strategy", strat, group, overall_win_rate)
        for strat, group in sorted(strategy_groups.items())
    ]

    # --- Group by regime ---
    regime_groups: dict[str, list[TradeRecord]] = defaultdict(list)
    for t in sorted_trades:
        regime_groups[t.regime_at_entry].append(t)
    by_regime = [
        _compute_stats("regime", regime, group, overall_win_rate)
        for regime, group in sorted(regime_groups.items())
    ]

    # --- Group by strategy + regime (combined) ---
    sr_groups: dict[str, list[TradeRecord]] = defaultdict(list)
    for t in sorted_trades:
        key = f"{t.strategy}|{t.regime_at_entry}"
        sr_groups[key].append(t)
    by_strategy_regime = [
        _compute_stats("strategy_regime", key, group, overall_win_rate)
        for key, group in sorted(sr_groups.items())
    ]

    # --- Group by consecutive losses at entry ---
    consec_losses = _compute_consecutive_losses_at_entry(sorted_trades)
    cl_groups: dict[str, list[TradeRecord]] = defaultdict(list)
    for t, cl in zip(sorted_trades, consec_losses):
        bucket = str(min(cl, 3)) if cl < 3 else "3+"
        cl_groups[bucket].append(t)
    by_consecutive_loss = [
        _compute_stats("consecutive_loss", bucket, group, overall_win_rate)
        for bucket, group in sorted(cl_groups.items())
    ]

    # --- Group by hour bucket (4-hour) ---
    hb_groups: dict[str, list[TradeRecord]] = defaultdict(list)
    for t in sorted_trades:
        bucket = _classify_hour_bucket(t.entry_time.hour)
        hb_groups[bucket].append(t)
    by_hour_bucket = [
        _compute_stats("hour_bucket", bucket, group, overall_win_rate)
        for bucket, group in sorted(hb_groups.items())
    ]

    return TradeAnalysis(
        overall_win_rate=overall_win_rate,
        overall_avg_pnl=overall_avg_pnl,
        total_trades=total,
        by_session=by_session,
        by_weekday=by_weekday,
        by_strategy=by_strategy,
        by_regime=by_regime,
        by_strategy_regime=by_strategy_regime,
        by_consecutive_loss=by_consecutive_loss,
        by_hour_bucket=by_hour_bucket,
    )


# ---------------------------------------------------------------------------
# 3. Filter generation
# ---------------------------------------------------------------------------

@dataclass
class ConditionalFilter:
    """A conditional entry block filter derived from trade analysis."""

    condition_name: str
    condition_check: str  # human-readable description
    block_reason: str
    win_rate: float
    sample_size: int
    avg_pnl: float
    # Structured matching fields (used by check_conditional_filters)
    condition_type: str = ""   # "session", "weekday", "strategy", "regime", "strategy_regime", "consecutive_loss", "hour_bucket"
    condition_value: str = ""  # "Asia", "Monday", "TREND_LONG", etc.


def generate_filters(
    analysis: TradeAnalysis,
    min_sample: int = 20,
    max_win_rate: float = 0.35,
) -> list[ConditionalFilter]:
    """Generate entry block filters from underperforming conditions.

    A condition becomes a filter if:
    - sample_size >= min_sample
    - win_rate < max_win_rate (default 35% -- significantly worse than 50%)
    - avg_pnl is negative

    Returns a list of ConditionalFilter objects.
    """
    filters: list[ConditionalFilter] = []

    all_groups: list[list[ConditionStats]] = [
        analysis.by_session,
        analysis.by_weekday,
        analysis.by_strategy,
        analysis.by_regime,
        analysis.by_strategy_regime,
        analysis.by_consecutive_loss,
        analysis.by_hour_bucket,
    ]

    for group in all_groups:
        for stats in group:
            if (
                stats.total_trades >= min_sample
                and stats.win_rate < max_win_rate
                and stats.avg_pnl < 0
            ):
                condition_check = _build_condition_check(stats)
                block_reason = (
                    f"Underperforming {stats.condition_name}={stats.condition_value}: "
                    f"win_rate={stats.win_rate:.1%}, avg_pnl={stats.avg_pnl:.2f}, "
                    f"n={stats.total_trades}"
                )
                filters.append(ConditionalFilter(
                    condition_name=stats.condition_name,
                    condition_check=condition_check,
                    block_reason=block_reason,
                    win_rate=stats.win_rate,
                    sample_size=stats.total_trades,
                    avg_pnl=stats.avg_pnl,
                    condition_type=stats.condition_name,
                    condition_value=stats.condition_value,
                ))

    return filters


def _build_condition_check(stats: ConditionStats) -> str:
    """Build a human-readable condition check description."""
    name = stats.condition_name
    value = stats.condition_value

    if name == "session":
        return f"Entry during {value} session"
    if name == "weekday":
        return f"Entry on {value}"
    if name == "strategy":
        return f"Strategy is {value}"
    if name == "regime":
        return f"Regime is {value}"
    if name == "strategy_regime":
        parts = value.split("|")
        if len(parts) == 2:
            return f"Strategy {parts[0]} during regime {parts[1]}"
        return f"Strategy+regime is {value}"
    if name == "consecutive_loss":
        return f"After {value} consecutive losses"
    if name == "hour_bucket":
        return f"Entry during hour bucket {value} UTC"
    return f"{name} is {value}"


# ---------------------------------------------------------------------------
# 4. Filter application
# ---------------------------------------------------------------------------

def check_conditional_filters(
    filters: list[ConditionalFilter],
    timestamp: datetime,
    strategy: str,
    regime: str,
    consecutive_losses: int,
) -> tuple[bool, str | None]:
    """Check if any conditional filter blocks this entry.

    Returns (is_blocked, filter_reason).
    Matches timestamp to session/weekday/hour, strategy, regime, consecutive_losses.
    """
    if not filters:
        return (False, None)

    session = classify_session(timestamp.hour)
    weekday = _WEEKDAY_NAMES[timestamp.weekday()]
    hour_bucket = _classify_hour_bucket(timestamp.hour)
    consec_bucket = str(min(consecutive_losses, 3)) if consecutive_losses < 3 else "3+"
    strategy_regime = f"{strategy}|{regime}"

    for f in filters:
        matched = False
        ct = f.condition_type or f.condition_name
        cv = f.condition_value

        if ct == "session" and cv == session:
            matched = True
        elif ct == "weekday" and cv == weekday:
            matched = True
        elif ct == "strategy" and cv == strategy:
            matched = True
        elif ct == "regime" and cv == regime:
            matched = True
        elif ct == "strategy_regime" and cv == strategy_regime:
            matched = True
        elif ct == "consecutive_loss" and cv == consec_bucket:
            matched = True
        elif ct == "hour_bucket" and cv == hour_bucket:
            matched = True

        if matched:
            return (True, f.block_reason)

    return (False, None)


# ---------------------------------------------------------------------------
# 5. Reports
# ---------------------------------------------------------------------------

def format_analysis_report(analysis: TradeAnalysis) -> str:
    """Human-readable analysis report.

    Shows all condition groups with win rate, avg PnL, sample size.
    Highlights underperforming conditions.
    """
    lines: list[str] = []
    lines.append("=" * 70)
    lines.append("TRADE PATTERN ANALYSIS REPORT")
    lines.append("=" * 70)
    lines.append("")
    lines.append(f"Total trades:     {analysis.total_trades}")
    lines.append(f"Overall win rate: {analysis.overall_win_rate:.1%}")
    lines.append(f"Overall avg PnL:  {analysis.overall_avg_pnl:.2f}")
    lines.append("")

    section_data: list[tuple[str, list[ConditionStats]]] = [
        ("By Session", analysis.by_session),
        ("By Weekday", analysis.by_weekday),
        ("By Strategy", analysis.by_strategy),
        ("By Regime", analysis.by_regime),
        ("By Strategy + Regime", analysis.by_strategy_regime),
        ("By Consecutive Losses", analysis.by_consecutive_loss),
        ("By Hour Bucket (4h)", analysis.by_hour_bucket),
    ]

    for section_name, stats_list in section_data:
        lines.append(f"--- {section_name} ---")
        if not stats_list:
            lines.append("  (no data)")
            lines.append("")
            continue
        lines.append(
            f"  {'Value':<25} {'Trades':>7} {'Wins':>6} {'WinRate':>8} "
            f"{'AvgPnL':>10} {'AvgPnLR':>8} {'Sig':>4}"
        )
        for s in stats_list:
            marker = " ***" if s.is_significant and s.win_rate < analysis.overall_win_rate else ""
            lines.append(
                f"  {s.condition_value:<25} {s.total_trades:>7} {s.winning_trades:>6} "
                f"{s.win_rate:>7.1%} {s.avg_pnl:>10.2f} {s.avg_pnl_r:>8.2f} "
                f"{'Y' if s.is_significant else 'N':>4}{marker}"
            )
        lines.append("")

    lines.append("*** = statistically significant underperformance")
    return "\n".join(lines)


def format_filter_report(filters: list[ConditionalFilter]) -> str:
    """Report of generated filters with rationale."""
    lines: list[str] = []
    lines.append("=" * 70)
    lines.append("CONDITIONAL ENTRY FILTERS")
    lines.append("=" * 70)
    lines.append("")

    if not filters:
        lines.append("No underperforming conditions found that meet filter criteria.")
        return "\n".join(lines)

    lines.append(f"Total filters generated: {len(filters)}")
    lines.append("")

    for i, f in enumerate(filters, 1):
        lines.append(f"Filter #{i}:")
        lines.append(f"  Condition:   {f.condition_check}")
        lines.append(f"  Win rate:    {f.win_rate:.1%}")
        lines.append(f"  Avg PnL:     {f.avg_pnl:.2f}")
        lines.append(f"  Sample size: {f.sample_size}")
        lines.append(f"  Block reason: {f.block_reason}")
        lines.append("")

    return "\n".join(lines)
