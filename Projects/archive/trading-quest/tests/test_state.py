"""Tests for quest state."""
import os
import tempfile
import unittest
from pathlib import Path

from tq.quest.state import QuestState


class TestQuestState(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_save_and_load(self):
        state = QuestState(
            quest_id="test-1",
            market="US",
            symbols=["AAPL"],
            initial_capital=100_000,
            current_capital=101_000,
            start_date="2024-01-01",
            current_date="2024-02-01",
        )
        state.save(Path(self.tmp_dir))
        loaded = QuestState.load("test-1", Path(self.tmp_dir))
        self.assertEqual(loaded.quest_id, "test-1")
        self.assertEqual(loaded.current_capital, 101_000)

    def test_load_nonexistent(self):
        with self.assertRaises(FileNotFoundError):
            QuestState.load("nonexistent", Path(self.tmp_dir))

    def test_checkpoint(self):
        state = QuestState(
            quest_id="test-1", market="US", symbols=["AAPL"],
            initial_capital=100_000, current_capital=100_000,
            start_date="2024-01-01", current_date="2024-01-01",
        )
        path = state.checkpoint(Path(self.tmp_dir))
        self.assertTrue(path.exists())

    def test_archive(self):
        state = QuestState(
            quest_id="test-1", market="US", symbols=["AAPL"],
            initial_capital=100_000, current_capital=100_000,
            start_date="2024-01-01", current_date="2024-01-01",
        )
        state.save(Path(self.tmp_dir))
        path = state.archive(Path(self.tmp_dir))
        self.assertTrue(path.exists())

    def test_to_dict(self):
        state = QuestState(
            quest_id="test-1", market="US", symbols=["AAPL"],
            initial_capital=100_000, current_capital=100_000,
            start_date="2024-01-01", current_date="2024-01-01",
        )
        d = state.to_dict()
        self.assertEqual(d["quest_id"], "test-1")
        self.assertIn("trade_log", d)

    def test_from_dict(self):
        d = {
            "quest_id": "test-1",
            "market": "US",
            "symbols": ["AAPL"],
            "initial_capital": 100_000,
            "current_capital": 99_000,
            "start_date": "2024-01-01",
            "current_date": "2024-01-15",
            "trade_log": [{"side": "BUY"}],
        }
        state = QuestState.from_dict(d)
        self.assertEqual(state.quest_id, "test-1")
        self.assertEqual(len(state.trade_log), 1)

    def test_trade_log_field(self):
        state = QuestState(
            quest_id="test-1", market="US", symbols=["AAPL"],
            initial_capital=100_000, current_capital=100_000,
            start_date="2024-01-01", current_date="2024-01-01",
        )
        state.trade_log.append({"symbol": "AAPL", "side": "BUY"})
        self.assertEqual(len(state.trade_log), 1)


if __name__ == "__main__":
    unittest.main()
