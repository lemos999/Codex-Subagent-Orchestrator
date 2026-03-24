"""Alert manager — dispatches notifications to multiple channels."""
from __future__ import annotations

import logging
from typing import Any

from tq.alert.telegram import TelegramAlert

logger = logging.getLogger(__name__)


class AlertManager:
    """Manages alert channels and dispatches notifications."""

    def __init__(self):
        self.channels: list[Any] = []

    # ------------------------------------------------------------------
    # Channel registration
    # ------------------------------------------------------------------

    def add_telegram(self, bot_token: str, chat_id: str) -> None:
        """Add Telegram channel."""
        if not bot_token or not chat_id:
            logger.warning(
                "Telegram credentials not provided; skipping Telegram channel"
            )
            return
        self.channels.append(TelegramAlert(bot_token, chat_id))
        logger.info("Telegram alert channel added")

    # ------------------------------------------------------------------
    # Dispatchers
    # ------------------------------------------------------------------

    def notify_trade(self, trade: dict) -> None:
        """Notify all channels about a trade."""
        for ch in self.channels:
            try:
                ch.send_trade_alert(trade)
            except Exception:
                logger.warning("Failed to notify trade on %s", type(ch).__name__,
                               exc_info=True)

    def notify_daily(self, quest_id: str, result: dict) -> None:
        """Notify daily summary."""
        for ch in self.channels:
            try:
                ch.send_daily_summary(quest_id, result)
            except Exception:
                logger.warning("Failed to notify daily on %s", type(ch).__name__,
                               exc_info=True)

    def notify_evolution(self, result: dict) -> None:
        """Notify evolution completion."""
        for ch in self.channels:
            try:
                ch.send_evolution_result(result)
            except Exception:
                logger.warning("Failed to notify evolution on %s", type(ch).__name__,
                               exc_info=True)

    def notify_phase(self, quest_id: str, old_phase: int, new_phase: int) -> None:
        """Notify phase transition."""
        for ch in self.channels:
            try:
                ch.send_phase_transition(quest_id, old_phase, new_phase)
            except Exception:
                logger.warning("Failed to notify phase on %s", type(ch).__name__,
                               exc_info=True)
