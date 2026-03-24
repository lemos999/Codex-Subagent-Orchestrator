"""Backfill 5m OHLCV data from 2022-01-01 for ETHUSDT and BTCUSDT.

Existing 5m data starts from 2024-10-01.
This script fills the gap: 2022-01-01 ~ 2024-09-30.

Usage: cd "Projects/Trading Value" && py -3 scripts/fetch_5m_backfill.py
"""
from __future__ import annotations

import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

import ccxt

SYMBOLS = ["ETH/USDT:USDT", "BTC/USDT:USDT"]
DB_PATH = str(Path(__file__).resolve().parent.parent / "data" / "cache.sqlite")

START_DATE = "2022-01-01T00:00:00Z"
END_DATE = "2024-10-01T00:00:00Z"  # existing data starts here
BATCH_LIMIT = 1500
TF = "5m"
TF_MS = 5 * 60 * 1000  # 5 minutes in ms


def symbol_label(symbol: str) -> str:
    return symbol.replace("/", "").replace(":USDT", "")


def fetch_and_store(exchange, conn, symbol, since_ms, until_ms):
    label = symbol_label(symbol)
    total = 0
    current = since_ms

    while current < until_ms:
        try:
            candles = exchange.fetch_ohlcv(symbol, TF, since=current, limit=BATCH_LIMIT)
        except Exception as e:
            print(f"  Error: {e}")
            time.sleep(5)
            continue

        if not candles:
            break

        rows = []
        for c in candles:
            ts_ms, o, h, l, cl, v = c
            if ts_ms >= until_ms:
                break
            dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            rows.append((label, TF, ts_ms, dt, o, h, l, cl, v or 0.0))

        if rows:
            conn.executemany("INSERT OR REPLACE INTO ohlcv VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)
            conn.commit()
            total += len(rows)

        last_ts = candles[-1][0]
        dt_str = datetime.fromtimestamp(last_ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        pct = (last_ts - since_ms) / (until_ms - since_ms) * 100
        print(f"  {label}/5m: {dt_str} ({pct:.0f}%) +{len(rows)} rows, total={total:,}")

        if last_ts >= until_ms:
            break

        # Always advance to avoid infinite loop (even if fewer candles returned)
        current = last_ts + TF_MS
        time.sleep(0.2)

    return total


def main():
    exchange = ccxt.binance({"options": {"defaultType": "future"}})
    exchange.load_markets()

    since_ms = exchange.parse8601(START_DATE)
    until_ms = exchange.parse8601(END_DATE)

    conn = sqlite3.connect(DB_PATH)

    for symbol in SYMBOLS:
        label = symbol_label(symbol)

        # Check if we already have some data in this range
        cur = conn.execute(
            "SELECT MIN(timestamp), MAX(timestamp), COUNT(*) FROM ohlcv "
            "WHERE symbol=? AND timeframe='5m' AND timestamp < ?",
            (label, until_ms),
        )
        row = cur.fetchone()
        existing = row[2] or 0
        if existing > 0:
            min_dt = datetime.fromtimestamp(row[0] / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
            max_dt = datetime.fromtimestamp(row[1] / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
            print(f"\n{label}/5m: {existing:,} existing rows ({min_dt} ~ {max_dt})")
            # Resume from last existing
            start = row[1] + 1
        else:
            print(f"\n{label}/5m: no existing data before 2024-10-01")
            start = since_ms

        expected = (until_ms - since_ms) // TF_MS
        print(f"  Expected ~{expected:,} bars from 2022-01-01 to 2024-10-01")
        print(f"  Fetching from {datetime.fromtimestamp(start/1000, tz=timezone.utc).strftime('%Y-%m-%d')}...")

        count = fetch_and_store(exchange, conn, symbol, start, until_ms)
        print(f"  Done: +{count:,} new rows")

    # Summary
    print("\n=== 5m Data Summary ===")
    cur = conn.execute(
        "SELECT symbol, MIN(datetime), MAX(datetime), COUNT(*) "
        "FROM ohlcv WHERE timeframe='5m' GROUP BY symbol"
    )
    for row in cur.fetchall():
        print(f"  {row[0]}/5m: {row[3]:,} bars ({row[1]} ~ {row[2]})")

    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
