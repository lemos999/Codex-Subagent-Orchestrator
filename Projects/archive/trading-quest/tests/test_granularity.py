"""Tests for granularity module."""
import unittest
from datetime import date

import pandas as pd
import numpy as np

from tq.data.granularity import (
    Granularity, resample_ohlcv, trading_minutes_per_day, is_trading_day,
)


class TestGranularity(unittest.TestCase):

    def test_from_string(self):
        self.assertEqual(Granularity.from_string("1m"), Granularity.M1)
        self.assertEqual(Granularity.from_string("5m"), Granularity.M5)
        self.assertEqual(Granularity.from_string("1d"), Granularity.D1)
        self.assertEqual(Granularity.from_string("1h"), Granularity.H1)

    def test_from_string_invalid(self):
        with self.assertRaises(ValueError):
            Granularity.from_string("99x")

    def test_minutes(self):
        self.assertEqual(Granularity.M1.minutes, 1)
        self.assertEqual(Granularity.M5.minutes, 5)
        self.assertEqual(Granularity.H1.minutes, 60)
        self.assertEqual(Granularity.D1.minutes, 1440)

    def test_pandas_freq(self):
        self.assertIn("min", Granularity.M5.pandas_freq)

    def test_resample_ohlcv(self):
        dates = pd.date_range("2024-01-01 09:30", periods=10, freq="min")
        df = pd.DataFrame({
            "open": np.arange(10.0),
            "high": np.arange(10.0) + 1,
            "low": np.arange(10.0) - 0.5,
            "close": np.arange(10.0) + 0.5,
            "volume": np.ones(10) * 100,
        }, index=dates)
        resampled = resample_ohlcv(df, Granularity.M5)
        self.assertLessEqual(len(resampled), 3)

    def test_resample_empty(self):
        df = pd.DataFrame()
        result = resample_ohlcv(df, Granularity.M5)
        self.assertTrue(result.empty)

    def test_trading_minutes_us(self):
        self.assertEqual(trading_minutes_per_day("US"), 390)

    def test_trading_minutes_krx(self):
        self.assertEqual(trading_minutes_per_day("KRX"), 360)

    def test_trading_minutes_crypto(self):
        self.assertEqual(trading_minutes_per_day("CRYPTO"), 1440)

    def test_is_trading_day_weekday(self):
        # 2024-01-16 is a Tuesday (regular trading day; Jan 15 is MLK Day holiday)
        self.assertTrue(is_trading_day(date(2024, 1, 16), "US"))

    def test_is_trading_day_us_holiday(self):
        # 2024-01-15 is Martin Luther King Jr. Day — US market closed
        self.assertFalse(is_trading_day(date(2024, 1, 15), "US"))

    def test_is_trading_day_us_fixed_holiday(self):
        # Christmas is a fixed US holiday
        self.assertFalse(is_trading_day(date(2025, 12, 25), "US"))

    def test_is_trading_day_weekend(self):
        # 2024-01-13 is a Saturday
        self.assertFalse(is_trading_day(date(2024, 1, 13), "US"))

    def test_is_trading_day_crypto(self):
        # Crypto trades every day
        self.assertTrue(is_trading_day(date(2024, 1, 13), "CRYPTO"))


if __name__ == "__main__":
    unittest.main()
