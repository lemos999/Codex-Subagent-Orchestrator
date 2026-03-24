"""Quest scoring system."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from tq.config import MAX_DRAWDOWN_LIMIT

logger = logging.getLogger(__name__)


@dataclass
class QuestScore:
    """Score for a single trading day or evaluation period."""
    return_pct: float = 0.0
    win_rate: float = 0.0
    trades: int = 0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0

    @property
    def composite_score(self) -> float:
        """Composite score combining multiple factors."""
        base = self.return_pct * 1000  # reward returns
        trade_bonus = min(self.trades * 10, 200)  # up to 200 points for activity
        wr_bonus = self.win_rate * 2  # up to 200 points
        dd_penalty = self.drawdown_penalty
        risk_adj = self.risk_adjusted_score

        return base + trade_bonus + wr_bonus - dd_penalty + risk_adj

    @property
    def drawdown_penalty(self) -> float:
        """Penalty for excessive drawdown."""
        if self.max_drawdown <= 0.05:
            return 0.0
        elif self.max_drawdown <= 0.10:
            return (self.max_drawdown - 0.05) * 1000
        elif self.max_drawdown <= MAX_DRAWDOWN_LIMIT:
            return 50 + (self.max_drawdown - 0.10) * 2000
        else:
            return 250 + (self.max_drawdown - MAX_DRAWDOWN_LIMIT) * 5000

    @property
    def risk_adjusted_score(self) -> float:
        """Risk-adjusted score bonus."""
        if self.sharpe_ratio <= 0:
            return 0.0
        return min(self.sharpe_ratio * 50, 200)

    def to_dict(self) -> dict:
        return {
            "return_pct": self.return_pct,
            "win_rate": self.win_rate,
            "trades": self.trades,
            "max_drawdown": self.max_drawdown,
            "sharpe_ratio": self.sharpe_ratio,
            "composite_score": self.composite_score,
            "drawdown_penalty": self.drawdown_penalty,
            "risk_adjusted_score": self.risk_adjusted_score,
        }


class ScoreTracker:
    """Tracks scores over a quest."""

    def __init__(self):
        self.daily_scores: list[QuestScore] = []
        self.total_score: float = 0.0

    def add_day(self, score: QuestScore) -> float:
        """Add a daily score. Returns cumulative total."""
        self.daily_scores.append(score)
        self.total_score += score.composite_score
        return self.total_score

    def get_average_score(self) -> float:
        """Average composite score per day."""
        if not self.daily_scores:
            return 0.0
        return self.total_score / len(self.daily_scores)

    def get_best_day(self) -> Optional[QuestScore]:
        """Day with the highest composite score."""
        if not self.daily_scores:
            return None
        return max(self.daily_scores, key=lambda s: s.composite_score)

    def get_worst_day(self) -> Optional[QuestScore]:
        """Day with the lowest composite score."""
        if not self.daily_scores:
            return None
        return min(self.daily_scores, key=lambda s: s.composite_score)

    def to_dict(self) -> dict:
        return {
            "total_score": self.total_score,
            "days": len(self.daily_scores),
            "average_score": self.get_average_score(),
            "daily_scores": [s.to_dict() for s in self.daily_scores],
        }
