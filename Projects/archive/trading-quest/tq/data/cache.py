"""SQLite cache for OHLCV data."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

import pandas as pd

from tq.data.schema import get_connection, init_db

logger = logging.getLogger(__name__)


class DataCache:
    """Caches daily and minute OHLCV data in SQLite."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path
        init_db(db_path)

    # ------------------------------------------------------------------
    # Daily
    # ------------------------------------------------------------------

    def save_daily(self, symbol: str, market: str, df: pd.DataFrame) -> int:
        """Save daily OHLCV data. Returns rows inserted."""
        if df.empty:
            return 0
        conn = get_connection(self.db_path)
        try:
            rows = 0
            for idx, row in df.iterrows():
                date_str = str(idx)[:10] if hasattr(idx, 'isoformat') else str(idx)[:10]
                try:
                    conn.execute(
                        "INSERT OR REPLACE INTO daily_ohlcv "
                        "(symbol, market, date, open, high, low, close, volume) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (symbol, market, date_str,
                         float(row.get("open", row.get("Open", 0))),
                         float(row.get("high", row.get("High", 0))),
                         float(row.get("low", row.get("Low", 0))),
                         float(row.get("close", row.get("Close", 0))),
                         float(row.get("volume", row.get("Volume", 0)))),
                    )
                    rows += 1
                except Exception as e:
                    logger.warning("Failed to insert daily row for %s: %s", symbol, e)
            conn.commit()
            self._log_fetch(conn, symbol, market, "1d",
                            str(df.index[0])[:10], str(df.index[-1])[:10], rows)
            return rows
        finally:
            conn.close()

    def load_daily(self, symbol: str, market: str,
                   start: Optional[str] = None,
                   end: Optional[str] = None) -> pd.DataFrame:
        """Load daily OHLCV data from cache."""
        conn = get_connection(self.db_path)
        try:
            query = "SELECT date, open, high, low, close, volume FROM daily_ohlcv WHERE symbol=? AND market=?"
            params: list = [symbol, market]
            if start:
                query += " AND date >= ?"
                params.append(start)
            if end:
                query += " AND date <= ?"
                params.append(end)
            query += " ORDER BY date"
            df = pd.read_sql_query(query, conn, params=params)
            if not df.empty:
                df["date"] = pd.to_datetime(df["date"])
                df.set_index("date", inplace=True)
            return df
        finally:
            conn.close()

    def has_daily(self, symbol: str, market: str,
                  start: Optional[str] = None,
                  end: Optional[str] = None) -> bool:
        """Check if daily data exists in cache."""
        conn = get_connection(self.db_path)
        try:
            query = "SELECT COUNT(*) FROM daily_ohlcv WHERE symbol=? AND market=?"
            params: list = [symbol, market]
            if start:
                query += " AND date >= ?"
                params.append(start)
            if end:
                query += " AND date <= ?"
                params.append(end)
            cursor = conn.execute(query, params)
            count = cursor.fetchone()[0]
            return count > 0
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Minute
    # ------------------------------------------------------------------

    def save_minute(self, symbol: str, market: str, df: pd.DataFrame) -> int:
        """Save minute OHLCV data. Returns rows inserted."""
        if df.empty:
            return 0
        conn = get_connection(self.db_path)
        try:
            rows = 0
            for idx, row in df.iterrows():
                dt_str = str(idx)[:19]
                try:
                    conn.execute(
                        "INSERT OR REPLACE INTO minute_ohlcv "
                        "(symbol, market, datetime, open, high, low, close, volume) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (symbol, market, dt_str,
                         float(row.get("open", row.get("Open", 0))),
                         float(row.get("high", row.get("High", 0))),
                         float(row.get("low", row.get("Low", 0))),
                         float(row.get("close", row.get("Close", 0))),
                         float(row.get("volume", row.get("Volume", 0)))),
                    )
                    rows += 1
                except Exception as e:
                    logger.warning("Failed to insert minute row for %s: %s", symbol, e)
            conn.commit()
            self._log_fetch(conn, symbol, market, "1m",
                            str(df.index[0])[:19], str(df.index[-1])[:19], rows)
            return rows
        finally:
            conn.close()

    def load_minute(self, symbol: str, market: str,
                    start: Optional[str] = None,
                    end: Optional[str] = None) -> pd.DataFrame:
        """Load minute OHLCV data from cache."""
        conn = get_connection(self.db_path)
        try:
            query = "SELECT datetime, open, high, low, close, volume FROM minute_ohlcv WHERE symbol=? AND market=?"
            params: list = [symbol, market]
            if start:
                query += " AND datetime >= ?"
                params.append(start)
            if end:
                query += " AND datetime <= ?"
                params.append(end)
            query += " ORDER BY datetime"
            df = pd.read_sql_query(query, conn, params=params)
            if not df.empty:
                df["datetime"] = pd.to_datetime(df["datetime"])
                df.set_index("datetime", inplace=True)
            return df
        finally:
            conn.close()

    def has_minute(self, symbol: str, market: str,
                   start: Optional[str] = None,
                   end: Optional[str] = None) -> bool:
        """Check if minute data exists in cache."""
        conn = get_connection(self.db_path)
        try:
            query = "SELECT COUNT(*) FROM minute_ohlcv WHERE symbol=? AND market=?"
            params: list = [symbol, market]
            if start:
                query += " AND datetime >= ?"
                params.append(start)
            if end:
                query += " AND datetime <= ?"
                params.append(end)
            cursor = conn.execute(query, params)
            count = cursor.fetchone()[0]
            return count > 0
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Universe
    # ------------------------------------------------------------------

    def save_universe(self, symbols: list[dict], market: str) -> int:
        """Save stock universe. Each dict: symbol, name, sector, category."""
        conn = get_connection(self.db_path)
        try:
            rows = 0
            now = datetime.now().strftime("%Y-%m-%d")
            for s in symbols:
                conn.execute(
                    "INSERT OR REPLACE INTO stock_universe "
                    "(symbol, market, name, sector, category, added_date) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (s["symbol"], market,
                     s.get("name", ""), s.get("sector", ""),
                     s.get("category", "top100"), now),
                )
                rows += 1
            conn.commit()
            return rows
        finally:
            conn.close()

    def load_universe(self, market: str,
                      category: Optional[str] = None) -> list[dict]:
        """Load stock universe."""
        conn = get_connection(self.db_path)
        try:
            query = "SELECT symbol, name, sector, category FROM stock_universe WHERE market=?"
            params: list = [market]
            if category:
                query += " AND category=?"
                params.append(category)
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_status(self) -> dict:
        """Get cache status info."""
        conn = get_connection(self.db_path)
        try:
            daily_count = conn.execute("SELECT COUNT(*) FROM daily_ohlcv").fetchone()[0]
            minute_count = conn.execute("SELECT COUNT(*) FROM minute_ohlcv").fetchone()[0]
            universe_count = conn.execute("SELECT COUNT(*) FROM stock_universe").fetchone()[0]
            daily_symbols = conn.execute(
                "SELECT COUNT(DISTINCT symbol) FROM daily_ohlcv"
            ).fetchone()[0]
            minute_symbols = conn.execute(
                "SELECT COUNT(DISTINCT symbol) FROM minute_ohlcv"
            ).fetchone()[0]
            return {
                "daily_rows": daily_count,
                "minute_rows": minute_count,
                "universe_count": universe_count,
                "daily_symbols": daily_symbols,
                "minute_symbols": minute_symbols,
            }
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _log_fetch(self, conn, symbol: str, market: str, interval: str,
                   start: str, end: str, rows: int) -> None:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "INSERT INTO fetch_log (symbol, market, interval, start_date, end_date, rows_fetched, fetched_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (symbol, market, interval, start, end, rows, now),
        )
        conn.commit()
