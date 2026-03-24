"""Web routes and API endpoints for Trading Quest."""
from __future__ import annotations

import json
import logging
import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from tq.config import QUESTS_DIR

logger = logging.getLogger(__name__)


def _get_quests_dir() -> Path:
    from flask import current_app

    configured = current_app.config.get("QUESTS_DIR")
    return Path(configured) if configured else QUESTS_DIR


def _get_cache():
    from flask import current_app
    from tq.data.cache import DataCache

    return DataCache(current_app.config.get("DATA_CACHE_PATH"))


def _normalize_list(value, default: list[str]) -> list[str]:
    if value is None:
        return list(default)
    if isinstance(value, str):
        items = [item.strip() for item in value.split(",")]
    else:
        items = [str(item).strip() for item in value]
    return [item for item in items if item]


def _load_cached_data(symbol: str, market: str, interval: str,
                      start: str | None = None,
                      end: str | None = None) -> pd.DataFrame:
    cache = _get_cache()
    normalized_symbol = symbol.upper()
    normalized_market = market.upper()
    if interval == "1d":
        return cache.load_daily(normalized_symbol, normalized_market, start, end)
    if interval == "1m":
        return cache.load_minute(normalized_symbol, normalized_market, start, end)
    raise ValueError(f"Unsupported interval: {interval}")


def _serialize_records(df: pd.DataFrame) -> list[dict]:
    records: list[dict] = []
    for idx, row in df.iterrows():
        record = {
            "timestamp": idx.isoformat() if hasattr(idx, "isoformat") else str(idx),
        }
        for key, value in row.items():
            if pd.isna(value):
                record[key] = None
            elif hasattr(value, "item"):
                record[key] = value.item()
            else:
                record[key] = value
        records.append(record)
    return records


