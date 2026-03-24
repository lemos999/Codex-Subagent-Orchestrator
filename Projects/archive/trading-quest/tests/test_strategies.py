"""Tests for strategy registry and built-in strategies."""
import unittest

import numpy as np
import pandas as pd

from tq.strategy.registry import list_all, get, auto_discover, get_strategy
from tq.strategy.base import BaseStrategy


class TestRegistry(unittest.TestCase):

    def test_auto_discover(self):
        auto_discover()
        strategies = list_all()
        self.assertGreaterEqual(len(strategies), 13)

    def test_list_all_has_ma_crossover(self):
        strategies = list_all()
        self.assertIn("ma_crossover", strategies)

    def test_list_all_has_rsi(self):
        strategies = list_all()
        self.assertIn("rsi", strategies)

    def test_list_all_has_macd(self):
        strategies = list_all()
        self.assertIn("macd", strategies)

    def test_list_all_has_bollinger(self):
        strategies = list_all()
        self.assertIn("bollinger", strategies)

    def test_list_all_has_momentum(self):
        strategies = list_all()
        self.assertIn("momentum", strategies)

    def test_list_all_has_vwap(self):
        strategies = list_all()
        self.assertIn("vwap", strategies)

    def test_list_all_has_ichimoku(self):
        strategies = list_all()
        self.assertIn("ichimoku", strategies)

    def test_list_all_has_supertrend(self):
        strategies = list_all()
        self.assertIn("supertrend", strategies)

    def test_list_all_has_donchian(self):
        strategies = list_all()
        self.assertIn("donchian", strategies)

    def test_list_all_has_mean_reversion(self):
        strategies = list_all()
        self.assertIn("mean_reversion", strategies)

    def test_list_all_has_volume_breakout(self):
        strategies = list_all()
        self.assertIn("volume_breakout", strategies)

    def test_list_all_has_stochastic(self):
        strategies = list_all()
        self.assertIn("stochastic", strategies)

    def test_list_all_has_multi_tf(self):
        strategies = list_all()
        self.assertIn("multi_tf", strategies)

    def test_get_strategy(self):
        strat = get_strategy("ma_crossover")
        self.assertIsInstance(strat, BaseStrategy)

    def test_get_unknown_strategy(self):
        with self.assertRaises(KeyError):
            get("nonexistent_strategy_xyz")

    def test_strategy_count_at_least_13(self):
        strategies = list_all()
        self.assertGreaterEqual(len(strategies), 13)


class TestBuiltinStrategies(unittest.TestCase):
    """Test that each strategy can decide() without crashing."""

    def _sample_data(self, n=100):
        np.random.seed(42)
        dates = pd.date_range("2024-01-01", periods=n, freq="D")
        close = 100 + np.cumsum(np.random.randn(n))
        return pd.DataFrame({
            "open": close - abs(np.random.randn(n) * 0.5),
            "high": close + abs(np.random.randn(n)),
            "low": close - abs(np.random.randn(n)),
            "close": close,
            "volume": np.random.uniform(1e6, 1e7, n),
        }, index=dates)

    def _test_strategy(self, name):
        strat = get_strategy(name)
        data = self._sample_data()
        signals = strat.decide(data, None)
        self.assertIsInstance(signals, list)

    def test_ma_crossover_decide(self):
        self._test_strategy("ma_crossover")

    def test_rsi_decide(self):
        self._test_strategy("rsi")

    def test_macd_decide(self):
        self._test_strategy("macd")

    def test_bollinger_decide(self):
        self._test_strategy("bollinger")

    def test_momentum_decide(self):
        self._test_strategy("momentum")

    def test_vwap_decide(self):
        self._test_strategy("vwap")

    def test_ichimoku_decide(self):
        self._test_strategy("ichimoku")

    def test_supertrend_decide(self):
        self._test_strategy("supertrend")

    def test_donchian_decide(self):
        self._test_strategy("donchian")

    def test_mean_reversion_decide(self):
        self._test_strategy("mean_reversion")

    def test_volume_breakout_decide(self):
        self._test_strategy("volume_breakout")

    def test_stochastic_decide(self):
        self._test_strategy("stochastic")

    def test_multi_tf_decide(self):
        self._test_strategy("multi_tf")

    def test_strategy_has_name(self):
        strat = get_strategy("ma_crossover")
        self.assertEqual(strat.name, "ma_crossover")

    def test_strategy_get_params(self):
        strat = get_strategy("ma_crossover")
        params = strat.get_params()
        self.assertIn("fast_period", params)

    def test_strategy_configure(self):
        strat = get_strategy("ma_crossover")
        strat.configure({"fast_period": 5})
        self.assertEqual(strat.fast_period, 5)

    def test_strategy_insufficient_data(self):
        strat = get_strategy("ma_crossover")
        data = self._sample_data(5)
        signals = strat.decide(data, None)
        self.assertEqual(signals, [])


if __name__ == "__main__":
    unittest.main()
