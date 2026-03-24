"""Tests for strategy ranking."""
import unittest

from tq.quest.ranking import StrategyRanker, StrategyResult


class TestStrategyResult(unittest.TestCase):

    def test_rank_score(self):
        r = StrategyResult("test", total_return_pct=5.0, composite_score=100,
                          sharpe_ratio=1.5, max_drawdown=0.05)
        self.assertGreater(r.rank_score, 0)

    def test_to_dict(self):
        r = StrategyResult("test")
        d = r.to_dict()
        self.assertIn("strategy_name", d)
        self.assertIn("rank_score", d)


class TestStrategyRanker(unittest.TestCase):

    def test_add_result(self):
        ranker = StrategyRanker()
        ranker.add_result(StrategyResult("test"))
        self.assertEqual(len(ranker.results), 1)

    def test_get_leaderboard(self):
        ranker = StrategyRanker()
        ranker.add_result(StrategyResult("a", composite_score=100))
        ranker.add_result(StrategyResult("b", composite_score=200))
        ranker.add_result(StrategyResult("c", composite_score=150))
        board = ranker.get_leaderboard(2)
        self.assertEqual(len(board), 2)
        self.assertEqual(board[0].strategy_name, "b")

    def test_compare(self):
        ranker = StrategyRanker()
        ranker.add_result(StrategyResult("a", composite_score=100))
        ranker.add_result(StrategyResult("b", composite_score=200))
        ranker.add_result(StrategyResult("c", composite_score=50))
        compared = ranker.compare(["a", "c"])
        self.assertEqual(len(compared), 2)

    def test_get_best(self):
        ranker = StrategyRanker()
        ranker.add_result(StrategyResult("a", composite_score=100))
        ranker.add_result(StrategyResult("b", composite_score=200))
        best = ranker.get_best()
        self.assertEqual(best.strategy_name, "b")

    def test_empty_ranker(self):
        ranker = StrategyRanker()
        self.assertIsNone(ranker.get_best())
        self.assertEqual(len(ranker.get_leaderboard()), 0)

    def test_format_leaderboard(self):
        ranker = StrategyRanker()
        ranker.add_result(StrategyResult("test", composite_score=100))
        text = ranker.format_leaderboard()
        self.assertIn("test", text)

    def test_format_empty_leaderboard(self):
        ranker = StrategyRanker()
        text = ranker.format_leaderboard()
        self.assertIn("No strategies", text)

    def test_to_dict(self):
        ranker = StrategyRanker()
        d = ranker.to_dict()
        self.assertIn("total_strategies", d)


if __name__ == "__main__":
    unittest.main()
