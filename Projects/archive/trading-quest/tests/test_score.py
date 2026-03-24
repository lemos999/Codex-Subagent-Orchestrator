"""Tests for quest scoring."""
import unittest

from tq.quest.score import QuestScore, ScoreTracker


class TestQuestScore(unittest.TestCase):

    def test_composite_score_positive_return(self):
        score = QuestScore(return_pct=1.0, trades=5, win_rate=60)
        self.assertGreater(score.composite_score, 0)

    def test_drawdown_penalty_none(self):
        score = QuestScore(max_drawdown=0.03)
        self.assertEqual(score.drawdown_penalty, 0)

    def test_drawdown_penalty_moderate(self):
        score = QuestScore(max_drawdown=0.08)
        self.assertGreater(score.drawdown_penalty, 0)

    def test_drawdown_penalty_high(self):
        score = QuestScore(max_drawdown=0.25)
        self.assertGreater(score.drawdown_penalty, 50)

    def test_risk_adjusted_score(self):
        score = QuestScore(sharpe_ratio=1.5)
        self.assertGreater(score.risk_adjusted_score, 0)

    def test_risk_adjusted_negative_sharpe(self):
        score = QuestScore(sharpe_ratio=-0.5)
        self.assertEqual(score.risk_adjusted_score, 0)

    def test_to_dict(self):
        score = QuestScore(return_pct=1.0, trades=5)
        d = score.to_dict()
        self.assertIn("composite_score", d)
        self.assertIn("drawdown_penalty", d)


class TestScoreTracker(unittest.TestCase):

    def test_add_day(self):
        tracker = ScoreTracker()
        score = QuestScore(return_pct=1.0, trades=3)
        total = tracker.add_day(score)
        self.assertGreater(total, 0)
        self.assertEqual(len(tracker.daily_scores), 1)

    def test_get_average_score(self):
        tracker = ScoreTracker()
        tracker.add_day(QuestScore(return_pct=1.0, trades=3))
        tracker.add_day(QuestScore(return_pct=2.0, trades=5))
        avg = tracker.get_average_score()
        self.assertGreater(avg, 0)

    def test_get_best_day(self):
        tracker = ScoreTracker()
        tracker.add_day(QuestScore(return_pct=1.0))
        tracker.add_day(QuestScore(return_pct=5.0))
        tracker.add_day(QuestScore(return_pct=2.0))
        best = tracker.get_best_day()
        self.assertIsNotNone(best)
        self.assertEqual(best.return_pct, 5.0)

    def test_get_worst_day(self):
        tracker = ScoreTracker()
        tracker.add_day(QuestScore(return_pct=1.0))
        tracker.add_day(QuestScore(return_pct=-2.0))
        worst = tracker.get_worst_day()
        self.assertIsNotNone(worst)
        self.assertEqual(worst.return_pct, -2.0)

    def test_empty_tracker(self):
        tracker = ScoreTracker()
        self.assertEqual(tracker.get_average_score(), 0.0)
        self.assertIsNone(tracker.get_best_day())
        self.assertIsNone(tracker.get_worst_day())


if __name__ == "__main__":
    unittest.main()
