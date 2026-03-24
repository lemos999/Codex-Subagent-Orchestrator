"""Abstract base class for live trading brokers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class LiveBroker(ABC):
    """Abstract base for live trading brokers.

    Every broker must implement these methods. The framework calls them
    from LiveRunner; individual implementations handle authentication
    and API specifics.
    """

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to the broker. Returns True on success."""
        ...

    @abstractmethod
    def get_balance(self) -> dict:
        """Return account balance info.

        Expected keys: total, available, currency.
        """
        ...

    @abstractmethod
    def get_positions(self) -> list[dict]:
        """Return current open positions.

        Each dict should have: symbol, qty, avg_price, unrealized_pnl.
        """
        ...

    @abstractmethod
    def place_order(
        self,
        symbol: str,
        side: str,
        qty: float,
        order_type: str = "MARKET",
        price: Optional[float] = None,
    ) -> dict:
        """Place an order. Returns order info dict with at least: order_id, status."""
        ...

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order. Returns True on success."""
        ...

    @abstractmethod
    def get_order_status(self, order_id: str) -> dict:
        """Get status of an order. Returns dict with: order_id, status, filled_qty."""
        ...
