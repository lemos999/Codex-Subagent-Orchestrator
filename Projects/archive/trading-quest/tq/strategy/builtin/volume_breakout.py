"""Volume Breakout strategy."""
from __future__ import annotations
from typing import Any
import pandas as pd
from tq.strategy.base import BaseStrategy
from tq.strategy.registry import strategy
from tq.strategy.indicator import sma, obv


@strategy("volume_breakout")
class VolumeBreakoutStrategy(BaseStrategy):
    name = "volume_breakout"
    description = "Buy on high-volume breakout, sell on volume divergence"

    def __init__(self, period: int = 20, volume_mult: float = 2.0):
        self.period = period
        self.volume_mult = volume_mult

    def decide(self, data: pd.DataFrame, portfolio: Any) -> list[dict]:
        if len(data) < self.period + 1:
            return []
        cols = {c.lower(): c for c in data.columns}
        close = data[cols.get("close", "close")]
        volume = data[cols.get("volume", "volume")]

        avg_vol = sma(volume, self.period)
        price_change = close.pct_change()

        signals = []
        symbol = data.attrs.get("symbol", "UNKNOWN") if hasattr(data, "attrs") else "UNKNOWN"

        vol_ratio = volume.iloc[-1] / avg_vol.iloc[-1] if avg_vol.iloc[-1] > 0 else 0
        if vol_ratio >= self.volume_mult and price_change.iloc[-1] > 0:
            signals.append({"symbol": symbol, "side": "BUY", "qty": 1,
                            "confidence": min(1.0, vol_ratio / self.volume_mult * 0.5),
                            "reason": f"Volume breakout ({vol_ratio:.1f}x avg)"})
        elif vol_ratio >= self.volume_mult and price_change.iloc[-1] < -0.01:
            signals.append({"symbol": symbol, "side": "SELL", "qty": 1,
                            "confidence": 0.6, "reason": f"Volume breakdown ({vol_ratio:.1f}x avg)"})
        return signals

    def get_params(self) -> dict:
        return {"period": self.period, "volume_mult": self.volume_mult}
