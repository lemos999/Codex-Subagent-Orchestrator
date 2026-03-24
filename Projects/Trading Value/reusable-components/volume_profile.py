"""Volume Profile strategy -- OBV trend + volume surge + VWMA."""
from __future__ import annotations
from typing import Any
import pandas as pd
from tq.strategy.base import BaseStrategy
from tq.strategy.registry import strategy
from tq.strategy.indicator import obv, sma


@strategy("volume_profile")
class VolumeProfile(BaseStrategy):
    """거래량 프로파일: OBV 추세 + 거래량 급증 감지 + 거래량 가중 이동평균"""

    name = "volume_profile"
    description = "OBV 방향 + 거래량이 20일 평균의 2배 이상일 때 신호"

    def __init__(self, period: int = 20, volume_mult: float = 2.0,
                 obv_sma_period: int = 10):
        self.period = period
        self.volume_mult = volume_mult
        self.obv_sma_period = obv_sma_period

    def decide(self, data: pd.DataFrame, portfolio: Any) -> list[dict]:
        if len(data) < self.period + self.obv_sma_period:
            return []
        cols = {c.lower(): c for c in data.columns}
        close = data[cols.get("close", "close")]
        volume = data[cols.get("volume", "volume")]

        signals = []
        symbol = data.attrs.get("symbol", "UNKNOWN") if hasattr(data, "attrs") else "UNKNOWN"

        # OBV and its trend
        obv_line = obv(close, volume)
        obv_ma = sma(obv_line, self.obv_sma_period)
        obv_rising = obv_line.iloc[-1] > obv_ma.iloc[-1] if pd.notna(obv_ma.iloc[-1]) else False
        obv_falling = obv_line.iloc[-1] < obv_ma.iloc[-1] if pd.notna(obv_ma.iloc[-1]) else False

        # Volume surge
        avg_vol = sma(volume, self.period)
        vol_ratio = volume.iloc[-1] / avg_vol.iloc[-1] if pd.notna(avg_vol.iloc[-1]) and avg_vol.iloc[-1] > 0 else 0
        is_surge = vol_ratio >= self.volume_mult

        # VWMA (volume-weighted moving average)
        vwma_num = (close * volume).rolling(window=self.period).sum()
        vwma_den = volume.rolling(window=self.period).sum()
        vwma = vwma_num / vwma_den.replace(0, float("nan"))
        price = close.iloc[-1]
        price_above_vwma = price > vwma.iloc[-1] if pd.notna(vwma.iloc[-1]) else False
        price_below_vwma = price < vwma.iloc[-1] if pd.notna(vwma.iloc[-1]) else False

        # Price direction
        price_up = close.iloc[-1] > close.iloc[-2] if len(close) >= 2 else False
        price_down = close.iloc[-1] < close.iloc[-2] if len(close) >= 2 else False

        # Buy: OBV rising + volume surge + price above VWMA + price up
        if obv_rising and is_surge and price_above_vwma and price_up:
            signals.append({"symbol": symbol, "side": "BUY", "qty": 1,
                            "confidence": min(1.0, vol_ratio / self.volume_mult * 0.5),
                            "reason": f"거래량 프로파일 매수: OBV상승+거래량{vol_ratio:.1f}배+VWMA상향"})
        # Sell: OBV falling + volume surge + price below VWMA + price down
        elif obv_falling and is_surge and price_below_vwma and price_down:
            signals.append({"symbol": symbol, "side": "SELL", "qty": 1,
                            "confidence": 0.65,
                            "reason": f"거래량 프로파일 매도: OBV하락+거래량{vol_ratio:.1f}배+VWMA하향"})

        return signals

    def get_params(self) -> dict:
        return {"period": self.period, "volume_mult": self.volume_mult,
                "obv_sma_period": self.obv_sma_period}
