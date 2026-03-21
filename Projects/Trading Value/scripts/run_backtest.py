"""Run backtest using historical data from cache.sqlite.

Usage: cd "Projects/Trading Value" && PYTHONPATH=src py -3 scripts/run_backtest.py
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from trading_value.adapters.backtest import BacktestConfig, BacktestEngine
from trading_value.core.models import Timeframe


DB_PATH = Path(__file__).resolve().parent.parent / "data" / "cache.sqlite"

TF_MAP = {
    "5m": Timeframe.M5,
    "15m": Timeframe.M15,
    "30m": Timeframe.M30,
    "1h": Timeframe.H1,
    "4h": Timeframe.H4,
}


def load_ohlcv(symbol: str, timeframe: str, conn: sqlite3.Connection) -> pd.DataFrame:
    """Load OHLCV data from cache.sqlite ohlcv table."""
    query = """
        SELECT datetime, open, high, low, close, volume
        FROM ohlcv
        WHERE symbol = ? AND timeframe = ?
        ORDER BY timestamp ASC
    """
    df = pd.read_sql_query(query, conn, params=(symbol, timeframe))
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
    df = df.rename(columns={"datetime": "timestamp"})
    return df


def load_30m_from_existing(symbol: str, conn: sqlite3.Connection) -> pd.DataFrame:
    """Load 30m data from the existing minute_ohlcv table."""
    query = """
        SELECT datetime, open, high, low, close, volume
        FROM minute_ohlcv
        WHERE symbol = ?
        ORDER BY datetime ASC
    """
    df = pd.read_sql_query(query, conn, params=(symbol,))
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
    df = df.rename(columns={"datetime": "timestamp"})
    return df


def main() -> None:
    conn = sqlite3.connect(str(DB_PATH))

    symbols = ["ETHUSDT", "BTCUSDT"]
    timeframes_to_load = ["5m", "15m", "1h", "4h"]

    print("Loading data...")
    data: dict[str, dict[Timeframe, pd.DataFrame]] = {}

    for symbol in symbols:
        data[symbol] = {}
        for tf_str in timeframes_to_load:
            df = load_ohlcv(symbol, tf_str, conn)
            tf = TF_MAP[tf_str]
            data[symbol][tf] = df
            print(f"  {symbol}/{tf_str}: {len(df)} bars ({df.index[0]} ~ {df.index[-1]})")

        # Load 30m from existing table or resample from ohlcv
        df_30m_existing = load_30m_from_existing(symbol, conn)
        if len(df_30m_existing) > 0:
            data[symbol][Timeframe.M30] = df_30m_existing
            print(f"  {symbol}/30m: {len(df_30m_existing)} bars (from minute_ohlcv)")
        else:
            # Resample 5m to 30m
            df_5m = data[symbol][Timeframe.M5]
            df_30m = df_5m.resample("30min").agg({
                "open": "first", "high": "max", "low": "min",
                "close": "last", "volume": "sum"
            }).dropna()
            data[symbol][Timeframe.M30] = df_30m
            print(f"  {symbol}/30m: {len(df_30m)} bars (resampled from 5m)")

    conn.close()

    # Find common date range across all symbols and timeframes
    min_dates = []
    max_dates = []
    for symbol in symbols:
        for tf, df in data[symbol].items():
            min_dates.append(df.index[0])
            max_dates.append(df.index[-1])

    start = max(min_dates)
    end = min(max_dates)
    print(f"\nCommon range: {start} ~ {end}")

    # Configure backtest
    config = BacktestConfig(
        symbols=symbols,
        initial_balance=10000.0,
        commission_rate=0.0004,
        slippage_ticks=0.5,
        risk_pct=0.0035,
        min_rr=1.5,
        min_qty=0.001,
    )

    print(f"\nRunning backtest...")
    print(f"  Initial balance: ${config.initial_balance:,.2f}")
    print(f"  Symbols: {config.symbols}")
    print(f"  Risk per trade: {config.risk_pct*100:.2f}%")
    print(f"  Min RR: {config.min_rr}")
    print()

    engine = BacktestEngine(config)

    try:
        result = engine.run(data)
    except Exception as e:
        print(f"\nBacktest error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

        # Print partial results if available
        if hasattr(engine, 'trade_records') and engine.trade_records:
            print(f"\nPartial results: {len(engine.trade_records)} trades completed before error")
        if hasattr(engine, 'decision_logs'):
            print(f"Decision logs: {len(engine.decision_logs)} entries")
        return

    # Print results
    print("=" * 60)
    print(result.summary())
    print("=" * 60)

    # Save detailed results
    output_dir = Path(__file__).resolve().parent.parent / "data" / "backtest_results"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save trade records as CSV
    if result.trades:
        trades_data = []
        for t in result.trades:
            trades_data.append({
                "symbol": t.symbol,
                "strategy": t.strategy,
                "side": t.side,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "qty": t.qty,
                "pnl": t.pnl,
                "pnl_r": t.pnl_r,
                "commission": t.commission_total,
                "entry_time": t.entry_time,
                "exit_time": t.exit_time,
                "duration_bars": t.duration_bars,
                "exit_reason": t.exit_reason,
                "regime_at_entry": t.regime_at_entry,
                "rr_planned": t.rr_planned,
                "rr_actual": t.rr_actual,
            })
        df_trades = pd.DataFrame(trades_data)
        trades_path = output_dir / "trades.csv"
        df_trades.to_csv(trades_path, index=False)
        print(f"\nTrades saved to: {trades_path}")

    # Save summary
    summary_path = output_dir / "summary.txt"
    with open(summary_path, "w") as f:
        f.write(result.summary())
    print(f"Summary saved to: {summary_path}")

    print(f"\nDecision logs: {len(result.decision_logs)} entries")
    print("Done.")


if __name__ == "__main__":
    main()
