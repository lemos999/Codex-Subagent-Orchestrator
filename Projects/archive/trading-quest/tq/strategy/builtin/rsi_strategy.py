"""RSI (Relative Strength Index) strategy."""
from __future__ import annotations
from typing import Any
import pandas as pd
from tq.strategy.base import BaseStrategy
from tq.strategy.registry import strategy
from tq.strategy.indicator import rsi


@strategy("rsi")
class RSIStrategy(BaseStrategy):
    name = "rsi"
    description = "Buy on RSI oversold, sell on RSI overbought"

    def __init__(self, period: int = 14, oversold: float = 30,
                 overbought: float = 70):
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

    def decide(self, data: pd.DataFrame, portfolio: Any) -> list[dict]:
        if len(data) < self.period + 1:
            return []
        close = data["close"] if "close" in data.columns else data["Close"]
        rsi_val = rsi(close, self.period)
        signals = []
        symbol = data.attrs.get("symbol", "UNKNOWN") if hasattr(data, "attrs") else "UNKNOWN"
        current_rsi = rsi_val.iloc[-1]
        if current_rsi < self.oversold:
            signals.append({"symbol": symbol, "side": "BUY", "qty": 1,
                            "confidence": min(1.0, (self.oversold - current_rsi) / 30),
                            "reason": f"RSI oversold ({current_rsi:.1f})"})
        elif current_rsi > self.overbought:
            signals.append({"symbol": symbol, "side": "SELL", "qty": 1,
                            "confidence": min(1.0, (current_rsi - self.overbought) / 30),
                            "reason": f"RSI overbought ({current_rsi:.1f})"})
        return signals

    def get_params(self) -> dict:
        return {"period": self.period, "oversold": self.oversold,
                "overbought": self.overbought}
