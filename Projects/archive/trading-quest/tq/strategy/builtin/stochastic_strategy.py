"""Stochastic Oscillator strategy."""
from __future__ import annotations
from typing import Any
import pandas as pd
from tq.strategy.base import BaseStrategy
from tq.strategy.registry import strategy
from tq.strategy.indicator import stochastic, crossover, crossunder


@strategy("stochastic")
class StochasticStrategy(BaseStrategy):
    name = "stochastic"
    description = "Buy on %K/%D cross in oversold zone, sell in overbought"

    def __init__(self, k_period: int = 14, d_period: int = 3,
                 oversold: float = 20, overbought: float = 80):
        self.k_period = k_period
        self.d_period = d_period
        self.oversold = oversold
        self.overbought = overbought

    def decide(self, data: pd.DataFrame, portfolio: Any) -> list[dict]:
        if len(data) < self.k_period + self.d_period:
            return []
        cols = {c.lower(): c for c in data.columns}
        high = data[cols.get("high", "high")]
        low = data[cols.get("low", "low")]
        close = data[cols.get("close", "close")]

        k, d = stochastic(high, low, close, self.k_period, self.d_period)
        signals = []
        symbol = data.attrs.get("symbol", "UNKNOWN") if hasattr(data, "attrs") else "UNKNOWN"

        if (crossover(k, d).iloc[-1] and k.iloc[-1] < self.oversold):
            signals.append({"symbol": symbol, "side": "BUY", "qty": 1,
                            "confidence": 0.65, "reason": "Stochastic oversold crossover"})
        elif (crossunder(k, d).iloc[-1] and k.iloc[-1] > self.overbought):
            signals.append({"symbol": symbol, "side": "SELL", "qty": 1,
                            "confidence": 0.65, "reason": "Stochastic overbought crossunder"})
        return signals

    def get_params(self) -> dict:
        return {"k_period": self.k_period, "d_period": self.d_period,
                "oversold": self.oversold, "overbought": self.overbought}
