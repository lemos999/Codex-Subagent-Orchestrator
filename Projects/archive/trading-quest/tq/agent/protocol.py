"""Agent communication protocol -- structured request/response."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class QuestRequest:
    """Structured request from quest engine to agent."""
    action: str  # "decide", "configure", "evaluate"
    observation: dict = field(default_factory=dict)
    available_symbols: list[str] = field(default_factory=list)
    available_strategies: list[str] = field(default_factory=list)
    constraints: dict = field(default_factory=dict)
    context: str = ""

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "observation": self.observation,
            "available_symbols": self.available_symbols,
            "available_strategies": self.available_strategies,
            "constraints": self.constraints,
            "context": self.context,
        }


@dataclass
class QuestResponse:
    """Structured response from agent to quest engine."""
    action_type: str = "hold"  # "hold", "buy", "sell", "set_strategy"
    symbol: str = ""
    qty: float = 0.0
    strategy_name: str = ""
    reasoning: str = ""
    confidence: float = 0.0
    metadata: dict = field(default_factory=dict)

    def to_action(self) -> dict:
        """Convert to action dict for AgentInterface.step()."""
        action = {"type": self.action_type}
        if self.action_type in ("buy", "sell"):
            action["symbol"] = self.symbol
            action["qty"] = self.qty
        elif self.action_type == "set_strategy":
            action["name"] = self.strategy_name
        return action

    def to_dict(self) -> dict:
        return {
            "action_type": self.action_type,
            "symbol": self.symbol,
            "qty": self.qty,
            "strategy_name": self.strategy_name,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


def format_quest_prompt(request: QuestRequest) -> str:
    """Format a quest request as a natural language prompt for an LLM agent."""
    obs = request.observation
    lines = [
        f"## Trading Quest - {request.action.upper()}",
        "",
        f"**Phase**: {obs.get('phase', '?')} | **Day**: {obs.get('day', '?')}",
        f"**Portfolio Value**: ${obs.get('portfolio_value', 0):,.2f}",
        f"**Cash**: ${obs.get('cash', 0):,.2f}",
        f"**Drawdown**: {obs.get('drawdown', 0):.2%}",
        f"**Score**: {obs.get('total_score', 0):,.0f}",
        "",
    ]

    if obs.get("positions"):
        lines.append("**Positions**:")
        for sym, pos in obs["positions"].items():
            lines.append(f"  - {sym}: {pos.get('qty', 0)} shares @ ${pos.get('avg_price', 0):,.2f}")
        lines.append("")

    if request.available_symbols:
        lines.append(f"**Available Symbols**: {', '.join(request.available_symbols[:20])}")
    if request.available_strategies:
        lines.append(f"**Available Strategies**: {', '.join(request.available_strategies)}")

    if request.constraints:
        lines.append("")
        lines.append("**Constraints**:")
        for k, v in request.constraints.items():
            lines.append(f"  - {k}: {v}")

    if request.context:
        lines.append("")
        lines.append(f"**Context**: {request.context}")

    lines.extend([
        "",
        "Respond with one of: HOLD, BUY <symbol> <qty>, SELL <symbol> <qty>, STRATEGY <name>",
    ])

    return "\n".join(lines)
