"""Trade analyzer -- discovers patterns and generates actionable insights."""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np
import pandas as pd

from tq.journal.journal import TradingJournal
from tq.strategy.indicator import adx, atr, sma

logger = logging.getLogger(__name__)


@dataclass
class AnalysisReport:
    """Container for analysis results."""
    win_rate: float = 0.0
    win_rate_trend: str = "stable"  # "improving", "declining", "stable"
    total_trades: int = 0
    total_score: float = 0.0
    profitable_strategies: list[str] = field(default_factory=list)
    losing_strategies: list[str] = field(default_factory=list)
    best_symbols: list[str] = field(default_factory=list)
    worst_symbols: list[str] = field(default_factory=list)
    optimal_position_size: float = 0.15
    lessons: list[str] = field(default_factory=list)
    strategy_weights: dict[str, float] = field(default_factory=dict)
    regime: str = "unknown"

    def to_dict(self) -> dict:
        return {
            "win_rate": self.win_rate,
            "win_rate_trend": self.win_rate_trend,
            "total_trades": self.total_trades,
            "total_score": self.total_score,
            "profitable_strategies": self.profitable_strategies,
            "losing_strategies": self.losing_strategies,
            "best_symbols": self.best_symbols,
            "worst_symbols": self.worst_symbols,
            "optimal_position_size": self.optimal_position_size,
            "lessons": self.lessons,
            "strategy_weights": self.strategy_weights,
            "regime": self.regime,
        }

    def format(self) -> str:
        lines = [
            f"Win Rate: {self.win_rate:.1%} ({self.win_rate_trend})",
            f"Total Trades: {self.total_trades}",
            f"Total Score: {self.total_score:+.1f}",
            f"Optimal Position Size: {self.optimal_position_size:.1%}",
            f"Regime: {self.regime}",
        ]
        if self.profitable_strategies:
            lines.append(f"Profitable Strategies: {', '.join(self.profitable_strategies)}")
        if self.losing_strategies:
            lines.append(f"Losing Strategies: {', '.join(self.losing_strategies)}")
        if self.best_symbols:
            lines.append(f"Best Symbols: {', '.join(self.best_symbols)}")
        if self.lessons:
            lines.append("Lessons:")
            for lesson in self.lessons:
                lines.append(f"  - {lesson}")
        if self.strategy_weights:
            lines.append("Strategy Weights:")
            for s, w in sorted(self.strategy_weights.items(), key=lambda x: -x[1]):
                lines.append(f"  {s}: {w:.2f}")
        return "\n".join(lines)


