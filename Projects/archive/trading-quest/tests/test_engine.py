"""Tests for quest engine with alert hooks."""
import unittest
from datetime import date
from unittest.mock import MagicMock

import pandas as pd

from tq.quest.engine import QuestEngine


class TestQuestEngine(unittest.TestCase):

    def test_run_basic(self):
        engine = QuestEngine("q-test", "us", ["AAPL"])
        result = engine.run("2024-01-15", 5)
        self.assertEqual(result["quest_id"], "q-test")
        self.assertEqual(result["days"], 5)

    def test_alert_manager_daily_called(self):
        mgr = MagicMock()
        engine = QuestEngine("q-test", "us", ["AAPL"], alert_manager=mgr)
        engine.run("2024-01-15", 3)
        self.assertEqual(mgr.notify_daily.call_count, 3)

    def test_alert_manager_phase_called(self):
        mgr = MagicMock()
        engine = QuestEngine("q-test", "us", ["AAPL"], alert_manager=mgr)
        engine.run("2024-01-01", 15)
        # Phase transitions happen at day 10 (1->2)
        self.assertTrue(mgr.notify_phase.called)

    def test_on_trade_fill_with_alert(self):
        mgr = MagicMock()
        engine = QuestEngine("q-test", "us", ["AAPL"], alert_manager=mgr)
        engine.on_trade_fill({"side": "BUY", "symbol": "AAPL", "price": 150})
        mgr.notify_trade.assert_called_once()

    def test_on_trade_fill_without_alert(self):
        engine = QuestEngine("q-test", "us", ["AAPL"])
        # Should not raise
        engine.on_trade_fill({"side": "BUY", "symbol": "AAPL"})

    def test_alert_failure_does_not_crash(self):
        mgr = MagicMock()
        mgr.notify_daily.side_effect = RuntimeError("boom")
        engine = QuestEngine("q-test", "us", ["AAPL"], alert_manager=mgr)
        # Should not raise
        engine.run("2024-01-15", 3)

    def test_no_alert_manager(self):
        engine = QuestEngine("q-test", "us", ["AAPL"])
        result = engine.run("2024-01-15", 3)
        self.assertEqual(result["days"], 3)

    def test_strategy_only_sees_history_up_to_simulation_day(self):
        class CaptureStrategy:
            name = "capture"

            def __init__(self):
                self.last_data = None

            def decide(self, data, portfolio):
                self.last_data = data.copy()
                return [{"symbol": "AAPL", "side": "BUY", "qty": 1}]

        engine = QuestEngine("q-test", "us", ["AAPL"])
        engine.strategy = CaptureStrategy()
        engine.broker.executor.commission_rate = 0.0
        engine.broker.executor.slippage_rate = 0.0
        engine.current_phase = 2

        history = pd.DataFrame({
            "open": [10, 11, 12, 13, 14],
            "high": [11, 12, 13, 14, 15],
            "low": [9, 10, 11, 12, 13],
            "close": [10, 11, 12, 13, 14],
            "volume": [100] * 5,
        }, index=pd.date_range("2024-01-01", periods=5, freq="D"))
        engine._data_cache["AAPL_1d"] = history

        engine._run_day(date(2024, 1, 3), 0)

        self.assertIsNotNone(engine.strategy.last_data)
        self.assertEqual(engine.strategy.last_data.index.max().date(), date(2024, 1, 3))
        self.assertEqual(len(engine.strategy.last_data), 3)
        self.assertAlmostEqual(engine.broker.portfolio.positions["AAPL"].avg_price, 12.0)

    def test_process_signals_skips_sell_without_position(self):
        engine = QuestEngine("q-test", "us", ["AAPL", "MSFT"])
        engine.broker.portfolio.buy("AAPL", 1, 100.0)
        engine._data_cache["AAPL_1d"] = pd.DataFrame({
            "open": [100.0],
            "high": [101.0],
            "low": [99.0],
            "close": [100.0],
            "volume": [1000.0],
        }, index=pd.date_range("2024-01-02", periods=1, freq="D"))
        engine._data_cache["MSFT_1d"] = pd.DataFrame({
            "open": [200.0],
            "high": [201.0],
            "low": [199.0],
            "close": [200.0],
            "volume": [1000.0],
        }, index=pd.date_range("2024-01-02", periods=1, freq="D"))

        fills = engine.process_signals(
            [{"symbol": "MSFT", "side": "SELL", "qty": 1}],
            "MSFT",
            "2024-01-02",
        )

        self.assertEqual(fills, [])
        self.assertEqual(engine.broker.pending_orders, [])
        self.assertIn("AAPL", engine.broker.portfolio.positions)
        self.assertNotIn("MSFT", engine.broker.portfolio.positions)


if __name__ == "__main__":
    unittest.main()
