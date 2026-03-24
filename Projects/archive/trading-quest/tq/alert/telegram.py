"""Telegram alert channel — sends trading notifications via Telegram Bot API."""
from __future__ import annotations

import logging
import urllib.request
import urllib.parse
import json

logger = logging.getLogger(__name__)


class TelegramAlert:
    """Send trading alerts via Telegram bot."""

    BASE_URL = "https://api.telegram.org/bot{token}/sendMessage"

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id

    # ------------------------------------------------------------------
    # Low-level send
    # ------------------------------------------------------------------

    def send(self, message: str) -> bool:
        """Send a text message. Returns True on success."""
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram not configured (missing token or chat_id)")
            return False

        url = self.BASE_URL.format(token=self.bot_token)
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "Markdown",
        }
        data = json.dumps(payload).encode("utf-8")

        try:
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                if body.get("ok"):
                    return True
                logger.warning("Telegram API returned ok=false: %s", body)
                return False
        except Exception:
            logger.warning("Telegram send failed", exc_info=True)
            return False

    # ------------------------------------------------------------------
    # Formatted alerts
    # ------------------------------------------------------------------

    def send_trade_alert(self, trade: dict) -> bool:
        """Format and send a trade alert.

        Expected keys: side, symbol, price, qty, strategy (optional),
        confidence (optional).
        """
        side = trade.get("side", "?").upper()
        icon = "\U0001f7e2" if side == "BUY" else "\U0001f534"  # green / red circle
        symbol = trade.get("symbol", "???")
        price = trade.get("price", 0)
        qty = trade.get("qty", 0)
        strategy = trade.get("strategy", "-")
        confidence = trade.get("confidence", "-")

        msg = (
            f"{icon} {side} {symbol}\n"
            f"Price: ${price:,.2f} | Qty: {qty}\n"
            f"Strategy: {strategy} | Confidence: {confidence}"
        )
        return self.send(msg)

    def send_daily_summary(self, quest_id: str, day_result: dict) -> bool:
        """Send daily quest summary."""
        day_date = day_result.get("date", "?")
        return_pct = day_result.get("return_pct", 0)
        trades = day_result.get("trades", 0)
        score = day_result.get("score", 0)
        win_rate = day_result.get("win_rate", 0)

        sign = "+" if return_pct >= 0 else ""
        msg = (
            f"\U0001f4ca Daily Summary [{day_date}]\n"
            f"Quest: {quest_id}\n"
            f"Return: {sign}{return_pct:.2f}% | Trades: {trades}\n"
            f"Score: {score:,.0f} pts | WR: {win_rate:.1f}%"
        )
        return self.send(msg)

    def send_evolution_result(self, result: dict) -> bool:
        """Send evolution completion alert."""
        gen = result.get("generation", "?")
        best_name = result.get("best_strategy", "?")
        best_score = result.get("best_score", 0)
        pop_size = result.get("population_size", 0)

        msg = (
            f"\U0001f9ec Evolution Complete\n"
            f"Generation: {gen} | Pop: {pop_size}\n"
            f"Best: {best_name} ({best_score:,.0f} pts)"
        )
        return self.send(msg)

    def send_phase_transition(self, quest_id: str, old_phase: int, new_phase: int) -> bool:
        """Alert on phase change."""
        msg = (
            f"\U0001f680 Phase Transition\n"
            f"Quest: {quest_id}\n"
            f"Phase {old_phase} -> Phase {new_phase}"
        )
        return self.send(msg)
