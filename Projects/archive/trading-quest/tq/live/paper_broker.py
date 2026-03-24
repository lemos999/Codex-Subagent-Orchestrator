"""Paper trading broker — simulates live orders using real-time prices."""
from __future__ import annotations

import logging
import uuid
from typing import Optional

from tq.live.broker_base import LiveBroker
from tq.sim.portfolio import VirtualPortfolio

logger = logging.getLogger(__name__)


class PaperBroker(LiveBroker):
    """Paper trading broker — uses real market prices but virtual portfolio.

    Always safe: no real money involved.
    """

    def __init__(self, market: str = "us", initial_capital: float = 100_000.0):
        self.market = market
        self.portfolio = VirtualPortfolio(initial_capital, market)
        self._orders: dict[str, dict] = {}
        self._connected = False

    def connect(self) -> bool:
        """Paper broker is always connected."""
        self._connected = True
        logger.info(
            "Paper broker connected (market=%s, capital=%.2f)",
            self.market, self.portfolio.initial_capital,
        )
        return True

    def get_balance(self) -> dict:
        """Return virtual portfolio balance."""
        return {
            "total": self.portfolio.total_value,
            "available": self.portfolio.cash,
            "currency": "USD" if self.market == "us" else "KRW",
        }

    def get_positions(self) -> list[dict]:
        """Return virtual positions."""
        positions = []
        for symbol, pos in self.portfolio.positions.items():
            qty = pos.qty if hasattr(pos, "qty") else pos
            avg_price = pos.avg_price if hasattr(pos, "avg_price") else 0.0
            unrealized = pos.unrealized_pnl if hasattr(pos, "unrealized_pnl") else 0.0
            positions.append({
                "symbol": symbol,
                "qty": qty,
                "avg_price": avg_price,
                "unrealized_pnl": unrealized,
            })
        return positions

    def place_order(
        self,
        symbol: str,
        side: str,
        qty: float,
        order_type: str = "MARKET",
        price: Optional[float] = None,
    ) -> dict:
        """Execute a paper trade.

        For MARKET orders, *price* should be provided (current market price).
        If not provided, the order is rejected — paper broker needs a price
        to simulate fills.
        """
        if price is None or price <= 0:
            logger.warning("Paper broker: price required for paper trades")
            return {
                "order_id": "",
                "status": "REJECTED",
                "error": "price_required",
            }

        order_id = str(uuid.uuid4())[:8]
        side_upper = side.upper()

        try:
            if side_upper == "BUY":
                trade = self.portfolio.buy(symbol, qty, price)
            elif side_upper == "SELL":
                trade = self.portfolio.sell(symbol, qty, price)
            else:
                return {
                    "order_id": order_id,
                    "status": "REJECTED",
                    "error": f"unknown_side: {side}",
                }

            order = {
                "order_id": order_id,
                "status": "FILLED",
                "symbol": symbol,
                "side": side_upper,
                "qty": qty,
                "filled_qty": qty,
                "price": price,
                "trade": trade,
            }
            self._orders[order_id] = order
            logger.info(
                "Paper %s %s x%.4f @ %.2f (id=%s)",
                side_upper, symbol, qty, price, order_id,
            )
            return order

        except ValueError as e:
            logger.warning("Paper order rejected: %s", e)
            return {
                "order_id": order_id,
                "status": "REJECTED",
                "error": str(e),
            }

    def cancel_order(self, order_id: str) -> bool:
        """Cancel a paper order (only if not yet filled)."""
        order = self._orders.get(order_id)
        if not order:
            return False
        if order["status"] == "FILLED":
            logger.warning("Cannot cancel filled order %s", order_id)
            return False
        order["status"] = "CANCELLED"
        return True

    def get_order_status(self, order_id: str) -> dict:
        """Get paper order status."""
        order = self._orders.get(order_id)
        if not order:
            return {"order_id": order_id, "status": "NOT_FOUND", "filled_qty": 0}
        return {
            "order_id": order_id,
            "status": order["status"],
            "filled_qty": order.get("filled_qty", 0),
        }
