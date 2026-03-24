"""RSI Divergence strategy -- price/RSI directional divergence."""
from __future__ import annotations
from typing import Any
import pandas as pd
from tq.strategy.base import BaseStrategy
from tq.strategy.registry import strategy
from tq.strategy.indicator import rsi


@strategy("rsi_divergence")
class RSIDivergence(BaseStrategy):
    """RSI 다이버전스: 가격과 RSI의 방향 괴리 감지"""

    name = "rsi_divergence"
    description = "강세: 가격 하락 but RSI 상승 -> 매수, 약세: 가격 상승 but RSI 하락 -> 매도"

    def __init__(self, rsi_period: int = 14, lookback: int = 20):
        self.rsi_period = rsi_period
        self.lookback = lookback

    def decide(self, data: pd.DataFrame, portfolio: Any) -> list[dict]:
        min_len = self.rsi_period + self.lookback + 1
        if len(data) < min_len:
            return []
        cols = {c.lower(): c for c in data.columns}
        close = data[cols.get("close", "close")]

        rsi_val = rsi(close, self.rsi_period)

        signals = []
        symbol = data.attrs.get("symbol", "UNKNOWN") if hasattr(data, "attrs") else "UNKNOWN"

        # Window for divergence detection
        price_window = close.iloc[-self.lookback:]
        rsi_window = rsi_val.iloc[-self.lookback:]

        if rsi_window.isna().all():
            return []

        price_curr = close.iloc[-1]
        rsi_curr = rsi_val.iloc[-1]

        if pd.isna(rsi_curr):
            return []

        price_min = price_window.min()
        price_max = price_window.max()
        rsi_min = rsi_window.min()
        rsi_max = rsi_window.max()

        # Bullish divergence: price near low but RSI above its low
        if (price_curr <= price_min * 1.005 and
                rsi_curr > rsi_min + 5 and rsi_curr < 40):
            signals.append({"symbol": symbol, "side": "BUY", "qty": 1,
                            "confidence": 0.7,
                            "reason": f"RSI 강세 다이버전스: 가격 저점 but RSI {rsi_curr:.0f} (상승)"})

        # Bearish divergence: price near high but RSI below its high
        elif (price_curr >= price_max * 0.995 and
              rsi_curr < rsi_max - 5 and rsi_curr > 60):
            signals.append({"symbol": symbol, "side": "SELL", "qty": 1,
                            "confidence": 0.7,
                            "reason": f"RSI 약세 다이버전스: 가격 고점 but RSI {rsi_curr:.0f} (하락)"})

        return signals

    def get_params(self) -> dict:
        return {"rsi_period": self.rsi_period, "lookback": self.lookback}
