"""Strategy ranking and leaderboard."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class StrategyResult:
    """Result of a strategy evaluation."""
    strategy_name: str
    total_return: float = 0.0
    total_return_pct: float = 0.0
    total_trades: int = 0
    win_rate: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    composite_score: float = 0.0
    days: int = 0
    params: dict = field(default_factory=dict)

    @property
    def rank_score(self) -> float:
        """Combined score for ranking."""
        return (
            self.composite_score * 0.4
            + self.total_return_pct * 10 * 0.3
            + self.sharpe_ratio * 50 * 0.2
            - self.max_drawdown * 100 * 0.1
        )

    def to_dict(self) -> dict:
        return {
            "strategy_name": self.strategy_name,
            "total_return": self.total_return,
            "total_return_pct": self.total_return_pct,
            "total_trades": self.total_trades,
            "win_rate": self.win_rate,
            "max_drawdown": self.max_drawdown,
            "sharpe_ratio": self.sharpe_ratio,
            "composite_score": self.composite_score,
            "rank_score": self.rank_score,
            "days": self.days,
            "params": self.params,
        }


class StrategyRanker:
    """Compare strategies and maintain a leaderboard."""

    def __init__(self):
        self.results: list[StrategyResult] = []

    def add_result(self, result: StrategyResult) -> None:
        """Add a strategy result."""
        self.results.append(result)

    def get_leaderboard(self, top_n: int = 10) -> list[StrategyResult]:
        """Get top N strategies by rank_score."""
        sorted_results = sorted(
            self.results, key=lambda r: r.rank_score, reverse=True
        )
        return sorted_results[:top_n]

    def compare(self, names: list[str]) -> list[StrategyResult]:
        """Compare specific strategies by name."""
        filtered = [r for r in self.results if r.strategy_name in names]
        return sorted(filtered, key=lambda r: r.rank_score, reverse=True)

    def get_best(self) -> Optional[StrategyResult]:
        """Get the best strategy."""
        if not self.results:
            return None
        return max(self.results, key=lambda r: r.rank_score)

    def format_leaderboard(self, top_n: int = 10) -> str:
        """Format leaderboard as a string table."""
        board = self.get_leaderboard(top_n)
        if not board:
            return "No strategies evaluated yet."

        lines = [
            f"{'Rank':<5} {'Strategy':<20} {'Return%':<10} {'WinRate':<10} "
            f"{'MaxDD':<10} {'Sharpe':<10} {'Score':<10}",
            "-" * 75,
        ]
        for i, r in enumerate(board, 1):
            lines.append(
                f"{i:<5} {r.strategy_name:<20} {r.total_return_pct:<10.2f} "
                f"{r.win_rate:<10.1f} {r.max_drawdown:<10.2%} "
                f"{r.sharpe_ratio:<10.2f} {r.rank_score:<10.1f}"
            )
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "total_strategies": len(self.results),
            "leaderboard": [r.to_dict() for r in self.get_leaderboard()],
        }
