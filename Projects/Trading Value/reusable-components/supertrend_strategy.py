"""Supertrend strategy."""
from __future__ import annotations
from typing import Any
import pandas as pd
from tq.strategy.base import BaseStrategy
from tq.strategy.registry import strategy
from tq.strategy.indicator import supertrend


@strategy("supertrend")
class SupertrendStrategy(BaseStrategy):
    name = "supertrend"
    description = "Trade based on Supertrend direction changes"

    def __init__(self, period: int = 10, multiplier: float = 3.0):
        self.period = period
        self.multiplier = multiplier

    def decide(self, data: pd.DataFrame, portfolio: Any) -> list[dict]:
        if len(data) < self.period + 5:
            return []
        cols = {c.lower(): c for c in data.columns}
        high = data[cols.get("high", "high")]
        low = data[cols.get("low", "low")]
        close = data[cols.get("close", "close")]

        st, direction = supertrend(high, low, close, self.period, self.multiplier)
        signals = []
        symbol = data.attrs.get("symbol", "UNKNOWN") if hasattr(data, "attrs") else "UNKNOWN"

        if direction.iloc[-1] == 1 and direction.iloc[-2] == -1:
            signals.append({"symbol": symbol, "side": "BUY", "qty": 1,
                            "confidence": 0.7, "reason": "Supertrend turned bullish"})
        elif direction.iloc[-1] == -1 and direction.iloc[-2] == 1:
            signals.append({"symbol": symbol, "side": "SELL", "qty": 1,
                            "confidence": 0.7, "reason": "Supertrend turned bearish"})
        return signals

    def get_params(self) -> dict:
        return {"period": self.period, "multiplier": self.multiplier}
