"""Order executor -- fills orders with slippage and commission."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from tq.sim.order import Order, OrderSide, OrderType, FillResult

logger = logging.getLogger(__name__)


class OrderExecutor:
    """Fills orders with realistic slippage and commission models."""

    def __init__(self, commission_rate: float = 0.001,
                 slippage_rate: float = 0.0005):
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate

    def fill(self, order: Order, current_price: float,
             high: Optional[float] = None,
             low: Optional[float] = None,
             timestamp: str = "") -> Optional[FillResult]:
        """Attempt to fill an order at the current price.

        Args:
            order: The order to fill.
            current_price: Current market price.
            high: High of the current bar (for limit/stop checks).
            low: Low of the current bar (for limit/stop checks).
            timestamp: Timestamp string for the fill.

        Returns:
            FillResult if the order can be filled, None otherwise.
        """
        if not timestamp:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if order.order_type == OrderType.MARKET:
            return self._fill_market(order, current_price, timestamp)
        elif order.order_type == OrderType.LIMIT:
            return self._fill_limit(order, current_price, high, low, timestamp)
        elif order.order_type == OrderType.STOP:
            return self._fill_stop(order, current_price, high, low, timestamp)

        logger.warning("Unknown order type: %s", order.order_type)
        return None

    def _fill_market(self, order: Order, price: float,
                     timestamp: str) -> FillResult:
        """Fill a market order with slippage."""
        slippage = price * self.slippage_rate
        if order.is_buy:
            fill_price = price + slippage  # worse price for buyer
        else:
            fill_price = price - slippage  # worse price for seller

        commission = fill_price * order.qty * self.commission_rate
        total_cost = fill_price * order.qty + (commission if order.is_buy else -commission)

        return FillResult(
            order=order,
            fill_price=fill_price,
            fill_qty=order.qty,
            commission=commission,
            slippage=slippage,
            total_cost=total_cost,
            timestamp=timestamp,
        )

    def _fill_limit(self, order: Order, price: float,
                    high: Optional[float], low: Optional[float],
                    timestamp: str) -> Optional[FillResult]:
        """Fill a limit order if the price is favorable."""
        if order.price is None:
            return None

        bar_low = low if low is not None else price
        bar_high = high if high is not None else price

        if order.is_buy and bar_low <= order.price:
            fill_price = min(order.price, price)
        elif order.is_sell and bar_high >= order.price:
            fill_price = max(order.price, price)
        else:
            return None  # not triggered

        commission = fill_price * order.qty * self.commission_rate
        total_cost = fill_price * order.qty + (commission if order.is_buy else -commission)

        return FillResult(
            order=order,
            fill_price=fill_price,
            fill_qty=order.qty,
            commission=commission,
            slippage=0.0,  # limit orders have no slippage
            total_cost=total_cost,
            timestamp=timestamp,
        )

    def _fill_stop(self, order: Order, price: float,
                   high: Optional[float], low: Optional[float],
                   timestamp: str) -> Optional[FillResult]:
        """Fill a stop order if the stop price is breached."""
        stop = order.stop_price or order.price
        if stop is None:
            return None

        bar_low = low if low is not None else price
        bar_high = high if high is not None else price

        triggered = False
        if order.is_sell and bar_low <= stop:
            triggered = True
        elif order.is_buy and bar_high >= stop:
            triggered = True

        if not triggered:
            return None

        # Once triggered, fill as market with slippage
        return self._fill_market(order, price, timestamp)
