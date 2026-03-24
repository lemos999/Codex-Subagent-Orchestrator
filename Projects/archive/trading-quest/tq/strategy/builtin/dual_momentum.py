"""Dual Momentum strategy -- absolute + relative momentum."""
from __future__ import annotations
from typing import Any
import pandas as pd
from tq.strategy.base import BaseStrategy
from tq.strategy.registry import strategy
from tq.strategy.indicator import roc, sma


@strategy("dual_momentum")
class DualMomentum(BaseStrategy):
    """듀얼 모멘텀: 절대 모멘텀 + 상대 모멘텀 동시 충족"""

    name = "dual_momentum"
    description = "절대: 12개월 수익률 > 0, 상대: SMA 위 + ROC 양수. 둘 다 충족 시 매수"

    def __init__(self, abs_period: int = 252, rel_period: int = 60,
                 sma_period: int = 50):
        self.abs_period = abs_period
        self.rel_period = rel_period
        self.sma_period = sma_period

    def decide(self, data: pd.DataFrame, portfolio: Any) -> list[dict]:
        min_len = max(self.abs_period, self.sma_period) + 2
        if len(data) < min_len:
            return []
        cols = {c.lower(): c for c in data.columns}
        close = data[cols.get("close", "close")]

        signals = []
        symbol = data.attrs.get("symbol", "UNKNOWN") if hasattr(data, "attrs") else "UNKNOWN"

        price = close.iloc[-1]

        # Absolute momentum: is the asset rising over abs_period?
        abs_roc = roc(close, self.abs_period)
        abs_momentum = abs_roc.iloc[-1] if pd.notna(abs_roc.iloc[-1]) else 0

        # Relative momentum: price above SMA + short-term ROC positive
        ma = sma(close, self.sma_period)
        rel_roc = roc(close, self.rel_period)
        rel_roc_val = rel_roc.iloc[-1] if pd.notna(rel_roc.iloc[-1]) else 0
        above_sma = price > ma.iloc[-1] if pd.notna(ma.iloc[-1]) else False

        # Dual momentum buy: both absolute and relative positive
        if abs_momentum > 0 and rel_roc_val > 0 and above_sma:
            conf = min(1.0, 0.5 + abs_momentum / 100 * 0.3 + rel_roc_val / 100 * 0.2)
            signals.append({"symbol": symbol, "side": "BUY", "qty": 1,
                            "confidence": conf,
                            "reason": f"듀얼모멘텀 매수: 절대ROC={abs_momentum:.1f}% + 상대ROC={rel_roc_val:.1f}%"})
        # Exit: either momentum turns negative
        elif abs_momentum < 0 and not above_sma:
            signals.append({"symbol": symbol, "side": "SELL", "qty": 1,
                            "confidence": 0.6,
                            "reason": f"듀얼모멘텀 매도: 절대ROC={abs_momentum:.1f}% + SMA하향"})

        return signals

    def get_params(self) -> dict:
        return {"abs_period": self.abs_period, "rel_period": self.rel_period,
                "sma_period": self.sma_period}
