"""DQN (Deep Q-Network) reinforcement learning agent for trading.

Implemented entirely in numpy -- no PyTorch, TensorFlow, or gymnasium
dependency required.
"""
from __future__ import annotations

import json
import logging
import random
from collections import deque
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# =====================================================================
# Trading environment (Gym-like interface)
# =====================================================================

class TradingEnvironment:
    """OpenAI Gym-like trading environment.

    State : feature vector from FeatureEngineering + position flag
    Actions: 0 = HOLD, 1 = BUY, 2 = SELL
    Reward : step-wise portfolio return (realised + unrealised).
    """

    HOLD, BUY, SELL = 0, 1, 2

    def __init__(
        self,
        data: pd.DataFrame,
        features: pd.DataFrame,
        initial_cash: float = 100_000.0,
    ):
        # Align data and features on common index
        common = data.index.intersection(features.index)
        self.data = data.loc[common]
        self.features = features.loc[common].values.astype(np.float64)
        self.initial_cash = initial_cash

        cols = {c.lower(): c for c in self.data.columns}
        self._close_col = cols.get("close", "close")

        self.n_steps = len(self.data)
        self.state_size = self.features.shape[1] + 1  # +1 for position flag

        # Episode state
        self._step = 0
        self._cash = initial_cash
        self._position = 0.0  # shares held
        self._prev_portfolio_value = initial_cash

    # -----------------------------------------------------------------

    def reset(self) -> np.ndarray:
        """Reset and return initial observation."""
        self._step = 0
        self._cash = self.initial_cash
        self._position = 0.0
        self._prev_portfolio_value = self.initial_cash
        return self._get_obs()

    def step(self, action: int) -> tuple[np.ndarray, float, bool, dict]:
        """Execute one step. Returns (obs, reward, done, info)."""
        price = float(self.data.iloc[self._step][self._close_col])

        # Execute action
        if action == self.BUY and self._position == 0.0 and price > 0:
            shares = int(self._cash * 0.95 / price)  # 95% of cash
            if shares > 0:
                self._position = float(shares)
                self._cash -= shares * price
        elif action == self.SELL and self._position > 0:
            self._cash += self._position * price
            self._position = 0.0

        self._step += 1
        done = self._step >= self.n_steps - 1

        # Current portfolio value
        if not done:
            new_price = float(self.data.iloc[self._step][self._close_col])
        else:
            new_price = price
        portfolio_value = self._cash + self._position * new_price

        # Reward = % change in portfolio value
        reward = (portfolio_value - self._prev_portfolio_value) / max(
            self._prev_portfolio_value, 1e-8
        )
        self._prev_portfolio_value = portfolio_value

        info = {
            "portfolio_value": portfolio_value,
            "cash": self._cash,
            "position": self._position,
            "price": new_price if not done else price,
        }
        obs = self._get_obs() if not done else np.zeros(self.state_size)
        return obs, reward, done, info

    # -----------------------------------------------------------------

    def _get_obs(self) -> np.ndarray:
        feat = self.features[self._step]
        pos_flag = np.array([1.0 if self._position > 0 else 0.0])
        return np.concatenate([feat, pos_flag])


# =====================================================================
# Simple neural network (pure numpy)
# =====================================================================

