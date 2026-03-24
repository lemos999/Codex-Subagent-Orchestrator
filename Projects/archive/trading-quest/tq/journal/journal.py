"""Private AI-only trading journal. Records every trade and learns from patterns.
Stored in a private location only the system accesses.
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class TradingJournal:
    """Private AI-only trading journal. Records every trade and learns from patterns.

    Storage layout::

        .tq-journal/
          trades/
            2024-03-17.jsonl    # one trade per line
          sessions/
            2024-03-17.json     # daily session summary
          analysis/
            strategy-stats.json # cumulative strategy analysis
            lessons.json        # learned lessons/rules
    """

    JOURNAL_PATH = Path(".tq-journal")

    def __init__(self, journal_path: Optional[Path] = None):
        self.journal_path = journal_path or self.JOURNAL_PATH
        self.journal_path.mkdir(parents=True, exist_ok=True)
        (self.journal_path / "trades").mkdir(exist_ok=True)
        (self.journal_path / "sessions").mkdir(exist_ok=True)
        (self.journal_path / "analysis").mkdir(exist_ok=True)

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_trade(self, trade: dict) -> None:
        """Record a completed trade with full context.

        Expected keys: symbol, side, entry_price, exit_price, quantity, pnl,
        pnl_pct, strategy, timeframe, duration, market_context, score,
        timestamp, reason.
        """
        trade_date = self._extract_date(trade.get("timestamp", ""))
        file_path = self.journal_path / "trades" / f"{trade_date}.jsonl"

        # Ensure score is set per return-weighted scoring rules
        if "score" not in trade:
            trade["score"] = self.calculate_score(trade)

        trade.setdefault("recorded_at", datetime.now().isoformat())
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(trade, default=str) + "\n")
        logger.debug("Recorded trade: %s %s pnl=%.2f",
                      trade.get("symbol"), trade.get("side"), trade.get("pnl", 0))

    def record_session(self, session: dict) -> None:
        """Record a trading session summary.

        Expected keys: date, total_trades, wins, losses, net_pnl, score,
        strategies_used, best_trade, worst_trade, lessons.
        """
        session_date = session.get("date", date.today().isoformat())
        file_path = self.journal_path / "sessions" / f"{session_date}.json"
        session.setdefault("recorded_at", datetime.now().isoformat())
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(session, f, indent=2, default=str)
        logger.debug("Recorded session: %s trades=%d score=%.1f",
                      session_date, session.get("total_trades", 0),
                      session.get("score", 0))

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load_history(self, days: int = 30) -> list[dict]:
        """Load recent trade history for analysis."""
        trades_dir = self.journal_path / "trades"
        if not trades_dir.exists():
            return []

        files = sorted(trades_dir.glob("*.jsonl"), reverse=True)[:days]
        all_trades: list[dict] = []
        for f in files:
            for line in f.read_text(encoding="utf-8").strip().splitlines():
                if line.strip():
                    try:
                        all_trades.append(json.loads(line))
                    except json.JSONDecodeError:
                        logger.warning("Skipping malformed line in %s", f.name)
        return all_trades

    def load_sessions(self, days: int = 30) -> list[dict]:
        """Load recent session summaries."""
        sessions_dir = self.journal_path / "sessions"
        if not sessions_dir.exists():
            return []

        files = sorted(sessions_dir.glob("*.json"), reverse=True)[:days]
        sessions: list[dict] = []
        for f in files:
            try:
                sessions.append(json.loads(f.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                logger.warning("Skipping malformed session file %s", f.name)
        return sessions

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_statistics(self) -> dict:
        """Calculate cumulative stats: win_rate, avg_win, avg_loss,
        profit_factor, score, best_strategy, worst_strategy,
        streak, drawdown, time_of_day_performance, etc.
        """
        trades = self.load_history(days=365)
        if not trades:
            return {
                "total_trades": 0, "wins": 0, "losses": 0,
                "win_rate": 0.0, "avg_win": 0.0, "avg_loss": 0.0,
                "profit_factor": 0.0, "total_score": 0.0,
                "total_pnl": 0.0, "best_strategy": None,
                "worst_strategy": None, "current_streak": 0,
                "max_drawdown": 0.0,
            }

        wins = [t for t in trades if t.get("pnl", 0) > 0]
        losses = [t for t in trades if t.get("pnl", 0) < 0]
        total_score = sum(t.get("score", 0) for t in trades)
        total_pnl = sum(t.get("pnl", 0) for t in trades)

        avg_win = sum(t["pnl"] for t in wins) / len(wins) if wins else 0.0
        avg_loss = sum(t["pnl"] for t in losses) / len(losses) if losses else 0.0

        gross_profit = sum(t["pnl"] for t in wins)
        gross_loss = abs(sum(t["pnl"] for t in losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        # Current streak
        streak = 0
        for t in reversed(trades):
            pnl = t.get("pnl", 0)
            if streak == 0:
                streak = 1 if pnl > 0 else -1
            elif (pnl > 0 and streak > 0) or (pnl < 0 and streak < 0):
                streak += 1 if streak > 0 else -1
            else:
                break

        # Best/worst strategy
        strategy_perf = self.get_strategy_performance()
        best_strat = max(strategy_perf, key=lambda s: strategy_perf[s].get("win_rate", 0),
                         default=None) if strategy_perf else None
        worst_strat = min(strategy_perf, key=lambda s: strategy_perf[s].get("win_rate", 1),
                          default=None) if strategy_perf else None

        # Max drawdown from session records
        sessions = self.load_sessions(days=365)
        cumulative_pnl = 0.0
        peak_pnl = 0.0
        max_dd = 0.0
        for s in sorted(sessions, key=lambda x: x.get("date", "")):
            cumulative_pnl += s.get("net_pnl", 0)
            peak_pnl = max(peak_pnl, cumulative_pnl)
            dd = peak_pnl - cumulative_pnl
            max_dd = max(max_dd, dd)

        return {
            "total_trades": len(trades),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": len(wins) / len(trades) if trades else 0.0,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
            "total_score": total_score,
            "total_pnl": total_pnl,
            "best_strategy": best_strat,
            "worst_strategy": worst_strat,
            "current_streak": streak,
            "max_drawdown": max_dd,
        }

    def get_strategy_performance(self) -> dict[str, dict]:
        """Per-strategy breakdown: win_rate, avg_pnl, trade_count, score."""
        trades = self.load_history(days=365)
        strats: dict[str, list[dict]] = {}
        for t in trades:
            s = t.get("strategy", "unknown")
            strats.setdefault(s, []).append(t)

        result: dict[str, dict] = {}
        for name, tlist in strats.items():
            wins = [t for t in tlist if t.get("pnl", 0) > 0]
            total_pnl = sum(t.get("pnl", 0) for t in tlist)
            total_score = sum(t.get("score", 0) for t in tlist)
            result[name] = {
                "trade_count": len(tlist),
                "wins": len(wins),
                "losses": len(tlist) - len(wins),
                "win_rate": len(wins) / len(tlist) if tlist else 0.0,
                "avg_pnl": total_pnl / len(tlist) if tlist else 0.0,
                "total_pnl": total_pnl,
                "total_score": total_score,
            }
        return result

    def get_symbol_performance(self) -> dict[str, dict]:
        """Per-symbol breakdown: which symbols perform best."""
        trades = self.load_history(days=365)
        syms: dict[str, list[dict]] = {}
        for t in trades:
            s = t.get("symbol", "UNKNOWN")
            syms.setdefault(s, []).append(t)

        result: dict[str, dict] = {}
        for name, tlist in syms.items():
            wins = [t for t in tlist if t.get("pnl", 0) > 0]
            total_pnl = sum(t.get("pnl", 0) for t in tlist)
            result[name] = {
                "trade_count": len(tlist),
                "wins": len(wins),
                "win_rate": len(wins) / len(tlist) if tlist else 0.0,
                "avg_pnl": total_pnl / len(tlist) if tlist else 0.0,
                "total_pnl": total_pnl,
            }
        return result

    def get_market_regime_performance(self) -> dict[str, dict]:
        """Performance in different market conditions (trending, ranging, volatile)."""
        trades = self.load_history(days=365)
        regimes: dict[str, list[dict]] = {}
        for t in trades:
            ctx = t.get("market_context", {})
            regime = ctx.get("regime", "unknown") if isinstance(ctx, dict) else "unknown"
            regimes.setdefault(regime, []).append(t)

        result: dict[str, dict] = {}
        for name, tlist in regimes.items():
            wins = [t for t in tlist if t.get("pnl", 0) > 0]
            total_pnl = sum(t.get("pnl", 0) for t in tlist)
            result[name] = {
                "trade_count": len(tlist),
                "wins": len(wins),
                "win_rate": len(wins) / len(tlist) if tlist else 0.0,
                "avg_pnl": total_pnl / len(tlist) if tlist else 0.0,
                "total_pnl": total_pnl,
            }
        return result

    # ------------------------------------------------------------------
    # Analysis persistence
    # ------------------------------------------------------------------

    def save_analysis(self, key: str, data: Any) -> None:
        """Save analysis results to the analysis directory."""
        file_path = self.journal_path / "analysis" / f"{key}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    def load_analysis(self, key: str) -> Optional[dict]:
        """Load saved analysis results."""
        file_path = self.journal_path / "analysis" / f"{key}.json"
        if not file_path.exists():
            return None
        try:
            return json.loads(file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def calculate_score(trade: dict) -> float:
        """Calculate score for a trade using return-weighted scoring.

        Win:  +0.1 + (return_pct * 10)  -- bigger wins = more points
        Loss: -0.2 - (abs(return_pct) * 10) -- bigger losses = more penalty
        Break-even: 0.0

        ``return_pct`` is expressed as a fraction (e.g. 0.02 for +2%).
        """
        pnl_pct = trade.get("pnl_pct", 0.0)
        if pnl_pct is None:
            pnl_pct = 0.0
        if pnl_pct > 0:  # win
            return 0.1 + (pnl_pct * 10)
        elif pnl_pct < 0:  # loss
            return -0.2 - (abs(pnl_pct) * 10)
        else:
            # Fallback: use pnl sign if pnl_pct is zero but pnl is nonzero
            pnl = trade.get("pnl", 0.0)
            if pnl is None:
                pnl = 0.0
            if pnl > 0:
                return 0.1
            elif pnl < 0:
                return -0.2
            return 0.0

    @staticmethod
    def format_score(trade: dict) -> str:
        """Format a trade's score for display with breakdown.

        Example output:
          Score: +0.1 (base) + 0.216 (return bonus) = +0.316 pts
        """
        pnl_pct = trade.get("pnl_pct", 0.0) or 0.0
        score = trade.get("score", TradingJournal.calculate_score(trade))

        if pnl_pct > 0:
            base = 0.1
            bonus = pnl_pct * 10
            return f"Score: +{base} (base) + {bonus:.3f} (return bonus) = {score:+.3f} pts"
        elif pnl_pct < 0:
            base = -0.2
            penalty = abs(pnl_pct) * 10
            return f"Score: {base} (base) - {penalty:.3f} (loss penalty) = {score:+.3f} pts"
        else:
            return f"Score: {score:+.3f} pts (break-even)"

    @staticmethod
    def _extract_date(timestamp: str) -> str:
        """Extract date string from a timestamp."""
        if not timestamp:
            return date.today().isoformat()
        return timestamp[:10]
