"""Tests for order types."""
import unittest

from tq.sim.order import Order, OrderSide, OrderType, FillResult, CompletedTrade


class TestOrder(unittest.TestCase):

    def test_buy_order(self):
        o = Order("AAPL", OrderSide.BUY, OrderType.MARKET, 10)
        self.assertTrue(o.is_buy)
        self.assertFalse(o.is_sell)

    def test_sell_order(self):
        o = Order("AAPL", OrderSide.SELL, OrderType.MARKET, 10)
        self.assertTrue(o.is_sell)
        self.assertFalse(o.is_buy)

    def test_limit_order(self):
        o = Order("AAPL", OrderSide.BUY, OrderType.LIMIT, 10, price=150.0)
        self.assertEqual(o.price, 150.0)

    def test_stop_order(self):
        o = Order("AAPL", OrderSide.SELL, OrderType.STOP, 10, stop_price=140.0)
        self.assertEqual(o.stop_price, 140.0)


class TestFillResult(unittest.TestCase):

    def test_net_proceeds_sell(self):
        order = Order("AAPL", OrderSide.SELL, OrderType.MARKET, 10)
        fill = FillResult(order=order, fill_price=150.0, fill_qty=10,
                         commission=1.5, slippage=0.1, total_cost=1498.5)
        self.assertGreater(fill.net_proceeds, 0)

    def test_net_proceeds_buy(self):
        order = Order("AAPL", OrderSide.BUY, OrderType.MARKET, 10)
        fill = FillResult(order=order, fill_price=150.0, fill_qty=10,
                         commission=1.5, slippage=0.1, total_cost=1501.5)
        self.assertLess(fill.net_proceeds, 0)


class TestCompletedTrade(unittest.TestCase):

    def test_winning_trade(self):
        ct = CompletedTrade("AAPL", entry_price=100, exit_price=110, qty=10)
        self.assertTrue(ct.is_win)
        self.assertGreater(ct.pnl, 0)

    def test_losing_trade(self):
        ct = CompletedTrade("AAPL", entry_price=110, exit_price=100, qty=10)
        self.assertFalse(ct.is_win)
        self.assertLess(ct.pnl, 0)

    def test_to_dict(self):
        ct = CompletedTrade("AAPL", entry_price=100, exit_price=110, qty=10)
        d = ct.to_dict()
        self.assertEqual(d["symbol"], "AAPL")
        self.assertIn("pnl", d)
        self.assertIn("is_win", d)

    def test_pnl_pct(self):
        ct = CompletedTrade("AAPL", entry_price=100, exit_price=110, qty=10)
        self.assertAlmostEqual(ct.pnl_pct, 0.1, places=2)


if __name__ == "__main__":
    unittest.main()
