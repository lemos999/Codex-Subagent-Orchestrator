"""Tests for data cache module."""
import os
import tempfile
import unittest

import pandas as pd
import numpy as np

from tq.data.cache import DataCache


class TestDataCache(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        self.tmp.close()
        self.cache = DataCache(self.tmp.name)

    def tearDown(self):
        os.unlink(self.tmp.name)

    def _sample_daily_df(self, n=5):
        dates = pd.date_range("2024-01-01", periods=n, freq="D")
        return pd.DataFrame({
            "open": np.random.uniform(100, 200, n),
            "high": np.random.uniform(200, 300, n),
            "low": np.random.uniform(50, 100, n),
            "close": np.random.uniform(100, 200, n),
            "volume": np.random.uniform(1e6, 1e7, n),
        }, index=dates)

    def test_save_and_load_daily(self):
        df = self._sample_daily_df()
        rows = self.cache.save_daily("AAPL", "US", df)
        self.assertEqual(rows, 5)
        loaded = self.cache.load_daily("AAPL", "US")
        self.assertEqual(len(loaded), 5)

    def test_has_daily(self):
        df = self._sample_daily_df()
        self.assertFalse(self.cache.has_daily("AAPL", "US"))
        self.cache.save_daily("AAPL", "US", df)
        self.assertTrue(self.cache.has_daily("AAPL", "US"))

    def test_save_empty_df(self):
        rows = self.cache.save_daily("AAPL", "US", pd.DataFrame())
        self.assertEqual(rows, 0)

    def test_save_and_load_minute(self):
        dates = pd.date_range("2024-01-01 09:30", periods=10, freq="min")
        df = pd.DataFrame({
            "open": np.random.uniform(100, 200, 10),
            "high": np.random.uniform(200, 300, 10),
            "low": np.random.uniform(50, 100, 10),
            "close": np.random.uniform(100, 200, 10),
            "volume": np.random.uniform(1e3, 1e4, 10),
        }, index=dates)
        rows = self.cache.save_minute("AAPL", "US", df)
        self.assertEqual(rows, 10)
        loaded = self.cache.load_minute("AAPL", "US")
        self.assertEqual(len(loaded), 10)

    def test_has_minute(self):
        self.assertFalse(self.cache.has_minute("AAPL", "US"))

    def test_save_and_load_universe(self):
        symbols = [
            {"symbol": "AAPL", "name": "Apple", "sector": "Tech"},
            {"symbol": "MSFT", "name": "Microsoft", "sector": "Tech"},
        ]
        rows = self.cache.save_universe(symbols, "US")
        self.assertEqual(rows, 2)
        loaded = self.cache.load_universe("US")
        self.assertEqual(len(loaded), 2)

    def test_get_status(self):
        status = self.cache.get_status()
        self.assertIn("daily_rows", status)
        self.assertIn("minute_rows", status)
        self.assertIn("universe_count", status)
        self.assertEqual(status["daily_rows"], 0)

    def test_load_daily_with_date_range(self):
        df = self._sample_daily_df(10)
        self.cache.save_daily("AAPL", "US", df)
        loaded = self.cache.load_daily("AAPL", "US", start="2024-01-03", end="2024-01-07")
        self.assertLessEqual(len(loaded), 5)


if __name__ == "__main__":
    unittest.main()
