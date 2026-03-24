"""Donchian + Larry Williams %R combination strategy."""
from __future__ import annotations
from typing import Any
import pandas as pd
from tq.strategy.base import BaseStrategy
from tq.strategy.registry import strategy
from tq.strategy.indicator import donchian_channel, williams_r


@strategy("donchian_larry")
class DonchianLarry(BaseStrategy):
    """돈치안 래리 윌리엄스: 돈치안 채널 + 래리 윌리엄스 %R 조합"""

    name = "donchian_larry"
    description = "돈치안 상단 돌파 + %R이 -20 이상이면 매수, 하단 이탈 + %R이 -80 이하이면 매도"

    def __init__(self, don_period: int = 20, wr_period: int = 14,
                 wr_overbought: float = -20, wr_oversold: float = -80):
        self.don_period = don_period
        self.wr_period = wr_period
        self.wr_overbought = wr_overbought
        self.wr_oversold = wr_oversold

    def decide(self, data: pd.DataFrame, portfolio: Any) -> list[dict]:
        min_len = max(self.don_period, self.wr_period) + 2
        if len(data) < min_len:
            return []
        cols = {c.lower(): c for c in data.columns}
        high = data[cols.get("high", "high")]
        low = data[cols.get("low", "low")]
        close = data[cols.get("close", "close")]

        upper, middle, lower = donchian_channel(high, low, self.don_period)
        wr = williams_r(high, low, close, self.wr_period)

        signals = []
        symbol = data.attrs.get("symbol", "UNKNOWN") if hasattr(data, "attrs") else "UNKNOWN"

        price = close.iloc[-1]
        wr_val = wr.iloc[-1]
        prev_upper = upper.iloc[-2]
        prev_lower = lower.iloc[-2]

        if pd.isna(wr_val) or pd.isna(prev_upper) or pd.isna(prev_lower):
            return []

        # Buy: price breaks above previous Donchian upper + %R confirms strength
        if price >= prev_upper and wr_val >= self.wr_overbought:
            signals.append({"symbol": symbol, "side": "BUY", "qty": 1,
                            "confidence": 0.7,
                            "reason": f"돈치안 상단돌파 + %R={wr_val:.0f} (강세확인)"})
        # Sell: price breaks below previous Donchian lower + %R confirms weakness
        elif price <= prev_lower and wr_val <= self.wr_oversold:
            signals.append({"symbol": symbol, "side": "SELL", "qty": 1,
                            "confidence": 0.7,
                            "reason": f"돈치안 하단이탈 + %R={wr_val:.0f} (약세확인)"})

        return signals

    def get_params(self) -> dict:
        return {"don_period": self.don_period, "wr_period": self.wr_period,
                "wr_overbought": self.wr_overbought, "wr_oversold": self.wr_oversold}
