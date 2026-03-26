"""Simulation exchange — replays historical 1m data as if live.

SimClock: manages virtual time, advances 1 minute per tick.
MockExchange: ccxt-compatible interface, serves data from sim_1m.sqlite.

Usage:
    clock = SimClock(start="2026-01-01 00:00:00")
    exchange = MockExchange(clock, db_path="data/sim_1m.sqlite")

    # Advance time by 1 minute
    clock.tick()

    # These work like ccxt
    exchange.fetch_ohlcv("ETH/USDT:USDT", "30m", limit=200)
    exchange.fetch_ticker("ETH/USDT:USDT")
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path


class SimClock:
    """Virtual clock for simulation. Advances 1 minute per tick."""

    def __init__(self, start: str, end: str | None = None):
        """
        Args:
            start: Start datetime string "YYYY-MM-DD HH:MM:SS" (UTC)
            end: Optional end datetime. If None, runs until data runs out.
        """
        self.current = datetime.strptime(start, "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=timezone.utc
        )
        self.start = self.current
        self.end = (
            datetime.strptime(end, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            if end
            else None
        )
        self.tick_count = 0

    def tick(self, minutes: int = 1) -> bool:
        """Advance clock by N minutes. Returns False if past end."""
        self.current += timedelta(minutes=minutes)
        self.tick_count += 1
        if self.end and self.current > self.end:
            return False
        return True

    def now(self) -> datetime:
        return self.current

    def is_30m_boundary(self) -> bool:
        """True if current time is at :00 or :30 (30-minute eval trigger)."""
        return self.current.minute % 30 == 0

    def elapsed_minutes(self) -> int:
        return int((self.current - self.start).total_seconds() / 60)

    def total_minutes(self) -> int | None:
        if self.end:
            return int((self.end - self.start).total_seconds() / 60)
        return None

    def progress(self) -> float:
        """0.0 to 1.0"""
        total = self.total_minutes()
        if total and total > 0:
            return min(1.0, self.elapsed_minutes() / total)
        return 0.0


class MockExchange:
    """ccxt-compatible exchange that serves historical data from SQLite."""

    def __init__(self, clock: SimClock, db_path: str = "data/sim_1m.sqlite"):
        self.clock = clock
        self.db_path = str(db_path)
        self._conn = sqlite3.connect(self.db_path)

        # Preload all data into memory for speed
        self._data: dict[str, list[tuple]] = {}
        self._load_all()

        # For ccxt compatibility
        self.markets = {}

    def _load_all(self):
        """Load all 1m data into memory, grouped by symbol."""
        cursor = self._conn.execute(
            "SELECT symbol, timestamp, open, high, low, close, volume "
            "FROM ohlcv_1m ORDER BY symbol, timestamp"
        )
        for row in cursor:
            sym = row[0]
            if sym not in self._data:
                self._data[sym] = []
            # (timestamp_ms, open, high, low, close, volume)
            self._data[sym].append((row[1], row[2], row[3], row[4], row[5], row[6]))

        for sym in self._data:
            print(f"  [sim] Loaded {len(self._data[sym]):,} 1m bars for {sym}")

    def _symbol_to_key(self, symbol: str) -> str:
        """Convert ccxt symbol to DB key: 'ETH/USDT:USDT' -> 'ETHUSDT'"""
        return symbol.replace("/", "").replace(":USDT", "")

    def load_markets(self):
        """No-op for compatibility."""
        pass

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 200,
                    since: int | None = None) -> list[list]:
        """Return OHLCV data up to current sim time, aggregated to timeframe."""
        key = self._symbol_to_key(symbol)
        if key not in self._data:
            return []

        now_ms = int(self.clock.now().timestamp() * 1000)
        bars_1m = self._data[key]

        # Filter: only bars up to current sim time
        available = [b for b in bars_1m if b[0] <= now_ms]
        if not available:
            return []

        # Aggregate 1m bars to requested timeframe
        tf_minutes = _tf_to_minutes(timeframe)
        if tf_minutes == 1:
            # Return raw 1m bars
            result = available[-limit:]
            return [[b[0], b[1], b[2], b[3], b[4], b[5]] for b in result]

        # Aggregate
        aggregated = _aggregate_bars(available, tf_minutes)
        result = aggregated[-limit:]
        return [[b[0], b[1], b[2], b[3], b[4], b[5]] for b in result]

    def fetch_ticker(self, symbol: str) -> dict:
        """Return current price (last 1m close)."""
        key = self._symbol_to_key(symbol)
        if key not in self._data:
            return {"last": 0.0}

        now_ms = int(self.clock.now().timestamp() * 1000)
        bars = self._data[key]

        # Find the last bar at or before current time
        last_price = 0.0
        for b in reversed(bars):
            if b[0] <= now_ms:
                last_price = b[4]  # close
                break

        return {"last": last_price, "symbol": symbol}


def _tf_to_minutes(tf: str) -> int:
    """Convert timeframe string to minutes."""
    mapping = {
        "1m": 1, "3m": 3, "5m": 5, "15m": 15, "30m": 30,
        "1h": 60, "2h": 120, "4h": 240, "6h": 360,
        "12h": 720, "1d": 1440,
    }
    return mapping.get(tf, 30)


def _aggregate_bars(bars_1m: list[tuple], tf_minutes: int) -> list[tuple]:
    """Aggregate 1m bars into larger timeframe bars."""
    if not bars_1m:
        return []

    tf_ms = tf_minutes * 60 * 1000
    result = []
    bucket_start = (bars_1m[0][0] // tf_ms) * tf_ms
    bucket_open = bars_1m[0][1]
    bucket_high = bars_1m[0][2]
    bucket_low = bars_1m[0][3]
    bucket_close = bars_1m[0][4]
    bucket_volume = bars_1m[0][5]

    for b in bars_1m[1:]:
        bar_bucket = (b[0] // tf_ms) * tf_ms
        if bar_bucket != bucket_start:
            # Emit completed bucket
            result.append((
                bucket_start, bucket_open, bucket_high,
                bucket_low, bucket_close, bucket_volume
            ))
            # Start new bucket
            bucket_start = bar_bucket
            bucket_open = b[1]
            bucket_high = b[2]
            bucket_low = b[3]
            bucket_close = b[4]
            bucket_volume = b[5]
        else:
            bucket_high = max(bucket_high, b[2])
            bucket_low = min(bucket_low, b[3])
            bucket_close = b[4]
            bucket_volume += b[5]

    # Emit last bucket
    result.append((
        bucket_start, bucket_open, bucket_high,
        bucket_low, bucket_close, bucket_volume
    ))

    return result
