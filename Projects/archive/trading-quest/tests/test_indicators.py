"""Tests for technical indicators."""
import unittest

import numpy as np
import pandas as pd

from tq.strategy import indicator as ind


class TestMovingAverages(unittest.TestCase):

    def setUp(self):
        self.series = pd.Series(np.arange(50, dtype=float))

    def test_sma(self):
        result = ind.sma(self.series, 10)
        self.assertEqual(len(result), 50)
        self.assertTrue(pd.isna(result.iloc[0]))
        self.assertAlmostEqual(result.iloc[9], 4.5)

    def test_ema(self):
        result = ind.ema(self.series, 10)
        self.assertEqual(len(result), 50)
        self.assertFalse(pd.isna(result.iloc[-1]))

    def test_wma(self):
        result = ind.wma(self.series, 5)
        self.assertEqual(len(result), 50)

    def test_dema(self):
        result = ind.dema(self.series, 10)
        self.assertEqual(len(result), 50)

    def test_tema(self):
        result = ind.tema(self.series, 10)
        self.assertEqual(len(result), 50)


class TestOscillators(unittest.TestCase):

    def setUp(self):
        np.random.seed(42)
        self.close = pd.Series(100 + np.cumsum(np.random.randn(100)))
        self.high = self.close + abs(np.random.randn(100))
        self.low = self.close - abs(np.random.randn(100))
        self.volume = pd.Series(np.random.uniform(1e6, 1e7, 100))

    def test_rsi(self):
        result = ind.rsi(self.close, 14)
        self.assertEqual(len(result), 100)
        # RSI should be between 0 and 100 (where not NaN)
        valid = result.dropna()
        self.assertTrue((valid >= 0).all() and (valid <= 100).all())

    def test_macd(self):
        macd_line, signal, hist = ind.macd(self.close)
        self.assertEqual(len(macd_line), 100)
        self.assertEqual(len(signal), 100)
        self.assertEqual(len(hist), 100)

    def test_stochastic(self):
        k, d = ind.stochastic(self.high, self.low, self.close)
        self.assertEqual(len(k), 100)
        self.assertEqual(len(d), 100)

    def test_williams_r(self):
        result = ind.williams_r(self.high, self.low, self.close)
        self.assertEqual(len(result), 100)

    def test_cci(self):
        result = ind.cci(self.high, self.low, self.close)
        self.assertEqual(len(result), 100)

    def test_momentum(self):
        result = ind.momentum(self.close, 10)
        self.assertEqual(len(result), 100)

    def test_roc(self):
        result = ind.roc(self.close, 10)
        self.assertEqual(len(result), 100)


class TestVolatility(unittest.TestCase):

    def setUp(self):
        np.random.seed(42)
        self.close = pd.Series(100 + np.cumsum(np.random.randn(100)))
        self.high = self.close + abs(np.random.randn(100))
        self.low = self.close - abs(np.random.randn(100))

    def test_bollinger_bands(self):
        upper, middle, lower = ind.bollinger_bands(self.close)
        self.assertEqual(len(upper), 100)
        valid_idx = upper.dropna().index
        self.assertTrue((upper[valid_idx] >= middle[valid_idx]).all())
        self.assertTrue((middle[valid_idx] >= lower[valid_idx]).all())

    def test_atr(self):
        result = ind.atr(self.high, self.low, self.close)
        self.assertEqual(len(result), 100)
        valid = result.dropna()
        self.assertTrue((valid >= 0).all())

    def test_keltner_channel(self):
        upper, middle, lower = ind.keltner_channel(self.high, self.low, self.close)
        self.assertEqual(len(upper), 100)

    def test_donchian_channel(self):
        upper, middle, lower = ind.donchian_channel(self.high, self.low)
        self.assertEqual(len(upper), 100)


class TestTrend(unittest.TestCase):

    def setUp(self):
        np.random.seed(42)
        self.close = pd.Series(100 + np.cumsum(np.random.randn(100)))
        self.high = self.close + abs(np.random.randn(100))
        self.low = self.close - abs(np.random.randn(100))

    def test_adx(self):
        result = ind.adx(self.high, self.low, self.close)
        self.assertEqual(len(result), 100)

    def test_supertrend(self):
        st, direction = ind.supertrend(self.high, self.low, self.close)
        self.assertEqual(len(st), 100)
        self.assertEqual(len(direction), 100)

    def test_ichimoku(self):
        result = ind.ichimoku(self.high, self.low, self.close)
        self.assertIn("tenkan_sen", result)
        self.assertIn("kijun_sen", result)
        self.assertIn("senkou_span_a", result)
        self.assertIn("senkou_span_b", result)
        self.assertIn("chikou_span", result)

    def test_parabolic_sar(self):
        result = ind.parabolic_sar(self.high, self.low)
        self.assertEqual(len(result), 100)


class TestVolume(unittest.TestCase):

    def setUp(self):
        np.random.seed(42)
        self.close = pd.Series(100 + np.cumsum(np.random.randn(100)))
        self.high = self.close + abs(np.random.randn(100))
        self.low = self.close - abs(np.random.randn(100))
        self.volume = pd.Series(np.random.uniform(1e6, 1e7, 100))

    def test_vwap(self):
        result = ind.vwap(self.high, self.low, self.close, self.volume)
        self.assertEqual(len(result), 100)

    def test_obv(self):
        result = ind.obv(self.close, self.volume)
        self.assertEqual(len(result), 100)

    def test_mfi(self):
        result = ind.mfi(self.high, self.low, self.close, self.volume)
        self.assertEqual(len(result), 100)

    def test_accumulation_distribution(self):
        result = ind.accumulation_distribution(self.high, self.low, self.close, self.volume)
        self.assertEqual(len(result), 100)


class TestPatternHelpers(unittest.TestCase):

    def test_crossover(self):
        a = pd.Series([1, 2, 3, 4, 5])
        b = pd.Series([3, 3, 3, 3, 3])
        result = ind.crossover(a, b)
        self.assertTrue(result.iloc[3])

    def test_crossunder(self):
        a = pd.Series([5, 4, 3, 2, 1])
        b = pd.Series([3, 3, 3, 3, 3])
        result = ind.crossunder(a, b)
        self.assertTrue(result.iloc[3])

    def test_highest(self):
        s = pd.Series([1, 5, 3, 2, 4])
        result = ind.highest(s, 3)
        self.assertEqual(result.iloc[-1], 4)

    def test_lowest(self):
        s = pd.Series([1, 5, 3, 2, 4])
        result = ind.lowest(s, 3)
        self.assertEqual(result.iloc[-1], 2)


if __name__ == "__main__":
    unittest.main()
