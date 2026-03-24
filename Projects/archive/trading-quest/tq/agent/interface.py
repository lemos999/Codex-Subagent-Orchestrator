"""Agent interface -- step-based environment for AI agents."""
from __future__ import annotations

import logging
from typing import Any, Optional

from tq.quest.engine import QuestEngine

logger = logging.getLogger(__name__)


class AgentInterface:
    """Step-based environment for AI trading agents.

    Provides a gym-like interface: reset() -> observation, step(action) -> (obs, reward, done, info).
    """

    def __init__(self, quest_id: str = "agent-quest",
                 market: str = "US",
                 symbols: Optional[list[str]] = None,
                 initial_capital: float = 100_000.0):
        self.quest_id = quest_id
        self.market = market
        self.symbols = symbols or ["AAPL", "MSFT"]
        self.initial_capital = initial_capital
        self.engine: Optional[QuestEngine] = None
        self._step_count = 0
        self._done = False

    def reset(self, start_date: str = "2024-01-01",
              strategy_name: str = "ma_crossover") -> dict:
        """Reset the environment and return initial observation."""
        self.engine = QuestEngine(
            quest_id=self.quest_id,
            market=self.market,
            symbols=self.symbols,
            initial_capital=self.initial_capital,
        )
        self.engine.start_quest(start_date, strategy_name)
        self._step_count = 0
        self._done = False
        return self.engine.get_observation()

    def step(self, action: dict) -> tuple[dict, float, bool, dict]:
        """Take an action and return (observation, reward, done, info).

        Actions:
            {"type": "hold"} -- do nothing
            {"type": "buy", "symbol": str, "qty": float}
            {"type": "sell", "symbol": str, "qty": float}
            {"type": "set_strategy", "name": str}
            {"type": "advance_day"}
        """
        if self._done or self.engine is None:
            return {}, 0.0, True, {"error": "Episode is done. Call reset()."}

        reward = 0.0
        info: dict[str, Any] = {}

        action_type = action.get("type", "hold")

        if action_type == "buy":
            symbol = action.get("symbol", self.symbols[0])
            qty = action.get("qty", 1)
            self.engine.submit_order(symbol, "BUY", qty)
            info["action"] = f"BUY {qty} {symbol}"

        elif action_type == "sell":
            symbol = action.get("symbol", self.symbols[0])
            qty = action.get("qty", 1)
            self.engine.submit_order(symbol, "SELL", qty)
            info["action"] = f"SELL {qty} {symbol}"

        elif action_type == "set_strategy":
            name = action.get("name", "ma_crossover")
            try:
                self.engine.set_strategy(name)
                info["action"] = f"Strategy set to {name}"
            except KeyError:
                info["error"] = f"Unknown strategy: {name}"

        elif action_type == "advance_day":
            from datetime import date, timedelta
            if self.engine.state:
                current = date.fromisoformat(self.engine.state.current_date)
                result = self.engine.auto_run_day(current)
                reward = result.get("score", 0)
                info["day_result"] = result
                self.engine.state.current_date = (current + timedelta(days=1)).isoformat()

        elif action_type == "hold":
            info["action"] = "hold"

        self._step_count += 1
        obs = self.engine.get_observation()

        # Check done conditions
        if self.engine.broker.pnl.current_drawdown() > 0.30:
            self._done = True
            info["done_reason"] = "max_drawdown_exceeded"
        elif self._step_count >= 1000:
            self._done = True
            info["done_reason"] = "max_steps"

        return obs, reward, self._done, info

    def get_available_actions(self) -> list[str]:
        """List available action types."""
        return ["hold", "buy", "sell", "set_strategy", "advance_day"]

    def get_state(self) -> dict:
        """Get current state summary."""
        if self.engine:
            return self.engine.get_observation()
        return {}
