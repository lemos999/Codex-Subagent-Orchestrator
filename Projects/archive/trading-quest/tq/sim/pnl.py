"""P&L tracking and daily summaries."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class DaySummary:
    """Summary of a single trading day."""
    date: str
    starting_value: float
    ending_value: float
    pnl: float = 0.0
    return_pct: float = 0.0
    trades: int = 0
    wins: int = 0
    losses: int = 0
    commission_total: float = 0.0
    max_drawdown: float = 0.0

    def __post_init__(self) -> None:
        if self.pnl == 0.0:
            self.pnl = self.ending_value - self.starting_value
        if self.return_pct == 0.0 and self.starting_value > 0:
            self.return_pct = self.pnl / self.starting_value * 100

    @property
    def win_rate(self) -> float:
        if self.trades == 0:
            return 0.0
        return self.wins / self.trades * 100

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "starting_value": self.starting_value,
            "ending_value": self.ending_value,
            "pnl": self.pnl,
            "return_pct": self.return_pct,
            "trades": self.trades,
            "wins": self.wins,
            "losses": self.losses,
            "win_rate": self.win_rate,
            "commission_total": self.commission_total,
            "max_drawdown": self.max_drawdown,
        }


class PnLTracker:
    """Tracks P&L over the course of a quest."""

    def __init__(self, initial_capital: float):
        self.initial_capital = initial_capital
        self.current_value = initial_capital
        self.peak_value = initial_capital
        self.daily_summaries: list[DaySummary] = []
        self.total_commission: float = 0.0
        self.total_trades: int = 0
        self.total_wins: int = 0
        self.total_losses: int = 0
        self._day_start_value: float = initial_capital

    def start_day(self, date: str) -> None:
        """Mark the start of a new trading day."""
        self._day_start_value = self.current_value
        self._current_date = date

    def record_trade(self, pnl: float, commission: float = 0.0) -> None:
        """Record a single trade result."""
        self.total_trades += 1
        self.total_commission += commission
        if pnl > 0:
            self.total_wins += 1
        elif pnl < 0:
            self.total_losses += 1
        self.current_value += pnl

    def update_value(self, value: float) -> None:
        """Update current portfolio value (e.g., mark-to-market)."""
        self.current_value = value
        self.peak_value = max(self.peak_value, value)

    def end_day(self, date: str, trades: int = 0,
                wins: int = 0, losses: int = 0,
                commission: float = 0.0) -> DaySummary:
        """Finalize the day and create a summary."""
        self.peak_value = max(self.peak_value, self.current_value)
        dd = self.current_drawdown()

        summary = DaySummary(
            date=date,
            starting_value=self._day_start_value,
            ending_value=self.current_value,
            trades=trades,
            wins=wins,
            losses=losses,
            commission_total=commission,
            max_drawdown=dd,
        )
        self.daily_summaries.append(summary)
        return summary

    def current_drawdown(self) -> float:
        """Current drawdown from peak."""
        if self.peak_value == 0:
            return 0.0
        dd = (self.peak_value - self.current_value) / self.peak_value
        return max(0.0, dd)

    def max_drawdown(self) -> float:
        """Maximum drawdown seen across all daily summaries."""
        if not self.daily_summaries:
            return self.current_drawdown()
        return max(s.max_drawdown for s in self.daily_summaries)

    @property
    def total_return(self) -> float:
        """Total return from initial capital."""
        return self.current_value - self.initial_capital

    @property
    def total_return_pct(self) -> float:
        """Total return percentage."""
        if self.initial_capital == 0:
            return 0.0
        return self.total_return / self.initial_capital * 100

    @property
    def win_rate(self) -> float:
        """Overall win rate."""
        if self.total_trades == 0:
            return 0.0
        return self.total_wins / self.total_trades * 100

    @property
    def sharpe_ratio(self) -> float:
        """Simplified Sharpe ratio from daily returns."""
        if len(self.daily_summaries) < 2:
            return 0.0
        returns = [s.return_pct for s in self.daily_summaries]
        mean_ret = sum(returns) / len(returns)
        variance = sum((r - mean_ret) ** 2 for r in returns) / (len(returns) - 1)
        std = variance ** 0.5
        if std == 0:
            return 0.0
        return mean_ret / std * (252 ** 0.5)  # annualized

    def to_dict(self) -> dict:
        return {
            "initial_capital": self.initial_capital,
            "current_value": self.current_value,
            "total_return": self.total_return,
            "total_return_pct": self.total_return_pct,
            "total_trades": self.total_trades,
            "win_rate": self.win_rate,
            "max_drawdown": self.max_drawdown(),
            "sharpe_ratio": self.sharpe_ratio,
            "total_commission": self.total_commission,
            "days": len(self.daily_summaries),
        }
