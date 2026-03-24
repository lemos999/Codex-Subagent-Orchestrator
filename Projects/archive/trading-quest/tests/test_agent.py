"""Tests for agent interface and protocol."""
import unittest

from tq.agent.protocol import QuestRequest, QuestResponse, format_quest_prompt
from tq.agent.sub_spec import generate_backtest_spec, generate_optimization_spec
from tq.agent.submix_spec import generate_multi_engine_backtest


class TestQuestRequest(unittest.TestCase):

    def test_to_dict(self):
        req = QuestRequest(action="decide", observation={"phase": 1})
        d = req.to_dict()
        self.assertEqual(d["action"], "decide")

    def test_available_fields(self):
        req = QuestRequest(
            action="decide",
            available_symbols=["AAPL"],
            available_strategies=["rsi"],
        )
        d = req.to_dict()
        self.assertIn("AAPL", d["available_symbols"])


class TestQuestResponse(unittest.TestCase):

    def test_to_action_buy(self):
        resp = QuestResponse(action_type="buy", symbol="AAPL", qty=10)
        action = resp.to_action()
        self.assertEqual(action["type"], "buy")
        self.assertEqual(action["symbol"], "AAPL")

    def test_to_action_hold(self):
        resp = QuestResponse(action_type="hold")
        action = resp.to_action()
        self.assertEqual(action["type"], "hold")

    def test_to_action_strategy(self):
        resp = QuestResponse(action_type="set_strategy", strategy_name="rsi")
        action = resp.to_action()
        self.assertEqual(action["name"], "rsi")


class TestFormatQuestPrompt(unittest.TestCase):

    def test_basic_format(self):
        req = QuestRequest(
            action="decide",
            observation={"phase": 1, "day": 5, "portfolio_value": 100000,
                         "cash": 50000, "drawdown": 0.02, "total_score": 500},
        )
        prompt = format_quest_prompt(req)
        self.assertIn("Phase", prompt)
        self.assertIn("decide", prompt.lower())

    def test_with_positions(self):
        req = QuestRequest(
            action="decide",
            observation={
                "phase": 1, "day": 5, "portfolio_value": 100000,
                "cash": 50000, "drawdown": 0.02, "total_score": 500,
                "positions": {"AAPL": {"qty": 10, "avg_price": 150}},
            },
        )
        prompt = format_quest_prompt(req)
        self.assertIn("AAPL", prompt)


class TestSubSpec(unittest.TestCase):

    def test_generate_backtest_spec(self):
        spec = generate_backtest_spec("test-1")
        self.assertEqual(spec["task"], "backtest")
        self.assertIn("command", spec)

    def test_generate_optimization_spec(self):
        spec = generate_optimization_spec("test-1")
        self.assertEqual(spec["task"], "optimize")
        self.assertIn("config", spec)

    def test_generate_multi_engine(self):
        spec = generate_multi_engine_backtest("test-1")
        self.assertEqual(spec["task"], "multi_engine_backtest")
        self.assertTrue(spec["parallel"])
        self.assertGreater(len(spec["sub_tasks"]), 0)


if __name__ == "__main__":
    unittest.main()
