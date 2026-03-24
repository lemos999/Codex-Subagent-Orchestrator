"""Tests for order executor."""
import unittest

from tq.sim.order import Order, OrderSide, OrderType
from tq.sim.executor import OrderExecutor


class TestOrderExecutor(unittest.TestCase):

    def setUp(self):
        self.executor = OrderExecutor(commission_rate=0.001, slippage_rate=0.0005)

    def test_fill_market_buy(self):
        order = Order("AAPL", OrderSide.BUY, OrderType.MARKET, 10)
        result = self.executor.fill(order, 150.0)
        self.assertIsNotNone(result)
        self.assertGreater(result.fill_price, 150.0)  # slippage
        self.assertEqual(result.fill_qty, 10)
        self.assertGreater(result.commission, 0)

    def test_fill_market_sell(self):
        order = Order("AAPL", OrderSide.SELL, OrderType.MARKET, 10)
        result = self.executor.fill(order, 150.0)
        self.assertIsNotNone(result)
        self.assertLess(result.fill_price, 150.0)  # slippage

    def test_fill_limit_buy_triggered(self):
        order = Order("AAPL", OrderSide.BUY, OrderType.LIMIT, 10, price=150.0)
        result = self.executor.fill(order, 148.0, high=151.0, low=147.0)
        self.assertIsNotNone(result)

    def test_fill_limit_buy_not_triggered(self):
        order = Order("AAPL", OrderSide.BUY, OrderType.LIMIT, 10, price=145.0)
        result = self.executor.fill(order, 150.0, high=152.0, low=148.0)
        self.assertIsNone(result)

    def test_fill_limit_sell_triggered(self):
        order = Order("AAPL", OrderSide.SELL, OrderType.LIMIT, 10, price=155.0)
        result = self.executor.fill(order, 156.0, high=157.0, low=154.0)
        self.assertIsNotNone(result)

    def test_fill_stop_sell_triggered(self):
        order = Order("AAPL", OrderSide.SELL, OrderType.STOP, 10, stop_price=145.0)
        result = self.executor.fill(order, 144.0, high=150.0, low=143.0)
        self.assertIsNotNone(result)

    def test_fill_stop_sell_not_triggered(self):
        order = Order("AAPL", OrderSide.SELL, OrderType.STOP, 10, stop_price=140.0)
        result = self.executor.fill(order, 150.0, high=152.0, low=148.0)
        self.assertIsNone(result)

    def test_limit_no_slippage(self):
        order = Order("AAPL", OrderSide.BUY, OrderType.LIMIT, 10, price=150.0)
        result = self.executor.fill(order, 148.0, high=151.0, low=147.0)
        self.assertIsNotNone(result)
        self.assertEqual(result.slippage, 0.0)


if __name__ == "__main__":
    unittest.main()
