"""Channel strategy -- Keltner/ATR channel bounce."""
from __future__ import annotations
from typing import Any
import pandas as pd
from tq.strategy.base import BaseStrategy
from tq.strategy.registry import strategy
from tq.strategy.indicator import keltner_channel


@strategy("channel")
class ChannelStrategy(BaseStrategy):
    """채널 전략: 가격 채널 (Keltner) 상하단 바운스"""

    name = "channel"
    description = "하단 터치 매수, 상단 터치 매도 (평균회귀), ATR 기반 채널 폭 동적 조정"

    def __init__(self, ema_period: int = 20, atr_period: int = 10,
                 multiplier: float = 2.0):
        self.ema_period = ema_period
        self.atr_period = atr_period
        self.multiplier = multiplier

    def decide(self, data: pd.DataFrame, portfolio: Any) -> list[dict]:
        min_len = max(self.ema_period, self.atr_period) + 2
        if len(data) < min_len:
            return []
        cols = {c.lower(): c for c in data.columns}
        high = data[cols.get("high", "high")]
        low = data[cols.get("low", "low")]
        close = data[cols.get("close", "close")]

        upper, middle, lower = keltner_channel(
            high, low, close, self.ema_period, self.atr_period, self.multiplier)

        signals = []
        symbol = data.attrs.get("symbol", "UNKNOWN") if hasattr(data, "attrs") else "UNKNOWN"

        price = close.iloc[-1]
        prev_price = close.iloc[-2]

        if pd.isna(upper.iloc[-1]) or pd.isna(lower.iloc[-1]):
            return []

        # Bounce from lower channel: mean reversion buy
        if price <= lower.iloc[-1] and prev_price > lower.iloc[-2]:
            signals.append({"symbol": symbol, "side": "BUY", "qty": 1,
                            "confidence": 0.6,
                            "reason": f"Keltner 하단 바운스 매수 (채널하단={lower.iloc[-1]:.2f})"})
        # Touch upper channel: mean reversion sell
        elif price >= upper.iloc[-1] and prev_price < upper.iloc[-2]:
            signals.append({"symbol": symbol, "side": "SELL", "qty": 1,
                            "confidence": 0.6,
                            "reason": f"Keltner 상단 바운스 매도 (채널상단={upper.iloc[-1]:.2f})"})

        return signals

    def get_params(self) -> dict:
        return {"ema_period": self.ema_period, "atr_period": self.atr_period,
                "multiplier": self.multiplier}
