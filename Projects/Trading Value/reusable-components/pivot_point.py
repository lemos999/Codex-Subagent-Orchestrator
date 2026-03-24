"""Pivot Point strategy -- support/resistance from previous day HLC."""
from __future__ import annotations
from typing import Any
import pandas as pd
from tq.strategy.base import BaseStrategy
from tq.strategy.registry import strategy


@strategy("pivot_point")
class PivotPointStrategy(BaseStrategy):
    """피봇 포인트: 전일 고가/저가/종가 기반 지지/저항 레벨"""

    name = "pivot_point"
    description = "P=(H+L+C)/3, R1=2P-L, S1=2P-H. S1 근처 반등 매수, R1 근처 저항 매도"

    def __init__(self, tolerance: float = 0.002):
        self.tolerance = tolerance

    def decide(self, data: pd.DataFrame, portfolio: Any) -> list[dict]:
        if len(data) < 3:
            return []
        cols = {c.lower(): c for c in data.columns}
        high = data[cols.get("high", "high")]
        low = data[cols.get("low", "low")]
        close = data[cols.get("close", "close")]

        signals = []
        symbol = data.attrs.get("symbol", "UNKNOWN") if hasattr(data, "attrs") else "UNKNOWN"

        # Previous day's HLC
        prev_h = high.iloc[-2]
        prev_l = low.iloc[-2]
        prev_c = close.iloc[-2]

        # Pivot levels
        pivot = (prev_h + prev_l + prev_c) / 3
        r1 = 2 * pivot - prev_l
        s1 = 2 * pivot - prev_h
        r2 = pivot + (prev_h - prev_l)
        s2 = pivot - (prev_h - prev_l)

        price = close.iloc[-1]

        if pivot == 0:
            return []

        tol = price * self.tolerance

        # Buy near S1 (support bounce)
        if abs(price - s1) <= tol and price > s1:
            signals.append({"symbol": symbol, "side": "BUY", "qty": 1,
                            "confidence": 0.6,
                            "reason": f"피봇 S1({s1:.2f}) 지지 반등"})
        # Buy near S2 (stronger support)
        elif abs(price - s2) <= tol and price > s2:
            signals.append({"symbol": symbol, "side": "BUY", "qty": 1,
                            "confidence": 0.65,
                            "reason": f"피봇 S2({s2:.2f}) 지지 반등"})
        # Sell near R1 (resistance)
        elif abs(price - r1) <= tol and price < r1:
            signals.append({"symbol": symbol, "side": "SELL", "qty": 1,
                            "confidence": 0.6,
                            "reason": f"피봇 R1({r1:.2f}) 저항 매도"})
        # Sell near R2 (stronger resistance)
        elif abs(price - r2) <= tol and price < r2:
            signals.append({"symbol": symbol, "side": "SELL", "qty": 1,
                            "confidence": 0.65,
                            "reason": f"피봇 R2({r2:.2f}) 저항 매도"})

        return signals

    def get_params(self) -> dict:
        return {"tolerance": self.tolerance}
