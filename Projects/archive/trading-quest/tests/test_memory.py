"""Tests for TradingMemory persistent learning system."""
import json
import tempfile
import unittest
from pathlib import Path

from tq.journal.memory import TradingMemory


class TestTradingMemory(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.memory_dir = Path(self.tmp_dir.name) / "memory"
        self.memory = TradingMemory(memory_dir=self.memory_dir)

    def tearDown(self):
        self.tmp_dir.cleanup()

    # ── Best Params ──

    def test_get_best_params_empty(self):
        result = self.memory.get_best_params("macd")
        self.assertEqual(result, {})

    def test_save_and_get_best_params(self):
        params = {"fast": 12, "slow": 26, "signal": 9}
        self.memory.save_best_params("macd", params, score=5.0,
                                     win_rate=0.65, trades=20)
        result = self.memory.get_best_params("macd")
        self.assertEqual(result, params)

    def test_save_best_params_only_overwrites_if_better(self):
        self.memory.save_best_params("macd", {"fast": 12}, score=5.0,
                                     win_rate=0.65, trades=20)
        self.memory.save_best_params("macd", {"fast": 10}, score=3.0,
                                     win_rate=0.50, trades=15)
        # Should still be the first one (score 5.0 > 3.0)
        result = self.memory.get_best_params("macd")
        self.assertEqual(result, {"fast": 12})

    def test_save_best_params_overwrites_when_higher_score(self):
        self.memory.save_best_params("macd", {"fast": 12}, score=5.0,
                                     win_rate=0.65, trades=20)
        self.memory.save_best_params("macd", {"fast": 8}, score=10.0,
                                     win_rate=0.70, trades=25)
        result = self.memory.get_best_params("macd")
        self.assertEqual(result, {"fast": 8})

    # ── Tried Params ──

    def test_has_tried_empty(self):
        self.assertFalse(self.memory.has_tried("macd", {"fast": 12}))

    def test_record_and_has_tried(self):
        params = {"fast": 12, "slow": 26}
        self.memory.record_trial("macd", params,
                                 {"score": 5.0, "win_rate": 0.6, "trades": 20})
        self.assertTrue(self.memory.has_tried("macd", params))
        self.assertFalse(self.memory.has_tried("macd", {"fast": 10, "slow": 26}))

    def test_get_untried_variations(self):
        base = {"fast": 12, "slow": 26}
        # Record the base as tried
        self.memory.record_trial("macd", base,
                                 {"score": 5.0, "win_rate": 0.6, "trades": 20})
        variations = self.memory.get_untried_variations("macd", base)
        self.assertIsInstance(variations, list)
        self.assertTrue(len(variations) > 0)
        # None of them should be the base params
        for v in variations:
            self.assertNotEqual(v, base)
        # None should be already tried
        for v in variations:
            self.assertFalse(self.memory.has_tried("macd", v))

    # ── Mistakes & Insights ──

    def test_record_and_get_mistakes(self):
        self.memory.record_mistake({
            "strategy": "macd",
            "params": {"fast": 5},
            "score": -3.0,
            "win_rate": 0.15,
            "reason": "too many false signals",
        })
        mistakes = self.memory.get_mistakes()
        self.assertEqual(len(mistakes), 1)
        self.assertEqual(mistakes[0]["strategy"], "macd")

    def test_get_mistakes_filtered_by_strategy(self):
        self.memory.record_mistake({"strategy": "macd", "score": -1})
        self.memory.record_mistake({"strategy": "rsi", "score": -2})
        self.assertEqual(len(self.memory.get_mistakes("macd")), 1)
        self.assertEqual(len(self.memory.get_mistakes("rsi")), 1)
        self.assertEqual(len(self.memory.get_mistakes()), 2)

    def test_record_and_get_insights(self):
        self.memory.record_insight({
            "strategy": "macd",
            "params": {"fast": 20},
            "score": 16.0,
            "win_rate": 0.65,
            "reason": "filtered noise well",
        })
        insights = self.memory.get_insights()
        self.assertEqual(len(insights), 1)
        self.assertEqual(insights[0]["score"], 16.0)

    def test_should_avoid(self):
        bad_params = {"fast": 5, "slow": 15}
        self.memory.record_mistake({
            "strategy": "macd",
            "params": bad_params,
            "score": -5.0,
            "reason": "terrible performance",
            "avoid": True,
        })
        should, reason = self.memory.should_avoid("macd", bad_params)
        self.assertTrue(should)
        self.assertIn("terrible", reason)

        # Different params should be OK
        should2, reason2 = self.memory.should_avoid("macd", {"fast": 12, "slow": 26})
        self.assertFalse(should2)

    # ── Session History ──

    def test_record_session_and_count(self):
        self.assertEqual(self.memory.get_session_count(), 0)
        self.memory.record_session({
            "strategy": "macd",
            "rounds": 5,
            "best_score": 10.0,
            "best_params": {"fast": 12},
        })
        self.assertEqual(self.memory.get_session_count(), 1)

    def test_cumulative_improvement(self):
        self.memory.record_session({
            "strategy": "macd", "rounds": 3, "best_score": 2.0,
        })
        self.memory.record_session({
            "strategy": "macd", "rounds": 5, "best_score": 8.0,
        })
        result = self.memory.get_cumulative_improvement("macd")
        self.assertEqual(result["sessions_count"], 2)
        self.assertEqual(result["first_score"], 2.0)
        self.assertEqual(result["best_score"], 8.0)
        self.assertGreater(result["improvement_pct"], 0)
        self.assertEqual(result["total_trials"], 8)

    def test_cumulative_improvement_no_sessions(self):
        result = self.memory.get_cumulative_improvement("nonexistent")
        self.assertEqual(result["sessions_count"], 0)

    # ── Summary ──

    def test_summary(self):
        self.memory.save_best_params("macd", {"fast": 12}, 5.0, 0.65, 20)
        self.memory.record_mistake({"strategy": "macd", "score": -1})
        self.memory.record_insight({"strategy": "macd", "score": 10})
        self.memory.record_session({
            "strategy": "macd", "rounds": 3, "best_score": 5.0,
        })

        summary = self.memory.get_summary()
        self.assertEqual(summary["sessions_count"], 1)
        self.assertIn("macd", summary["strategies_with_best"])
        self.assertEqual(summary["mistakes_count"], 1)
        self.assertEqual(summary["insights_count"], 1)

    # ── Forget ──

    def test_forget_all(self):
        self.memory.save_best_params("macd", {"fast": 12}, 5.0, 0.65, 20)
        self.memory.record_trial("macd", {"fast": 12},
                                 {"score": 5.0, "win_rate": 0.65, "trades": 20})
        self.memory.record_mistake({"strategy": "macd", "score": -1})
        self.memory.record_session({"strategy": "macd", "best_score": 5.0})

        self.memory.forget()

        self.assertEqual(self.memory.get_best_params("macd"), {})
        self.assertFalse(self.memory.has_tried("macd", {"fast": 12}))
        self.assertEqual(self.memory.get_mistakes(), [])
        self.assertEqual(self.memory.get_session_count(), 0)

    def test_forget_strategy(self):
        self.memory.save_best_params("macd", {"fast": 12}, 5.0, 0.65, 20)
        self.memory.save_best_params("rsi", {"period": 14}, 3.0, 0.55, 15)
        self.memory.record_mistake({"strategy": "macd", "score": -1})
        self.memory.record_mistake({"strategy": "rsi", "score": -2})

        self.memory.forget("macd")

        self.assertEqual(self.memory.get_best_params("macd"), {})
        self.assertNotEqual(self.memory.get_best_params("rsi"), {})
        self.assertEqual(len(self.memory.get_mistakes("macd")), 0)
        self.assertEqual(len(self.memory.get_mistakes("rsi")), 1)

    # ── Params Hash ──

    def test_params_hash_deterministic(self):
        params = {"fast": 12, "slow": 26}
        h1 = TradingMemory._params_hash(params)
        h2 = TradingMemory._params_hash(params)
        self.assertEqual(h1, h2)

    def test_params_hash_order_independent(self):
        h1 = TradingMemory._params_hash({"fast": 12, "slow": 26})
        h2 = TradingMemory._params_hash({"slow": 26, "fast": 12})
        self.assertEqual(h1, h2)

    # ── JSON file persistence ──

    def test_files_are_json_readable(self):
        self.memory.save_best_params("macd", {"fast": 12}, 5.0, 0.65, 20)
        path = self.memory_dir / "best-params.json"
        self.assertTrue(path.exists())
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertIn("macd", data)


if __name__ == "__main__":
    unittest.main()
