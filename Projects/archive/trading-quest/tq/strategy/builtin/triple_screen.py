"""Alexander Elder Triple Screen strategy."""
from __future__ import annotations
from typing import Any
import pandas as pd
from tq.strategy.base import BaseStrategy
from tq.strategy.registry import strategy
from tq.strategy.indicator import sma, rsi, stochastic


@strategy("triple_screen")
class TripleScreen(BaseStrategy):
    """알렉산더 엘더 3중 스크린: 장기추세 + 중기오실레이터 + 단기진입"""

    name = "triple_screen"
    description = "Screen1: SMA50 방향(장기), Screen2: Stochastic/RSI(중기), Screen3: 직전 고저 돌파(단기)"

    def __init__(self, trend_period: int = 50, rsi_period: int = 14,
                 stoch_k: int = 14, stoch_d: int = 3,
                 rsi_oversold: float = 40, rsi_overbought: float = 60):
        self.trend_period = trend_period
        self.rsi_period = rsi_period
        self.stoch_k = stoch_k
        self.stoch_d = stoch_d
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought

    def decide(self, data: pd.DataFrame, portfolio: Any) -> list[dict]:
        min_len = self.trend_period + 5
        if len(data) < min_len:
            return []
        cols = {c.lower(): c for c in data.columns}
        high = data[cols.get("high", "high")]
        low = data[cols.get("low", "low")]
        close = data[cols.get("close", "close")]

        signals = []
        symbol = data.attrs.get("symbol", "UNKNOWN") if hasattr(data, "attrs") else "UNKNOWN"

        # Screen 1: Long-term trend via SMA direction
        ma = sma(close, self.trend_period)
        if pd.isna(ma.iloc[-1]) or pd.isna(ma.iloc[-2]):
            return []
        trend_up = ma.iloc[-1] > ma.iloc[-2]
        trend_down = ma.iloc[-1] < ma.iloc[-2]

        # Screen 2: Oscillator in the direction of the trend
        rsi_val = rsi(close, self.rsi_period)
        k, d = stochastic(high, low, close, self.stoch_k, self.stoch_d)

        rsi_curr = rsi_val.iloc[-1] if pd.notna(rsi_val.iloc[-1]) else 50
        stoch_curr = k.iloc[-1] if pd.notna(k.iloc[-1]) else 50

        # In uptrend: look for oversold pullback (buy the dip)
        osc_buy = trend_up and (rsi_curr < self.rsi_oversold or stoch_curr < 30)
        # In downtrend: look for overbought rally (sell the rally)
        osc_sell = trend_down and (rsi_curr > self.rsi_overbought or stoch_curr > 70)

        # Screen 3: Short-term entry trigger
        price = close.iloc[-1]
        prev_high = high.iloc[-2]
        prev_low = low.iloc[-2]

        if osc_buy and price > prev_high:
            signals.append({"symbol": symbol, "side": "BUY", "qty": 1,
                            "confidence": 0.75,
                            "reason": f"3중스크린 매수: 상승추세+오실레이터과매도+직전고점돌파"})
        elif osc_sell and price < prev_low:
            signals.append({"symbol": symbol, "side": "SELL", "qty": 1,
                            "confidence": 0.75,
                            "reason": f"3중스크린 매도: 하락추세+오실레이터과매수+직전저점이탈"})

        return signals

    def get_params(self) -> dict:
        return {"trend_period": self.trend_period, "rsi_period": self.rsi_period,
                "stoch_k": self.stoch_k, "stoch_d": self.stoch_d,
                "rsi_oversold": self.rsi_oversold, "rsi_overbought": self.rsi_overbought}
