"""Adaptive meta-strategy that self-learns from journal analysis."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from tq.strategy.base import BaseStrategy
from tq.strategy.registry import strategy as strategy_decorator, get as get_strategy_cls
from tq.journal.journal import TradingJournal
from tq.journal.analyzer import TradeAnalyzer
from tq.journal.rules import TradingRules
from tq.strategy.indicator import adx, atr, sma, rsi, macd

logger = logging.getLogger(__name__)


# Default sub-strategies to delegate to
_DEFAULT_SUB_STRATEGIES = [
    "ma_crossover", "rsi", "macd", "bollinger", "momentum",
]


@strategy_decorator("adaptive")
class AdaptiveStrategy(BaseStrategy):
    """Meta-strategy that adapts based on journal analysis.

    This strategy:
    1. Detects current market regime
    2. Checks journal for which strategies perform best in this regime
    3. Delegates to the best-performing strategy
    4. Adjusts position size based on confidence
    5. Records results back to journal

    Scoring: +0.1 per win, -0.2 per loss
    Target: +4% in 5 days
    """

    name = "adaptive"
    description = "Self-learning meta-strategy v2: macd 집중 + 빠른 손절 + 다중 확인 진입"
    version = "2.0"

    def __init__(self, **params):
        self.target_return_5d = params.get("target_return_5d", 0.04)
        self.max_loss_per_trade = params.get("max_loss_per_trade", 0.005)  # v2: 0.5% 빠른 손절
        self.min_win_rate = params.get("min_win_rate", 0.67)
        self.position_size_pct = params.get("position_size_pct", 0.10)   # v2: 10%로 축소
        self.use_journal = params.get("use_journal", True)

        self.journal = TradingJournal()
        self.analyzer = TradeAnalyzer(self.journal)
        self.rules = TradingRules()

        self._active_strategy: Optional[BaseStrategy] = None
        self._active_strategy_name: str = ""
        self._current_regime: str = "unknown"
        self._strategy_weights: dict[str, float] = {}
        self._sub_strategy_names: list[str] = list(_DEFAULT_SUB_STRATEGIES)
        self._sub_strategies: dict[str, BaseStrategy] = {}
        self._day_trades: list[dict] = []
        self._session_count: int = 0

        self._pipeline_config: Optional[dict] = None
        self._memory = None

        self._init_sub_strategies()
        self._load_pipeline_config()
        self._load_memory_params()

    def _init_sub_strategies(self) -> None:
        """Initialize available sub-strategies."""
        for name in self._sub_strategy_names:
            try:
                cls = get_strategy_cls(name)
                self._sub_strategies[name] = cls()
            except (KeyError, Exception) as e:
                logger.debug("Could not load sub-strategy '%s': %s", name, e)

    def _load_memory_params(self) -> None:
        """Load best known params from persistent memory for each sub-strategy."""
        try:
            from tq.journal.memory import TradingMemory
            self._memory = TradingMemory()
            for name, strat in self._sub_strategies.items():
                best = self._memory.get_best_params(name)
                if best and hasattr(strat, "configure"):
                    strat.configure(best)
                    logger.info(
                        "Loaded memory params for '%s': %s", name, best
                    )
        except Exception as exc:
            logger.debug("Failed to load memory params: %s", exc)

    def _load_pipeline_config(self) -> None:
        """Load the latest pipeline results to know which strategies to use."""
        config_path = Path(".tq-journal/pipeline/best-config.json")
        if not config_path.exists():
            return
        try:
            self._pipeline_config = json.loads(
                config_path.read_text(encoding="utf-8")
            )
            # Use pipeline's recommended strategies and weights
            strategies = self._pipeline_config.get("strategies", [])
            if strategies:
                pipeline_names = [s["strategy"] for s in strategies
                                  if isinstance(s, dict) and "strategy" in s]
                if pipeline_names:
                    self._sub_strategy_names = list(
                        dict.fromkeys(pipeline_names + self._sub_strategy_names)
                    )
                    self._init_sub_strategies()
            weights = self._pipeline_config.get("strategy_weights", {})
            if weights:
                self._strategy_weights = weights
            logger.info("Loaded pipeline config with %d strategies", len(strategies))
        except (json.JSONDecodeError, OSError) as exc:
            logger.debug("Failed to load pipeline config: %s", exc)

    def decide(self, data: pd.DataFrame, portfolio: Any) -> list[dict]:
        """Main decision method.

        1. Detect market regime
        2. Select best strategy for this regime (from journal analysis)
        3. Get signal from selected strategy
        4. Apply position sizing rules
        5. Add stop-loss based on ATR
        """
        if data is None or data.empty or len(data) < 30:
            return []

        symbol = (data.attrs.get("symbol", "UNKNOWN")
                  if hasattr(data, "attrs") else "UNKNOWN")

        close = data["close"] if "close" in data.columns else data["Close"]
        high = data["high"] if "high" in data.columns else data["High"]
        low = data["low"] if "low" in data.columns else data["Low"]

        # 1. Detect market regime
        self._current_regime = self.analyzer.detect_market_regime(symbol, data)

        # 2. Select best strategy
        self._select_strategy(symbol, data)

        if self._active_strategy is None:
            return []

        # 3. Get signal from selected strategy
        signals = self._active_strategy.decide(data, portfolio)
        if not signals:
            return []

        # 4. v2 다중 지표 확인 필터 (진입 품질 강화)
        rsi_val = rsi(close, 14)
        current_rsi = rsi_val.iloc[-1] if not rsi_val.empty else 50
        sma20 = sma(close, 20)
        sma50_val = sma(close, 50)
        current_sma20 = sma20.iloc[-1] if not sma20.empty else close.iloc[-1]
        current_sma50 = sma50_val.iloc[-1] if not sma50_val.empty else close.iloc[-1]
        current_price = close.iloc[-1]

        filtered_signals = []
        for sig in signals:
            if sig.get("side", "").upper() == "SELL":
                # 매도는 항상 허용 (빠른 탈출)
                filtered_signals.append(sig)
                continue

            # v2 진입 조건: 3가지 모두 충족해야 매수
            # 1) 규칙 필터 통과
            allowed, reason = self.rules.check_entry(
                symbol=sig.get("symbol", symbol),
                strategy=self._active_strategy_name,
                regime=self._current_regime,
                indicators={"confidence": sig.get("confidence", 0)},
            )
            if not allowed:
                logger.debug("Signal blocked by rule: %s", reason)
                continue

            # 2) RSI 필터: 과매수(>70) 상태에서 매수 금지
            if current_rsi > 70:
                logger.debug("Signal blocked: RSI=%.1f (과매수)", current_rsi)
                continue

            # 3) 추세 확인: 가격이 SMA20 아래이면 매수 금지 (하락 추세)
            if current_price < current_sma20 and self._current_regime == "trending_down":
                logger.debug("Signal blocked: 하락 추세 (price < SMA20)")
                continue

            # 4) 변동성 필터: ATR이 너무 크면 (가격 대비 3% 초과) 매수 금지
            atr_val_series = atr(high, low, close, period=14)
            if not atr_val_series.empty:
                atr_pct = atr_val_series.iloc[-1] / current_price
                if atr_pct > 0.03:
                    logger.debug("Signal blocked: 변동성 과다 ATR=%.1f%%", atr_pct*100)
                    continue

            filtered_signals.append(sig)

        if not filtered_signals:
            return []

        # 5. Apply position sizing and stop-loss
        atr_val = atr(high, low, close, period=14)
        current_atr = atr_val.iloc[-1] if not atr_val.empty else 0
        current_price = close.iloc[-1]

        result = []
        for sig in filtered_signals:
            sig = dict(sig)  # copy

            # Position sizing based on portfolio value and Kelly
            if hasattr(portfolio, "total_value"):
                pv = portfolio.total_value
            elif hasattr(portfolio, "cash"):
                pv = portfolio.cash
            else:
                pv = 100_000

            # Use analyzer-recommended position size
            pos_pct = self.position_size_pct
            if self._strategy_weights:
                weight = self._strategy_weights.get(self._active_strategy_name, 0.5)
                pos_pct = self.position_size_pct * weight * 2  # scale by weight
                pos_pct = max(0.05, min(0.25, pos_pct))

            if sig.get("side", "").upper() == "BUY":
                max_cost = pv * pos_pct
                price = sig.get("price") or current_price
                if price > 0:
                    qty = int(max_cost / price)
                    if qty <= 0:
                        continue
                    sig["qty"] = qty

                    # v2: 빠른 손절 (-0.5%) + 적절한 익절 (+1%)
                    # 손절: max_loss_per_trade (0.5%) 또는 ATR 기반 중 더 타이트한 것
                    max_loss_price = price * (1 - self.max_loss_per_trade)
                    if current_atr > 0:
                        atr_stop = price - 1.0 * current_atr  # v2: 1.0x ATR (기존 1.5x)
                        sig["stop_loss"] = max(atr_stop, max_loss_price)
                    else:
                        sig["stop_loss"] = max_loss_price

                    # v2: 익절은 손절의 2배 (리스크:리워드 = 1:2)
                    risk = price - sig["stop_loss"]
                    sig["take_profit"] = price + 2.0 * risk

            sig["reason"] = (
                f"[adaptive/{self._active_strategy_name}] "
                f"regime={self._current_regime} "
                f"{sig.get('reason', '')}"
            )
            result.append(sig)

        return result

    def _select_strategy(self, symbol: str, data: pd.DataFrame) -> None:
        """Select the best strategy for the current regime."""
        if not self._sub_strategies:
            return

        # Check journal for strategy weights
        if self.use_journal:
            self._strategy_weights = self.analyzer.recommend_strategy_weights()

        # If we have weights, pick the highest-weighted strategy
        if self._strategy_weights:
            # Filter to available sub-strategies
            available = {
                name: w for name, w in self._strategy_weights.items()
                if name in self._sub_strategies
            }
            if available:
                best_name = max(available, key=available.get)
                self._active_strategy = self._sub_strategies[best_name]
                self._active_strategy_name = best_name
                return

        # v2: 일지 분석 결과 기반 — macd가 유일한 양호 전략
        # 국면별로 macd를 우선하되, 보조 전략을 백업으로
        regime = self._current_regime
        if regime in ("trending_up",):
            preferred = ["macd", "ma_crossover", "bollinger"]
        elif regime in ("trending_down",):
            preferred = ["macd"]  # 하락장에서는 macd만 (나머지는 손실 기록)
        elif regime == "volatile":
            preferred = ["macd", "bollinger"]
        else:  # ranging / unknown
            preferred = ["macd", "stochastic", "bollinger"]

        for name in preferred:
            if name in self._sub_strategies:
                self._active_strategy = self._sub_strategies[name]
                self._active_strategy_name = name
                return

        # Fallback: first available
        if self._sub_strategies:
            name = next(iter(self._sub_strategies))
            self._active_strategy = self._sub_strategies[name]
            self._active_strategy_name = name

    def on_day_start(self, date: str, portfolio: Any) -> None:
        """Called at the start of each trading day."""
        self._day_trades = []
        # Refresh rules periodically
        if self._session_count % 5 == 0 and self.use_journal:
            try:
                self.rules.update_rules(self.analyzer)
            except Exception:
                logger.debug("Failed to update rules", exc_info=True)

    def on_day_end(self, date: str, portfolio: Any) -> None:
        """Record session to journal and update analysis."""
        self._session_count += 1

        if not self.use_journal:
            return

        # Build session summary
        wins = sum(1 for t in self._day_trades if t.get("pnl", 0) > 0)
        losses = sum(1 for t in self._day_trades if t.get("pnl", 0) < 0)
        net_pnl = sum(t.get("pnl", 0) for t in self._day_trades)
        score = sum(t.get("score", 0) for t in self._day_trades)

        strategies_used = list({t.get("strategy", "") for t in self._day_trades})
        best_trade = max(self._day_trades, key=lambda t: t.get("pnl", 0),
                         default=None) if self._day_trades else None
        worst_trade = min(self._day_trades, key=lambda t: t.get("pnl", 0),
                          default=None) if self._day_trades else None

        session = {
            "date": date,
            "total_trades": len(self._day_trades),
            "wins": wins,
            "losses": losses,
            "net_pnl": net_pnl,
            "score": score,
            "strategies_used": strategies_used,
            "best_trade": best_trade,
            "worst_trade": worst_trade,
            "regime": self._current_regime,
            "lessons": [],
        }

        try:
            self.journal.record_session(session)
        except Exception:
            logger.debug("Failed to record session", exc_info=True)

    def record_completed_trade(self, trade_info: dict) -> None:
        """Record a completed trade to the journal.
        Called by the engine after a trade fill.
        """
        trade_info["score"] = TradingJournal.calculate_score(trade_info)
        trade_info.setdefault("strategy", self._active_strategy_name)
        trade_info.setdefault("market_context", {"regime": self._current_regime})

        self._day_trades.append(trade_info)

        if self.use_journal:
            try:
                self.journal.record_trade(trade_info)
            except Exception:
                logger.debug("Failed to record trade", exc_info=True)

    def get_params(self) -> dict:
        return {
            "target_return_5d": self.target_return_5d,
            "max_loss_per_trade": self.max_loss_per_trade,
            "min_win_rate": self.min_win_rate,
            "position_size_pct": self.position_size_pct,
            "use_journal": self.use_journal,
            "active_strategy": self._active_strategy_name,
            "current_regime": self._current_regime,
        }

    def configure(self, params: dict) -> None:
        """Set tunable parameters."""
        for key in ("target_return_5d", "max_loss_per_trade", "min_win_rate",
                     "position_size_pct", "use_journal"):
            if key in params:
                setattr(self, key, params[key])
