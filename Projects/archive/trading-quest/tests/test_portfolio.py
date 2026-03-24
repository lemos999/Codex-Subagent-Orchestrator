"""Tests for virtual portfolio."""
import unittest

from tq.sim.portfolio import VirtualPortfolio, Position


class TestPosition(unittest.TestCase):

    def test_market_value(self):
        pos = Position("AAPL", qty=10, avg_price=100, current_price=110)
        self.assertEqual(pos.market_value, 1100)

    def test_unrealized_pnl(self):
        pos = Position("AAPL", qty=10, avg_price=100, current_price=110)
        self.assertEqual(pos.unrealized_pnl, 100)

    def test_unrealized_pnl_pct(self):
        pos = Position("AAPL", qty=10, avg_price=100, current_price=110)
        self.assertAlmostEqual(pos.unrealized_pnl_pct, 0.1)

    def test_to_dict(self):
        pos = Position("AAPL", qty=10, avg_price=100, current_price=110)
        d = pos.to_dict()
        self.assertEqual(d["symbol"], "AAPL")
        self.assertIn("market_value", d)


class TestVirtualPortfolio(unittest.TestCase):

    def test_initial_state(self):
        p = VirtualPortfolio(100_000)
        self.assertEqual(p.cash, 100_000)
        self.assertEqual(p.total_value, 100_000)
        self.assertEqual(len(p.positions), 0)

    def test_buy(self):
        p = VirtualPortfolio(100_000)
        trade = p.buy("AAPL", 10, 150)
        self.assertEqual(p.cash, 98_500)
        self.assertIn("AAPL", p.positions)
        self.assertEqual(p.positions["AAPL"].qty, 10)

    def test_sell(self):
        p = VirtualPortfolio(100_000)
        p.buy("AAPL", 10, 150)
        trade = p.sell("AAPL", 5, 160)
        self.assertEqual(p.positions["AAPL"].qty, 5)
        self.assertIn("pnl", trade)

    def test_sell_all(self):
        p = VirtualPortfolio(100_000)
        p.buy("AAPL", 10, 150)
        p.sell("AAPL", 10, 160)
        self.assertNotIn("AAPL", p.positions)

    def test_buy_insufficient_funds(self):
        p = VirtualPortfolio(100)
        with self.assertRaises(ValueError):
            p.buy("AAPL", 10, 150)

    def test_sell_more_than_held(self):
        p = VirtualPortfolio(100_000)
        p.buy("AAPL", 5, 100)
        with self.assertRaises(ValueError):
            p.sell("AAPL", 10, 100)

    def test_sell_no_position(self):
        p = VirtualPortfolio(100_000)
        with self.assertRaises(ValueError):
            p.sell("AAPL", 5, 100)

    def test_total_value_with_positions(self):
        p = VirtualPortfolio(100_000)
        p.buy("AAPL", 10, 100)  # cost 1000
        p.update_price("AAPL", 110)
        self.assertEqual(p.total_value, 99_000 + 1100)

    def test_current_drawdown_no_loss(self):
        p = VirtualPortfolio(100_000)
        self.assertEqual(p.current_drawdown(), 0.0)

    def test_current_drawdown_with_loss(self):
        p = VirtualPortfolio(100_000)
        p.buy("AAPL", 10, 100)
        p.update_price("AAPL", 50)  # lost 500
        dd = p.current_drawdown()
        self.assertGreater(dd, 0)

    def test_trade_history(self):
        p = VirtualPortfolio(100_000)
        p.buy("AAPL", 10, 100)
        p.sell("AAPL", 10, 110)
        self.assertEqual(len(p.trade_history), 2)

    def test_to_dict(self):
        p = VirtualPortfolio(100_000)
        d = p.to_dict()
        self.assertIn("cash", d)
        self.assertIn("total_value", d)
        self.assertIn("return_pct", d)

    def test_update_price(self):
        p = VirtualPortfolio(100_000)
        p.buy("AAPL", 10, 100)
        p.update_price("AAPL", 120)
        self.assertEqual(p.positions["AAPL"].current_price, 120)

    def test_buy_average_price(self):
        p = VirtualPortfolio(100_000)
        p.buy("AAPL", 10, 100)
        p.buy("AAPL", 10, 200)
        self.assertEqual(p.positions["AAPL"].qty, 20)
        self.assertAlmostEqual(p.positions["AAPL"].avg_price, 150)

    def test_zero_qty_raises(self):
        p = VirtualPortfolio(100_000)
        with self.assertRaises(ValueError):
            p.buy("AAPL", 0, 100)

    def test_negative_price_raises(self):
        p = VirtualPortfolio(100_000)
        with self.assertRaises(ValueError):
            p.buy("AAPL", 10, -5)


if __name__ == "__main__":
    unittest.main()
