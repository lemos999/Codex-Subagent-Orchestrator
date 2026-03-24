"""Multi-timeframe strategy."""
from __future__ import annotations
from typing import Any
import pandas as pd
from tq.strategy.base import BaseStrategy
from tq.strategy.registry import strategy
from tq.strategy.indicator import sma, ema, rsi, macd


@strategy("multi_tf")
class MultiTimeframeStrategy(BaseStrategy):
    name = "multi_tf"
    description = "Combines signals from multiple timeframes (1d + 1h)"
    timeframes = ["1d", "1h"]

    def __init__(self, trend_period: int = 50, entry_period: int = 14):
        self.trend_period = trend_period
        self.entry_period = entry_period

    def decide(self, data: pd.DataFrame, portfolio: Any) -> list[dict]:
        """Default single-timeframe fallback."""
        if len(data) < self.trend_period + 1:
            return []
        close = data["close"] if "close" in data.columns else data["Close"]
        trend_ma = sma(close, self.trend_period)
        entry_rsi = rsi(close, self.entry_period)

        signals = []
        symbol = data.attrs.get("symbol", "UNKNOWN") if hasattr(data, "attrs") else "UNKNOWN"
        price = close.iloc[-1]

        if price > trend_ma.iloc[-1] and entry_rsi.iloc[-1] < 40:
            signals.append({"symbol": symbol, "side": "BUY", "qty": 1,
                            "confidence": 0.7, "reason": "MTF: uptrend + RSI dip"})
        elif price < trend_ma.iloc[-1] and entry_rsi.iloc[-1] > 60:
            signals.append({"symbol": symbol, "side": "SELL", "qty": 1,
                            "confidence": 0.7, "reason": "MTF: downtrend + RSI high"})
        return signals

    def on_candle_mtf(self, candles: dict[str, pd.DataFrame],
                      portfolio: Any) -> list[dict]:
        """Multi-timeframe analysis."""
        daily = candles.get("1d")
        hourly = candles.get("1h")
        if daily is None or hourly is None:
            first = next(iter(candles.values()), None)
            if first is not None:
                return self.decide(first, portfolio)
            return []

        if len(daily) < self.trend_period or len(hourly) < self.entry_period:
            return []

        close_d = daily["close"] if "close" in daily.columns else daily["Close"]
        close_h = hourly["close"] if "close" in hourly.columns else hourly["Close"]

        trend_ma = sma(close_d, self.trend_period)
        entry_rsi = rsi(close_h, self.entry_period)

        signals = []
        symbol = daily.attrs.get("symbol", "UNKNOWN") if hasattr(daily, "attrs") else "UNKNOWN"
        price = close_h.iloc[-1]
        uptrend = close_d.iloc[-1] > trend_ma.iloc[-1]

        if uptrend and entry_rsi.iloc[-1] < 35:
            signals.append({"symbol": symbol, "side": "BUY", "qty": 1,
                            "confidence": 0.75, "reason": "MTF: daily uptrend + hourly RSI oversold"})
        elif not uptrend and entry_rsi.iloc[-1] > 65:
            signals.append({"symbol": symbol, "side": "SELL", "qty": 1,
                            "confidence": 0.75, "reason": "MTF: daily downtrend + hourly RSI overbought"})
        return signals

    def get_params(self) -> dict:
        return {"trend_period": self.trend_period,
                "entry_period": self.entry_period}
