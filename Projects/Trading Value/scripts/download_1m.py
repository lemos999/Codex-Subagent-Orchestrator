"""Download 1-minute OHLCV data from Binance Futures for simulation.

Downloads 3 months of 1m candles for ETH, BTC, SOL, XRP.
Stores in data/sim_1m.sqlite.

Usage: cd "Projects/Trading Value" && py -3 scripts/download_1m.py
       py -3 scripts/download_1m.py --days 7     (last 7 days only, for testing)
       py -3 scripts/download_1m.py --update      (append missing data)
"""
from __future__ import annotations
import sys, time, sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

import ccxt

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "sim_1m.sqlite"

SYMBOLS = ["ETHUSDT", "BTCUSDT", "SOLUSDT", "XRPUSDT"]
DEFAULT_DAYS = 90  # 3 months


def init_db(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ohlcv_1m (
            symbol TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            datetime TEXT NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            volume REAL NOT NULL,
            PRIMARY KEY (symbol, timestamp)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_ohlcv_1m_sym_dt
        ON ohlcv_1m (symbol, datetime)
    """)
    conn.commit()


def get_last_timestamp(conn: sqlite3.Connection, symbol: str) -> int | None:
    row = conn.execute(
        "SELECT MAX(timestamp) FROM ohlcv_1m WHERE symbol=?", (symbol,)
    ).fetchone()
    return row[0] if row and row[0] else None


def download_symbol(exchange, conn: sqlite3.Connection, symbol: str, days: int, update: bool):
    print(f"\n{'='*50}")
    print(f"  {symbol}")
    print(f"{'='*50}")

    if update:
        last_ts = get_last_timestamp(conn, symbol)
        if last_ts:
            since = last_ts + 60_000  # next minute
            last_dt = datetime.fromtimestamp(last_ts / 1000, tz=timezone.utc)
            print(f"  Updating from {last_dt.strftime('%Y-%m-%d %H:%M')}")
        else:
            since = int((datetime.now(tz=timezone.utc) - timedelta(days=days)).timestamp() * 1000)
            print(f"  No existing data, downloading {days} days")
    else:
        since = int((datetime.now(tz=timezone.utc) - timedelta(days=days)).timestamp() * 1000)
        print(f"  Downloading {days} days")

    now_ms = int(datetime.now(tz=timezone.utc).timestamp() * 1000)
    total = 0
    batch_size = 1500  # Binance max per request

    while since < now_ms:
        try:
            candles = exchange.fetch_ohlcv(
                symbol.replace("USDT", "/USDT:USDT"),
                "1m", since=since, limit=batch_size
            )
        except Exception as e:
            print(f"  Error: {e}, retrying in 5s...")
            time.sleep(5)
            continue

        if not candles:
            break

        rows = []
        for c in candles:
            ts = c[0]
            dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            rows.append((symbol, ts, dt, c[1], c[2], c[3], c[4], c[5]))

        conn.executemany(
            "INSERT OR REPLACE INTO ohlcv_1m VALUES (?,?,?,?,?,?,?,?)",
            rows
        )
        conn.commit()

        total += len(candles)
        last_dt = datetime.fromtimestamp(candles[-1][0] / 1000, tz=timezone.utc)
        since = candles[-1][0] + 60_000

        # Progress
        pct = min(100, (since - (now_ms - days * 86400_000)) / (days * 86400_000) * 100)
        print(f"  {last_dt.strftime('%Y-%m-%d %H:%M')} | {total:>8,} rows | {pct:.0f}%", end="\r")

        # Rate limit: Binance allows 1200 req/min, be conservative
        time.sleep(0.5)

    print(f"\n  Done: {total:,} rows downloaded for {symbol}")
    return total


def main():
    days = DEFAULT_DAYS
    update = False

    if "--days" in sys.argv:
        idx = sys.argv.index("--days")
        days = int(sys.argv[idx + 1])
    if "--update" in sys.argv:
        update = True

    print(f"Simulation Data Downloader")
    print(f"  DB: {DB_PATH}")
    print(f"  Symbols: {', '.join(SYMBOLS)}")
    print(f"  Period: {'update' if update else f'{days} days'}")

    exchange = ccxt.binance({"options": {"defaultType": "future"}})
    exchange.load_markets()

    conn = sqlite3.connect(str(DB_PATH))
    init_db(conn)

    grand_total = 0
    for sym in SYMBOLS:
        n = download_symbol(exchange, conn, sym, days, update)
        grand_total += n

    # Summary
    print(f"\n{'='*50}")
    print(f"  COMPLETE: {grand_total:,} total rows")
    for sym in SYMBOLS:
        row = conn.execute(
            "SELECT COUNT(*), MIN(datetime), MAX(datetime) FROM ohlcv_1m WHERE symbol=?",
            (sym,)
        ).fetchone()
        print(f"  {sym}: {row[0]:,} rows ({row[1]} ~ {row[2]})")
    print(f"  DB size: {DB_PATH.stat().st_size / 1024 / 1024:.1f} MB")
    conn.close()


if __name__ == "__main__":
    main()
