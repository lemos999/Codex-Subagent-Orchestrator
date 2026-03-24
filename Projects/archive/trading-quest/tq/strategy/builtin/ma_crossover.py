"""Moving Average Crossover strategy."""
from __future__ import annotations
from typing import Any
import pandas as pd
from tq.strategy.base import BaseStrategy
from tq.strategy.registry import strategy
from tq.strategy.indicator import sma, ema, crossover, crossunder


@strategy("ma_crossover")
class MACrossoverStrategy(BaseStrategy):
    name = "ma_crossover"
    description = "Buy when fast MA crosses above slow MA, sell on cross below"

    def __init__(self, fast_period: int = 10, slow_period: int = 30,
                 use_ema: bool = False):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.use_ema = use_ema

    def decide(self, data: pd.DataFrame, portfolio: Any) -> list[dict]:
        if len(data) < self.slow_period + 1:
            return []
        close = data["close"] if "close" in data.columns else data["Close"]
        ma_func = ema if self.use_ema else sma
        fast = ma_func(close, self.fast_period)
        slow = ma_func(close, self.slow_period)

        signals = []
        symbol = data.attrs.get("symbol", "UNKNOWN") if hasattr(data, "attrs") else "UNKNOWN"
        if crossover(fast, slow).iloc[-1]:
            signals.append({"symbol": symbol, "side": "BUY", "qty": 1,
                            "confidence": 0.7, "reason": "MA crossover"})
        elif crossunder(fast, slow).iloc[-1]:
            signals.append({"symbol": symbol, "side": "SELL", "qty": 1,
                            "confidence": 0.7, "reason": "MA crossunder"})
        return signals

    def get_params(self) -> dict:
        return {"fast_period": self.fast_period, "slow_period": self.slow_period,
                "use_ema": self.use_ema}
