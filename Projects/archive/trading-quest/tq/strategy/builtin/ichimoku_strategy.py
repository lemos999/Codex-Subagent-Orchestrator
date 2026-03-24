"""Ichimoku Cloud strategy."""
from __future__ import annotations
from typing import Any
import pandas as pd
from tq.strategy.base import BaseStrategy
from tq.strategy.registry import strategy
from tq.strategy.indicator import ichimoku


@strategy("ichimoku")
class IchimokuStrategy(BaseStrategy):
    name = "ichimoku"
    description = "Trade based on Ichimoku cloud signals"

    def __init__(self, tenkan: int = 9, kijun: int = 26, senkou_b: int = 52):
        self.tenkan = tenkan
        self.kijun = kijun
        self.senkou_b = senkou_b

    def decide(self, data: pd.DataFrame, portfolio: Any) -> list[dict]:
        if len(data) < self.senkou_b + self.kijun:
            return []
        cols = {c.lower(): c for c in data.columns}
        high = data[cols.get("high", "high")]
        low = data[cols.get("low", "low")]
        close = data[cols.get("close", "close")]

        ich = ichimoku(high, low, close, self.tenkan, self.kijun, self.senkou_b)
        signals = []
        symbol = data.attrs.get("symbol", "UNKNOWN") if hasattr(data, "attrs") else "UNKNOWN"

        tenkan_sen = ich["tenkan_sen"]
        kijun_sen = ich["kijun_sen"]
        price = close.iloc[-1]

        # Tenkan/Kijun cross
        if (tenkan_sen.iloc[-1] > kijun_sen.iloc[-1] and
                tenkan_sen.iloc[-2] <= kijun_sen.iloc[-2]):
            signals.append({"symbol": symbol, "side": "BUY", "qty": 1,
                            "confidence": 0.7, "reason": "Ichimoku TK cross up"})
        elif (tenkan_sen.iloc[-1] < kijun_sen.iloc[-1] and
              tenkan_sen.iloc[-2] >= kijun_sen.iloc[-2]):
            signals.append({"symbol": symbol, "side": "SELL", "qty": 1,
                            "confidence": 0.7, "reason": "Ichimoku TK cross down"})
        return signals

    def get_params(self) -> dict:
        return {"tenkan": self.tenkan, "kijun": self.kijun,
                "senkou_b": self.senkou_b}
