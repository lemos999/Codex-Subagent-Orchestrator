"""MACD strategy."""
from __future__ import annotations
from typing import Any
import pandas as pd
from tq.strategy.base import BaseStrategy
from tq.strategy.registry import strategy
from tq.strategy.indicator import macd, crossover, crossunder


@strategy("macd")
class MACDStrategy(BaseStrategy):
    name = "macd"
    description = "Buy/sell on MACD signal line crossovers"

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        self.fast = fast
        self.slow = slow
        self.signal = signal

    def decide(self, data: pd.DataFrame, portfolio: Any) -> list[dict]:
        if len(data) < self.slow + self.signal:
            return []
        close = data["close"] if "close" in data.columns else data["Close"]
        macd_line, signal_line, hist = macd(close, self.fast, self.slow, self.signal)
        signals = []
        symbol = data.attrs.get("symbol", "UNKNOWN") if hasattr(data, "attrs") else "UNKNOWN"
        if crossover(macd_line, signal_line).iloc[-1]:
            signals.append({"symbol": symbol, "side": "BUY", "qty": 1,
                            "confidence": 0.65, "reason": "MACD bullish crossover"})
        elif crossunder(macd_line, signal_line).iloc[-1]:
            signals.append({"symbol": symbol, "side": "SELL", "qty": 1,
                            "confidence": 0.65, "reason": "MACD bearish crossover"})
        return signals

    def get_params(self) -> dict:
        return {"fast": self.fast, "slow": self.slow, "signal": self.signal}
