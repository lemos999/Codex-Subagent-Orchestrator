"""Ichimoku Advanced strategy -- triple confirmation."""
from __future__ import annotations
from typing import Any
import pandas as pd
from tq.strategy.base import BaseStrategy
from tq.strategy.registry import strategy
from tq.strategy.indicator import ichimoku


@strategy("ichimoku_advanced")
class IchimokuAdvanced(BaseStrategy):
    """일목균형표 고급: 전환선/기준선 교차 + 구름 돌파 + 후행스팬 확인"""

    name = "ichimoku_advanced"
    description = "3중 확인: 전환선>기준선 + 가격>구름 + 후행스팬>26일전 가격"

    def __init__(self, tenkan: int = 9, kijun: int = 26, senkou_b: int = 52):
        self.tenkan = tenkan
        self.kijun = kijun
        self.senkou_b = senkou_b

    def decide(self, data: pd.DataFrame, portfolio: Any) -> list[dict]:
        min_len = self.senkou_b + self.kijun + 1
        if len(data) < min_len:
            return []
        cols = {c.lower(): c for c in data.columns}
        high = data[cols.get("high", "high")]
        low = data[cols.get("low", "low")]
        close = data[cols.get("close", "close")]

        ich = ichimoku(high, low, close, self.tenkan, self.kijun, self.senkou_b)
        signals = []
        symbol = data.attrs.get("symbol", "UNKNOWN") if hasattr(data, "attrs") else "UNKNOWN"

        tenkan_sen = ich["tenkan_sen"]
        kijun_sen = ich["kijun_sen"]
        senkou_a = ich["senkou_span_a"]
        senkou_b_val = ich["senkou_span_b"]
        chikou = ich["chikou_span"]

        price = close.iloc[-1]

        # Cloud top/bottom at current bar
        cloud_top = max(senkou_a.iloc[-1], senkou_b_val.iloc[-1]) if pd.notna(senkou_a.iloc[-1]) and pd.notna(senkou_b_val.iloc[-1]) else None
        cloud_bottom = min(senkou_a.iloc[-1], senkou_b_val.iloc[-1]) if pd.notna(senkou_a.iloc[-1]) and pd.notna(senkou_b_val.iloc[-1]) else None

        # Chikou confirmation: chikou (shifted back 26) vs price 26 bars ago
        chikou_idx = -1 - self.kijun
        chikou_ok_buy = False
        chikou_ok_sell = False
        if abs(chikou_idx) < len(close) and pd.notna(chikou.iloc[-1]):
            price_26_ago = close.iloc[chikou_idx]
            chikou_ok_buy = chikou.iloc[-1] > price_26_ago
            chikou_ok_sell = chikou.iloc[-1] < price_26_ago

        tk_cross_up = (pd.notna(tenkan_sen.iloc[-1]) and pd.notna(kijun_sen.iloc[-1]) and
                       pd.notna(tenkan_sen.iloc[-2]) and pd.notna(kijun_sen.iloc[-2]) and
                       tenkan_sen.iloc[-1] > kijun_sen.iloc[-1] and
                       tenkan_sen.iloc[-2] <= kijun_sen.iloc[-2])

        tk_cross_down = (pd.notna(tenkan_sen.iloc[-1]) and pd.notna(kijun_sen.iloc[-1]) and
                         pd.notna(tenkan_sen.iloc[-2]) and pd.notna(kijun_sen.iloc[-2]) and
                         tenkan_sen.iloc[-1] < kijun_sen.iloc[-1] and
                         tenkan_sen.iloc[-2] >= kijun_sen.iloc[-2])

        # Triple buy: TK cross up + price above cloud + chikou above 26-ago price
        if tk_cross_up and cloud_top is not None and price > cloud_top and chikou_ok_buy:
            signals.append({"symbol": symbol, "side": "BUY", "qty": 1,
                            "confidence": 0.8, "reason": "일목 3중 확인 매수: TK교차+구름돌파+후행스팬"})
        # Partial buy: TK cross up + price above cloud (2/3 confirmation)
        elif tk_cross_up and cloud_top is not None and price > cloud_top:
            signals.append({"symbol": symbol, "side": "BUY", "qty": 1,
                            "confidence": 0.6, "reason": "일목 2중 확인 매수: TK교차+구름돌파"})
        # Triple sell
        elif tk_cross_down and cloud_bottom is not None and price < cloud_bottom and chikou_ok_sell:
            signals.append({"symbol": symbol, "side": "SELL", "qty": 1,
                            "confidence": 0.8, "reason": "일목 3중 확인 매도: TK교차+구름이탈+후행스팬"})
        elif tk_cross_down and cloud_bottom is not None and price < cloud_bottom:
            signals.append({"symbol": symbol, "side": "SELL", "qty": 1,
                            "confidence": 0.6, "reason": "일목 2중 확인 매도: TK교차+구름이탈"})

        return signals

    def get_params(self) -> dict:
        return {"tenkan": self.tenkan, "kijun": self.kijun,
                "senkou_b": self.senkou_b}
