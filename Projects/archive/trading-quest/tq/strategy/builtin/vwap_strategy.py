"""VWAP strategy."""
from __future__ import annotations
from typing import Any
import pandas as pd
from tq.strategy.base import BaseStrategy
from tq.strategy.registry import strategy
from tq.strategy.indicator import vwap


@strategy("vwap")
class VWAPStrategy(BaseStrategy):
    name = "vwap"
    description = "Buy below VWAP, sell above VWAP"
    timeframes = ["1m", "5m"]

    def __init__(self, threshold: float = 0.002):
        self.threshold = threshold

    def decide(self, data: pd.DataFrame, portfolio: Any) -> list[dict]:
        if len(data) < 5:
            return []
        cols = {c.lower(): c for c in data.columns}
        high = data[cols.get("high", "high")]
        low = data[cols.get("low", "low")]
        close = data[cols.get("close", "close")]
        volume = data[cols.get("volume", "volume")]

        vwap_val = vwap(high, low, close, volume)
        signals = []
        symbol = data.attrs.get("symbol", "UNKNOWN") if hasattr(data, "attrs") else "UNKNOWN"
        price = close.iloc[-1]
        current_vwap = vwap_val.iloc[-1]
        if current_vwap == 0:
            return []
        diff_pct = (price - current_vwap) / current_vwap
        if diff_pct < -self.threshold:
            signals.append({"symbol": symbol, "side": "BUY", "qty": 1,
                            "confidence": min(1.0, abs(diff_pct) / self.threshold * 0.5),
                            "reason": f"Below VWAP ({diff_pct:.2%})"})
        elif diff_pct > self.threshold:
            signals.append({"symbol": symbol, "side": "SELL", "qty": 1,
                            "confidence": 0.6, "reason": f"Above VWAP ({diff_pct:.2%})"})
        return signals

    def get_params(self) -> dict:
        return {"threshold": self.threshold}
