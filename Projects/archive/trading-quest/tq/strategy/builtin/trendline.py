"""Trendline strategy -- linear regression of highs/lows for breakout."""
from __future__ import annotations
from typing import Any
import numpy as np
import pandas as pd
from tq.strategy.base import BaseStrategy
from tq.strategy.registry import strategy


@strategy("trendline")
class TrendlineStrategy(BaseStrategy):
    """빗각/추세선: 고점 연결 하락 추세선 돌파 매수, 저점 연결 상승 추세선 이탈 매도"""

    name = "trendline"
    description = "최근 N개 고점/저점으로 추세선 계산 (선형 회귀), 돌파 시 신호 발생"

    def __init__(self, lookback: int = 20, min_slope_pct: float = 0.001):
        self.lookback = lookback
        self.min_slope_pct = min_slope_pct

    def _linreg_value_at_end(self, series: pd.Series) -> float:
        """Linear regression of a series, return projected value at last index."""
        y = series.values.astype(float)
        x = np.arange(len(y), dtype=float)
        mask = ~np.isnan(y)
        if mask.sum() < 3:
            return float("nan")
        x_m, y_m = x[mask], y[mask]
        n = len(x_m)
        sx = x_m.sum()
        sy = y_m.sum()
        sxy = (x_m * y_m).sum()
        sxx = (x_m * x_m).sum()
        denom = n * sxx - sx * sx
        if denom == 0:
            return float("nan")
        slope = (n * sxy - sx * sy) / denom
        intercept = (sy - slope * sx) / n
        return slope * (len(series) - 1) + intercept

    def decide(self, data: pd.DataFrame, portfolio: Any) -> list[dict]:
        if len(data) < self.lookback + 2:
            return []
        cols = {c.lower(): c for c in data.columns}
        high = data[cols.get("high", "high")]
        low = data[cols.get("low", "low")]
        close = data[cols.get("close", "close")]

        signals = []
        symbol = data.attrs.get("symbol", "UNKNOWN") if hasattr(data, "attrs") else "UNKNOWN"

        # Compute trendlines using lookback window (excluding last bar)
        window_high = high.iloc[-(self.lookback + 1):-1]
        window_low = low.iloc[-(self.lookback + 1):-1]

        # Resistance trendline (from highs)
        resistance = self._linreg_value_at_end(window_high)
        # Support trendline (from lows)
        support = self._linreg_value_at_end(window_low)

        price = close.iloc[-1]
        prev_price = close.iloc[-2]

        if np.isnan(resistance) or np.isnan(support):
            return []

        avg_price = (resistance + support) / 2
        if avg_price == 0:
            return []

        # Breakout above resistance trendline
        if price > resistance and prev_price <= resistance:
            signals.append({"symbol": symbol, "side": "BUY", "qty": 1,
                            "confidence": 0.65,
                            "reason": f"추세선 상향돌파: 저항선 {resistance:.2f} 돌파"})
        # Breakdown below support trendline
        elif price < support and prev_price >= support:
            signals.append({"symbol": symbol, "side": "SELL", "qty": 1,
                            "confidence": 0.65,
                            "reason": f"추세선 하향이탈: 지지선 {support:.2f} 이탈"})

        return signals

    def get_params(self) -> dict:
        return {"lookback": self.lookback, "min_slope_pct": self.min_slope_pct}