class TradeAnalyzer:
    """Analyzes trading journal to discover patterns and generate insights."""

    def __init__(self, journal: TradingJournal):
        self.journal = journal

    def analyze_recent(self, days: int = 10) -> AnalysisReport:
        """Analyze recent trades and generate actionable insights."""
        trades = self.journal.load_history(days=days)
        report = AnalysisReport()

        if not trades:
            report.lessons.append("No trade history yet. Start trading to build data.")
            return report

        report.total_trades = len(trades)
        wins = [t for t in trades if t.get("pnl", 0) > 0]
        report.win_rate = len(wins) / len(trades) if trades else 0.0
        report.total_score = sum(t.get("score", 0) for t in trades)

        # Win rate trend
        report.win_rate_trend = self._compute_win_rate_trend(trades)

        # Strategy analysis
        strat_perf = self.journal.get_strategy_performance()
        for name, perf in strat_perf.items():
            if perf["win_rate"] >= 0.5 and perf["total_pnl"] > 0:
                report.profitable_strategies.append(name)
            elif perf["win_rate"] < 0.5 or perf["total_pnl"] < 0:
                report.losing_strategies.append(name)

        # Symbol analysis
        sym_perf = self.journal.get_symbol_performance()
        sorted_syms = sorted(sym_perf.items(), key=lambda x: x[1].get("total_pnl", 0),
                             reverse=True)
        report.best_symbols = [s for s, _ in sorted_syms[:3] if sym_perf[s]["total_pnl"] > 0]
        report.worst_symbols = [s for s, _ in sorted_syms[-3:] if sym_perf[s]["total_pnl"] < 0]

        # Optimal position sizing via Kelly criterion
        report.optimal_position_size = self._kelly_criterion(trades)

        # Generate lessons
        report.lessons = self.generate_lessons()

        # Strategy weights
        report.strategy_weights = self.recommend_strategy_weights()

        # Save analysis
        self.journal.save_analysis("strategy-stats", strat_perf)
        self.journal.save_analysis("latest-report", report.to_dict())

        return report

    def generate_lessons(self) -> list[str]:
        """Extract lessons from trade history."""
        lessons: list[str] = []
        strat_perf = self.journal.get_strategy_performance()
        regime_perf = self.journal.get_market_regime_performance()
        stats = self.journal.get_statistics()

        # Strategy-regime interactions
        for strat_name, perf in strat_perf.items():
            if perf["trade_count"] >= 5 and perf["win_rate"] < 0.5:
                lessons.append(
                    f"Strategy '{strat_name}' has low win rate "
                    f"({perf['win_rate']:.0%}) over {perf['trade_count']} trades "
                    f"-- consider reducing allocation or disabling."
                )
            if perf["trade_count"] >= 5 and perf["win_rate"] >= 0.67:
                lessons.append(
                    f"Strategy '{strat_name}' is performing well "
                    f"({perf['win_rate']:.0%} win rate) -- increase allocation."
                )

        # Regime lessons
        for regime, perf in regime_perf.items():
            if regime == "unknown":
                continue
            if perf["trade_count"] >= 3 and perf["win_rate"] < 0.4:
                lessons.append(
                    f"Trading in '{regime}' regime has poor results "
                    f"({perf['win_rate']:.0%} win rate) -- avoid or reduce size."
                )

        # Score lessons
        if stats.get("total_score", 0) < 0:
            lessons.append(
                "Overall score is negative. Focus on win rate (need 67%+) "
                "rather than trade frequency."
            )

        # Streak lessons
        streak = stats.get("current_streak", 0)
        if streak <= -3:
            lessons.append(
                f"Currently on a {abs(streak)}-trade losing streak. "
                "Consider reducing position size or pausing."
            )

        # Win rate threshold
        win_rate = stats.get("win_rate", 0)
        if 0 < win_rate < 0.67 and stats.get("total_trades", 0) >= 10:
            lessons.append(
                f"Win rate ({win_rate:.0%}) is below the 67% break-even threshold. "
                "Tighten entry criteria and use higher-confidence setups only."
            )

        if not lessons:
            lessons.append("Insufficient data for detailed lessons. Keep trading.")

        # Save lessons
        self.journal.save_analysis("lessons", {"lessons": lessons})
        return lessons

    def recommend_strategy_weights(self) -> dict[str, float]:
        """Recommend which strategies to use and their allocation weight.
        Based on recent performance, scale winning strategies up, losing ones down.
        """
        strat_perf = self.journal.get_strategy_performance()
        if not strat_perf:
            return {}

        # Score each strategy: win_rate * 2 + normalized_pnl
        scores: dict[str, float] = {}
        for name, perf in strat_perf.items():
            if perf["trade_count"] < 2:
                scores[name] = 0.1  # minimal weight for untested
                continue
            wr = perf["win_rate"]
            # Asymmetric scoring penalty: need 67%+ to break even
            if wr < 0.5:
                score = wr * 0.5  # heavy penalty
            elif wr < 0.67:
                score = wr * 1.0  # moderate
            else:
                score = wr * 2.0  # reward high win rate
            scores[name] = max(0.05, score)

        total = sum(scores.values())
        if total == 0:
            return {name: 1.0 / len(scores) for name in scores}

        return {name: score / total for name, score in scores.items()}

    def recommend_parameters(self, strategy: str) -> dict:
        """Suggest optimal parameters for a strategy based on journal analysis."""
        trades = self.journal.load_history(days=90)
        strat_trades = [t for t in trades if t.get("strategy") == strategy]
        if len(strat_trades) < 5:
            return {}

        # Analyze which indicator values at entry led to wins
        winning_indicators: list[dict] = []
        for t in strat_trades:
            if t.get("pnl", 0) > 0:
                indicators = t.get("indicators_at_entry", {})
                if indicators:
                    winning_indicators.append(indicators)

        if not winning_indicators:
            return {}

        # Average winning indicator values as recommended params
        result: dict[str, float] = {}
        keys = set()
        for ind in winning_indicators:
            keys.update(ind.keys())
        for key in keys:
            vals = [ind[key] for ind in winning_indicators
                    if key in ind and isinstance(ind[key], (int, float))]
            if vals:
                result[key] = sum(vals) / len(vals)
        return result

    def detect_market_regime(self, symbol: str, data: pd.DataFrame) -> str:
        """Detect current market regime: 'trending_up', 'trending_down',
        'ranging', 'volatile'.

        Uses ADX, ATR, and price vs SMA.
        """
        if data is None or len(data) < 30:
            return "unknown"

        close = data["close"] if "close" in data.columns else data["Close"]
        high = data["high"] if "high" in data.columns else data["High"]
        low = data["low"] if "low" in data.columns else data["Low"]

        # ADX for trend strength
        adx_val = adx(high, low, close, period=14)
        current_adx = adx_val.iloc[-1] if not adx_val.empty else 0

        # ATR for volatility
        atr_val = atr(high, low, close, period=14)
        current_atr = atr_val.iloc[-1] if not atr_val.empty else 0
        avg_atr = atr_val.rolling(50).mean().iloc[-1] if len(atr_val) >= 50 else current_atr

        # Price vs SMA for direction
        sma_50 = sma(close, 50)
        current_price = close.iloc[-1]
        current_sma = sma_50.iloc[-1] if not sma_50.empty else current_price

        # Handle NaN
        if any(math.isnan(v) for v in [current_adx, current_atr, avg_atr, current_sma]
               if isinstance(v, float)):
            return "unknown"

        # High volatility check
        if avg_atr > 0 and current_atr > avg_atr * 1.5:
            return "volatile"

        # Trending check (ADX > 25 = trending)
        if current_adx > 25:
            if current_price > current_sma:
                return "trending_up"
            else:
                return "trending_down"

        return "ranging"

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _compute_win_rate_trend(self, trades: list[dict]) -> str:
        """Determine if win rate is improving, declining, or stable."""
        if len(trades) < 10:
            return "stable"
        mid = len(trades) // 2
        first_half = trades[:mid]
        second_half = trades[mid:]

        wr1 = sum(1 for t in first_half if t.get("pnl", 0) > 0) / len(first_half)
        wr2 = sum(1 for t in second_half if t.get("pnl", 0) > 0) / len(second_half)

        diff = wr2 - wr1
        if diff > 0.05:
            return "improving"
        elif diff < -0.05:
            return "declining"
        return "stable"

    def _kelly_criterion(self, trades: list[dict]) -> float:
        """Calculate optimal position size using Kelly Criterion.

        Kelly % = W - (1-W)/R
        W = win probability, R = win/loss ratio

        With asymmetric scoring (+0.1/-0.2), we apply a safety factor.
        """
        if len(trades) < 5:
            return 0.15  # default conservative

        wins = [t for t in trades if t.get("pnl", 0) > 0]
        losses = [t for t in trades if t.get("pnl", 0) < 0]

        if not wins or not losses:
            return 0.10

        w = len(wins) / len(trades)
        avg_win = sum(abs(t["pnl"]) for t in wins) / len(wins)
        avg_loss = sum(abs(t["pnl"]) for t in losses) / len(losses)

        if avg_loss == 0:
            return 0.15

        r = avg_win / avg_loss
        kelly = w - (1 - w) / r

        # Half-Kelly for safety, clamped to [0.05, 0.25]
        half_kelly = kelly / 2.0
        return max(0.05, min(0.25, half_kelly))
