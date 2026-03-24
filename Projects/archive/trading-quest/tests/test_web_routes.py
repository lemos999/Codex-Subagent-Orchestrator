"""Tests for web API routes."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from tq.data.cache import DataCache
from tq.quest.state import QuestState

try:
    from tq.web.app import create_app
except ImportError:
    create_app = None


@unittest.skipIf(create_app is None, "Flask not installed")
class TestWebRoutes(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.quests_dir = Path(self.tmp_dir.name) / "quests"
        self.db_path = str(Path(self.tmp_dir.name) / "cache.sqlite")

        cache = DataCache(self.db_path)
        dates = pd.date_range("2024-01-01", periods=30, freq="D")
        frame = pd.DataFrame({
            "open": [100.0 + i for i in range(30)],
            "high": [101.0 + i for i in range(30)],
            "low": [99.0 + i for i in range(30)],
            "close": [100.5 + i for i in range(30)],
            "volume": [1000.0 + i for i in range(30)],
        }, index=dates)
        cache.save_daily("AAPL", "US", frame)

        state = QuestState(
            quest_id="q-web-1",
            market="US",
            symbols=["AAPL"],
            initial_capital=100_000,
            current_capital=101_250,
            start_date="2024-01-01",
            current_date="2024-01-30",
            strategy_name="macd",
            total_score=25.0,
            trade_log=[{
                "symbol": "AAPL",
                "side": "BUY",
                "qty": 1,
                "price": 123.45,
                "timestamp": "2024-01-15",
            }],
        )
        state.save(self.quests_dir)

        app = create_app({
            "TESTING": True,
            "DATA_CACHE_PATH": self.db_path,
            "QUESTS_DIR": self.quests_dir,
        })
        self.client = app.test_client()

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_api_quests_lists_active_quests(self):
        response = self.client.get("/api/quests")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(len(payload["quests"]), 1)
        self.assertEqual(payload["quests"][0]["quest_id"], "q-web-1")

    def test_api_quest_trades_returns_trade_log(self):
        response = self.client.get("/api/quest/q-web-1/trades")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["trade_count"], 1)
        self.assertEqual(payload["trade_log"][0]["symbol"], "AAPL")

    def test_api_data_returns_requested_date_range(self):
        response = self.client.get(
            "/api/data/AAPL?market=US&start=2024-01-05&end=2024-01-06"
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["symbol"], "AAPL")
        self.assertEqual(payload["count"], 2)
        self.assertEqual(payload["rows"][0]["timestamp"][:10], "2024-01-05")

    def test_api_indicators_returns_sma_and_bollinger(self):
        response = self.client.get("/api/data/AAPL/indicators?market=US")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["count"], 30)
        self.assertIn("sma", payload["rows"][-1])
        self.assertIn("bb_upper", payload["rows"][-1])
        self.assertIsNotNone(payload["rows"][-1]["sma"])

    @patch("tq.quest.engine.QuestEngine.run")
    def test_api_compare_runs_strategy_ranking(self, mock_run):
        mock_run.side_effect = [
            {
                "return_pct": 4.0,
                "total_trades": 12,
                "total_score": 80.0,
                "max_drawdown": 0.10,
                "days": 30,
            },
            {
                "return_pct": 2.0,
                "total_trades": 8,
                "total_score": 50.0,
                "max_drawdown": 0.08,
                "days": 30,
            },
        ]

        response = self.client.post("/api/compare", json={
            "market": "US",
            "symbols": ["AAPL"],
            "strategies": ["macd", "rsi"],
            "days": 30,
            "start_date": "2024-01-01",
        })

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["total_strategies"], 2)
        self.assertEqual(payload["leaderboard"][0]["strategy_name"], "macd")
        self.assertEqual(len(payload["results"]), 2)


if __name__ == "__main__":
    unittest.main()
