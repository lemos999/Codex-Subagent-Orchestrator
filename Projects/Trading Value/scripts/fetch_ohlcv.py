"""Fetch historical OHLCV data from Binance Futures via ccxt.

Stores data in data/cache.sqlite in a new `ohlcv` table with timeframe column.
Fetches: 5m, 15m, 1h, 4h for ETHUSDT and BTCUSDT.
"""
from __future__ import annotations

import sqlite3
import time
from datetime import datetime, timezone

import ccxt


SYMBOLS = ["ETH/USDT:USDT", "BTC/USDT:USDT"]
TIMEFRAMES = ["5m", "15m", "1h", "4h"]
DB_PATH = "data/cache.sqlite"

# Start from 2024-10-01 to have enough warmup data
START_DATE = "2024-10-01T00:00:00Z"
BATCH_LIMIT = 1500  # Binance max per request


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ohlcv (
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            datetime TEXT NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            volume REAL NOT NULL,
            PRIMARY KEY (symbol, timeframe, timestamp)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_ohlcv_sym_tf_ts
        ON ohlcv (symbol, timeframe, timestamp)
    """)
    conn.commit()


def symbol_label(symbol: str) -> str:
    """ETH/USDT:USDT → ETHUSDT"""
    return symbol.replace("/", "").replace(":USDT", "")


def fetch_and_store(
    exchange: ccxt.Exchange,
    conn: sqlite3.Connection,
    symbol: str,
    timeframe: str,
    since_ms: int,
) -> int:
    """Fetch all candles from since_ms to now. Returns total rows inserted."""
    label = symbol_label(symbol)
    total = 0
    current_since = since_ms

    while True:
        try:
            candles = exchange.fetch_ohlcv(
                symbol, timeframe, since=current_since, limit=BATCH_LIMIT
            )
        except Exception as e:
            print(f"  Error fetching {label}/{timeframe}: {e}")
            time.sleep(5)
            continue

        if not candles:
            break

        rows = []
        for c in candles:
            ts_ms, o, h, l, cl, v = c
            dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            rows.append((label, timeframe, ts_ms, dt, o, h, l, cl, v or 0.0))

        conn.executemany(
            "INSERT OR REPLACE INTO ohlcv VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()
        total += len(rows)

        last_ts = candles[-1][0]
        dt_str = datetime.fromtimestamp(last_ts / 1000, tz=timezone.utc).strftime(
            "%Y-%m-%d %H:%M"
        )
        print(f"  {label}/{timeframe}: +{len(rows)} rows (up to {dt_str}), total={total}")

        if len(candles) < BATCH_LIMIT:
            break

        current_since = last_ts + 1
        time.sleep(0.3)  # rate limit

    return total


def main() -> None:
    exchange = ccxt.binance({"options": {"defaultType": "future"}})
    exchange.load_markets()

    since_ms = exchange.parse8601(START_DATE)

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    for symbol in SYMBOLS:
        for tf in TIMEFRAMES:
            label = symbol_label(symbol)
            # Check existing data
            cursor = conn.execute(
                "SELECT MAX(timestamp) FROM ohlcv WHERE symbol=? AND timeframe=?",
                (label, tf),
            )
            row = cursor.fetchone()
            start = row[0] + 1 if row[0] else since_ms

            dt_str = datetime.fromtimestamp(start / 1000, tz=timezone.utc).strftime(
                "%Y-%m-%d %H:%M"
            )
            print(f"\nFetching {label}/{tf} from {dt_str}...")
            count = fetch_and_store(exchange, conn, symbol, tf, start)
            print(f"  Done: {count} new rows")

    # Summary
    print("\n=== Summary ===")
    cursor = conn.execute(
        "SELECT symbol, timeframe, count(*), min(datetime), max(datetime) FROM ohlcv GROUP BY symbol, timeframe"
    )
    for row in cursor.fetchall():
        print(f"  {row[0]}/{row[1]}: {row[2]} rows ({row[3]} ~ {row[4]})")

    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
