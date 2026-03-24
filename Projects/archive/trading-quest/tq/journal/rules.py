"""Dynamic rules learned from journal analysis.
Rules are automatically generated and updated based on trade outcomes.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from tq.journal.analyzer import TradeAnalyzer

logger = logging.getLogger(__name__)


class TradingRules:
    """Dynamic rules learned from journal analysis.
    Rules are automatically generated and updated based on trade outcomes.
    """

    RULES_PATH = Path(".tq-journal/analysis/rules.json")

    def __init__(self, rules_path: Optional[Path] = None):
        self.rules_path = rules_path or self.RULES_PATH
        self.rules: list[dict] = self._load_rules()

    def _load_rules(self) -> list[dict]:
        """Load rules from disk."""
        if not self.rules_path.exists():
            return []
        try:
            data = json.loads(self.rules_path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else data.get("rules", [])
        except (json.JSONDecodeError, OSError):
            return []

    def _save_rules(self) -> None:
        """Persist rules to disk."""
        self.rules_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.rules_path, "w", encoding="utf-8") as f:
            json.dump(self.rules, f, indent=2, default=str)

    def check_entry(self, symbol: str, strategy: str, regime: str,
                    indicators: dict) -> tuple[bool, str]:
        """Check if a trade entry is allowed by learned rules.
        Returns (allowed, reason).
        """
        for rule in self.rules:
            if not rule.get("active", True):
                continue

            rule_type = rule.get("type", "")

            # Block strategy in specific regime
            if rule_type == "block_strategy_regime":
                if (rule.get("strategy") == strategy and
                        rule.get("regime") == regime):
                    return False, rule.get("reason", "Blocked by learned rule")

            # Block symbol
            if rule_type == "block_symbol":
                if rule.get("symbol") == symbol:
                    return False, rule.get("reason", "Symbol blocked")

            # Conservative mode
            if rule_type == "conservative_mode":
                # Only allow high-confidence entries
                confidence = indicators.get("confidence", 0)
                if confidence < rule.get("min_confidence", 0.7):
                    return False, (
                        f"Conservative mode active: confidence {confidence:.2f} "
                        f"below threshold {rule.get('min_confidence', 0.7)}"
                    )

            # Block strategy globally
            if rule_type == "block_strategy":
                if rule.get("strategy") == strategy:
                    return False, rule.get("reason", "Strategy blocked")

        return True, "OK"

    def update_rules(self, analyzer: "TradeAnalyzer") -> None:
        """Auto-generate rules from analyzer insights."""
        new_rules: list[dict] = []

        strat_perf = analyzer.journal.get_strategy_performance()
        regime_perf = analyzer.journal.get_market_regime_performance()
        stats = analyzer.journal.get_statistics()

        # Rule: block strategies with <50% win rate and >= 5 trades
        for name, perf in strat_perf.items():
            if perf["trade_count"] >= 5 and perf["win_rate"] < 0.50:
                new_rules.append({
                    "type": "block_strategy",
                    "strategy": name,
                    "reason": (
                        f"Strategy '{name}' has {perf['win_rate']:.0%} win rate "
                        f"over {perf['trade_count']} trades (below 50% threshold)"
                    ),
                    "active": True,
                })

        # Rule: block symbols with negative expectancy
        sym_perf = analyzer.journal.get_symbol_performance()
        for sym, perf in sym_perf.items():
            if perf["trade_count"] >= 5 and perf["avg_pnl"] < 0:
                new_rules.append({
                    "type": "block_symbol",
                    "symbol": sym,
                    "reason": (
                        f"Symbol '{sym}' has negative avg PnL "
                        f"({perf['avg_pnl']:.2f}) over {perf['trade_count']} trades"
                    ),
                    "active": True,
                })

        # Rule: conservative mode if score is negative for 3+ sessions
        sessions = analyzer.journal.load_sessions(days=5)
        if len(sessions) >= 3:
            recent_scores = [s.get("score", 0) for s in sessions[:3]]
            if all(s < 0 for s in recent_scores):
                new_rules.append({
                    "type": "conservative_mode",
                    "min_confidence": 0.7,
                    "reason": "Negative score for 3+ consecutive sessions",
                    "active": True,
                })

        self.rules = new_rules
        self._save_rules()
        logger.info("Updated %d trading rules", len(self.rules))

    def format_rules(self) -> str:
        """Format rules for display."""
        if not self.rules:
            return "No active trading rules."
        lines = [f"Active Trading Rules ({len(self.rules)}):"]
        for i, rule in enumerate(self.rules, 1):
            status = "ACTIVE" if rule.get("active", True) else "INACTIVE"
            lines.append(f"  {i}. [{status}] {rule.get('reason', rule.get('type', 'unknown'))}")
        return "\n".join(lines)
