"""Bollinger Bands strategy."""
from __future__ import annotations
from typing import Any
import pandas as pd
from tq.strategy.base import BaseStrategy
from tq.strategy.registry import strategy
from tq.strategy.indicator import bollinger_bands


@strategy("bollinger")
class BollingerStrategy(BaseStrategy):
    name = "bollinger"
    description = "Buy at lower band, sell at upper band"

    def __init__(self, period: int = 20, std_dev: float = 2.0):
        self.period = period
        self.std_dev = std_dev

    def decide(self, data: pd.DataFrame, portfolio: Any) -> list[dict]:
        if len(data) < self.period + 1:
            return []
        close = data["close"] if "close" in data.columns else data["Close"]
        upper, middle, lower = bollinger_bands(close, self.period, self.std_dev)
        signals = []
        symbol = data.attrs.get("symbol", "UNKNOWN") if hasattr(data, "attrs") else "UNKNOWN"
        price = close.iloc[-1]
        if price <= lower.iloc[-1]:
            signals.append({"symbol": symbol, "side": "BUY", "qty": 1,
                            "confidence": 0.6, "reason": "Price at lower Bollinger band"})
        elif price >= upper.iloc[-1]:
            signals.append({"symbol": symbol, "side": "SELL", "qty": 1,
                            "confidence": 0.6, "reason": "Price at upper Bollinger band"})
        return signals

    def get_params(self) -> dict:
        return {"period": self.period, "std_dev": self.std_dev}
