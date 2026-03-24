"""SQLite schema for Trading Quest data cache."""
from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from tq.config import DB_PATH

logger = logging.getLogger(__name__)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS daily_ohlcv (
    symbol      TEXT    NOT NULL,
    market      TEXT    NOT NULL,
    date        TEXT    NOT NULL,
    open        REAL    NOT NULL,
    high        REAL    NOT NULL,
    low         REAL    NOT NULL,
    close       REAL    NOT NULL,
    volume      REAL    NOT NULL,
    PRIMARY KEY (symbol, market, date)
);

CREATE TABLE IF NOT EXISTS minute_ohlcv (
    symbol      TEXT    NOT NULL,
    market      TEXT    NOT NULL,
    datetime    TEXT    NOT NULL,
    open        REAL    NOT NULL,
    high        REAL    NOT NULL,
    low         REAL    NOT NULL,
    close       REAL    NOT NULL,
    volume      REAL    NOT NULL,
    PRIMARY KEY (symbol, market, datetime)
);

CREATE TABLE IF NOT EXISTS stock_universe (
    symbol      TEXT    NOT NULL,
    market      TEXT    NOT NULL,
    name        TEXT    DEFAULT '',
    sector      TEXT    DEFAULT '',
    category    TEXT    DEFAULT 'top100',
    added_date  TEXT    NOT NULL,
    PRIMARY KEY (symbol, market)
);

CREATE TABLE IF NOT EXISTS fetch_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol      TEXT    NOT NULL,
    market      TEXT    NOT NULL,
    interval    TEXT    NOT NULL,
    start_date  TEXT    NOT NULL,
    end_date    TEXT    NOT NULL,
    rows_fetched INTEGER NOT NULL,
    fetched_at  TEXT    NOT NULL
);
"""


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Get a SQLite connection, creating the database if needed."""
    path = Path(db_path) if db_path else DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(db_path: Path | str | None = None) -> None:
    """Initialize all tables."""
    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
        logger.info("Database initialized at %s", db_path or DB_PATH)
    finally:
        conn.close()
