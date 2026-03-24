"""Fetch full historical OHLCV data from Binance Futures.

Downloads all available history for ETHUSDT and BTCUSDT Perp.
Timeframes: 5m, 15m, 1h, 4h
Start: 2019-09-01 (earliest futures data)

Usage: cd "Projects/Trading Value" && py -3 scripts/fetch_full_history.py
"""
from __future__ import annotations

import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import ccxt

SYMBOLS = ["ETH/USDT:USDT", "BTC/USDT:USDT"]
TIMEFRAMES = ["15m", "1h", "4h"]  # 5m handled separately (huge volume)
DB_PATH = str(Path(__file__).resolve().parent.parent / "data" / "cache.sqlite")

START_DATE = "2019-09-01T00:00:00Z"
BATCH_LIMIT = 1500

TF_MS = {
    "5m": 5 * 60 * 1000,
    "15m": 15 * 60 * 1000,
    "1h": 60 * 60 * 1000,
    "4h": 4 * 60 * 60 * 1000,
}


def symbol_label(symbol: str) -> str:
    return symbol.replace("/", "").replace(":USDT", "")


def fetch_range(exchange, conn, symbol, tf, since_ms, until_ms):
    label = symbol_label(symbol)
    total = 0
    current = since_ms

    while current < until_ms:
        try:
            candles = exchange.fetch_ohlcv(symbol, tf, since=current, limit=BATCH_LIMIT)
        except Exception as e:
            print(f"  Error: {e}", flush=True)
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
            rows.append((label, tf, ts_ms, dt, o, h, l, cl, v or 0.0))

        if rows:
            conn.executemany("INSERT OR REPLACE INTO ohlcv VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)
            conn.commit()
            total += len(rows)

        last_ts = candles[-1][0]
        if last_ts >= until_ms:
            break

        pct = (last_ts - since_ms) / max(until_ms - since_ms, 1) * 100
        dt_str = datetime.fromtimestamp(last_ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        print(f"  {label}/{tf}: {dt_str} ({pct:.0f}%) total={total:,}", flush=True)

        current = last_ts + TF_MS.get(tf, 60000)
        time.sleep(0.2)

    return total


def main():
    exchange = ccxt.binance({"options": {"defaultType": "future"}})
    exchange.load_markets()

    since_ms = exchange.parse8601(START_DATE)
    now_ms = int(time.time() * 1000)

    conn = sqlite3.connect(DB_PATH)

    # Ensure table exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ohlcv (
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            datetime TEXT NOT NULL,
            open REAL NOT NULL, high REAL NOT NULL, low REAL NOT NULL,
            close REAL NOT NULL, volume REAL NOT NULL,
            PRIMARY KEY (symbol, timeframe, timestamp)
        )
    """)
    conn.commit()

    for symbol in SYMBOLS:
        label = symbol_label(symbol)
        for tf in TIMEFRAMES:
            # Check existing data
            cur = conn.execute(
                "SELECT MIN(timestamp), MAX(timestamp), COUNT(*) FROM ohlcv "
                "WHERE symbol=? AND timeframe=?", (label, tf))
            row = cur.fetchone()
            existing = row[2] or 0

            if existing > 0 and row[0] and row[0] <= since_ms + TF_MS.get(tf, 60000) * 10:
                # Already have data from near start
                min_dt = datetime.fromtimestamp(row[0] / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
                max_dt = datetime.fromtimestamp(row[1] / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
                print(f"\n{label}/{tf}: already have {existing:,} bars ({min_dt} ~ {max_dt}) — skipping")
                continue

            # Need to backfill before existing data
            if existing > 0:
                fill_until = row[0]  # fill up to existing start
                min_dt = datetime.fromtimestamp(row[0] / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
                print(f"\n{label}/{tf}: backfilling before {min_dt}...")
            else:
                fill_until = now_ms
                print(f"\n{label}/{tf}: fetching full history from 2019-09...")

            count = fetch_range(exchange, conn, symbol, tf, since_ms, fill_until)
            print(f"  Done: +{count:,} new rows")

    # Also fetch 5m back to 2019
    print("\n--- 5m backfill to 2019 ---")
    for symbol in SYMBOLS:
        label = symbol_label(symbol)
        cur = conn.execute(
            "SELECT MIN(timestamp), COUNT(*) FROM ohlcv WHERE symbol=? AND timeframe='5m'",
            (label,))
        row = cur.fetchone()
        if row[0]:
            existing_start = row[0]
            if existing_start <= since_ms + TF_MS["5m"] * 10:
                min_dt = datetime.fromtimestamp(existing_start / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
                print(f"{label}/5m: already starts at {min_dt} — skipping")
                continue
            min_dt = datetime.fromtimestamp(existing_start / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
            print(f"{label}/5m: backfilling before {min_dt}...")
            count = fetch_range(exchange, conn, symbol, "5m", since_ms, existing_start)
            print(f"  Done: +{count:,} new rows")
        else:
            print(f"{label}/5m: no data, fetching full...")
            count = fetch_range(exchange, conn, symbol, "5m", since_ms, now_ms)
            print(f"  Done: +{count:,} new rows")

    # Summary
    print("\n=== Full History Summary ===")
    cur = conn.execute(
        "SELECT symbol, timeframe, COUNT(*), MIN(datetime), MAX(datetime) "
        "FROM ohlcv GROUP BY symbol, timeframe ORDER BY symbol, timeframe")
    for row in cur.fetchall():
        print(f"  {row[0]:>8s}/{row[1]:<4s}: {row[2]:>9,} bars  ({row[3][:10]} ~ {row[4][:10]})")

    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
