"""Strategy benchmark -- runs 10 strategies x 7 time periods = 70 tests.

Scoring rules:
  Win:  +0.1 + (return_pct * 10)
  Loss: -0.2 - (abs(return_pct) * 10)
  Score starts at 0 per test.
  Minimum 4 complete trades (buy+sell = 1 trade) per test.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Callable, Optional

from tq.journal.journal import TradingJournal

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────
# Data classes
# ──────────────────────────────────────────────────────────────────────

@dataclass
class TradeDetail:
    """One completed round-trip trade."""
    entry_price: float
    exit_price: float
    qty: float
    pnl: float
    pnl_pct: float
    score: float
    entry_time: str = ""
    exit_time: str = ""


@dataclass
class SingleTestResult:
    """Result of running one strategy for one time period."""
    strategy: str
    symbol: str
    days: int
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    total_return_pct: float = 0.0          # 전체 수익률 (실현+미실현)
    realized_return_pct: float = 0.0       # 실현 수익률
    unrealized_return_pct: float = 0.0     # 미실현 수익률
    realized_pnl: float = 0.0             # 실현 손익 금액
    unrealized_pnl: float = 0.0           # 미실현 손익 금액
    total_score: float = 0.0              # 점수 (실현 기준만)
    max_drawdown: float = 0.0
    portfolio_value: float = 0.0
    initial_capital: float = 100_000.0
    open_positions: int = 0               # 미청산 포지션 수
    min_trades_met: bool = False
    trades: list[TradeDetail] = field(default_factory=list)
    error: str = ""


@dataclass
class BenchmarkResult:
    """Result of the full benchmark run."""
    results: list[SingleTestResult] = field(default_factory=list)
    start_date: str = "2024-01-02"
    elapsed_seconds: float = 0.0

    def get(self, strategy: str, days: int) -> Optional[SingleTestResult]:
        """Get result for a specific strategy + period combo."""
        for r in self.results:
            if r.strategy == strategy and r.days == days:
                return r
        return None

    def best_strategy_for_period(self, days: int) -> Optional[SingleTestResult]:
        """Get the best-scoring strategy for a given period."""
        period_results = [r for r in self.results if r.days == days and not r.error]
        if not period_results:
            return None
        return max(period_results, key=lambda r: r.total_score)


# ──────────────────────────────────────────────────────────────────────
# Benchmark configurations
# ──────────────────────────────────────────────────────────────────────

STRATEGIES = [
    ("bollinger", "TSLA"),
    ("mean_reversion", "TSLA"),
    ("macd", "MSFT"),
    ("stochastic", "MSFT"),
    ("ma_crossover", "AAPL"),
    ("rsi", "NVDA"),
    ("dqn", "AAPL"),
    ("ichimoku", "JPM"),
    ("donchian", "GOOGL"),
    ("momentum", "TSLA"),
]

PERIODS = [3, 5, 30, 60, 120, 180, 252]
PERIOD_NAMES = ["3일", "5일", "30일", "60일", "120일", "180일", "1년"]

QUICK_PERIODS = [3, 30, 252]
QUICK_PERIOD_NAMES = ["3일", "30일", "1년"]

MIN_TRADES = 4


# ──────────────────────────────────────────────────────────────────────
# Main benchmark class
# ──────────────────────────────────────────────────────────────────────

class StrategyBenchmark:
    """Run benchmark tests across multiple strategies and time periods."""

    def __init__(self):
        self.journal = TradingJournal()
        self.periods = list(PERIODS)
        self.period_names = list(PERIOD_NAMES)

    def run_single_test(
        self,
        strategy_name: str,
        symbol: str,
        days: int,
        start_date: str = "2024-01-02",
    ) -> SingleTestResult:
        """Run a single strategy for N days and return results.

        Uses the existing QuestEngine with DB cache.
        """
        from tq.quest.engine import QuestEngine

        result = SingleTestResult(
            strategy=strategy_name,
            symbol=symbol,
            days=days,
            initial_capital=100_000.0,
        )

        try:
            engine = QuestEngine(
                quest_id=f"bench-{strategy_name}-{symbol}-{days}d",
                market="US",
                symbols=[symbol],
                initial_capital=100_000.0,
            )

            summary = engine.run(start_date, days, strategy_name)

            # Extract completed trades from the broker
            completed = engine.broker.completed_trades

            trades_detail: list[TradeDetail] = []
            total_score = 0.0
            wins = 0
            losses = 0

            for ct in completed:
                pnl_pct = ct.pnl_pct
                score = self._calculate_score(pnl_pct)
                total_score += score

                if ct.pnl > 0:
                    wins += 1
                else:
                    losses += 1

                trades_detail.append(TradeDetail(
                    entry_price=ct.entry_price,
                    exit_price=ct.exit_price,
                    qty=ct.qty,
                    pnl=ct.pnl,
                    pnl_pct=pnl_pct,
                    score=score,
                    entry_time=ct.entry_time,
                    exit_time=ct.exit_time,
                ))

            total_trades = len(completed)
            result.total_trades = total_trades
            result.wins = wins
            result.losses = losses
            result.win_rate = wins / total_trades if total_trades > 0 else 0.0
            result.total_return_pct = summary.get("return_pct", 0.0)
            result.total_score = total_score
            result.max_drawdown = summary.get("max_drawdown", 0.0)
            result.portfolio_value = summary.get("portfolio_value", 100_000.0)
            result.min_trades_met = total_trades >= MIN_TRADES
            result.trades = trades_detail

            # 실현/미실현 분리
            realized = sum(ct.pnl for ct in completed)
            result.realized_pnl = realized
            result.realized_return_pct = realized / 100_000.0 if 100_000.0 > 0 else 0.0

            portfolio_val = result.portfolio_value
            total_pnl = portfolio_val - 100_000.0
            result.unrealized_pnl = total_pnl - realized
            result.unrealized_return_pct = result.unrealized_pnl / 100_000.0

            # 미청산 포지션
            result.open_positions = len(engine.broker.portfolio.positions)

        except Exception as e:
            result.error = str(e)
            logger.warning("Test failed: %s on %s (%dd): %s",
                           strategy_name, symbol, days, e)

        return result

    def run_full_benchmark(
        self,
        callback: Optional[Callable[[str], None]] = None,
        quick: bool = False,
    ) -> BenchmarkResult:
        """Run all 10 strategies x 7 periods = 70 tests (or quick mode: 30)."""
        periods = QUICK_PERIODS if quick else self.periods
        period_names = QUICK_PERIOD_NAMES if quick else self.period_names
        total_tests = len(STRATEGIES) * len(periods)

        start_time = time.time()
        bench = BenchmarkResult(start_date="2024-01-02")
        completed = 0

        for strat_name, symbol in STRATEGIES:
            for period_days, period_label in zip(periods, period_names):
                completed += 1
                if callback:
                    callback(
                        f"[{completed}/{total_tests}] "
                        f"{strat_name} on {symbol} ({period_label})..."
                    )

                result = self.run_single_test(
                    strat_name, symbol, period_days, "2024-01-02"
                )
                bench.results.append(result)

        bench.elapsed_seconds = time.time() - start_time
        return bench

    def format_results(self, result: BenchmarkResult, quick: bool = False) -> str:
        """Format results as a comprehensive table."""
        periods = QUICK_PERIODS if quick else self.periods
        period_names = QUICK_PERIOD_NAMES if quick else self.period_names

        lines: list[str] = []

        # ── Header ──
        lines.append("=" * 90)
        lines.append("  전략 벤치마크 결과")
        lines.append(f"  기간: {result.start_date} ~")
        lines.append("  점수: 수익 +0.1+(수익률x10) / 손실 -0.2-(손실률x10)")
        lines.append(f"  소요 시간: {result.elapsed_seconds:.1f}초")
        lines.append("=" * 90)
        lines.append("")

        # ── Summary table ──
        # Build header row
        col_w = 8
        header_parts = [f"{'전략':<20s} {'종목':<6s}"]
        for pn in period_names:
            header_parts.append(f"{pn:>{col_w}s}")
        lines.append("".join(header_parts))
        lines.append("-" * (28 + col_w * len(period_names)))

        for idx, (strat_name, symbol) in enumerate(STRATEGIES, 1):
            row_parts = [f"{idx:2d}. {strat_name:<16s} {symbol:<6s}"]
            for pd_val in periods:
                r = result.get(strat_name, pd_val)
                if r is None or r.error:
                    row_parts.append(f"{'ERR':>{col_w}s}")
                elif not r.min_trades_met:
                    row_parts.append(f"{'<4tr':>{col_w}s}")
                else:
                    score_str = f"{r.total_score:+.1f}"
                    row_parts.append(f"{score_str:>{col_w}s}")
            lines.append("".join(row_parts))

        lines.append("-" * (28 + col_w * len(period_names)))

        # Best per period
        best_parts = [f"{'최고:':<28s}"]
        for pd_val in periods:
            best = result.best_strategy_for_period(pd_val)
            if best:
                best_parts.append(f"{best.strategy:>{col_w}s}")
            else:
                best_parts.append(f"{'N/A':>{col_w}s}")
        lines.append("".join(best_parts))
        lines.append("")

        # ── Detailed tables for each period ──
        for pd_val, pd_name in zip(periods, period_names):
            lines.append("=" * 90)
            lines.append(f"  기간별 상세 ({pd_name})")
            lines.append("=" * 90)
            detail_header = (
                f"{'전략':<16s} {'종목':<6s} {'거래':>4s} {'승':>3s} "
                f"{'패':>3s} {'승률':>6s} {'실현수익':>8s} {'미실현':>8s} "
                f"{'점수':>7s} {'낙폭':>6s} {'보유':>3s} {'비고':>4s}"
            )
            lines.append(detail_header)
            lines.append("-" * 100)

            period_results = [
                r for r in result.results if r.days == pd_val
            ]
            # Sort by score descending
            period_results.sort(key=lambda x: x.total_score, reverse=True)

            for r in period_results:
                if r.error:
                    lines.append(
                        f"{r.strategy:<16s} {r.symbol:<6s} "
                        f"{'ERROR: ' + r.error[:40]}"
                    )
                    continue

                wr_str = f"{r.win_rate:.0%}" if r.total_trades > 0 else "N/A"
                realized_str = f"{r.realized_return_pct*100:+.2f}%"
                unrealized_str = f"{r.unrealized_return_pct*100:+.2f}%"
                score_str = f"{r.total_score:+.1f}"
                dd_str = f"{r.max_drawdown:.1%}" if r.max_drawdown else "0.0%"
                pos_str = f"{r.open_positions}" if r.open_positions > 0 else "-"
                note = "" if r.min_trades_met else "<4tr"

                lines.append(
                    f"{r.strategy:<16s} {r.symbol:<6s} "
                    f"{r.total_trades:>4d} {r.wins:>3d} {r.losses:>3d} "
                    f"{wr_str:>6s} {realized_str:>8s} {unrealized_str:>8s} "
                    f"{score_str:>7s} {dd_str:>6s} {pos_str:>3s} {note:>4s}"
                )

            lines.append("")

        # ── Overall summary ──
        lines.append("=" * 90)
        lines.append("  종합 요약")
        lines.append("=" * 90)

        all_valid = [r for r in result.results if not r.error]
        total_trades = sum(r.total_trades for r in all_valid)
        met_min = sum(1 for r in all_valid if r.min_trades_met)
        below_min = sum(1 for r in all_valid if not r.min_trades_met)
        errors = sum(1 for r in result.results if r.error)

        lines.append(f"  총 테스트: {len(result.results)}")
        lines.append(f"  총 거래: {total_trades}")
        lines.append(f"  최소 4거래 충족: {met_min}")
        lines.append(f"  최소 4거래 미달: {below_min}")
        lines.append(f"  에러: {errors}")
        lines.append("")

        # Best overall strategy (by average score across periods)
        strat_avg: dict[str, list[float]] = {}
        for r in all_valid:
            strat_avg.setdefault(r.strategy, []).append(r.total_score)
        if strat_avg:
            best_strat = max(strat_avg, key=lambda s: sum(strat_avg[s]) / len(strat_avg[s]))
            avg = sum(strat_avg[best_strat]) / len(strat_avg[best_strat])
            lines.append(f"  최고 전략 (평균 점수): {best_strat} ({avg:+.2f})")

        lines.append("=" * 90)
        return "\n".join(lines)

    # ──────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _calculate_score(pnl_pct: float) -> float:
        """Calculate score for a single trade.

        Win:  +0.1 + (return_pct * 10)
        Loss: -0.2 - (abs(return_pct) * 10)
        """
        if pnl_pct > 0:
            return 0.1 + (pnl_pct * 10)
        elif pnl_pct < 0:
            return -0.2 - (abs(pnl_pct) * 10)
        return 0.0
