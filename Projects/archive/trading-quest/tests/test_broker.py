"""Tests for simulation broker."""
import unittest

from tq.sim.broker import SimBroker
from tq.sim.order import Order, OrderSide, OrderType


class TestSimBroker(unittest.TestCase):

    def test_initial_state(self):
        broker = SimBroker(100_000)
        self.assertEqual(broker.cash, 100_000)
        self.assertEqual(broker.total_value, 100_000)

    def test_submit_and_process_buy(self):
        broker = SimBroker(100_000)
        order = Order("AAPL", OrderSide.BUY, OrderType.MARKET, 10)
        broker.submit_order(order)
        fills = broker.process_bar("AAPL", 150, 155, 148, 152, "2024-01-15")
        self.assertEqual(len(fills), 1)
        self.assertLess(broker.cash, 100_000)

    def test_submit_and_process_sell(self):
        broker = SimBroker(100_000)
        # Buy first
        buy = Order("AAPL", OrderSide.BUY, OrderType.MARKET, 10)
        broker.submit_order(buy)
        broker.process_bar("AAPL", 150, 155, 148, 152, "2024-01-15")

        # Then sell
        sell = Order("AAPL", OrderSide.SELL, OrderType.MARKET, 10)
        broker.submit_order(sell)
        fills = broker.process_bar("AAPL", 155, 160, 153, 158, "2024-01-16")
        self.assertEqual(len(fills), 1)

    def test_start_and_end_day(self):
        broker = SimBroker(100_000)
        broker.start_day("2024-01-15")
        summary = broker.end_day("2024-01-15")
        self.assertIn("date", summary)
        self.assertEqual(summary["date"], "2024-01-15")

    def test_completed_trades_recorded(self):
        broker = SimBroker(100_000)
        buy = Order("AAPL", OrderSide.BUY, OrderType.MARKET, 10)
        broker.submit_order(buy)
        broker.process_bar("AAPL", 150, 155, 148, 152, "2024-01-15")

        sell = Order("AAPL", OrderSide.SELL, OrderType.MARKET, 10)
        broker.submit_order(sell)
        broker.process_bar("AAPL", 155, 160, 153, 158, "2024-01-16")

        self.assertEqual(len(broker.completed_trades), 1)

    def test_cash_setter(self):
        broker = SimBroker(100_000)
        broker.cash = 50_000
        self.assertEqual(broker.cash, 50_000)


if __name__ == "__main__":
    unittest.main()
