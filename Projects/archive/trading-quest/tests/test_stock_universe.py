"""Tests for stock universe."""
import os
import tempfile
import unittest

from tq.data.stock_universe import StockUniverse, TOP_US_STOCKS, TOP_KRX_STOCKS, TOP_CRYPTO_PAIRS
from tq.data.cache import DataCache


class TestStockUniverse(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        self.tmp.close()
        self.cache = DataCache(self.tmp.name)
        self.universe = StockUniverse(self.cache)

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_get_all_symbols_us(self):
        symbols = self.universe.get_all_symbols("US")
        self.assertEqual(symbols, TOP_US_STOCKS)

    def test_get_all_symbols_krx(self):
        symbols = self.universe.get_all_symbols("KRX")
        self.assertEqual(symbols, TOP_KRX_STOCKS)

    def test_get_all_symbols_crypto(self):
        symbols = self.universe.get_all_symbols("CRYPTO")
        self.assertEqual(symbols, TOP_CRYPTO_PAIRS)

    def test_build(self):
        symbols = self.universe.build("US")
        self.assertGreater(len(symbols), 0)

    def test_load_triggers_build(self):
        symbols = self.universe.load("US")
        self.assertGreater(len(symbols), 0)


class TestCuratedLists(unittest.TestCase):

    def test_us_stocks_not_empty(self):
        self.assertGreater(len(TOP_US_STOCKS), 50)

    def test_us_stocks_contains_aapl(self):
        self.assertIn("AAPL", TOP_US_STOCKS)

    def test_krx_stocks_not_empty(self):
        self.assertGreater(len(TOP_KRX_STOCKS), 10)

    def test_crypto_pairs_not_empty(self):
        self.assertGreater(len(TOP_CRYPTO_PAIRS), 10)

    def test_crypto_contains_btcusdt(self):
        self.assertIn("BTCUSDT", TOP_CRYPTO_PAIRS)


if __name__ == "__main__":
    unittest.main()
