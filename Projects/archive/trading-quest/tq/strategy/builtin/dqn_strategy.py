"""DQN reinforcement learning trading strategy."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from tq.strategy.base import BaseStrategy
from tq.strategy.registry import strategy
from tq.strategy.ml.features import FeatureEngineering
from tq.strategy.ml.dqn_agent import DQNAgent, TradingEnvironment

logger = logging.getLogger(__name__)

_MODELS_DIR = Path("models") / "dqn"


@strategy("dqn")
class DQNStrategy(BaseStrategy):
    """DQN reinforcement learning trading agent.

    Auto-trains on first invocation, retrains every *retrain_days* calls.
    """

    name = "dqn"
    description = "DQN reinforcement learning trading agent"

    def __init__(
        self,
        episodes: int = 50,
        hidden_size: int = 64,
        retrain_days: int = 100,
    ):
        self.episodes = episodes
        self.hidden_size = hidden_size
        self.retrain_days = retrain_days

        self.feat_eng = FeatureEngineering()
        self._symbol_agents: dict[str, DQNAgent] = {}
        self._days_since_train = 0

    # -----------------------------------------------------------------
    # BaseStrategy interface
    # -----------------------------------------------------------------

    def decide(self, data: pd.DataFrame, portfolio: Any) -> list[dict]:
        symbol = (
            data.attrs.get("symbol", "UNKNOWN") if hasattr(data, "attrs") else "UNKNOWN"
        )

        if len(data) < self.feat_eng.MIN_ROWS + 10:
            return []

        agent = self._ensure_trained(symbol, data)
        if agent is None:
            return []

        # Build feature vector for the latest step
        feat_df = self.feat_eng.build_features(data)
        if feat_df.empty:
            return []

        feat_vec = feat_df.values[-1]
        # Append position flag (assume no position info -> 0)
        state = _append_pos_flag(feat_vec, 0.0)

        action = agent.act_greedy(state)
        self._days_since_train += 1

        signals: list[dict] = []
        if action == TradingEnvironment.BUY:
            signals.append({
                "symbol": symbol,
                "side": "BUY",
                "qty": 1,
                "confidence": 0.6,
                "reason": "DQN agent: BUY",
            })
        elif action == TradingEnvironment.SELL:
            signals.append({
                "symbol": symbol,
                "side": "SELL",
                "qty": 1,
                "confidence": 0.6,
                "reason": "DQN agent: SELL",
            })
        return signals

    def get_params(self) -> dict:
        return {
            "episodes": self.episodes,
            "hidden_size": self.hidden_size,
            "retrain_days": self.retrain_days,
        }

    # -----------------------------------------------------------------
    # Training helpers
    # -----------------------------------------------------------------

    def _ensure_trained(
        self, symbol: str, data: pd.DataFrame
    ) -> DQNAgent | None:
        agent = self._symbol_agents.get(symbol)

        needs_train = (
            agent is None or self._days_since_train >= self.retrain_days
        )
        if not needs_train:
            return agent

        # Try loading saved agent
        model_dir = _MODELS_DIR / symbol
        if agent is None and model_dir.exists() and (model_dir / "meta.json").exists():
            try:
                feat_df = self.feat_eng.build_features(data)
                state_size = feat_df.shape[1] + 1  # +1 for position flag
                agent = DQNAgent(
                    state_size=state_size, hidden_size=self.hidden_size
                )
                agent.load(model_dir)
                self._symbol_agents[symbol] = agent
                self._days_since_train = 0
                logger.info("Loaded saved DQN agent for %s", symbol)
                return agent
            except Exception as e:
                logger.warning("Failed to load DQN agent for %s: %s", symbol, e)

        return self._train_agent(symbol, data)

    def _train_agent(
        self, symbol: str, data: pd.DataFrame
    ) -> DQNAgent | None:
        try:
            feat_df = self.feat_eng.build_features(data)
            if len(feat_df) < 30:
                logger.warning("Insufficient data to train DQN for %s", symbol)
                return None

            env = TradingEnvironment(data, feat_df, initial_cash=100_000.0)
            agent = DQNAgent(
                state_size=env.state_size,
                hidden_size=self.hidden_size,
            )
            rewards = agent.train(env, episodes=self.episodes)
            agent.epsilon = agent.epsilon_min  # inference mode

            avg_reward = sum(rewards[-10:]) / max(len(rewards[-10:]), 1)
            logger.info(
                "Trained DQN for %s: %d episodes, avg_reward(last10)=%.4f",
                symbol, self.episodes, avg_reward,
            )

            model_dir = _MODELS_DIR / symbol
            agent.save(model_dir)

            self._symbol_agents[symbol] = agent
            self._days_since_train = 0
            return agent
        except Exception as e:
            logger.warning("DQN training failed for %s: %s", symbol, e)
            return None


def _append_pos_flag(feat, position: float):
    """Append a position flag to the feature vector."""
    import numpy as np
    flag = np.array([1.0 if position > 0 else 0.0])
    return np.concatenate([feat, flag])
