"""Tests for configuration module."""
import unittest
from pathlib import Path

from tq import config
from tq.config import QuestConfig


class TestConfig(unittest.TestCase):

    def test_project_root_exists(self):
        self.assertTrue(config.PROJECT_ROOT.exists())

    def test_markets_tuple(self):
        self.assertIn("US", config.MARKETS)
        self.assertIn("KRX", config.MARKETS)
        self.assertIn("CRYPTO", config.MARKETS)

    def test_default_capital(self):
        self.assertEqual(config.DEFAULT_CAPITAL["US"], 100_000)
        self.assertEqual(config.DEFAULT_CAPITAL["KRX"], 100_000_000)
        self.assertEqual(config.DEFAULT_CAPITAL["CRYPTO"], 10_000)

    def test_commission_rates(self):
        self.assertGreater(config.COMMISSION_RATE["US"], 0)
        self.assertGreater(config.COMMISSION_RATE["KRX"], 0)

    def test_slippage_rates(self):
        self.assertGreater(config.SLIPPAGE_RATE["US"], 0)

    def test_quest_config_defaults(self):
        qc = QuestConfig()
        self.assertEqual(qc.market, "US")
        self.assertGreater(qc.initial_capital, 0)

    def test_quest_config_auto_commission(self):
        qc = QuestConfig(market="KRX")
        self.assertEqual(qc.commission_rate, config.COMMISSION_RATE["KRX"])

    def test_quest_config_auto_capital(self):
        qc = QuestConfig(market="US", initial_capital=0)
        self.assertEqual(qc.initial_capital, config.DEFAULT_CAPITAL["US"])

    def test_db_path(self):
        self.assertTrue(str(config.DB_PATH).endswith("cache.sqlite"))


if __name__ == "__main__":
    unittest.main()