class SimpleNN:
    """Minimal feed-forward network with two hidden layers + ReLU.

    Used as Q-function approximator for DQN.
    """

    def __init__(self, input_size: int, hidden_size: int, output_size: int):
        rng = np.random.RandomState(42)
        scale1 = np.sqrt(2.0 / input_size)
        scale2 = np.sqrt(2.0 / hidden_size)
        scale3 = np.sqrt(2.0 / hidden_size)

        self.W1 = rng.randn(input_size, hidden_size).astype(np.float64) * scale1
        self.b1 = np.zeros(hidden_size, dtype=np.float64)
        self.W2 = rng.randn(hidden_size, hidden_size).astype(np.float64) * scale2
        self.b2 = np.zeros(hidden_size, dtype=np.float64)
        self.W3 = rng.randn(hidden_size, output_size).astype(np.float64) * scale3
        self.b3 = np.zeros(output_size, dtype=np.float64)

    def forward(self, x: np.ndarray) -> np.ndarray:
        """Forward pass. *x* shape: (batch, input_size) or (input_size,)."""
        single = x.ndim == 1
        if single:
            x = x.reshape(1, -1)
        self._z1 = x @ self.W1 + self.b1
        self._a1 = np.maximum(0, self._z1)
        self._z2 = self._a1 @ self.W2 + self.b2
        self._a2 = np.maximum(0, self._z2)
        self._z3 = self._a2 @ self.W3 + self.b3
        out = self._z3
        if single:
            out = out.ravel()
        self._input = x
        return out

    def update(self, target: np.ndarray, lr: float) -> float:
        """Single backward pass with MSE loss.  *target* must match last
        forward output shape. Returns scalar loss."""
        single = target.ndim == 1
        if single:
            target = target.reshape(1, -1)

        pred = self._z3
        n = pred.shape[0]
        loss = float(np.mean((pred - target) ** 2))

        # Gradient of MSE
        d3 = 2 * (pred - target) / n
        np.clip(d3, -5, 5, out=d3)

        dW3 = self._a2.T @ d3
        db3 = d3.sum(axis=0)

        d2 = (d3 @ self.W3.T) * (self._z2 > 0).astype(float)
        dW2 = self._a1.T @ d2
        db2 = d2.sum(axis=0)

        d1 = (d2 @ self.W2.T) * (self._z1 > 0).astype(float)
        dW1 = self._input.T @ d1
        db1 = d1.sum(axis=0)

        for dW in (dW1, dW2, dW3, db1, db2, db3):
            np.clip(dW, -5, 5, out=dW)

        self.W1 -= lr * dW1
        self.b1 -= lr * db1
        self.W2 -= lr * dW2
        self.b2 -= lr * db2
        self.W3 -= lr * dW3
        self.b3 -= lr * db3
        return loss

    def copy_from(self, other: SimpleNN) -> None:
        """Copy weights from *other* network (target network sync)."""
        self.W1 = other.W1.copy()
        self.b1 = other.b1.copy()
        self.W2 = other.W2.copy()
        self.b2 = other.b2.copy()
        self.W3 = other.W3.copy()
        self.b3 = other.b3.copy()


# =====================================================================
# DQN Agent
# =====================================================================