def register_routes(app):
    """Register all routes on the Flask app."""
    from flask import jsonify, render_template, request

    @app.route("/")
    def index():
        """Dashboard home page."""
        return render_template("index.html")

    @app.route("/quest")
    @app.route("/quest/<quest_id>")
    def quest_page(quest_id: str = None):
        """Quest detail page."""
        return render_template("quest.html", quest_id=quest_id)

    @app.route("/leaderboard")
    def leaderboard_page():
        """Strategy leaderboard page."""
        return render_template("leaderboard.html")

    @app.route("/backtest")
    def backtest_page():
        """Live backtest visualization page."""
        return render_template("backtest.html")

    @app.route("/api/backtest/stream", methods=["POST"])
    def api_backtest_stream():
        """Stream backtest results day-by-day using Server-Sent Events (SSE).

        Body: {market, symbols, strategy, start_date, days, capital}

        Each SSE event contains one day's result with OHLCV, trade info,
        portfolio state, and score.
        """
        from flask import Response, stream_with_context
        from tq.quest.engine import QuestEngine
        from tq.data.granularity import is_trading_day

        data = request.get_json() or {}
        market = data.get("market", "US")
        symbols_raw = data.get("symbols", "AAPL")
        if isinstance(symbols_raw, str):
            symbols = [s.strip() for s in symbols_raw.split(",") if s.strip()]
        else:
            symbols = [str(s).strip() for s in symbols_raw if str(s).strip()]
        strategy_name = data.get("strategy", "ma_crossover")
        start_date = data.get("start_date", "2024-01-01")
        days = int(data.get("days", 60))
        capital = float(data.get("capital", 100_000))

        def generate():
            try:
                engine = QuestEngine(
                    quest_id="backtest-stream",
                    market=market,
                    symbols=symbols,
                    initial_capital=capital,
                )

                # Set strategy
                try:
                    engine.set_strategy(strategy_name)
                except KeyError:
                    yield f"data: {json.dumps({'error': f'Unknown strategy: {strategy_name}'})}\n\n"
                    return

                # Prepare phase manager
                visible_start = date.fromisoformat(start_date)
                from tq.quest.phase import PhaseManager
                engine.phase_manager = PhaseManager(visible_start)

                current = date.fromisoformat(start_date)
                days_run = 0
                total_score = 0.0
                total_trades = 0
                total_wins = 0
                trade_log = []

                while days_run < days:
                    if not is_trading_day(current, market):
                        current += timedelta(days=1)
                        continue

                    # Run the day
                    day_result = engine._run_day(current, days_run)
                    engine.day_results.append(day_result)
                    total_score += day_result.get("score", 0)
                    day_trades_count = day_result.get("trades", 0)
                    total_trades += day_trades_count

                    # Phase transition check
                    new_phase = engine._check_phase_transition(days_run)
                    if new_phase != engine.current_phase:
                        engine.current_phase = new_phase

                    # Collect OHLCV for each symbol
                    ohlcv_data = {}
                    for sym in symbols:
                        sym_data = engine._get_data(sym, current)
                        if sym_data is not None and not sym_data.empty:
                            last_row = sym_data.iloc[-1]
                            col_map = {}
                            for col in ["open", "high", "low", "close", "volume"]:
                                if col in sym_data.columns:
                                    col_map[col] = col
                                elif col.capitalize() in sym_data.columns:
                                    col_map[col] = col.capitalize()

                            ohlcv_data[sym] = {
                                "open": float(last_row[col_map.get("open", "open")]) if "open" in col_map else 0,
                                "high": float(last_row[col_map.get("high", "high")]) if "high" in col_map else 0,
                                "low": float(last_row[col_map.get("low", "low")]) if "low" in col_map else 0,
                                "close": float(last_row[col_map.get("close", "close")]) if "close" in col_map else 0,
                                "volume": float(last_row[col_map.get("volume", "volume")]) if "volume" in col_map else 0,
                            }

                    # Collect new trades from broker filled_orders
                    new_trades = []
                    for fill in engine.broker.filled_orders:
                        if fill.timestamp == current.isoformat():
                            trade_entry = {
                                "symbol": fill.order.symbol,
                                "side": fill.order.side.value,
                                "qty": fill.fill_qty,
                                "price": fill.fill_price,
                                "commission": fill.commission,
                            }
                            new_trades.append(trade_entry)
                            trade_log.append(trade_entry)

                    # Collect completed trades for P&L
                    completed_pnl = []
                    for ct in engine.broker.completed_trades:
                        if ct.exit_time == current.isoformat():
                            completed_pnl.append({
                                "symbol": ct.symbol,
                                "entry_price": ct.entry_price,
                                "exit_price": ct.exit_price,
                                "qty": ct.qty,
                                "pnl": ct.pnl,
                            })

                    # Positions
                    positions = {}
                    for sym, pos in engine.broker.portfolio.positions.items():
                        if pos.qty > 0:
                            positions[sym] = {
                                "qty": pos.qty,
                                "avg_price": pos.avg_price,
                                "current_price": pos.current_price,
                            }

                    # Win rate
                    if engine.broker.pnl.total_trades > 0:
                        win_rate = engine.broker.pnl.total_wins / engine.broker.pnl.total_trades * 100
                    else:
                        win_rate = 0.0

                    event_data = {
                        "day": days_run + 1,
                        "total_days": days,
                        "date": current.isoformat(),
                        "ohlcv": ohlcv_data,
                        "signal": new_trades[0]["side"] if new_trades else None,
                        "trades_today": new_trades,
                        "completed_trades": completed_pnl,
                        "portfolio_value": engine.broker.total_value,
                        "cash": engine.broker.cash,
                        "score": day_result.get("score", 0),
                        "total_score": total_score,
                        "total_trades": total_trades,
                        "win_rate": round(win_rate, 1),
                        "return_pct": round(
                            (engine.broker.total_value - capital) / capital * 100, 2
                        ),
                        "max_drawdown": round(engine.broker.pnl.current_drawdown() * 100, 2),
                        "phase": engine.current_phase,
                        "positions": positions,
                    }

                    yield f"data: {json.dumps(event_data)}\n\n"

                    days_run += 1
                    current += timedelta(days=1)

                # Send completion event
                yield f"data: {json.dumps({'done': True, 'total_score': total_score, 'total_trades': total_trades})}\n\n"

            except Exception as e:
                logger.error("Backtest stream error: %s", e, exc_info=True)
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    # ------------------------------------------------------------------
    # API endpoints
    # ------------------------------------------------------------------

    @app.route("/api/strategies")
    def api_strategies():
        """List available strategies."""
        from tq.strategy.registry import list_all
        strategies = list_all()
        return jsonify({"strategies": strategies})

    @app.route("/api/quests")
    def api_quests():
        """List all active quests."""
        from tq.quest.state import QuestState

        quests = []
        quests_dir = _get_quests_dir()
        if not quests_dir.exists():
            return jsonify({"quests": quests})

        for path in sorted(quests_dir.glob("*.json")):
            if "_checkpoint_" in path.stem:
                continue
            try:
                state = QuestState.load(path.stem, quests_dir)
            except Exception:
                logger.warning("Failed to load quest state from %s", path, exc_info=True)
                continue
            quests.append(state.to_dict())

        quests.sort(
            key=lambda item: (item.get("current_date", ""), item.get("quest_id", "")),
            reverse=True,
        )
        return jsonify({"quests": quests})

    @app.route("/api/quest/<quest_id>")
    def api_quest_status(quest_id: str):
        """Get quest status."""
        try:
            from tq.quest.state import QuestState
            state = QuestState.load(quest_id, _get_quests_dir())
            return jsonify(state.to_dict())
        except FileNotFoundError:
            return jsonify({"error": f"Quest {quest_id} not found"}), 404

    @app.route("/api/quest/<quest_id>/trades")
    def api_quest_trades(quest_id: str):
        """Get quest trade log."""
        try:
            from tq.quest.state import QuestState

            state = QuestState.load(quest_id, _get_quests_dir())
            return jsonify({
                "quest_id": quest_id,
                "trade_log": state.trade_log,
                "trade_count": len(state.trade_log),
            })
        except FileNotFoundError:
            return jsonify({"error": f"Quest {quest_id} not found"}), 404

    @app.route("/api/quest", methods=["POST"])
    def api_start_quest():
        """Start a new quest."""
        data = request.get_json() or {}
        from tq.quest.engine import QuestEngine
        symbols = _normalize_list(data.get("symbols"), ["AAPL", "MSFT"])
        engine = QuestEngine(
            quest_id=data.get("quest_id", "web-quest"),
            market=data.get("market", "US"),
            symbols=symbols,
            initial_capital=data.get("capital", 100_000),
        )
        state = engine.start_quest(
            data.get("start_date", "2024-01-01"),
            data.get("strategy", "ma_crossover"),
            quests_dir=_get_quests_dir(),
        )
        return jsonify(state.to_dict()), 201

    @app.route("/api/quest/<quest_id>/run", methods=["POST"])
    def api_run_quest(quest_id: str):
        """Run quest for N days."""
        data = request.get_json() or {}
        from tq.quest.engine import QuestEngine
        from tq.quest.state import QuestState

        quests_dir = _get_quests_dir()
        state = None
        try:
            state = QuestState.load(quest_id, quests_dir)
        except FileNotFoundError:
            pass

        symbols = _normalize_list(
            state.symbols if state else data.get("symbols"),
            ["AAPL"],
        )
        engine = QuestEngine(
            quest_id=quest_id,
            market=(state.market if state else data.get("market", "US")),
            symbols=symbols,
            initial_capital=(state.initial_capital if state else data.get("capital", 100_000)),
        )
        if state:
            engine.resume_quest(quest_id, quests_dir)

        result = engine.run(
            data.get("start_date") or (state.current_date if state else "2024-01-15"),
            data.get("days", 10),
            data.get("strategy") or (state.strategy_name if state else "ma_crossover"),
        )
        return jsonify(result)

    @app.route("/api/data/inventory")
    def api_data_inventory():
        """Return backdata inventory: per-market summary and per-symbol details."""
        from tq.data.schema import get_connection
        import os

        try:
            cache = _get_cache()
            conn = get_connection(cache.db_path)
            try:
                # Per-symbol details
                symbol_rows = conn.execute("""
                    SELECT
                        market,
                        symbol,
                        COUNT(*) AS candle_count,
                        MIN(date) AS min_date,
                        MAX(date) AS max_date,
                        (SELECT close FROM daily_ohlcv d2
                         WHERE d2.symbol = d.symbol AND d2.market = d.market
                         ORDER BY d2.date DESC LIMIT 1) AS latest_close,
                        MAX(high) AS all_time_high,
                        MIN(low) AS all_time_low
                    FROM daily_ohlcv d
                    GROUP BY market, symbol
                    ORDER BY market, candle_count DESC
                """).fetchall()

                # Per-market summary
                market_rows = conn.execute("""
                    SELECT
                        market,
                        COUNT(DISTINCT symbol) AS symbol_count,
                        COUNT(*) AS total_candles,
                        MIN(date) AS min_date,
                        MAX(date) AS max_date
                    FROM daily_ohlcv
                    GROUP BY market
                    ORDER BY market
                """).fetchall()

                # DB file size
                db_path = cache.db_path
                db_size_bytes = 0
                if db_path:
                    try:
                        db_size_bytes = os.path.getsize(str(db_path))
                    except OSError:
                        pass
                else:
                    from tq.data.schema import DB_PATH
                    try:
                        db_size_bytes = os.path.getsize(str(DB_PATH))
                    except OSError:
                        pass

                symbols = [
                    {
                        "market": r["market"],
                        "symbol": r["symbol"],
                        "candle_count": r["candle_count"],
                        "min_date": r["min_date"],
                        "max_date": r["max_date"],
                        "latest_close": r["latest_close"],
                        "all_time_high": r["all_time_high"],
                        "all_time_low": r["all_time_low"],
                    }
                    for r in symbol_rows
                ]

                markets = [
                    {
                        "market": r["market"],
                        "symbol_count": r["symbol_count"],
                        "total_candles": r["total_candles"],
                        "min_date": r["min_date"],
                        "max_date": r["max_date"],
                    }
                    for r in market_rows
                ]

                return jsonify({
                    "markets": markets,
                    "symbols": symbols,
                    "db_size_bytes": db_size_bytes,
                })
            finally:
                conn.close()
        except Exception as e:
            logger.error("Inventory error: %s", e, exc_info=True)
            return jsonify({"error": str(e)}), 500

    @app.route("/data")
    def data_page():
        """Backdata inventory page."""
        return render_template("data.html")

    @app.route("/api/data/status")
    def api_data_status():
        """Get data cache status."""
        try:
            return jsonify(_get_cache().get_status())
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/data/<symbol>")
    def api_symbol_data(symbol: str):
        """Return cached OHLCV data for a symbol."""
        market = request.args.get("market", "US")
        interval = request.args.get("interval", "1d")
        start = request.args.get("start")
        end = request.args.get("end")

        try:
            data = _load_cached_data(symbol, market, interval, start, end)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        if data.empty:
            return jsonify({"error": f"No cached data for {symbol.upper()}"}), 404

        return jsonify({
            "symbol": symbol.upper(),
            "market": market.upper(),
            "interval": interval,
            "count": len(data),
            "rows": _serialize_records(data),
        })

    @app.route("/api/data/<symbol>/indicators")
    def api_symbol_indicators(symbol: str):
        """Return cached OHLCV data with SMA and Bollinger Bands."""
        from tq.strategy.indicator import bollinger_bands, sma

        market = request.args.get("market", "US")
        interval = request.args.get("interval", "1d")
        start = request.args.get("start")
        end = request.args.get("end")
        sma_period = int(request.args.get("sma_period", 20))
        bb_period = int(request.args.get("bb_period", 20))
        bb_std_dev = float(request.args.get("bb_std_dev", 2.0))

        try:
            data = _load_cached_data(symbol, market, interval, start, end)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        if data.empty:
            return jsonify({"error": f"No cached data for {symbol.upper()}"}), 404

        close = data["close"] if "close" in data.columns else data["Close"]
        upper, middle, lower = bollinger_bands(close, bb_period, bb_std_dev)
        indicator_frame = pd.DataFrame({
            "close": close,
            "sma": sma(close, sma_period),
            "bb_upper": upper,
            "bb_middle": middle,
            "bb_lower": lower,
        }, index=data.index)

        return jsonify({
            "symbol": symbol.upper(),
            "market": market.upper(),
            "interval": interval,
            "params": {
                "sma_period": sma_period,
                "bb_period": bb_period,
                "bb_std_dev": bb_std_dev,
            },
            "count": len(indicator_frame),
            "rows": _serialize_records(indicator_frame),
        })

    @app.route("/api/leaderboard")
    def api_leaderboard():
        """Get strategy leaderboard."""
        from tq.quest.ranking import StrategyRanker
        ranker = StrategyRanker()
        return jsonify(ranker.to_dict())

    @app.route("/api/mission", methods=["POST"])
    def api_mission():
        """Run a mission until objectives are met or max iterations reached.

        Streams iteration-by-iteration results as SSE events.
        Tries ALL available strategies, then optimizes the best ones.
        """
        from flask import Response, stream_with_context
        from tq.quest.engine import QuestEngine
        from tq.strategy.registry import list_all

        data = request.get_json() or {}
        market = data.get("market", "US")
        symbols_raw = data.get("symbols", "AAPL,TSLA,META")
        if isinstance(symbols_raw, str):
            symbols = [s.strip() for s in symbols_raw.split(",") if s.strip()]
        else:
            symbols = [str(s).strip() for s in symbols_raw if str(s).strip()]
        days = int(data.get("days", 252))
        capital = float(data.get("capital", 100_000))
        allow_short = str(data.get("allow_short", "false")).lower() == "true"
        max_iterations = int(data.get("max_iterations", 50))
        if max_iterations <= 0:
            max_iterations = 999999  # infinite mode
        target_win_rate = float(data.get("target_win_rate", 0.60))
        target_return_pct = float(data.get("target_return_pct", 4.0))
        target_score = float(data.get("target_score", 10.0))
        interval = data.get("interval", "1d")  # "1d", "1m", "5m", "15m"
        start_date_str = data.get("start_date", "2024-01-02")

        def _run_single_backtest(syms, strat_name, strat_params, bt_days,
                                 bt_capital, bt_market,
                                 bt_interval="1d"):
            """Run one backtest and return summary with per-trade details.

            bt_interval: "1d" for daily, "1m" for minute-bar scalping.
            """
            engine = QuestEngine(
                quest_id="mission-bt",
                market=bt_market,
                symbols=syms,
                initial_capital=bt_capital,
                allow_short=allow_short,
            )
            try:
                engine.set_strategy(strat_name)
            except KeyError:
                return None

            if strat_params and engine.strategy:
                engine.strategy.configure(strat_params)

            from datetime import date as dt_date, timedelta
            from tq.data.granularity import is_trading_day

            visible_start = dt_date.fromisoformat(start_date_str)
            from tq.quest.phase import PhaseManager
            engine.phase_manager = PhaseManager(visible_start)

            if bt_interval in ("1m", "5m", "15m", "30m", "1h", "4h"):
                return _run_minute_backtest(
                    engine, syms, bt_days, bt_capital, bt_market,
                    visible_start)

            current = visible_start
            days_run = 0

            while days_run < bt_days:
                if not is_trading_day(current, bt_market):
                    current += timedelta(days=1)
                    continue
                day_result = engine._run_day(current, days_run)
                engine.day_results.append(day_result)
                new_phase = engine._check_phase_transition(days_run)
                if new_phase != engine.current_phase:
                    engine.current_phase = new_phase
                days_run += 1
                current += timedelta(days=1)

            return _collect_backtest_results(engine, bt_capital)

        def _run_minute_backtest(engine, syms, bt_days, bt_capital,
                                 bt_market, visible_start):
            """Run backtest on minute-bar data for scalping/day-trading."""
            from datetime import date as dt_date, timedelta
            from tq.data.granularity import is_trading_day
            from tq.data.cache import DataCache

            # For 30m/1h/4h: load ALL data at once (not per-day),
            # then iterate by day. These intervals have native data.
            # For 1m/5m/15m: load per-day and optionally resample.
            resample_map = {"5m": "5min", "15m": "15min"}
            resample_rule = resample_map.get(interval)

            cache = DataCache()

            # Pre-load all interval data per symbol
            symbol_data: dict[str, pd.DataFrame] = {}
            for symbol in syms:
                try:
                    raw = cache.load_minute(
                        symbol.upper(), bt_market.upper())
                    if not raw.empty:
                        # Detect actual data interval
                        if len(raw) > 1:
                            actual_gap = (raw.index[1] - raw.index[0]).total_seconds() / 60
                        else:
                            actual_gap = 60
                        # Filter by matching interval or resample
                        if interval in ("30m", "1h", "4h"):
                            # Native data: filter to matching interval
                            target_mins = {"30m": 30, "1h": 60, "4h": 240}[interval]
                            if actual_gap <= target_mins:
                                resampled = raw.resample(
                                    {"30m": "30min", "1h": "1h", "4h": "4h"}[interval]
                                ).agg({
                                    "open": "first", "high": "max",
                                    "low": "min", "close": "last",
                                    "volume": "sum",
                                }).dropna()
                                symbol_data[symbol] = resampled
                            else:
                                symbol_data[symbol] = raw
                        else:
                            symbol_data[symbol] = raw
                except Exception:
                    pass

            current = visible_start
            days_run = 0

            while days_run < bt_days:
                if not is_trading_day(current, bt_market):
                    current += timedelta(days=1)
                    continue

                date_str = current.isoformat()
                engine.broker.start_day(date_str)

                for symbol in syms:
                    # Slice this day's data from pre-loaded
                    full_df = symbol_data.get(symbol, pd.DataFrame())
                    if full_df.empty:
                        continue
                    day_start_ts = pd.Timestamp(date_str)
                    day_end_ts = day_start_ts + pd.Timedelta(days=1)
                    minute_df = full_df.loc[
                        (full_df.index >= day_start_ts) &
                        (full_df.index < day_end_ts)
                    ]

                    # Resample 1m → 5m/15m if needed
                    if not minute_df.empty and resample_rule:
                        minute_df = minute_df.resample(resample_rule).agg({
                            "open": "first", "high": "max",
                            "low": "min", "close": "last",
                            "volume": "sum",
                        }).dropna()

                    if minute_df.empty:
                        # Fallback: try daily data for this day
                        daily = engine._get_data(symbol, current)
                        if daily is not None and not daily.empty:
                            daily.attrs["symbol"] = symbol
                            signals = engine.strategy.decide(
                                daily, engine.broker.portfolio)
                            engine.process_signals(signals, symbol, date_str)
                        continue

                    # Candle-by-candle execution on minute bars
                    # Use iloc slicing instead of pd.concat (O(1) vs O(n²))
                    minute_df.attrs["symbol"] = symbol
                    for i in range(len(minute_df)):
                        row = minute_df.iloc[i]
                        # Slice up to current candle (view, not copy)
                        accumulated = minute_df.iloc[:i + 1]
                        accumulated.attrs["symbol"] = symbol

                        ts = str(minute_df.index[i])
                        o = float(row["open"])
                        h = float(row["high"])
                        l = float(row["low"])
                        c = float(row["close"])

                        # First: fill any pending orders at this bar's prices
                        engine.broker.process_bar(symbol, o, h, l, c, ts)

                        # Then: generate new signals from strategy
                        signals = engine.strategy.decide(
                            accumulated, engine.broker.portfolio)

                        # Submit signals as orders
                        if signals:
                            engine.process_signals(
                                signals, symbol, ts)

                # End of day — close all positions for day-trading
                day_summary = engine.broker.end_day(date_str)

                days_run += 1
                current += timedelta(days=1)

            return _collect_backtest_results(engine, bt_capital)

        def _collect_backtest_results(engine, bt_capital):
            """Collect completed trades and compute stats."""
            # Force-close all open positions at last known price
            for sym, pos in list(engine.broker.portfolio.positions.items()):
                last_price = engine.broker.portfolio._prices.get(sym, 0)
                if last_price <= 0:
                    continue
                if pos.qty > 0:
                    # Close long
                    try:
                        engine.broker.portfolio.sell(sym, pos.qty, last_price)
                        entry_p = engine.broker._entry_prices.pop(sym, last_price)
                        from tq.sim.order import CompletedTrade
                        ct = CompletedTrade(
                            symbol=sym, entry_price=entry_p,
                            exit_price=last_price, qty=pos.qty)
                        engine.broker.completed_trades.append(ct)
                    except Exception:
                        pass
                elif pos.qty < 0:
                    # Close short
                    try:
                        engine.broker.portfolio.buy_to_cover(
                            sym, abs(pos.qty), last_price)
                        entry_p = engine.broker._entry_prices.pop(sym, last_price)
                        from tq.sim.order import CompletedTrade
                        ct = CompletedTrade(
                            symbol=sym, entry_price=entry_p,
                            exit_price=last_price, qty=abs(pos.qty),
                            is_short=True)
                        engine.broker.completed_trades.append(ct)
                    except Exception:
                        pass

            trades_list = []
            for ct in engine.broker.completed_trades:
                trades_list.append({
                    "symbol": ct.symbol,
                    "entry_price": ct.entry_price,
                    "exit_price": ct.exit_price,
                    "qty": ct.qty,
                    "pnl": ct.pnl,
                    "pnl_pct": ct.pnl_pct,
                })

            total_trades = len(trades_list)
            wins = sum(1 for t in trades_list if t["pnl"] > 0)
            losses = total_trades - wins
            win_rate = wins / total_trades if total_trades > 0 else 0.0
            realized_pnl = sum(t["pnl"] for t in trades_list)
            return_pct = (realized_pnl / bt_capital * 100) if bt_capital > 0 else 0.0

            # Count buy/sell (long/short) trades
            buys = sum(1 for f in engine.broker.filled_orders if f.order.is_buy)
            sells = sum(1 for f in engine.broker.filled_orders if not f.order.is_buy)

            # Compute score from completed trades + win_rate + risk/reward quality
            raw_score = 0.0
            total_profit = 0.0
            total_loss = 0.0
            for t in trades_list:
                cost = t["entry_price"] * t["qty"]
                pnl_pct_t = t["pnl"] / cost if cost > 0 else 0
                if t["pnl"] > 0:
                    raw_score += 0.1 + abs(pnl_pct_t) * 10
                    total_profit += abs(t["pnl"])
                else:
                    raw_score += -0.2 - abs(pnl_pct_t) * 10
                    total_loss += abs(t["pnl"])

            # Risk/reward ratio bonus
            # Target: 7:3 (profit:loss) → ratio = 2.33
            # Actual ratio > 2.0 gets bonus, < 1.0 gets penalty
            rr_mult = 1.0
            if total_trades >= 5:
                if total_loss > 0:
                    rr_ratio = total_profit / total_loss
                else:
                    rr_ratio = 10.0 if total_profit > 0 else 0.0

                if rr_ratio >= 2.0:
                    rr_mult = 1.0 + min(0.3, (rr_ratio - 2.0) * 0.1)  # up to 1.3x
                elif rr_ratio < 1.0:
                    rr_mult = 0.7 + rr_ratio * 0.3  # 0.7~1.0

                # Win rate quality multiplier
                wr_mult = 0.6 + (win_rate * 0.8)  # 0.6~1.4 range
                score = raw_score * wr_mult * rr_mult
            else:
                score = raw_score * 0.8 if total_trades > 0 else 0.0
                rr_ratio = 0.0

            current_params = engine.strategy.get_params() if engine.strategy else {}

            return {
                "trades": total_trades,
                "wins": wins,
                "losses": losses,
                "buys": buys,
                "sells": sells,
                "win_rate": win_rate,
                "rr_ratio": round(rr_ratio, 2) if total_trades >= 5 else 0.0,
                "score": round(score, 2),
                "return_pct": round(return_pct, 2),
                "realized_pnl": round(realized_pnl, 2),
                "current_params": current_params,
            }

        def _generate_param_variations(base_params):
            """Generate parameter variations for optimization."""
            variations = []
            for key, val in base_params.items():
                if isinstance(val, int):
                    for factor in [0.7, 0.85, 1.15, 1.3, 1.5, 0.5]:
                        nv = max(2, int(val * factor))
                        if nv != val:
                            new_p = dict(base_params)
                            new_p[key] = nv
                            variations.append(new_p)
                elif isinstance(val, float):
                    for factor in [0.7, 0.85, 1.15, 1.3, 1.5, 0.5]:
                        nv = round(max(0.01, val * factor), 4)
                        if abs(nv - val) > 0.001:
                            new_p = dict(base_params)
                            new_p[key] = nv
                            variations.append(new_p)
            # Also try multi-param combos (random pairs)
            keys = [k for k, v in base_params.items()
                    if isinstance(v, (int, float))]
            if len(keys) >= 2:
                for _ in range(min(5, len(keys))):
                    new_p = dict(base_params)
                    k1, k2 = random.sample(keys, 2)
                    for k in [k1, k2]:
                        v = base_params[k]
                        factor = random.choice([0.8, 0.9, 1.1, 1.2])
                        if isinstance(v, int):
                            new_p[k] = max(2, int(v * factor))
                        else:
                            new_p[k] = round(max(0.01, v * factor), 4)
                    variations.append(new_p)
            return variations

        def generate():
            try:
                from tq.journal.memory import TradingMemory
                memory = TradingMemory()

                # Get all strategies, skip slow ones
                skip = {"dqn", "lstm", "adaptive", "multi_tf"}
                all_strategies = [s for s in list_all() if s not in skip]

                iteration = 0
                best_score = float("-inf")
                best_win_rate = 0.0
                best_return_pct = -999.0
                best_trades = 0
                best_strategy = ""
                best_params = {}
                strategies_tried = set()
                params_tried = 0
                mission_complete = False
                zero_score_count = {}  # strategy -> consecutive 0-score count
                strat_best: dict[str, dict] = {}  # per-strategy best params

                # Phase 1: SCAN - try each strategy with best known or default params
                # Limit phase 1 to at most 40% of budget so phase 2 has room
                # Phase 1: scan all strategies if budget allows, else 40% of budget
                phase1_budget = min(
                    len(all_strategies),
                    max(len(all_strategies), int(max_iterations * 0.4)),
                )
                scan_results = []
                phase1_skips = 0

                # Shuffle strategies with bias toward least-tried
                tried_data = memory._load_json("tried-params.json")
                random.shuffle(all_strategies)  # base randomness
                # Then stable-sort: least-tried bubble up, but ties are random
                all_strategies.sort(
                    key=lambda s: len(tried_data.get(s, {})))

                for strat_name in all_strategies:
                    if iteration >= phase1_budget:
                        break
                    if phase1_skips > len(all_strategies):
                        break

                    # Skip strategies that have been tried 100+ times
                    # with avg score <= 0 (clearly not working)
                    strat_trials = tried_data.get(strat_name, {})
                    if len(strat_trials) >= 100:
                        avg = sum(t.get("score", 0) for t in strat_trials.values()) / len(strat_trials)
                        if avg <= 0:
                            continue  # skip exhausted low-performers

                    # Start from memory's best known params
                    starting_params = memory.get_best_params(strat_name)
                    strat_params = dict(starting_params) if starting_params else {}

                    # Phase 1: small variation near best (learning, not random)
                    if strat_params and memory.has_tried(strat_name, strat_params):
                        untried = memory.get_untried_variations(
                            strat_name, strat_params)
                        if untried:
                            strat_params = random.choice(untried[:3])
                        # else: use best params as-is (will hit cache below)

                    # If already tried, use cached score for ranking
                    # but don't count as a new iteration
                    if memory.has_tried(strat_name, strat_params):
                        h = memory._params_hash(strat_params)
                        cached = tried_data.get(strat_name, {}).get(h)
                        if cached and cached.get("score", 0) != 0:
                            # Add to scan_results for Phase 2 ranking
                            scan_results.append({
                                "strategy": strat_name,
                                "score": cached["score"],
                                "win_rate": cached.get("win_rate", 0),
                                "return_pct": 0,
                                "params": strat_params,
                                "v_count": 0,
                                "cached": True,
                            })
                        continue  # don't waste iteration budget

                    result = _run_single_backtest(
                        symbols, strat_name, strat_params, days, capital,
                        market, interval)
                    if result is None:
                        phase1_skips += 1
                        continue

                    iteration += 1

                    strategies_tried.add(strat_name)
                    params_tried += 1

                    # Record to memory
                    memory.record_trial(strat_name, result["current_params"], {
                        "score": result["score"],
                        "win_rate": result["win_rate"],
                        "trades": result["trades"],
                    })

                    # Record mistakes/insights (only when trades > 0)
                    if result["trades"] > 0:
                        if result["score"] < -2 or result["win_rate"] < 0.2:
                            memory.record_mistake({
                                "strategy": strat_name,
                                "params": result["current_params"],
                                "symbols": symbols,
                                "score": result["score"],
                                "win_rate": result["win_rate"],
                                "trades": result["trades"],
                                "reason": f"점수 {result['score']:.1f}, 승률 {result['win_rate']:.1%}",
                                "avoid": True,
                            })
                        if result["win_rate"] > 0.6:
                            memory.record_insight({
                                "strategy": strat_name,
                                "params": result["current_params"],
                                "symbols": symbols,
                                "score": result["score"],
                                "win_rate": result["win_rate"],
                                "trades": result["trades"],
                                "reason": f"승률 {result['win_rate']:.1%}, 점수 {result['score']:.1f}",
                            })

                    # Track consecutive 0-score for skip logic
                    if result["score"] == 0.0:
                        zero_score_count[strat_name] = zero_score_count.get(strat_name, 0) + 1
                    else:
                        zero_score_count[strat_name] = 0

                    # Track best
                    if result["score"] > best_score:
                        best_score = result["score"]
                        best_win_rate = result["win_rate"]
                        best_return_pct = result["return_pct"]
                        best_trades = result["trades"]
                        best_strategy = strat_name
                        best_params = dict(result["current_params"])

                    # Check objectives
                    wr_met = bool(result["win_rate"] >= target_win_rate)
                    ret_met = bool(result["return_pct"] >= target_return_pct)
                    sc_met = bool(result["score"] >= target_score)
                    v_count = sum([wr_met, ret_met, sc_met])
                    objectives_met = {
                        "win_rate": wr_met,
                        "return_pct": ret_met,
                        "score": sc_met,
                    }

                    scan_results.append({
                        "strategy": strat_name,
                        "score": result["score"],
                        "win_rate": result["win_rate"],
                        "return_pct": result["return_pct"],
                        "params": result["current_params"],
                        "v_count": v_count,
                    })

                    # Short param summary for log
                    p_summary = ""
                    if result["current_params"]:
                        p_keys = list(result["current_params"].keys())[:3]
                        p_parts = [f"{k}={result['current_params'][k]}"
                                   for k in p_keys]
                        p_summary = ",".join(p_parts)

                    evt = {
                        "iteration": iteration,
                        "max_iterations": max_iterations,
                        "strategy": strat_name,
                        "params": result["current_params"],
                        "params_summary": p_summary,
                        "trades": result["trades"],
                        "wins": result["wins"],
                        "losses": result["losses"],
                        "buys": result.get("buys", 0),
                        "sells": result.get("sells", 0),
                        "rr_ratio": result.get("rr_ratio", 0),
                        "win_rate": round(result["win_rate"], 4),
                        "return_pct": result["return_pct"],
                        "score": result["score"],
                        "objectives_met": objectives_met,
                        "status": "탐색 중",
                        "best_so_far": {
                            "strategy": best_strategy,
                            "score": best_score,
                            "win_rate": round(best_win_rate, 4),
                            "return_pct": best_return_pct,
                        },
                    }
                    yield f"data: {json.dumps(evt)}\n\n"

                    # Only stop early if past minimum 20% of budget
                    if ret_met and sc_met and iteration >= max_iterations * 0.2:
                        mission_complete = True
                        break

                # Phase 2: OPTIMIZE - prioritize VV results, combine them
                if not mission_complete and iteration < max_iterations:
                    # Rank strategies: VV+ first, then by score
                    # VV (2+): highest priority
                    # V (1) with score>0: second tier
                    # Others: fallback
                    ranked = sorted(scan_results,
                                    key=lambda x: (x.get("v_count", 0), x["score"]),
                                    reverse=True)

                    # Take top 5 (VV first, then best scores)
                    top_strategies = ranked[:5]

                    vv_count = sum(1 for r in ranked if r.get("v_count", 0) >= 2)
                    if vv_count:
                        vv_strats = [r["strategy"] for r in ranked if r.get("v_count", 0) >= 2]
                        yield f"data: {json.dumps({'status': f'VV 유망 전략 {vv_count}개: {vv_strats[:5]}'})}\n\n"

                    if not top_strategies:
                        yield f"data: {json.dumps({'status': 'Phase 1에서 유효한 전략 없음. 최적화 건너뜀.'})}\n\n"

                    exhausted_strategies = set()
                    strat_idx = 0
                    # Track per-strategy best for smarter base_params selection
                    strat_best: dict[str, dict] = {}
                    for sr in top_strategies:
                        sn = sr["strategy"]
                        if sn not in strat_best or sr["score"] > strat_best[sn]["score"]:
                            strat_best[sn] = {"score": sr["score"], "params": dict(sr["params"])}

                    while (iteration < max_iterations
                           and not mission_complete):
                        # If all top strategies exhausted, expand pool
                        if len(exhausted_strategies) >= len(top_strategies):
                            remaining = [r for r in ranked
                                         if r["strategy"] not in exhausted_strategies]
                            if remaining:
                                top_strategies.extend(remaining[:3])
                            else:
                                break  # truly no more strategies
                        # Round-robin through top strategies
                        top_entry = top_strategies[strat_idx % len(top_strategies)]
                        strat_name = top_entry["strategy"]
                        strat_idx += 1

                        # Skip exhausted strategies (but not zero-score — they get another chance with new params)
                        if strat_name in exhausted_strategies:
                            continue

                        # Use per-strategy best params as base (not global best)
                        if strat_name in strat_best:
                            base_params = strat_best[strat_name]["params"]
                        else:
                            base_params = top_entry["params"]

                        # Generate variations
                        variations = _generate_param_variations(base_params)
                        mem_untried = memory.get_untried_variations(
                            strat_name, base_params)
                        all_candidates = variations + mem_untried

                        # Filter already-tried
                        candidates = [p for p in all_candidates
                                      if not memory.has_tried(strat_name, p)]

                        # Random fallback — always generate fresh candidates
                        if not candidates:
                            for _ in range(20):
                                rnd_p = dict(base_params)
                                for k, v in rnd_p.items():
                                    if isinstance(v, int):
                                        rnd_p[k] = max(2, v + random.randint(-10, 10))
                                    elif isinstance(v, float):
                                        rnd_p[k] = round(
                                            max(0.01, v * random.uniform(0.5, 1.5)), 4)
                                if not memory.has_tried(strat_name, rnd_p):
                                    candidates.append(rnd_p)
                            if not candidates:
                                exhausted_strategies.add(strat_name)
                                continue

                        # Filter out avoidable candidates
                        safe_candidates = []
                        for c in candidates:
                            avoid, _ = memory.should_avoid(strat_name, c)
                            if not avoid:
                                safe_candidates.append(c)
                        if not safe_candidates:
                            safe_candidates = candidates[:1]  # last resort

                        # 70% exploit (near best), 30% explore (wider range)
                        if random.random() < 0.7 and len(safe_candidates) > 1:
                            # Exploit: pick from top 3 closest variations
                            strat_params = safe_candidates[0]
                        else:
                            # Explore: pick random from all candidates
                            strat_params = random.choice(safe_candidates)

                        iteration += 1
                        result = _run_single_backtest(
                            symbols, strat_name, strat_params, days, capital,
                            market, interval)
                        if result is None:
                            continue

                        params_tried += 1

                        # Periodic compact for long runs
                        if iteration % 500 == 0 and iteration > 0:
                            memory.compact()

                        # Record to memory
                        memory.record_trial(
                            strat_name, result["current_params"], {
                                "score": result["score"],
                                "win_rate": result["win_rate"],
                                "trades": result["trades"],
                            })

                        # Record mistakes/insights (only when trades > 0)
                        if result["trades"] > 0:
                            if result["score"] < -2 or result["win_rate"] < 0.2:
                                memory.record_mistake({
                                    "strategy": strat_name,
                                    "params": result["current_params"],
                                    "symbols": symbols,
                                    "score": result["score"],
                                    "win_rate": result["win_rate"],
                                    "trades": result["trades"],
                                    "reason": f"점수 {result['score']:.1f}, 승률 {result['win_rate']:.1%}",
                                    "avoid": True,
                                })
                            if result["win_rate"] > 0.6:
                                memory.record_insight({
                                    "strategy": strat_name,
                                    "params": result["current_params"],
                                    "symbols": symbols,
                                    "score": result["score"],
                                    "win_rate": result["win_rate"],
                                    "trades": result["trades"],
                                    "reason": f"승률 {result['win_rate']:.1%}, 점수 {result['score']:.1f}",
                                })

                        # Track consecutive 0-score
                        if result["score"] == 0.0:
                            zero_score_count[strat_name] = zero_score_count.get(strat_name, 0) + 1
                        else:
                            zero_score_count[strat_name] = 0

                        # Track per-strategy best (for smarter base_params)
                        cur_params = result["current_params"]
                        cur_score = result["score"]
                        sb = strat_best.get(strat_name)
                        if not sb or cur_score > sb["score"]:
                            strat_best[strat_name] = {
                                "score": cur_score,
                                "params": dict(cur_params),
                            }

                        # Track global best
                        if cur_score > best_score:
                            best_score = cur_score
                            best_win_rate = result["win_rate"]
                            best_return_pct = result["return_pct"]
                            best_trades = result["trades"]
                            best_strategy = strat_name
                            best_params = dict(cur_params)

                        wr_met = bool(result["win_rate"] >= target_win_rate)
                        ret_met_p2 = bool(result["return_pct"] >= target_return_pct)
                        sc_met_p2 = bool(result["score"] >= target_score)
                        v_count_p2 = sum([wr_met, ret_met_p2, sc_met_p2])

                        # VV+ in Phase 2: promote this strategy to top of rotation
                        if v_count_p2 >= 2 and strat_name not in [t["strategy"] for t in top_strategies[:2]]:
                            top_strategies.insert(0, {
                                "strategy": strat_name,
                                "score": cur_score,
                                "params": dict(cur_params),
                                "v_count": v_count_p2,
                            })
                        ret_met = bool(result["return_pct"] >= target_return_pct)
                        sc_met = bool(result["score"] >= target_score)
                        objectives_met = {
                            "win_rate": wr_met,
                            "return_pct": ret_met,
                            "score": sc_met,
                        }

                        p_summary = ""
                        if result["current_params"]:
                            p_keys = list(result["current_params"].keys())[:3]
                            p_parts = [
                                f"{k}={result['current_params'][k]}"
                                for k in p_keys]
                            p_summary = ",".join(p_parts)

                        evt = {
                            "iteration": iteration,
                            "max_iterations": max_iterations,
                            "strategy": strat_name,
                            "params": result["current_params"],
                            "params_summary": p_summary,
                            "trades": result["trades"],
                            "wins": result["wins"],
                            "losses": result["losses"],
                            "win_rate": round(result["win_rate"], 4),
                            "return_pct": result["return_pct"],
                            "score": result["score"],
                            "objectives_met": objectives_met,
                            "status": "최적화 중",
                            "best_so_far": {
                                "strategy": best_strategy,
                                "score": best_score,
                                "win_rate": round(best_win_rate, 4),
                                "return_pct": best_return_pct,
                            },
                        }
                        yield f"data: {json.dumps(evt)}\n\n"

                        # Only stop early if past minimum 20% of budget
                        if ret_met and sc_met and iteration >= max_iterations * 0.2:
                            mission_complete = True
                            break

                # Save ALL per-strategy bests to memory (not just global best)
                for sn, sb in strat_best.items():
                    sb_params = sb.get("params", {})
                    sb_score = sb.get("score", 0)
                    if sb_params and sb_score > 0:
                        # Look up win_rate/trades from tried-params
                        h = memory._params_hash(sb_params)
                        tried_data = memory._load_json("tried-params.json")
                        trial = tried_data.get(sn, {}).get(h, {})
                        sb_wr = trial.get("win_rate", 0)
                        sb_tr = trial.get("trades", 0)
                        memory.save_best_params(
                            sn, sb_params, sb_score,
                            sb_wr, sb_tr,
                            context={"symbols": symbols, "days": days,
                                     "mission": True},
                        )

                # Also save global best (redundant but ensures it's captured)
                if best_params and best_strategy:
                    memory.save_best_params(
                        best_strategy, best_params, best_score,
                        best_win_rate, best_trades,
                        context={"symbols": symbols, "days": days,
                                 "mission": True},
                    )

                # Record session
                memory.record_session({
                    "strategy": best_strategy,
                    "symbols": symbols,
                    "rounds": iteration,
                    "best_score": best_score,
                    "best_params": best_params,
                    "best_win_rate": best_win_rate,
                    "mission": True,
                    "mission_complete": mission_complete,
                })

                # Flush and compact memory before final report
                memory.compact()
                memory.flush()

                # Get cumulative stats
                summary = memory.get_summary()

                final = {
                    "done": True,
                    "mission_complete": mission_complete,
                    "iterations_used": iteration,
                    "best": {
                        "strategy": best_strategy,
                        "params": best_params,
                        "score": best_score,
                        "win_rate": round(best_win_rate, 4),
                        "return_pct": best_return_pct,
                    },
                    "strategies_tried": len(strategies_tried),
                    "params_tried": params_tried,
                    "cumulative": {
                        "sessions": summary["sessions_count"],
                        "total_tried": summary["total_tried"],
                        "mistakes_learned": summary["mistakes_count"],
                        "insights_found": summary["insights_count"],
                    },
                }
                yield f"data: {json.dumps(final)}\n\n"

            except Exception as e:
                logger.error("Mission error: %s", e, exc_info=True)
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    @app.route("/api/memory-status")
    def api_memory_status():
        """Get AI trading memory status."""
        from tq.journal.memory import TradingMemory
        try:
            memory = TradingMemory()
            summary = memory.get_summary()
            return jsonify(summary)
        except Exception as e:
            logger.error("Memory status error: %s", e, exc_info=True)
            return jsonify({"error": str(e)}), 500

    @app.route("/api/symbols")
    def api_symbols():
        """Return available symbols grouped by market."""
        from tq.data.schema import get_connection

        try:
            cache = _get_cache()
            conn = get_connection(cache.db_path)
            try:
                rows = conn.execute("""
                    SELECT market, symbol
                    FROM daily_ohlcv
                    GROUP BY market, symbol
                    ORDER BY market, symbol
                """).fetchall()

                grouped: dict[str, list[str]] = {}
                for r in rows:
                    mkt = r["market"]
                    if mkt not in grouped:
                        grouped[mkt] = []
                    grouped[mkt].append(r["symbol"])

                return jsonify({"markets": grouped})
            finally:
                conn.close()
        except Exception as e:
            logger.error("Symbols API error: %s", e, exc_info=True)
            return jsonify({"markets": {}}), 500

    @app.route("/api/compare", methods=["POST"])
    def api_compare():
        """Run a strategy comparison."""
        from tq.quest.engine import QuestEngine
        from tq.quest.ranking import StrategyRanker, StrategyResult

        data = request.get_json() or {}
        strategies = _normalize_list(
            data.get("strategies"),
            ["ma_crossover", "rsi", "macd"],
        )
        if not strategies:
            return jsonify({"error": "At least one strategy is required"}), 400

        symbols = _normalize_list(data.get("symbols"), ["AAPL", "MSFT"])
        market = data.get("market", "US")
        days = int(data.get("days", 30))
        start_date = data.get("start_date", "2024-01-01")
        capital = float(data.get("capital", 100_000))

        ranker = StrategyRanker()
        for strategy_name in strategies:
            engine = QuestEngine(
                quest_id=f"compare-{strategy_name}",
                market=market,
                symbols=symbols,
                initial_capital=capital,
            )
            result = engine.run(start_date, days, strategy_name)
            ranker.add_result(StrategyResult(
                strategy_name=strategy_name,
                total_return_pct=result.get("return_pct", 0.0),
                total_trades=result.get("total_trades", 0),
                composite_score=result.get("total_score", 0.0),
                max_drawdown=result.get("max_drawdown", 0.0),
                days=result.get("days", 0),
            ))

        return jsonify({
            **ranker.to_dict(),
            "results": [result.to_dict() for result in ranker.compare(strategies)],
        })
