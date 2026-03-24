"""Momentum strategy."""
from __future__ import annotations
from typing import Any
import pandas as pd
from tq.strategy.base import BaseStrategy
from tq.strategy.registry import strategy
from tq.strategy.indicator import momentum, rsi


@strategy("momentum")
class MomentumStrategy(BaseStrategy):
    name = "momentum"
    description = "Buy on strong positive momentum, sell on negative"

    def __init__(self, period: int = 10, threshold: float = 0.02):
        self.period = period
        self.threshold = threshold

    def decide(self, data: pd.DataFrame, portfolio: Any) -> list[dict]:
        if len(data) < self.period + 1:
            return []
        close = data["close"] if "close" in data.columns else data["Close"]
        mom = momentum(close, self.period)
        rsi_val = rsi(close, 14)
        signals = []
        symbol = data.attrs.get("symbol", "UNKNOWN") if hasattr(data, "attrs") else "UNKNOWN"
        mom_pct = mom.iloc[-1] / close.iloc[-self.period - 1] if close.iloc[-self.period - 1] != 0 else 0
        if mom_pct > self.threshold and rsi_val.iloc[-1] < 70:
            signals.append({"symbol": symbol, "side": "BUY", "qty": 1,
                            "confidence": min(1.0, mom_pct / self.threshold * 0.5),
                            "reason": f"Strong momentum ({mom_pct:.2%})"})
        elif mom_pct < -self.threshold:
            signals.append({"symbol": symbol, "side": "SELL", "qty": 1,
                            "confidence": 0.6, "reason": f"Negative momentum ({mom_pct:.2%})"})
        return signals

    def get_params(self) -> dict:
        return {"period": self.period, "threshold": self.threshold}