class DQNAgent:
    """Deep Q-Network agent for trading decisions."""

    def __init__(
        self,
        state_size: int,
        action_size: int = 3,
        hidden_size: int = 64,
        lr: float = 0.001,
        gamma: float = 0.99,
        epsilon: float = 1.0,
        epsilon_min: float = 0.01,
        epsilon_decay: float = 0.995,
        memory_size: int = 2000,
        target_update_freq: int = 10,
    ):
        self.state_size = state_size
        self.action_size = action_size
        self.hidden_size = hidden_size
        self.lr = lr
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay
        self.target_update_freq = target_update_freq

        self.q_network = SimpleNN(state_size, hidden_size, action_size)
        self.target_network = SimpleNN(state_size, hidden_size, action_size)
        self.target_network.copy_from(self.q_network)

        self.memory: deque = deque(maxlen=memory_size)
        self._train_step = 0

    # -----------------------------------------------------------------

    def act(self, state: np.ndarray) -> int:
        """Epsilon-greedy action selection."""
        if random.random() < self.epsilon:
            return random.randint(0, self.action_size - 1)
        q_values = self.q_network.forward(state)
        return int(np.argmax(q_values))

    def act_greedy(self, state: np.ndarray) -> int:
        """Greedy action (no exploration)."""
        q_values = self.q_network.forward(state)
        return int(np.argmax(q_values))

    def remember(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        next_state: np.ndarray,
        done: bool,
    ) -> None:
        self.memory.append((state, action, reward, next_state, done))

    def replay(self, batch_size: int = 32) -> float:
        """Train on a random mini-batch from the replay buffer.

        Returns the average loss.
        """
        if len(self.memory) < batch_size:
            return 0.0

        batch = random.sample(list(self.memory), batch_size)
        states = np.array([t[0] for t in batch])
        actions = np.array([t[1] for t in batch])
        rewards = np.array([t[2] for t in batch])
        next_states = np.array([t[3] for t in batch])
        dones = np.array([t[4] for t in batch], dtype=float)

        # Current Q values
        current_q = self.q_network.forward(states)

        # Target Q values
        next_q = self.target_network.forward(next_states)
        max_next_q = np.max(next_q, axis=1)
        target_q = current_q.copy()
        for i in range(batch_size):
            target_q[i, actions[i]] = rewards[i] + (1 - dones[i]) * self.gamma * max_next_q[i]

        # Re-forward to set internal state for backward pass
        self.q_network.forward(states)
        loss = self.q_network.update(target_q, self.lr)

        # Decay epsilon
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

        # Periodic target network sync
        self._train_step += 1
        if self._train_step % self.target_update_freq == 0:
            self.target_network.copy_from(self.q_network)

        return loss

    def train(
        self,
        env: TradingEnvironment,
        episodes: int = 100,
        batch_size: int = 32,
    ) -> list[float]:
        """Train the agent on the trading environment.

        Returns a list of total rewards per episode.
        """
        episode_rewards: list[float] = []

        for ep in range(episodes):
            state = env.reset()
            total_reward = 0.0
            done = False

            while not done:
                action = self.act(state)
                next_state, reward, done, info = env.step(action)
                self.remember(state, action, reward, next_state, done)
                self.replay(batch_size)
                state = next_state
                total_reward += reward

            episode_rewards.append(total_reward)
            if (ep + 1) % 10 == 0:
                logger.info(
                    "DQN episode %d/%d: reward=%.4f, eps=%.3f",
                    ep + 1, episodes, total_reward, self.epsilon,
                )

        return episode_rewards

    # -----------------------------------------------------------------
    # Persistence
    # -----------------------------------------------------------------

    def save(self, path: Path) -> None:
        """Save agent to *path* directory."""
        path.mkdir(parents=True, exist_ok=True)
        for name, net in [("q", self.q_network), ("target", self.target_network)]:
            np.save(str(path / f"{name}_W1.npy"), net.W1)
            np.save(str(path / f"{name}_b1.npy"), net.b1)
            np.save(str(path / f"{name}_W2.npy"), net.W2)
            np.save(str(path / f"{name}_b2.npy"), net.b2)
            np.save(str(path / f"{name}_W3.npy"), net.W3)
            np.save(str(path / f"{name}_b3.npy"), net.b3)
        meta = {
            "state_size": self.state_size,
            "action_size": self.action_size,
            "hidden_size": self.hidden_size,
            "lr": self.lr,
            "gamma": self.gamma,
            "epsilon": self.epsilon,
            "epsilon_min": self.epsilon_min,
            "epsilon_decay": self.epsilon_decay,
        }
        (path / "meta.json").write_text(json.dumps(meta))

    def load(self, path: Path) -> None:
        """Load agent from *path* directory."""
        meta = json.loads((path / "meta.json").read_text())
        self.state_size = meta["state_size"]
        self.action_size = meta["action_size"]
        self.hidden_size = meta["hidden_size"]
        self.epsilon = meta.get("epsilon", self.epsilon_min)

        self.q_network = SimpleNN(self.state_size, self.hidden_size, self.action_size)
        self.target_network = SimpleNN(self.state_size, self.hidden_size, self.action_size)

        for name, net in [("q", self.q_network), ("target", self.target_network)]:
            net.W1 = np.load(str(path / f"{name}_W1.npy"))
            net.b1 = np.load(str(path / f"{name}_b1.npy"))
            net.W2 = np.load(str(path / f"{name}_W2.npy"))
            net.b2 = np.load(str(path / f"{name}_b2.npy"))
            net.W3 = np.load(str(path / f"{name}_W3.npy"))
            net.b3 = np.load(str(path / f"{name}_b3.npy"))
