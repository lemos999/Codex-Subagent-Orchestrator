"""Order types and fill results for the simulation engine."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"


@dataclass
class Order:
    """A trading order."""
    symbol: str
    side: OrderSide
    order_type: OrderType
    qty: float
    price: Optional[float] = None      # limit / stop price
    stop_price: Optional[float] = None  # for stop orders
    strategy: str = ""
    confidence: float = 0.0
    timestamp: str = ""

    @property
    def is_buy(self) -> bool:
        return self.side == OrderSide.BUY

    @property
    def is_sell(self) -> bool:
        return self.side == OrderSide.SELL


@dataclass
class FillResult:
    """Result of filling an order."""
    order: Order
    fill_price: float
    fill_qty: float
    commission: float
    slippage: float
    total_cost: float  # fill_price * fill_qty + commission (for buys)
    timestamp: str = ""
    success: bool = True

    @property
    def net_proceeds(self) -> float:
        """Net proceeds for sell orders (after commission)."""
        if self.order.is_sell:
            return self.fill_price * self.fill_qty - self.commission
        return -(self.fill_price * self.fill_qty + self.commission)


@dataclass
class CompletedTrade:
    """A completed round-trip trade (buy + sell or short + cover)."""
    symbol: str
    entry_price: float
    exit_price: float
    qty: float
    entry_time: str = ""
    exit_time: str = ""
    pnl: float = 0.0
    pnl_pct: float = 0.0
    commission_total: float = 0.0
    strategy: str = ""
    holding_period: int = 0  # in minutes or days
    is_short: bool = False   # True if this was a short trade

    def __post_init__(self) -> None:
        if self.pnl == 0.0 and self.entry_price > 0:
            if self.is_short:
                # Short: profit when price drops
                self.pnl = (self.entry_price - self.exit_price) * self.qty - self.commission_total
                self.pnl_pct = (self.entry_price - self.exit_price) / self.entry_price
            else:
                # Long: profit when price rises
                self.pnl = (self.exit_price - self.entry_price) * self.qty - self.commission_total
                self.pnl_pct = (self.exit_price - self.entry_price) / self.entry_price

    @property
    def is_win(self) -> bool:
        return self.pnl > 0

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "qty": self.qty,
            "entry_time": self.entry_time,
            "exit_time": self.exit_time,
            "pnl": self.pnl,
            "pnl_pct": self.pnl_pct,
            "commission_total": self.commission_total,
            "strategy": self.strategy,
            "holding_period": self.holding_period,
            "is_win": self.is_win,
        }
