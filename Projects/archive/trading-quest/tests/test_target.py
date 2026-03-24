"""Tests for daily target evaluation."""
import unittest

from tq.quest.target import evaluate_daily_target


class TestEvaluateDailyTarget(unittest.TestCase):

    def test_positive_return_passes(self):
        result = evaluate_daily_target({"return_pct": 2.0, "trades": 5, "win_rate": 60})
        self.assertTrue(result["passed"])

    def test_zero_trades_neutral(self):
        result = evaluate_daily_target({"return_pct": 0, "trades": 0, "win_rate": 0})
        self.assertTrue(result["passed"])

    def test_negative_return_fails(self):
        result = evaluate_daily_target({"return_pct": -1.0, "trades": 3, "win_rate": 30})
        self.assertFalse(result["passed"])

    def test_excessive_drawdown_fails(self):
        result = evaluate_daily_target({
            "return_pct": 1.0, "trades": 5, "win_rate": 60,
            "max_drawdown": 0.25,
        })
        self.assertFalse(result["passed"])

    def test_feedback_includes_info(self):
        result = evaluate_daily_target({
            "return_pct": 1.5, "trades": 4, "win_rate": 75,
        })
        self.assertIsInstance(result["feedback"], list)
        self.assertGreater(len(result["feedback"]), 0)


if __name__ == "__main__":
    unittest.main()
