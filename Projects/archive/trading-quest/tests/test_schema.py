"""Tests for database schema module."""
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from tq.data.schema import init_db, get_connection


class TestSchema(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        self.tmp.close()
        self.db_path = self.tmp.name

    def tearDown(self):
        os.unlink(self.db_path)

    def test_init_db_creates_tables(self):
        init_db(self.db_path)
        conn = get_connection(self.db_path)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()
        self.assertIn("daily_ohlcv", tables)
        self.assertIn("minute_ohlcv", tables)
        self.assertIn("stock_universe", tables)
        self.assertIn("fetch_log", tables)

    def test_get_connection_returns_row_factory(self):
        init_db(self.db_path)
        conn = get_connection(self.db_path)
        self.assertEqual(conn.row_factory, sqlite3.Row)
        conn.close()

    def test_init_db_idempotent(self):
        init_db(self.db_path)
        init_db(self.db_path)  # should not raise


if __name__ == "__main__":
    unittest.main()
