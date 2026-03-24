"""Candle Pattern strategy -- detect hammer, engulfing, doji, morning/evening star."""
from __future__ import annotations
from typing import Any
import pandas as pd
import numpy as np
from tq.strategy.base import BaseStrategy
from tq.strategy.registry import strategy
from tq.strategy.indicator import sma


@strategy("candle_pattern")
class CandlePattern(BaseStrategy):
    """캔들 패턴: 망치형, 장악형, 도지, 십자, 샛별 감지"""

    name = "candle_pattern"
    description = "패턴 감지: hammer, engulfing, doji, morning_star, evening_star"

    def __init__(self, trend_period: int = 20):
        self.trend_period = trend_period

    def decide(self, data: pd.DataFrame, portfolio: Any) -> list[dict]:
        if len(data) < self.trend_period + 3:
            return []
        cols = {c.lower(): c for c in data.columns}
        open_ = data[cols.get("open", "open")]
        high = data[cols.get("high", "high")]
        low = data[cols.get("low", "low")]
        close = data[cols.get("close", "close")]

        signals = []
        symbol = data.attrs.get("symbol", "UNKNOWN") if hasattr(data, "attrs") else "UNKNOWN"

        # Trend direction via SMA
        ma = sma(close, self.trend_period)
        if pd.isna(ma.iloc[-1]):
            return []
        in_downtrend = close.iloc[-1] < ma.iloc[-1]
        in_uptrend = close.iloc[-1] > ma.iloc[-1]

        # Helper values for last candle
        o, h, l, c = open_.iloc[-1], high.iloc[-1], low.iloc[-1], close.iloc[-1]
        body = abs(c - o)
        full_range = h - l if h != l else 0.0001
        body_ratio = body / full_range
        upper_shadow = h - max(o, c)
        lower_shadow = min(o, c) - l

        # Previous candle
        o1, h1, l1, c1 = open_.iloc[-2], high.iloc[-2], low.iloc[-2], close.iloc[-2]
        body1 = abs(c1 - o1)

        # 2 candles ago
        o2, h2, l2, c2 = open_.iloc[-3], high.iloc[-3], low.iloc[-3], close.iloc[-3]

        detected = []

        # 1. Hammer (downtrend, small body at top, long lower shadow)
        if in_downtrend and lower_shadow > 2 * body and upper_shadow < body * 0.5 and body_ratio < 0.4:
            detected.append(("망치형(Hammer)", "BUY", 0.65))

        # 2. Bullish Engulfing (downtrend, current green engulfs previous red)
        if in_downtrend and c1 < o1 and c > o and o <= c1 and c >= o1 and body > body1:
            detected.append(("강세장악형(Bullish Engulfing)", "BUY", 0.7))

        # 3. Bearish Engulfing (uptrend, current red engulfs previous green)
        if in_uptrend and c1 > o1 and c < o and o >= c1 and c <= o1 and body > body1:
            detected.append(("약세장악형(Bearish Engulfing)", "SELL", 0.7))

        # 4. Doji (very small body)
        if body_ratio < 0.05:
            if in_uptrend:
                detected.append(("도지(Doji) - 상승추세 전환 가능", "SELL", 0.5))
            elif in_downtrend:
                detected.append(("도지(Doji) - 하락추세 전환 가능", "BUY", 0.5))

        # 5. Morning Star (downtrend: big red, small body, big green)
        if (in_downtrend and c2 < o2 and abs(c2 - o2) > body1 * 1.5 and
                body1 < abs(c2 - o2) * 0.3 and c > o and body > abs(c2 - o2) * 0.5):
            detected.append(("샛별(Morning Star)", "BUY", 0.75))

        # 6. Evening Star (uptrend: big green, small body, big red)
        if (in_uptrend and c2 > o2 and abs(c2 - o2) > body1 * 1.5 and
                body1 < abs(c2 - o2) * 0.3 and c < o and body > abs(c2 - o2) * 0.5):
            detected.append(("저녁별(Evening Star)", "SELL", 0.75))

        # Return the highest-confidence pattern detected
        if detected:
            detected.sort(key=lambda x: x[2], reverse=True)
            name, side, conf = detected[0]
            signals.append({"symbol": symbol, "side": side, "qty": 1,
                            "confidence": conf, "reason": f"캔들패턴: {name}"})

        return signals

    def get_params(self) -> dict:
        return {"trend_period": self.trend_period}
