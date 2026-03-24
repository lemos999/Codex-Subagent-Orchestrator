"""Tests for strategy optimizer."""
import unittest

import numpy as np
import pandas as pd

from tq.quest.optimizer import StrategyOptimizer, OptimizationResult


class TestOptimizationResult(unittest.TestCase):

    def test_overfitting_ratio(self):
        r = OptimizationResult("test", params={}, train_score=100, validation_score=80)
        self.assertAlmostEqual(r.overfitting_ratio, 0.2)

    def test_overfitting_zero_train(self):
        r = OptimizationResult("test", params={}, train_score=0, validation_score=0)
        self.assertEqual(r.overfitting_ratio, 0.0)

    def test_to_dict(self):
        r = OptimizationResult("test", params={"a": 1})
        d = r.to_dict()
        self.assertIn("strategy_name", d)
        self.assertIn("overfitting_ratio", d)


class TestStrategyOptimizer(unittest.TestCase):

    def _sample_data(self, n=100):
        np.random.seed(42)
        dates = pd.date_range("2024-01-01", periods=n, freq="D")
        return pd.DataFrame({
            "close": 100 + np.cumsum(np.random.randn(n)),
            "volume": np.random.uniform(1e6, 1e7, n),
        }, index=dates)

    def test_split_data(self):
        opt = StrategyOptimizer(train_ratio=0.7)
        data = self._sample_data()
        train, val = opt.split_data(data)
        self.assertEqual(len(train), 70)
        self.assertEqual(len(val), 30)

    def test_walk_forward(self):
        opt = StrategyOptimizer(train_ratio=0.7, n_windows=2)
        data = self._sample_data()
        param_grid = [{"a": 1}, {"a": 2}, {"a": 3}]

        def eval_fn(df, params):
            return params.get("a", 0) * len(df)

        results = opt.walk_forward(data, eval_fn, param_grid, "test")
        self.assertEqual(len(results), 2)

    def test_get_best_params(self):
        opt = StrategyOptimizer()
        self.assertIsNone(opt.get_best_params())

        opt.results = [
            OptimizationResult("a", {"x": 1}, validation_score=10),
            OptimizationResult("b", {"x": 2}, validation_score=20),
        ]
        best = opt.get_best_params()
        self.assertEqual(best["x"], 2)

    def test_to_dict(self):
        opt = StrategyOptimizer()
        d = opt.to_dict()
        self.assertIn("train_ratio", d)
        self.assertIn("results", d)


if __name__ == "__main__":
    unittest.main()
