"""Simulation broker -- ties together portfolio, executor, and P&L tracking."""
from __future__ import annotations

import logging
from typing import Optional

from tq.sim.order import Order, OrderSide, OrderType, FillResult, CompletedTrade
from tq.sim.portfolio import VirtualPortfolio
from tq.sim.executor import OrderExecutor
from tq.sim.pnl import PnLTracker

logger = logging.getLogger(__name__)


class SimBroker:
    """Simulation broker that ties portfolio + executor + P&L tracker."""

    def __init__(self, initial_capital: float, market: str = "US",
                 commission_rate: float = 0.001,
                 slippage_rate: float = 0.0005,
                 allow_short: bool = False):
        self.portfolio = VirtualPortfolio(initial_capital, market)
        self.executor = OrderExecutor(commission_rate, slippage_rate)
        self.pnl = PnLTracker(initial_capital)
        self.market = market
        self.allow_short = allow_short
        self.pending_orders: list[Order] = []
        self.filled_orders: list[FillResult] = []
        self.completed_trades: list[CompletedTrade] = []
        self._entry_prices: dict[str, float] = {}  # symbol -> entry price
        self._entry_times: dict[str, str] = {}

    def submit_order(self, order: Order) -> None:
        """Submit an order for execution."""
        self.pending_orders.append(order)

    def process_bar(self, symbol: str, open_: float, high: float,
                    low: float, close: float, timestamp: str = "") -> list[FillResult]:
        """Process a price bar, attempting to fill pending orders."""
        self.portfolio.update_price(symbol, close)
        fills: list[FillResult] = []

        remaining = []
        for order in self.pending_orders:
            if order.symbol != symbol:
                remaining.append(order)
                continue

            result = self.executor.fill(
                order, close, high=high, low=low, timestamp=timestamp
            )
            if result is None:
                remaining.append(order)
                continue

            # Execute in portfolio
            try:
                # Check if this is covering a short position
                pos = self.portfolio.positions.get(symbol)
                is_short_cover = (order.is_buy and pos is not None and pos.qty < 0)
                is_short_open = (order.is_sell and (pos is None or pos.qty <= 0)
                                 and self.allow_short)

                if order.is_buy and is_short_cover:
                    self.portfolio.buy_to_cover(symbol, result.fill_qty, result.fill_price)
                elif order.is_buy:
                    self.portfolio.buy(symbol, result.fill_qty, result.fill_price)
                    self._entry_prices[symbol] = result.fill_price
                    self._entry_times[symbol] = timestamp
                else:
                    self.portfolio.sell(symbol, result.fill_qty, result.fill_price,
                                       allow_short=self.allow_short)

                # Track entry for completed trade recording
                if order.is_buy and not is_short_cover:
                    pass  # already set above
                elif order.is_sell and is_short_open:
                    self._entry_prices[symbol] = result.fill_price
                    self._entry_times[symbol] = timestamp

                # Record completed trade for position closures
                is_close = (order.is_sell and not is_short_open) or is_short_cover
                if is_close:
                    entry_price = self._entry_prices.pop(symbol, result.fill_price)
                    entry_time = self._entry_times.pop(symbol, "")

                    # Record completed trade
                    ct = CompletedTrade(
                        symbol=symbol,
                        entry_price=entry_price,
                        exit_price=result.fill_price,
                        qty=result.fill_qty,
                        entry_time=entry_time,
                        is_short=is_short_cover,
                        exit_time=timestamp,
                        commission_total=result.commission * 2,  # entry + exit
                        strategy=order.strategy,
                    )
                    self.completed_trades.append(ct)
                    self.pnl.record_trade(ct.pnl, ct.commission_total)

                self.filled_orders.append(result)
                fills.append(result)
            except ValueError as e:
                logger.warning("Order fill failed in portfolio: %s", e)
                remaining.append(order)

        self.pending_orders = remaining
        self.pnl.update_value(self.portfolio.total_value)
        return fills

    def start_day(self, date: str) -> None:
        """Mark start of a trading day."""
        self.pnl.start_day(date)

    def end_day(self, date: str) -> dict:
        """Mark end of a trading day. Returns day summary."""
        day_trades = [f for f in self.filled_orders
                      if f.timestamp.startswith(date)]
        day_completed = [ct for ct in self.completed_trades
                         if ct.exit_time.startswith(date)]
        wins = sum(1 for ct in day_completed if ct.is_win)
        losses = sum(1 for ct in day_completed if not ct.is_win and ct.pnl != 0)
        commission = sum(f.commission for f in day_trades)

        summary = self.pnl.end_day(
            date=date,
            trades=len(day_trades),
            wins=wins,
            losses=losses,
            commission=commission,
        )
        return summary.to_dict()

    @property
    def cash(self) -> float:
        return self.portfolio.cash

    @cash.setter
    def cash(self, value: float) -> None:
        self.portfolio.cash = value

    @property
    def total_value(self) -> float:
        return self.portfolio.total_value
