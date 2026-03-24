"""Donchian Channel strategy."""
from __future__ import annotations
from typing import Any
import pandas as pd
from tq.strategy.base import BaseStrategy
from tq.strategy.registry import strategy
from tq.strategy.indicator import donchian_channel


@strategy("donchian")
class DonchianStrategy(BaseStrategy):
    name = "donchian"
    description = "Breakout strategy using Donchian channels"

    def __init__(self, period: int = 20):
        self.period = period

    def decide(self, data: pd.DataFrame, portfolio: Any) -> list[dict]:
        if len(data) < self.period + 1:
            return []
        cols = {c.lower(): c for c in data.columns}
        high = data[cols.get("high", "high")]
        low = data[cols.get("low", "low")]
        close = data[cols.get("close", "close")]

        upper, middle, lower = donchian_channel(high, low, self.period)
        signals = []
        symbol = data.attrs.get("symbol", "UNKNOWN") if hasattr(data, "attrs") else "UNKNOWN"
        price = close.iloc[-1]

        if price >= upper.iloc[-2]:  # breakout above previous upper
            signals.append({"symbol": symbol, "side": "BUY", "qty": 1,
                            "confidence": 0.65, "reason": "Donchian upper breakout"})
        elif price <= lower.iloc[-2]:
            signals.append({"symbol": symbol, "side": "SELL", "qty": 1,
                            "confidence": 0.65, "reason": "Donchian lower breakout"})
        return signals

    def get_params(self) -> dict:
        return {"period": self.period}
