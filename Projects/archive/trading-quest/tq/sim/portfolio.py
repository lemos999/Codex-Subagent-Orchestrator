"""Virtual portfolio for paper/sim trading."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Position:
    """A position in a single symbol."""
    symbol: str
    qty: float
    avg_price: float
    current_price: float = 0.0

    @property
    def market_value(self) -> float:
        return self.qty * self.current_price

    @property
    def cost_basis(self) -> float:
        return self.qty * self.avg_price

    @property
    def unrealized_pnl(self) -> float:
        return self.market_value - self.cost_basis

    @property
    def unrealized_pnl_pct(self) -> float:
        if self.cost_basis == 0:
            return 0.0
        return self.unrealized_pnl / self.cost_basis

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "qty": self.qty,
            "avg_price": self.avg_price,
            "current_price": self.current_price,
            "market_value": self.market_value,
            "unrealized_pnl": self.unrealized_pnl,
        }


class VirtualPortfolio:
    """Tracks cash, positions, and P&L for simulated trading."""

    def __init__(self, initial_capital: float, market: str = "us"):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.market = market
        self.positions: dict[str, Position] = {}
        self.trades: list[dict] = []
        self.trade_history: list[dict] = []
        self._peak_value = initial_capital
        self._prices: dict[str, float] = {}  # last known prices

    def update_price(self, symbol: str, price: float) -> None:
        """Update the current price of a symbol."""
        self._prices[symbol] = price
        if symbol in self.positions:
            self.positions[symbol].current_price = price

    @property
    def total_value(self) -> float:
        """Total portfolio value: cash + longs - short liabilities."""
        value = self.cash
        for p in self.positions.values():
            if p.qty >= 0:
                value += p.qty * p.current_price  # long: market value
            else:
                # short: unrealized P&L = (entry - current) * abs(qty)
                value += (p.avg_price - p.current_price) * abs(p.qty)
        return value

    def buy(self, symbol: str, qty: float, price: float) -> dict:
        """Buy shares. Returns trade dict."""
        if qty <= 0 or price <= 0:
            raise ValueError("qty and price must be positive")
        cost = qty * price
        if cost > self.cash:
            raise ValueError(f"Insufficient cash: need {cost:.2f}, have {self.cash:.2f}")
        self.cash -= cost
        self._prices[symbol] = price

        if symbol in self.positions:
            pos = self.positions[symbol]
            total_qty = pos.qty + qty
            pos.avg_price = (pos.avg_price * pos.qty + price * qty) / total_qty
            pos.qty = total_qty
            pos.current_price = price
        else:
            self.positions[symbol] = Position(
                symbol=symbol, qty=qty, avg_price=price, current_price=price
            )

        trade = {
            "symbol": symbol, "side": "BUY", "qty": qty,
            "price": price, "cost": cost,
        }
        self.trades.append(trade)
        self.trade_history.append(trade)
        self.update_peak()
        return trade

    def sell(self, symbol: str, qty: float, price: float,
             allow_short: bool = False) -> dict:
        """Sell shares. If allow_short=True, allows short selling (negative qty)."""
        if qty <= 0 or price <= 0:
            raise ValueError("qty and price must be positive")

        has_position = symbol in self.positions
        current_qty = self.positions[symbol].qty if has_position else 0.0

        if current_qty <= 0 and not allow_short:
            raise ValueError(f"No long position in {symbol}")
        if qty > current_qty and not allow_short:
            raise ValueError(f"Cannot sell {qty} {symbol}, only hold {current_qty}")

        proceeds = qty * price
        self.cash += proceeds
        self._prices[symbol] = price

        if has_position:
            pos = self.positions[symbol]
            pnl = (price - pos.avg_price) * min(qty, max(0, pos.qty))
            pos.qty -= qty
            pos.current_price = price

            if pos.qty < 0:
                # Went short — update avg_price to short entry price
                pos.avg_price = price
            if abs(pos.qty) < 1e-10:
                del self.positions[symbol]
        else:
            # New short position
            pnl = 0.0
            self.positions[symbol] = Position(
                symbol=symbol, qty=-qty, avg_price=price, current_price=price
            )

        trade = {
            "symbol": symbol, "side": "SELL", "qty": qty,
            "price": price, "proceeds": proceeds, "pnl": pnl,
        }
        self.trades.append(trade)
        self.trade_history.append(trade)
        self.update_peak()
        return trade

    def buy_to_cover(self, symbol: str, qty: float, price: float) -> dict:
        """Close a short position by buying back."""
        if symbol not in self.positions:
            raise ValueError(f"No position in {symbol}")
        pos = self.positions[symbol]
        if pos.qty >= 0:
            raise ValueError(f"{symbol} is not a short position")

        short_qty = abs(pos.qty)
        cover_qty = min(qty, short_qty)
        cost = cover_qty * price
        self.cash -= cost
        self._prices[symbol] = price

        # PnL for short: profit when price drops (entry - exit)
        pnl = (pos.avg_price - price) * cover_qty

        pos.qty += cover_qty
        pos.current_price = price
        if abs(pos.qty) < 1e-10:
            del self.positions[symbol]

        trade = {
            "symbol": symbol, "side": "BUY", "qty": cover_qty,
            "price": price, "cost": cost, "pnl": pnl,
        }
        self.trades.append(trade)
        self.trade_history.append(trade)
        self.update_peak()
        return trade

    def update_peak(self) -> None:
        """Update peak portfolio value."""
        self._peak_value = max(self._peak_value, self.total_value)

    def current_drawdown(self) -> float:
        """Calculate current drawdown from peak."""
        self.update_peak()
        if self._peak_value == 0:
            return 0.0
        dd = (self._peak_value - self.total_value) / self._peak_value
        return max(0.0, dd)

    def to_dict(self) -> dict:
        """Serialize portfolio state."""
        return {
            "cash": self.cash,
            "initial_capital": self.initial_capital,
            "total_value": self.total_value,
            "positions": {s: p.to_dict() for s, p in self.positions.items()},
            "drawdown": self.current_drawdown(),
            "trade_count": len(self.trades),
            "return_pct": (self.total_value - self.initial_capital) / self.initial_capital * 100
            if self.initial_capital > 0 else 0.0,
        }
