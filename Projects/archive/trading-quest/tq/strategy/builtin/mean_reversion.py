"""Mean Reversion strategy."""
from __future__ import annotations
from typing import Any
import pandas as pd
from tq.strategy.base import BaseStrategy
from tq.strategy.registry import strategy
from tq.strategy.indicator import sma, bollinger_bands, rsi


@strategy("mean_reversion")
class MeanReversionStrategy(BaseStrategy):
    name = "mean_reversion"
    description = "Buy below mean, sell above mean using z-score"

    def __init__(self, period: int = 20, z_threshold: float = 2.0):
        self.period = period
        self.z_threshold = z_threshold

    def decide(self, data: pd.DataFrame, portfolio: Any) -> list[dict]:
        if len(data) < self.period + 1:
            return []
        close = data["close"] if "close" in data.columns else data["Close"]
        mean = sma(close, self.period)
        std = close.rolling(window=self.period).std()
        z_score = (close - mean) / std.replace(0, float("nan"))

        signals = []
        symbol = data.attrs.get("symbol", "UNKNOWN") if hasattr(data, "attrs") else "UNKNOWN"
        z = z_score.iloc[-1]

        if z < -self.z_threshold:
            signals.append({"symbol": symbol, "side": "BUY", "qty": 1,
                            "confidence": min(1.0, abs(z) / self.z_threshold * 0.5),
                            "reason": f"Mean reversion BUY (z={z:.2f})"})
        elif z > self.z_threshold:
            signals.append({"symbol": symbol, "side": "SELL", "qty": 1,
                            "confidence": min(1.0, abs(z) / self.z_threshold * 0.5),
                            "reason": f"Mean reversion SELL (z={z:.2f})"})
        return signals

    def get_params(self) -> dict:
        return {"period": self.period, "z_threshold": self.z_threshold}
