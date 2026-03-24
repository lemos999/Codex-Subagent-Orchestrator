"""Tests for live trading module."""
import unittest
from unittest.mock import MagicMock, patch

from tq.live.broker_base import LiveBroker
from tq.live.paper_broker import PaperBroker
from tq.live.runner import LiveRunner
from tq.strategy.base import BaseStrategy


class DummyStrategy(BaseStrategy):
    name = "dummy"

    def decide(self, data, portfolio):
        return []


class TestPaperBroker(unittest.TestCase):
    """Test PaperBroker end-to-end."""

    def test_connect(self):
        broker = PaperBroker(market="us", initial_capital=10_000)
        self.assertTrue(broker.connect())

    def test_get_balance(self):
        broker = PaperBroker(initial_capital=50_000)
        broker.connect()
        bal = broker.get_balance()
        self.assertEqual(bal["available"], 50_000)

    def test_buy_and_sell(self):
        broker = PaperBroker(initial_capital=10_000)
        broker.connect()

        # Buy
        order = broker.place_order("AAPL", "BUY", 10, "MARKET", price=100.0)
        self.assertEqual(order["status"], "FILLED")
        self.assertEqual(order["filled_qty"], 10)

        # Check balance
        bal = broker.get_balance()
        self.assertAlmostEqual(bal["available"], 9_000.0)

        # Check positions
        positions = broker.get_positions()
        self.assertEqual(len(positions), 1)
        self.assertEqual(positions[0]["symbol"], "AAPL")
        self.assertEqual(positions[0]["qty"], 10)

        # Sell
        order = broker.place_order("AAPL", "SELL", 5, "MARKET", price=110.0)
        self.assertEqual(order["status"], "FILLED")

        bal = broker.get_balance()
        self.assertAlmostEqual(bal["available"], 9_550.0)

    def test_buy_insufficient_funds(self):
        broker = PaperBroker(initial_capital=100)
        broker.connect()
        order = broker.place_order("AAPL", "BUY", 10, "MARKET", price=100.0)
        self.assertEqual(order["status"], "REJECTED")

    def test_sell_more_than_held(self):
        broker = PaperBroker(initial_capital=10_000)
        broker.connect()
        broker.place_order("AAPL", "BUY", 5, "MARKET", price=100.0)
        order = broker.place_order("AAPL", "SELL", 10, "MARKET", price=100.0)
        self.assertEqual(order["status"], "REJECTED")

    def test_order_without_price_rejected(self):
        broker = PaperBroker(initial_capital=10_000)
        broker.connect()
        order = broker.place_order("AAPL", "BUY", 10, "MARKET")
        self.assertEqual(order["status"], "REJECTED")

    def test_get_order_status(self):
        broker = PaperBroker(initial_capital=10_000)
        broker.connect()
        order = broker.place_order("AAPL", "BUY", 1, "MARKET", price=100.0)
        status = broker.get_order_status(order["order_id"])
        self.assertEqual(status["status"], "FILLED")

    def test_get_order_status_not_found(self):
        broker = PaperBroker(initial_capital=10_000)
        status = broker.get_order_status("nonexistent")
        self.assertEqual(status["status"], "NOT_FOUND")

    def test_cancel_filled_order(self):
        broker = PaperBroker(initial_capital=10_000)
        broker.connect()
        order = broker.place_order("AAPL", "BUY", 1, "MARKET", price=100.0)
        self.assertFalse(broker.cancel_order(order["order_id"]))

    def test_unknown_side_rejected(self):
        broker = PaperBroker(initial_capital=10_000)
        broker.connect()
        order = broker.place_order("AAPL", "SHORT", 1, "MARKET", price=100.0)
        self.assertEqual(order["status"], "REJECTED")


class TestLiveRunner(unittest.TestCase):
    """Test LiveRunner logic."""

    def test_run_once_no_data(self):
        broker = PaperBroker(initial_capital=10_000)
        broker.connect()
        strategy = DummyStrategy()
        runner = LiveRunner(broker, strategy, "us", ["AAPL"])
        result = runner.run_once()
        self.assertEqual(result["orders_placed"], 0)

    def test_run_once_with_signals(self):
        broker = PaperBroker(initial_capital=10_000)
        broker.connect()

        strategy = DummyStrategy()
        strategy.decide = MagicMock(return_value=[
            {"symbol": "AAPL", "side": "BUY", "qty": 1, "price": 100.0}
        ])

        # Mock data fetcher
        fetcher = MagicMock()
        fetcher.fetch_latest.return_value = MagicMock(empty=False)

        runner = LiveRunner(broker, strategy, "us", ["AAPL"],
                            data_fetcher=fetcher)
        result = runner.run_once()
        self.assertEqual(result["orders_placed"], 1)

    def test_stop(self):
        broker = PaperBroker(initial_capital=10_000)
        broker.connect()
        runner = LiveRunner(broker, DummyStrategy(), "us", ["AAPL"])
        runner._running = True
        runner.stop()
        self.assertFalse(runner._running)


class TestBrokerBaseIsAbstract(unittest.TestCase):
    """Verify LiveBroker cannot be instantiated directly."""

    def test_cannot_instantiate(self):
        with self.assertRaises(TypeError):
            LiveBroker()  # type: ignore[abstract]


if __name__ == "__main__":
    unittest.main()
