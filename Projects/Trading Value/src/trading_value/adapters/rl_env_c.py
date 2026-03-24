"""Track C: LSTM + Sharpe reward RL environment.

Key differences from Track B (rl_env.py):
- Reward based on rolling Sharpe ratio, not raw PnL
- Observation includes last N returns for LSTM temporal context
- Penalizes volatility of returns, not just drawdown
"""
from __future__ import annotations

import numpy as np

from .rl_env import TradingEnv, Action


class TradingEnvC(TradingEnv):
    """Track C environment: Sharpe-optimized reward with return history.

    Inherits all observation/action logic from Track B.
    Overrides reward computation to optimize Sharpe ratio.
    """

    def __init__(self, *args, sharpe_window: int = 48, **kwargs):
        # Override reward defaults for Track C
        kwargs.setdefault("position_change_penalty", 0.35)
        kwargs.setdefault("holding_cost", 0.001)
        kwargs.setdefault("profitable_hold_bonus_max", 0.01)
        kwargs.setdefault("profitable_close_bonus", 0.1)
        kwargs.setdefault("drawdown_penalty_factor", 0.0)  # replaced by Sharpe penalty
        super().__init__(*args, **kwargs)
        self.sharpe_window = sharpe_window
        self._return_history: list[float] = []
        self._prev_balance: float = self.initial_balance

    def reset(self, seed=None, options=None):
        obs, info = super().reset(seed=seed, options=options)
        self._return_history = []
        self._prev_balance = self.initial_balance
        return obs, info

    def step(self, action: int):
        obs, reward_base, terminated, truncated, info = super().step(action)

        # Track bar-level return
        current_balance = self._balance
        bar_return = (current_balance - self._prev_balance) / max(self._prev_balance, 1.0)
        self._prev_balance = current_balance
        self._return_history.append(bar_return)

        # Replace drawdown penalty with Sharpe-based reward shaping
        reward = reward_base  # base already has PnL components

        # Rolling Sharpe component (updated every bar)
        if len(self._return_history) >= self.sharpe_window:
            recent = np.array(self._return_history[-self.sharpe_window:])
            mean_r = np.mean(recent)
            std_r = np.std(recent)
            if std_r > 0:
                rolling_sharpe = mean_r / std_r
                # Reward for positive Sharpe, penalize negative
                reward += 0.05 * np.clip(rolling_sharpe, -2.0, 2.0)
            else:
                # Zero volatility = flat, slight penalty for inaction
                if self._position == 0:
                    reward -= 0.001

        # Volatility penalty: penalize high variance of recent returns
        if len(self._return_history) >= 20:
            recent_vol = np.std(self._return_history[-20:])
            reward -= 0.5 * recent_vol  # penalize volatile equity curve

        # Consistency bonus: reward streaks of positive bars
        if len(self._return_history) >= 5:
            last_5 = self._return_history[-5:]
            positive_streak = sum(1 for r in last_5 if r > 0)
            if positive_streak >= 4:
                reward += 0.02  # bonus for consistent gains

        info["rolling_sharpe"] = (
            np.mean(self._return_history[-self.sharpe_window:]) /
            max(np.std(self._return_history[-self.sharpe_window:]), 1e-8)
            if len(self._return_history) >= self.sharpe_window else 0.0
        )

        return obs, float(reward), terminated, truncated, info
