"""Tests for P&L tracker."""
import unittest

from tq.sim.pnl import PnLTracker, DaySummary


class TestDaySummary(unittest.TestCase):

    def test_auto_pnl(self):
        ds = DaySummary(date="2024-01-01", starting_value=100000, ending_value=101000)
        self.assertEqual(ds.pnl, 1000)

    def test_auto_return_pct(self):
        ds = DaySummary(date="2024-01-01", starting_value=100000, ending_value=101000)
        self.assertAlmostEqual(ds.return_pct, 1.0)

    def test_win_rate(self):
        ds = DaySummary(date="2024-01-01", starting_value=100000, ending_value=101000,
                        trades=10, wins=7)
        self.assertAlmostEqual(ds.win_rate, 70.0)

    def test_win_rate_no_trades(self):
        ds = DaySummary(date="2024-01-01", starting_value=100000, ending_value=100000)
        self.assertEqual(ds.win_rate, 0.0)

    def test_to_dict(self):
        ds = DaySummary(date="2024-01-01", starting_value=100000, ending_value=101000)
        d = ds.to_dict()
        self.assertIn("pnl", d)
        self.assertIn("win_rate", d)


class TestPnLTracker(unittest.TestCase):

    def test_initial_state(self):
        tracker = PnLTracker(100_000)
        self.assertEqual(tracker.current_value, 100_000)
        self.assertEqual(tracker.total_trades, 0)

    def test_record_trade_win(self):
        tracker = PnLTracker(100_000)
        tracker.record_trade(500, 1.0)
        self.assertEqual(tracker.total_wins, 1)
        self.assertEqual(tracker.total_trades, 1)

    def test_record_trade_loss(self):
        tracker = PnLTracker(100_000)
        tracker.record_trade(-300, 1.0)
        self.assertEqual(tracker.total_losses, 1)

    def test_update_value(self):
        tracker = PnLTracker(100_000)
        tracker.update_value(105_000)
        self.assertEqual(tracker.peak_value, 105_000)

    def test_current_drawdown(self):
        tracker = PnLTracker(100_000)
        tracker.update_value(110_000)
        tracker.current_value = 100_000
        dd = tracker.current_drawdown()
        self.assertAlmostEqual(dd, 10_000 / 110_000, places=4)

    def test_end_day(self):
        tracker = PnLTracker(100_000)
        tracker.start_day("2024-01-01")
        tracker.current_value = 101_000
        summary = tracker.end_day("2024-01-01", trades=3, wins=2)
        self.assertEqual(summary.trades, 3)
        self.assertEqual(len(tracker.daily_summaries), 1)

    def test_total_return(self):
        tracker = PnLTracker(100_000)
        tracker.current_value = 110_000
        self.assertEqual(tracker.total_return, 10_000)
        self.assertAlmostEqual(tracker.total_return_pct, 10.0)

    def test_win_rate(self):
        tracker = PnLTracker(100_000)
        tracker.record_trade(100, 0)
        tracker.record_trade(-50, 0)
        tracker.record_trade(200, 0)
        self.assertAlmostEqual(tracker.win_rate, 200.0 / 3)

    def test_to_dict(self):
        tracker = PnLTracker(100_000)
        d = tracker.to_dict()
        self.assertIn("total_return", d)
        self.assertIn("sharpe_ratio", d)

    def test_sharpe_ratio_no_data(self):
        tracker = PnLTracker(100_000)
        self.assertEqual(tracker.sharpe_ratio, 0.0)


if __name__ == "__main__":
    unittest.main()
