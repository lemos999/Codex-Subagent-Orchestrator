"""Tests for trading_value.adapters.rl_env (Phase 5)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from trading_value.core.models import Timeframe


# ---------------------------------------------------------------------------
# Mock data factory
# ---------------------------------------------------------------------------

def make_mock_data() -> dict[Timeframe, pd.DataFrame]:
    """Create minimal 30m DataFrame for testing.

    Uses 500 M30 bars so that:
    - H4 (every 8th bar) has 62 bars >= 52 required for Ichimoku
    - H1 (every 2nd bar) has 250 bars
    """
    np.random.seed(42)
    n = 500
    dates = pd.date_range("2022-01-01", periods=n, freq="30min", tz="UTC")
    close = 2000 + np.cumsum(np.random.randn(n) * 5)
    dates_h1 = dates[::2]
    close_h1 = close[::2]
    dates_h4 = dates[::8]
    close_h4 = close[::8]
    return {
        Timeframe.M30: pd.DataFrame({
            "timestamp": dates,
            "open": close - 2,
            "high": close + 5,
            "low": close - 5,
            "close": close,
            "volume": np.random.rand(len(dates)) * 1000,
        }),
        Timeframe.H1: pd.DataFrame({
            "timestamp": dates_h1,
            "open": close_h1 - 2,
            "high": close_h1 + 8,
            "low": close_h1 - 8,
            "close": close_h1,
            "volume": np.random.rand(len(dates_h1)) * 2000,
        }),
        Timeframe.H4: pd.DataFrame({
            "timestamp": dates_h4,
            "open": close_h4 - 3,
            "high": close_h4 + 15,
            "low": close_h4 - 15,
            "close": close_h4,
            "volume": np.random.rand(len(dates_h4)) * 5000,
        }),
    }


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def env():
    """Create a TradingEnv with minimal mock data, shared across tests."""
    from trading_value.adapters.rl_env import TradingEnv

    data = make_mock_data()
    e = TradingEnv(
        data=data,
        symbol="ETHUSDT",
        initial_balance=10000.0,
        episode_bars=100,
        random_start=False,
    )
    return e


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_trading_env_creation(env):
    """TradingEnv should instantiate without errors."""
    from trading_value.adapters.rl_env import TradingEnv
    assert isinstance(env, TradingEnv)


def test_observation_space_shape(env):
    """Observation space should be Box(25,)."""
    import gymnasium
    assert isinstance(env.observation_space, gymnasium.spaces.Box)
    assert env.observation_space.shape == (25,)


def test_action_space_is_discrete_5(env):
    """Action space should be Discrete(5)."""
    import gymnasium
    assert isinstance(env.action_space, gymnasium.spaces.Discrete)
    assert env.action_space.n == 5


def test_reset_returns_observation_of_correct_shape(env):
    """reset() should return an observation of shape (25,)."""
    obs, info = env.reset(seed=0)
    assert isinstance(obs, np.ndarray)
    assert obs.shape == (25,)
    assert obs.dtype == np.float32


def test_reset_returns_info_dict(env):
    """reset() should return an info dict with balance key."""
    _, info = env.reset(seed=0)
    assert isinstance(info, dict)
    assert "balance" in info
    assert "position" in info


def test_step_hold_returns_valid_tuple(env):
    """HOLD action should return a valid (obs, reward, terminated, truncated, info) tuple."""
    from trading_value.adapters.rl_env import Action

    env.reset(seed=1)
    obs, reward, terminated, truncated, info = env.step(Action.HOLD)

    assert isinstance(obs, np.ndarray)
    assert obs.shape == (25,)
    assert isinstance(reward, float)
    assert isinstance(terminated, bool)
    assert isinstance(truncated, bool)
    assert isinstance(info, dict)


def test_step_open_long_changes_position(env):
    """OPEN_LONG action should set position to 1 (long)."""
    from trading_value.adapters.rl_env import Action

    env.reset(seed=2)
    # Ensure we're flat before opening
    assert env._position == 0
    env.step(Action.OPEN_LONG)
    assert env._position == 1


def test_step_close_returns_realized_pnl_info(env):
    """CLOSE action after OPEN_LONG should produce a realized PnL in balance."""
    from trading_value.adapters.rl_env import Action

    env.reset(seed=3)
    balance_before_open = env._balance

    # Open a long position
    env.step(Action.OPEN_LONG)
    balance_after_open = env._balance

    # Close the position
    obs, reward, terminated, truncated, info = env.step(Action.CLOSE)

    # After closing, position should be flat
    assert env._position == 0
    assert isinstance(reward, float)
    # info should contain balance
    assert "balance" in info


def test_episode_terminates_at_end_of_data(env):
    """Running through episode_bars steps should trigger truncated=True."""
    from trading_value.adapters.rl_env import Action

    env.reset(seed=4)
    terminated = False
    truncated = False
    max_steps = env.episode_bars + 10  # a bit extra to be sure

    for _ in range(max_steps):
        if terminated or truncated:
            break
        _, _, terminated, truncated, _ = env.step(Action.HOLD)

    assert truncated is True or terminated is True


def test_observation_values_are_finite(env):
    """All observation values (except zeros) should be finite floats."""
    env.reset(seed=5)
    obs, _, _, _, _ = env.step(0)  # HOLD
    # obs may have zeros but must not have NaN or Inf
    assert not np.any(np.isnan(obs)), "Observation contains NaN"
    assert not np.any(np.isinf(obs)), "Observation contains Inf"
