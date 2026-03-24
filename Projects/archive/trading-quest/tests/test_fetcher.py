"""Tests for data fetcher."""
import unittest

from tq.data.fetcher import (
    DataFetcher, YFinanceFetcher, KRXFetcher, BinanceFetcher, get_fetcher,
)


class TestGetFetcher(unittest.TestCase):

    def test_us_fetcher(self):
        f = get_fetcher("US")
        self.assertIsInstance(f, YFinanceFetcher)

    def test_krx_fetcher(self):
        f = get_fetcher("KRX")
        self.assertIsInstance(f, KRXFetcher)

    def test_crypto_fetcher(self):
        f = get_fetcher("CRYPTO")
        self.assertIsInstance(f, BinanceFetcher)

    def test_case_insensitive(self):
        f = get_fetcher("us")
        self.assertIsInstance(f, YFinanceFetcher)


class TestYFinanceFetcher(unittest.TestCase):

    def test_get_top_symbols(self):
        f = YFinanceFetcher()
        symbols = f.get_top_symbols(10)
        self.assertEqual(len(symbols), 10)
        self.assertIn("AAPL", symbols)

    def test_get_all_symbols(self):
        f = YFinanceFetcher()
        symbols = f.get_all_symbols()
        self.assertGreater(len(symbols), 0)


class TestKRXFetcher(unittest.TestCase):

    def test_get_top_symbols(self):
        f = KRXFetcher()
        symbols = f.get_top_symbols(5)
        self.assertEqual(len(symbols), 5)

    def test_market_attribute(self):
        f = KRXFetcher()
        self.assertEqual(f.market, "KRX")


class TestBinanceFetcher(unittest.TestCase):

    def test_get_top_symbols(self):
        f = BinanceFetcher()
        symbols = f.get_top_symbols(5)
        self.assertEqual(len(symbols), 5)
        self.assertIn("BTCUSDT", symbols)

    def test_market_attribute(self):
        f = BinanceFetcher()
        self.assertEqual(f.market, "CRYPTO")


class TestDataFetcherABC(unittest.TestCase):

    def test_cannot_instantiate(self):
        with self.assertRaises(TypeError):
            DataFetcher()


if __name__ == "__main__":
    unittest.main()
