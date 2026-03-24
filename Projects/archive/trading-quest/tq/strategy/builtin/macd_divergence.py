"""MACD Divergence strategy -- price/MACD directional divergence."""
from __future__ import annotations
from typing import Any
import pandas as pd
import numpy as np
from tq.strategy.base import BaseStrategy
from tq.strategy.registry import strategy
from tq.strategy.indicator import macd


@strategy("macd_divergence")
class MACDDivergence(BaseStrategy):
    """MACD 다이버전스: 가격 신고가 but MACD 낮아짐 = 하락 전환 신호"""

    name = "macd_divergence"
    description = "강세: 가격 신저가+MACD 높아짐 -> 매수, 약세: 가격 신고가+MACD 낮아짐 -> 매도"

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9,
                 lookback: int = 20):
        self.fast = fast
        self.slow = slow
        self.signal = signal
        self.lookback = lookback

    def decide(self, data: pd.DataFrame, portfolio: Any) -> list[dict]:
        min_len = self.slow + self.signal + self.lookback
        if len(data) < min_len:
            return []
        cols = {c.lower(): c for c in data.columns}
        close = data[cols.get("close", "close")]

        macd_line, signal_line, hist = macd(close, self.fast, self.slow, self.signal)

        signals = []
        symbol = data.attrs.get("symbol", "UNKNOWN") if hasattr(data, "attrs") else "UNKNOWN"

        # Look at the last `lookback` bars for divergence
        price_window = close.iloc[-self.lookback:]
        macd_window = macd_line.iloc[-self.lookback:]

        if macd_window.isna().all():
            return []

        # Find recent lows and highs
        price_curr = close.iloc[-1]
        macd_curr = macd_line.iloc[-1]

        price_min = price_window.min()
        price_max = price_window.max()
        price_min_idx = price_window.idxmin()
        price_max_idx = price_window.idxmax()

        if pd.isna(macd_curr):
            return []

        # Bullish divergence: price makes new low but MACD doesn't
        # Price near its lookback low, MACD above its lookback low
        macd_at_price_low = macd_line.loc[price_min_idx] if price_min_idx in macd_line.index else None
        if (macd_at_price_low is not None and pd.notna(macd_at_price_low) and
                price_curr <= price_min * 1.005 and
                macd_curr > macd_window.min()):
            signals.append({"symbol": symbol, "side": "BUY", "qty": 1,
                            "confidence": 0.7,
                            "reason": f"MACD 강세 다이버전스: 가격 신저가 but MACD 상승"})

        # Bearish divergence: price makes new high but MACD doesn't
        macd_at_price_high = macd_line.loc[price_max_idx] if price_max_idx in macd_line.index else None
        if (macd_at_price_high is not None and pd.notna(macd_at_price_high) and
                price_curr >= price_max * 0.995 and
                macd_curr < macd_window.max()):
            signals.append({"symbol": symbol, "side": "SELL", "qty": 1,
                            "confidence": 0.7,
                            "reason": f"MACD 약세 다이버전스: 가격 신고가 but MACD 하락"})

        return signals

    def get_params(self) -> dict:
        return {"fast": self.fast, "slow": self.slow, "signal": self.signal,
                "lookback": self.lookback}
