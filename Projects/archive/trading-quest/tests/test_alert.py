"""Tests for alert module."""
import unittest
from unittest.mock import patch, MagicMock

from tq.alert.telegram import TelegramAlert
from tq.alert.manager import AlertManager


class TestTelegramAlert(unittest.TestCase):
    """Test TelegramAlert formatting and graceful degradation."""

    def test_send_returns_false_when_not_configured(self):
        alert = TelegramAlert("", "")
        self.assertFalse(alert.send("hello"))

    def test_send_returns_false_when_token_missing(self):
        alert = TelegramAlert("", "12345")
        self.assertFalse(alert.send("hello"))

    def test_send_returns_false_when_chat_id_missing(self):
        alert = TelegramAlert("some_token", "")
        self.assertFalse(alert.send("hello"))

    @patch("tq.alert.telegram.urllib.request.urlopen")
    def test_send_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"ok": true}'
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        alert = TelegramAlert("token123", "chat456")
        self.assertTrue(alert.send("test message"))

    @patch("tq.alert.telegram.urllib.request.urlopen")
    def test_send_api_failure(self, mock_urlopen):
        mock_urlopen.side_effect = Exception("network error")
        alert = TelegramAlert("token123", "chat456")
        self.assertFalse(alert.send("test"))

    def test_send_trade_alert_format(self):
        """Test that trade alert calls send with correct format."""
        alert = TelegramAlert("tok", "chat")
        with patch.object(alert, "send", return_value=True) as mock_send:
            alert.send_trade_alert({
                "side": "BUY",
                "symbol": "AAPL",
                "price": 150.25,
                "qty": 10,
                "strategy": "macd",
                "confidence": 0.8,
            })
            msg = mock_send.call_args[0][0]
            self.assertIn("BUY", msg)
            self.assertIn("AAPL", msg)
            self.assertIn("150.25", msg)

    def test_send_daily_summary_format(self):
        alert = TelegramAlert("tok", "chat")
        with patch.object(alert, "send", return_value=True) as mock_send:
            alert.send_daily_summary("q-test", {
                "date": "2024-01-15",
                "return_pct": 1.23,
                "trades": 3,
                "score": 1234,
                "win_rate": 66.7,
            })
            msg = mock_send.call_args[0][0]
            self.assertIn("q-test", msg)
            self.assertIn("+1.23%", msg)

    def test_send_phase_transition_format(self):
        alert = TelegramAlert("tok", "chat")
        with patch.object(alert, "send", return_value=True) as mock_send:
            alert.send_phase_transition("q-test", 1, 2)
            msg = mock_send.call_args[0][0]
            self.assertIn("Phase 1", msg)
            self.assertIn("Phase 2", msg)

    def test_send_evolution_result_format(self):
        alert = TelegramAlert("tok", "chat")
        with patch.object(alert, "send", return_value=True) as mock_send:
            alert.send_evolution_result({
                "generation": 5,
                "best_strategy": "evo_gen5_001",
                "best_score": 9999,
                "population_size": 20,
            })
            msg = mock_send.call_args[0][0]
            self.assertIn("evo_gen5_001", msg)


class TestAlertManager(unittest.TestCase):
    """Test AlertManager dispatching."""

    def test_add_telegram_without_credentials(self):
        mgr = AlertManager()
        mgr.add_telegram("", "")
        self.assertEqual(len(mgr.channels), 0)

    def test_add_telegram_with_credentials(self):
        mgr = AlertManager()
        mgr.add_telegram("token", "chat")
        self.assertEqual(len(mgr.channels), 1)

    def test_notify_trade_dispatches(self):
        mgr = AlertManager()
        mock_channel = MagicMock()
        mgr.channels.append(mock_channel)
        mgr.notify_trade({"side": "BUY", "symbol": "AAPL"})
        mock_channel.send_trade_alert.assert_called_once()

    def test_notify_daily_dispatches(self):
        mgr = AlertManager()
        mock_channel = MagicMock()
        mgr.channels.append(mock_channel)
        mgr.notify_daily("q-1", {"date": "2024-01-01"})
        mock_channel.send_daily_summary.assert_called_once()

    def test_notify_evolution_dispatches(self):
        mgr = AlertManager()
        mock_channel = MagicMock()
        mgr.channels.append(mock_channel)
        mgr.notify_evolution({"generation": 1})
        mock_channel.send_evolution_result.assert_called_once()

    def test_notify_phase_dispatches(self):
        mgr = AlertManager()
        mock_channel = MagicMock()
        mgr.channels.append(mock_channel)
        mgr.notify_phase("q-1", 1, 2)
        mock_channel.send_phase_transition.assert_called_once()

    def test_channel_exception_does_not_crash(self):
        mgr = AlertManager()
        mock_channel = MagicMock()
        mock_channel.send_trade_alert.side_effect = RuntimeError("boom")
        mgr.channels.append(mock_channel)
        # Should not raise
        mgr.notify_trade({"side": "BUY"})


if __name__ == "__main__":
    unittest.main()
