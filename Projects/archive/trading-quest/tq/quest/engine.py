"""Quest engine -- runs simulated trading quests with scoring and phases."""
from __future__ import annotations

import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from tq.config import (
    COMMISSION_RATE, SLIPPAGE_RATE, DEFAULT_CAPITAL,
    CHECKPOINT_INTERVAL, MAX_DRAWDOWN_LIMIT,
)
from tq.data.fetcher import get_fetcher
from tq.data.granularity import is_trading_day
from tq.sim.broker import SimBroker
from tq.sim.order import Order, OrderSide, OrderType
from tq.sim.portfolio import Position
from tq.quest.score import QuestScore, ScoreTracker
from tq.quest.phase import QuestPhase, PhaseManager
from tq.quest.state import QuestState
from tq.quest.target import evaluate_daily_target
from tq.strategy.registry import get as get_strategy_cls

logger = logging.getLogger(__name__)


class QuestEngine:
    """Runs a trading quest: iterates day-by-day, executes strategy,
    tracks score and phases, and optionally dispatches alerts."""

    def __init__(
        self,
        quest_id: str,
        market: str,
        symbols: list[str],
        initial_capital: float = 100_000.0,
        alert_manager: Optional[Any] = None,
        allow_short: bool = False,
    ):
        self.quest_id = quest_id
        self.market = market.upper()
        self.symbols = symbols
        self.initial_capital = initial_capital
        self.alert_manager = alert_manager
        self.allow_short = allow_short

        commission = COMMISSION_RATE.get(self.market, 0.001)
        slippage = SLIPPAGE_RATE.get(self.market, 0.0005)

        self.broker = SimBroker(initial_capital, self.market, commission, slippage,
                                allow_short=allow_short)
        self.fetcher = get_fetcher(self.market)
        self.score_tracker = ScoreTracker()
        self.phase_manager: Optional[PhaseManager] = None
        self.strategy: Optional[Any] = None
        self.state: Optional[QuestState] = None

        self.current_phase: int = 1
        self.day_results: list[dict] = []
        self.total_score: float = 0.0
        self._data_cache: dict[str, pd.DataFrame] = {}
        self.quests_dir: Optional[Path] = None

    # ------------------------------------------------------------------
    # Quest lifecycle
    # ------------------------------------------------------------------

    def start_quest(self, start_date: str, strategy_name: str = "ma_crossover",
                    quests_dir: Optional[Path] = None) -> QuestState:
        """Start a new quest from scratch."""
        visible_start = date.fromisoformat(start_date)
        current_date = visible_start + timedelta(days=365)
        self.quests_dir = quests_dir

        self.phase_manager = PhaseManager(visible_start)
        self.set_strategy(strategy_name)

        self.state = QuestState(
            quest_id=self.quest_id,
            market=self.market,
            symbols=self.symbols,
            initial_capital=self.initial_capital,
            current_capital=self.initial_capital,
            start_date=start_date,
            current_date=current_date.isoformat(),
            strategy_name=strategy_name,
        )
        self.state.save(self.quests_dir)
        logger.info("Quest %s started: market=%s, start=%s, capital=%.0f",
                     self.quest_id, self.market, start_date, self.initial_capital)
        return self.state

    def resume_quest(self, quest_id: str, quests_dir: Optional[Path] = None) -> QuestState:
        """Resume an existing quest from saved state."""
        self.quests_dir = quests_dir
        self.state = QuestState.load(quest_id, quests_dir)
        self.quest_id = self.state.quest_id
        self.market = self.state.market
        self.symbols = self.state.symbols
        self.initial_capital = self.state.initial_capital

        commission = COMMISSION_RATE.get(self.market, 0.001)
        slippage = SLIPPAGE_RATE.get(self.market, 0.0005)
        self.broker = SimBroker(self.initial_capital, self.market, commission, slippage)
        self.broker.cash = self.state.current_capital
        self._restore_positions(self.state.positions)

        visible_start = date.fromisoformat(self.state.start_date)
        self.phase_manager = PhaseManager(visible_start)

        if self.state.strategy_name:
            self.set_strategy(self.state.strategy_name)

        self.day_results = self.state.daily_results
        self.total_score = self.state.total_score
        self.current_phase = self.state.phase
        return self.state

    def set_strategy(self, strategy_name: str) -> None:
        """Set the active strategy."""
        try:
            cls = get_strategy_cls(strategy_name)
            self.strategy = cls()
            if self.state:
                self.state.strategy_name = strategy_name
                self.state.save(self.quests_dir)
            logger.info("Strategy set: %s", strategy_name)
        except KeyError:
            logger.error("Unknown strategy: %s", strategy_name)
            raise

    # ------------------------------------------------------------------
    # Core loop
    # ------------------------------------------------------------------

    def run(self, start_date: Optional[str], days: int,
            strategy_name: str = "default") -> dict:
        """Run the quest for *days* trading days starting from *start_date*.

        Returns a summary dict.
        """
        if start_date is None:
            if self.state:
                start_date = self.state.current_date
            else:
                raise ValueError("start_date is required when no quest state is loaded")

        if strategy_name != "default" and (self.strategy is None or self.strategy.name != strategy_name):
            try:
                self.set_strategy(strategy_name)
            except KeyError:
                pass

        logger.info(
            "Quest %s: running %d days from %s (market=%s, strategy=%s)",
            self.quest_id, days, start_date, self.market, strategy_name,
        )

        current = date.fromisoformat(start_date)
        days_run = 0
        while days_run < days:
            if not is_trading_day(current, self.market):
                current += timedelta(days=1)
                continue

            day_result = self._run_day(current, days_run)
            self.day_results.append(day_result)
            self.total_score += day_result.get("score", 0)

            # Alert: daily summary
            if self.alert_manager:
                try:
                    self.alert_manager.notify_daily(self.quest_id, day_result)
                except Exception:
                    logger.warning("Failed to send daily alert", exc_info=True)

            # Phase transition check
            new_phase = self._check_phase_transition(days_run)
            if new_phase != self.current_phase:
                old_phase = self.current_phase
                self.current_phase = new_phase
                logger.info("Phase transition: %d -> %d", old_phase, new_phase)
                if self.alert_manager:
                    try:
                        self.alert_manager.notify_phase(
                            self.quest_id, old_phase, new_phase,
                        )
                    except Exception:
                        logger.warning("Failed to send phase alert", exc_info=True)

            # Checkpoint
            if self.state and days_run > 0 and days_run % CHECKPOINT_INTERVAL == 0:
                self._update_state()
                self.state.checkpoint(self.quests_dir)

            days_run += 1
            current += timedelta(days=1)

        if self.state:
            self._update_state()
            self.state.save(self.quests_dir)

        return self._build_summary()

    def _run_day(self, day: date, day_idx: int) -> dict:
        """Simulate a single trading day."""
        date_str = day.isoformat()
        self.broker.start_day(date_str)

        trades_today = 0
        wins = 0
        losses = 0

        # Notify strategy of day start
        if self.strategy and hasattr(self.strategy, "on_day_start"):
            try:
                self.strategy.on_day_start(date_str, self.broker.portfolio)
            except Exception:
                logger.debug("Strategy on_day_start failed", exc_info=True)

        if self.strategy:
            for symbol in self.symbols:
                data = self._get_data(symbol, day)
                if data is None or data.empty:
                    continue

                # Set symbol attr for strategy
                data.attrs["symbol"] = symbol

                if self.current_phase == 1:
                    # Phase 1: minute data for recent 25 days
                    signals = self._run_minute_strategy(symbol, day, data)
                else:
                    signals = self.strategy.decide(data, self.broker.portfolio)

                fills = self.process_signals(signals, symbol, date_str)
                for fill in fills:
                    trades_today += 1
                    self._record_trade_log(fill, date_str)

        # Notify strategy of day end
        if self.strategy and hasattr(self.strategy, "on_day_end"):
            try:
                self.strategy.on_day_end(date_str, self.broker.portfolio)
            except Exception:
                logger.debug("Strategy on_day_end failed", exc_info=True)

        # End day
        day_summary = self.broker.end_day(date_str)

        # Compute score
        pnl_summary = self.broker.pnl
        quest_score = QuestScore(
            return_pct=day_summary.get("return_pct", 0.0),
            win_rate=day_summary.get("win_rate", 0.0),
            trades=day_summary.get("trades", 0),
            max_drawdown=pnl_summary.current_drawdown(),
            sharpe_ratio=pnl_summary.sharpe_ratio,
        )
        score = quest_score.composite_score
        self.score_tracker.add_day(quest_score)

        result = {
            "date": date_str,
            "day_idx": day_idx,
            "return_pct": day_summary.get("return_pct", 0.0),
            "trades": day_summary.get("trades", 0),
            "score": score,
            "win_rate": day_summary.get("win_rate", 0.0),
            "max_drawdown": pnl_summary.current_drawdown(),
            "portfolio_value": self.broker.total_value,
        }

        # Days with 0 trades are neutral (pass)
        target_eval = evaluate_daily_target(result)
        result["target_passed"] = target_eval["passed"]

        return result

    def _run_minute_strategy(self, symbol: str, day: date,
                             daily_data: pd.DataFrame) -> list[dict]:
        """Run strategy on minute data (Phase 1)."""
        if not self.strategy:
            return []

        # For Phase 1, use daily data as fallback
        # The minute data would be fetched separately in full implementation
        return self.strategy.decide(daily_data, self.broker.portfolio)

    def _run_mtf_strategy(self, symbol: str, day: date) -> list[dict]:
        """Run multi-timeframe strategy (Phase 3)."""
        if not self.strategy:
            return []

        candles = {}
        for tf in getattr(self.strategy, "timeframes", ["1d"]):
            data = self._get_data(symbol, day, timeframe=tf)
            if data is not None and not data.empty:
                candles[tf] = data

        if hasattr(self.strategy, "on_candle_mtf"):
            return self.strategy.on_candle_mtf(candles, self.broker.portfolio)
        return []

    # ------------------------------------------------------------------
    # Order processing
    # ------------------------------------------------------------------

    def process_signals(self, signals: list[dict], symbol: str,
                        timestamp: str = "") -> list:
        """Process strategy signals into orders."""
        fills = []
        for sig in signals:
            order_symbol = sig.get("symbol", symbol)
            side_str = sig.get("side", "").upper()
            if side_str not in ("BUY", "SELL"):
                continue

            qty = sig.get("qty", 0)
            if qty <= 0:
                continue

            if side_str == "BUY":
                # Auto position sizing: use up to 30% of available cash per trade
                last_price = self.broker.portfolio._prices.get(order_symbol, 0)
                if last_price > 0:
                    max_affordable = (self.broker.portfolio.cash * 0.3) / last_price
                    if max_affordable < 0.001:
                        continue  # not enough cash
                    qty = min(qty, max_affordable)
                    # Round to reasonable precision
                    if last_price > 1000:
                        qty = round(qty, 4)
                    elif last_price > 1:
                        qty = round(qty, 2)
                    else:
                        qty = round(qty, 0)
                    if qty <= 0:
                        continue

            if side_str == "SELL":
                position = self.broker.portfolio.positions.get(order_symbol)
                if position is None or position.qty <= 0:
                    if not self.allow_short:
                        logger.debug("Skipping SELL for %s: no open position", order_symbol)
                        continue
                    # Short selling: use same sizing as buy
                    last_price = self.broker.portfolio._prices.get(order_symbol, 0)
                    if last_price > 0:
                        max_affordable = (self.broker.portfolio.cash * 0.3) / last_price
                        qty = min(qty, max_affordable)
                        if last_price > 1000:
                            qty = round(qty, 4)
                        elif last_price > 1:
                            qty = round(qty, 2)
                        if qty <= 0:
                            continue
                else:
                    qty = min(qty, position.qty)

            order = Order(
                symbol=order_symbol,
                side=OrderSide.BUY if side_str == "BUY" else OrderSide.SELL,
                order_type=OrderType.MARKET,
                qty=qty,
                strategy=getattr(self.strategy, "name", ""),
                confidence=sig.get("confidence", 0.0),
                timestamp=timestamp,
            )
            self.broker.submit_order(order)

        # Support both date ("2024-01-02") and datetime ("2026-03-01 00:21:00") timestamps
        if timestamp:
            current_day = date.fromisoformat(timestamp[:10])
        else:
            current_day = None
        symbols_to_process = {order.symbol for order in self.broker.pending_orders}

        # Process only symbols with pending orders at the simulated day's prices.
        for sym in sorted(symbols_to_process):
            data = self._get_data(sym, current_day)
            if data is not None and not data.empty:
                close = data["close"].iloc[-1] if "close" in data.columns else data["Close"].iloc[-1]
                high = data["high"].iloc[-1] if "high" in data.columns else data["High"].iloc[-1]
                low = data["low"].iloc[-1] if "low" in data.columns else data["Low"].iloc[-1]
                open_ = data["open"].iloc[-1] if "open" in data.columns else data["Open"].iloc[-1]
                result = self.broker.process_bar(sym, open_, high, low, close, timestamp)
                fills.extend(result)

                for fill in result:
                    trade_info = {
                        "symbol": sym,
                        "side": fill.order.side.value,
                        "qty": fill.fill_qty,
                        "price": fill.fill_price,
                        "strategy": fill.order.strategy,
                        "timestamp": timestamp,
                    }
                    # Enrich with completed trade PnL if this was a sell
                    if fill.order.side.value == "SELL":
                        for ct in self.broker.completed_trades:
                            if (ct.symbol == sym and ct.exit_time == timestamp
                                    and ct.qty == fill.fill_qty):
                                trade_info["entry_price"] = ct.entry_price
                                trade_info["exit_price"] = ct.exit_price
                                trade_info["pnl"] = ct.pnl
                                trade_info["pnl_pct"] = ct.pnl_pct
                                break
                    self.on_trade_fill(trade_info)
        return fills

    def submit_order(self, symbol: str, side: str, qty: float,
                     order_type: str = "MARKET",
                     price: Optional[float] = None) -> None:
        """Submit a manual order."""
        order = Order(
            symbol=symbol,
            side=OrderSide.BUY if side.upper() == "BUY" else OrderSide.SELL,
            order_type=OrderType(order_type.upper()),
            qty=qty,
            price=price,
        )
        self.broker.submit_order(order)

    def on_trade_fill(self, trade: dict) -> None:
        """Called after a trade is filled. Dispatches alert and records to journal."""
        if self.alert_manager:
            try:
                self.alert_manager.notify_trade(trade)
            except Exception:
                logger.warning("Failed to send trade alert", exc_info=True)

        # Record to journal if strategy supports it (adaptive strategy)
        if self.strategy and hasattr(self.strategy, "record_completed_trade"):
            try:
                self.strategy.record_completed_trade(trade)
            except Exception:
                logger.debug("Failed to record trade to journal", exc_info=True)

    # ------------------------------------------------------------------
    # Batch / multi-phase
    # ------------------------------------------------------------------

    def auto_run_day(self, current_date: date) -> dict:
        """Automatically run a single day (Phase 2+)."""
        if not is_trading_day(current_date, self.market):
            return {"date": current_date.isoformat(), "skipped": True}
        return self._run_day(current_date, len(self.day_results))

    def auto_run_batch(self, start_date: str, days: int) -> list[dict]:
        """Auto-run a batch of days (Phase 2)."""
        results = []
        current = date.fromisoformat(start_date)
        days_run = 0
        while days_run < days:
            if is_trading_day(current, self.market):
                result = self.auto_run_day(current)
                results.append(result)
                days_run += 1
            current += timedelta(days=1)
        return results

    def run_to_phase(self, target_phase: int, max_days: int = 100) -> dict:
        """Run until reaching a target phase."""
        days_run = 0
        current = date.fromisoformat(
            self.state.current_date if self.state else "2024-01-01"
        )
        while self.current_phase < target_phase and days_run < max_days:
            if is_trading_day(current, self.market):
                result = self._run_day(current, days_run)
                self.day_results.append(result)
                self.total_score += result.get("score", 0)
                new_phase = self._check_phase_transition(days_run)
                if new_phase != self.current_phase:
                    self.current_phase = new_phase
                days_run += 1
            current += timedelta(days=1)
        if self.state:
            self._update_state()
            self.state.save(self.quests_dir)
        return self._build_summary()

    # ------------------------------------------------------------------
    # Data access
    # ------------------------------------------------------------------

    def _get_data(self, symbol: str, day: Optional[date] = None,
                  timeframe: str = "1d") -> Optional[pd.DataFrame]:
        """Get OHLCV data for a symbol, with caching."""
        cache_key = f"{symbol}_{timeframe}"
        if cache_key in self._data_cache:
            return self._slice_history(self._data_cache[cache_key], day)

        try:
            return self._slice_history(self.ensure_data(symbol, timeframe), day)
        except Exception as e:
            logger.warning("Failed to get data for %s: %s", symbol, e)
            return None

    def ensure_data(self, symbol: str, timeframe: str = "1d") -> pd.DataFrame:
        """Ensure data is available. Checks SQLite cache first, then fetches."""
        cache_key = f"{symbol}_{timeframe}"

        # 1. Check in-memory cache
        if cache_key in self._data_cache and not self._data_cache[cache_key].empty:
            return self._data_cache[cache_key]

        # 2. Check SQLite cache (DB may have more data than yfinance free tier)
        try:
            from tq.data.cache import DataCache
            db_cache = DataCache()
            if timeframe == "1d":
                df = db_cache.load_daily(symbol, self.market)
                if not df.empty and len(df) > 50:
                    self._data_cache[cache_key] = df
                    logger.info("Loaded %d rows from DB cache for %s", len(df), symbol)
                    return df
        except Exception:
            pass

        # 3. Fallback: fetch from API
        try:
            start = (date.today() - timedelta(days=400)).isoformat()
            end = date.today().isoformat()
            df = self.fetcher.fetch_timeframe(symbol, start, end, timeframe)
            self._data_cache[cache_key] = df
            return df
        except Exception:
            logger.warning("Data fetch failed for %s", symbol, exc_info=True)
            return pd.DataFrame()

    def _slice_history(self, data: pd.DataFrame,
                       day: Optional[date]) -> pd.DataFrame:
        """Limit visible data to the current simulation day."""
        if day is None or data is None or data.empty:
            return data

        cutoff = pd.Timestamp(day) + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
        if isinstance(data.index, pd.DatetimeIndex):
            if data.index.tz is not None:
                if cutoff.tzinfo is None:
                    cutoff = cutoff.tz_localize(data.index.tz)
                else:
                    cutoff = cutoff.tz_convert(data.index.tz)
            history = data.loc[data.index <= cutoff].copy()
        else:
            history = data.loc[data.index <= day.isoformat()].copy()

        history.attrs = dict(getattr(data, "attrs", {}))
        return history

    def get_visible_data(self, symbol: str) -> pd.DataFrame:
        """Get data visible to the current quest (up to current_date)."""
        data = self._get_data(symbol)
        if data is None or data.empty:
            return pd.DataFrame()
        if self.state:
            current = date.fromisoformat(self.state.current_date[:10])
            return self._slice_history(data, current)
        return data

    def get_observation(self) -> dict:
        """Get current observation for agent interface."""
        return {
            "quest_id": self.quest_id,
            "market": self.market,
            "phase": self.current_phase,
            "day": len(self.day_results),
            "total_score": self.total_score,
            "portfolio_value": self.broker.total_value,
            "cash": self.broker.cash,
            "drawdown": self.broker.pnl.current_drawdown(),
            "positions": self.broker.portfolio.to_dict().get("positions", {}),
        }

    # ------------------------------------------------------------------
    # Phase logic
    # ------------------------------------------------------------------

    def _check_phase_transition(self, day_idx: int) -> int:
        """Determine current phase based on quest progress."""
        if self.phase_manager:
            score = self.day_results[-1].get("score", 0.0) if self.day_results else 0.0
            drawdown = self.broker.pnl.current_drawdown()
            new_phase = self.phase_manager.record_day(score, drawdown)
            if new_phase:
                return new_phase.value
            return self.phase_manager.current_phase.value

        # Fallback simple phase logic
        if day_idx >= 20:
            return 3
        elif day_idx >= 10:
            return 2
        return 1

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------

    def _update_state(self) -> None:
        """Update state from current engine state."""
        if not self.state:
            return
        self.state.current_capital = self.broker.cash
        self.state.total_score = self.total_score
        self.state.phase = self.current_phase
        self.state.daily_results = self.day_results
        self.state.current_day = len(self.day_results)
        self.state.positions = self.broker.portfolio.to_dict().get("positions", {})
        if self.day_results:
            next_day = date.fromisoformat(self.day_results[-1]["date"]) + timedelta(days=1)
            self.state.current_date = next_day.isoformat()

    def _record_trade_log(self, fill, date_str: str) -> None:
        """Record a trade in the state trade_log."""
        if not self.state:
            return
        self.state.trade_log.append({
            "symbol": fill.order.symbol,
            "side": fill.order.side.value,
            "qty": fill.fill_qty,
            "price": fill.fill_price,
            "commission": fill.commission,
            "timestamp": date_str,
        })

    def _restore_positions(self, positions: dict[str, dict]) -> None:
        """Restore saved positions into the broker portfolio."""
        self.broker.portfolio.positions = {}
        for symbol, raw in positions.items():
            position = Position(
                symbol=symbol,
                qty=float(raw.get("qty", 0.0)),
                avg_price=float(raw.get("avg_price", 0.0)),
                current_price=float(raw.get("current_price", raw.get("avg_price", 0.0))),
            )
            self.broker.portfolio.positions[symbol] = position
            self.broker.portfolio.update_price(symbol, position.current_price)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def _build_summary(self) -> dict:
        total_trades = sum(d.get("trades", 0) for d in self.day_results)
        return {
            "quest_id": self.quest_id,
            "days": len(self.day_results),
            "total_score": self.total_score,
            "total_trades": total_trades,
            "final_phase": self.current_phase,
            "portfolio_value": self.broker.total_value,
            "return_pct": (self.broker.total_value - self.initial_capital)
                          / self.initial_capital * 100,
            "max_drawdown": self.broker.pnl.max_drawdown(),
        }
