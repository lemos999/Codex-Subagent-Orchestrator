"""ATR Breakout strategy -- Larry Williams volatility breakout."""
from __future__ import annotations
from typing import Any
import pandas as pd
from tq.strategy.base import BaseStrategy
from tq.strategy.registry import strategy
from tq.strategy.indicator import atr


@strategy("atr_breakout")
class ATRBreakout(BaseStrategy):
    """ATR 변동성 돌파: 전일 종가 + ATR*k 돌파 시 매수 (래리 윌리엄스 변동성 돌파)"""

    name = "atr_breakout"
    description = "매수: 당일시가 + ATR(20)*0.5 초과 시, 매도: 다음날 시가 (1일 보유), k값 조절 가능"

    def __init__(self, atr_period: int = 20, k: float = 0.5):
        self.atr_period = atr_period
        self.k = k

    def decide(self, data: pd.DataFrame, portfolio: Any) -> list[dict]:
        if len(data) < self.atr_period + 2:
            return []
        cols = {c.lower(): c for c in data.columns}
        high = data[cols.get("high", "high")]
        low = data[cols.get("low", "low")]
        close = data[cols.get("close", "close")]
        open_ = data[cols.get("open", "open")]

        atr_val = atr(high, low, close, self.atr_period)

        signals = []
        symbol = data.attrs.get("symbol", "UNKNOWN") if hasattr(data, "attrs") else "UNKNOWN"

        curr_atr = atr_val.iloc[-2]  # Use previous day's ATR
        if pd.isna(curr_atr) or curr_atr == 0:
            return []

        # Today's open + ATR*k = breakout level
        today_open = open_.iloc[-1]
        breakout_level = today_open + curr_atr * self.k
        breakdown_level = today_open - curr_atr * self.k

        price = close.iloc[-1]
        today_high = high.iloc[-1]

        # Breakout buy: today's high reached the breakout level
        if today_high >= breakout_level and price > today_open:
            signals.append({"symbol": symbol, "side": "BUY", "qty": 1,
                            "confidence": min(0.8, 0.5 + (price - breakout_level) / curr_atr * 0.3),
                            "reason": f"ATR돌파 매수: 시가({today_open:.2f})+ATR*{self.k}={breakout_level:.2f}"})
        # Exit signal: if already holding, suggest sell at close (1-day hold)
        elif price < breakdown_level:
            signals.append({"symbol": symbol, "side": "SELL", "qty": 1,
                            "confidence": 0.6,
                            "reason": f"ATR하향이탈: 시가({today_open:.2f})-ATR*{self.k}={breakdown_level:.2f}"})

        return signals

    def get_params(self) -> dict:
        return {"atr_period": self.atr_period, "k": self.k}
