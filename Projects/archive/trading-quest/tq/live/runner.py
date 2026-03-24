"""Live runner — executes a strategy in live/paper mode with real-time data."""
from __future__ import annotations

import logging
import time
from typing import Optional, Any

from tq.live.broker_base import LiveBroker
from tq.strategy.base import BaseStrategy

logger = logging.getLogger(__name__)


class LiveRunner:
    """Runs a strategy in live/paper mode with real-time data.

    Fetches latest market data, runs the strategy, and executes signals
    through the broker.
    """

    def __init__(
        self,
        broker: LiveBroker,
        strategy: BaseStrategy,
        market: str,
        symbols: list[str],
        alert_manager: Optional[Any] = None,
        data_fetcher: Optional[Any] = None,
    ):
        self.broker = broker
        self.strategy = strategy
        self.market = market
        self.symbols = symbols
        self.alert_manager = alert_manager
        self.data_fetcher = data_fetcher
        self._running = False

    def run_once(self) -> dict:
        """Fetch latest data, run strategy, execute signals.

        Returns a summary dict of actions taken.
        """
        results: list[dict] = []

        for symbol in self.symbols:
            try:
                # Fetch latest candle data
                data = None
                if self.data_fetcher:
                    data = self.data_fetcher.fetch_latest(symbol)

                if data is None or (hasattr(data, "empty") and data.empty):
                    logger.debug("No data for %s, skipping", symbol)
                    continue

                # Run strategy
                signals = self.strategy.decide(data, None)

                # Execute signals
                for signal in signals:
                    sig_symbol = signal.get("symbol", symbol)
                    side = signal.get("side", "").upper()
                    qty = signal.get("qty", 0)
                    price = signal.get("price")

                    if not side or qty <= 0:
                        continue

                    order = self.broker.place_order(
                        symbol=sig_symbol,
                        side=side,
                        qty=qty,
                        order_type=signal.get("order_type", "MARKET"),
                        price=price,
                    )
                    results.append(order)

                    # Alert on fill
                    if order.get("status") == "FILLED" and self.alert_manager:
                        try:
                            self.alert_manager.notify_trade({
                                "symbol": sig_symbol,
                                "side": side,
                                "qty": qty,
                                "price": price or 0,
                                "strategy": self.strategy.name,
                            })
                        except Exception:
                            logger.warning("Alert failed", exc_info=True)

            except Exception:
                logger.error("Error processing %s", symbol, exc_info=True)

        return {
            "symbols_checked": len(self.symbols),
            "orders_placed": len(results),
            "orders": results,
        }

    def start_loop(self, interval_seconds: int = 60) -> None:
        """Run continuously at the specified interval.

        Press Ctrl+C to stop.
        """
        logger.info(
            "Starting live loop: %s symbols, interval=%ds",
            len(self.symbols), interval_seconds,
        )
        self._running = True
        try:
            while self._running:
                result = self.run_once()
                logger.info(
                    "Loop tick: %d orders placed",
                    result.get("orders_placed", 0),
                )
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            logger.info("Live loop stopped by user")
            self._running = False

    def stop(self) -> None:
        """Stop the live loop."""
        self._running = False
