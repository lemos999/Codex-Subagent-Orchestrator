"""Market data fetchers -- retrieves OHLCV data from multiple sources."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

from tq.data.granularity import Granularity, YFINANCE_INTERVALS, resample_ohlcv

logger = logging.getLogger(__name__)


class DataFetcher(ABC):
    """Abstract base for all market data fetchers."""

    market: str = ""

    @abstractmethod
    def fetch_daily(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        """Fetch daily OHLCV data."""
        ...

    @abstractmethod
    def fetch_intraday(self, symbol: str, start: str, end: str,
                       interval: str = "1m") -> pd.DataFrame:
        """Fetch intraday OHLCV data."""
        ...

    def fetch_timeframe(self, symbol: str, start: str, end: str,
                        granularity: str = "1d") -> pd.DataFrame:
        """Fetch data at any supported granularity.

        Uses native intervals where possible, otherwise fetches at a finer
        granularity and resamples.
        """
        g = Granularity.from_string(granularity)
        if g == Granularity.D1:
            return self.fetch_daily(symbol, start, end)

        # Try native interval first
        native = YFINANCE_INTERVALS.get(g.value)
        if native:
            df = self.fetch_intraday(symbol, start, end, interval=native)
            if not df.empty:
                return df

        # Fallback: fetch 1m and resample
        df = self.fetch_intraday(symbol, start, end, interval="1m")
        if df.empty:
            return df
        return resample_ohlcv(df, g)

    def fetch_latest(self, symbol: str, interval: str = "1m",
                     limit: int = 100) -> Optional[pd.DataFrame]:
        """Fetch latest candles for live trading."""
        end = datetime.now()
        if interval == "1d":
            start = end - timedelta(days=limit + 5)
        else:
            minutes = Granularity.from_string(interval).minutes * limit
            start = end - timedelta(minutes=minutes + 60)
        start_str = start.strftime("%Y-%m-%d")
        end_str = end.strftime("%Y-%m-%d")
        try:
            if interval == "1d":
                return self.fetch_daily(symbol, start_str, end_str)
            return self.fetch_intraday(symbol, start_str, end_str, interval=interval)
        except Exception:
            logger.warning("fetch_latest failed for %s", symbol, exc_info=True)
            return None

    @abstractmethod
    def get_top_symbols(self, n: int = 100) -> list[str]:
        """Return top N symbols for this market."""
        ...

    @abstractmethod
    def get_all_symbols(self) -> list[str]:
        """Return all available symbols for this market."""
        ...


class YFinanceFetcher(DataFetcher):
    """Fetcher using yfinance library."""

    market = "US"

    def fetch_daily(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        return self._fetch_interval(symbol, start, end, "1d")

    def fetch_intraday(self, symbol: str, start: str, end: str,
                       interval: str = "1m") -> pd.DataFrame:
        return self._fetch_interval(symbol, start, end, interval)

    def _fetch_interval(self, symbol: str, start: str, end: str,
                        interval: str) -> pd.DataFrame:
        """Fetch data using yfinance."""
        try:
            import yfinance as yf  # type: ignore[import-untyped]
        except ImportError:
            logger.error("yfinance not installed. Run: pip install yfinance")
            return pd.DataFrame()

        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start, end=end, interval=interval)
            if df.empty:
                logger.warning("No data returned for %s [%s~%s] (%s)",
                               symbol, start, end, interval)
                return df
            # Normalize columns
            df.columns = [c.lower() for c in df.columns]
            # Keep only OHLCV
            cols = ["open", "high", "low", "close", "volume"]
            available = [c for c in cols if c in df.columns]
            df = df[available]
            logger.info("Fetched %d rows for %s [%s~%s] (%s)",
                        len(df), symbol, start, end, interval)
            return df
        except Exception:
            logger.error("yfinance fetch failed for %s", symbol, exc_info=True)
            return pd.DataFrame()

    def get_top_symbols(self, n: int = 100) -> list[str]:
        from tq.data.stock_universe import TOP_US_STOCKS
        return TOP_US_STOCKS[:n]

    def get_all_symbols(self) -> list[str]:
        from tq.data.stock_universe import TOP_US_STOCKS
        return TOP_US_STOCKS


class KRXFetcher(DataFetcher):
    """Fetcher for Korean stock market.

    Uses yfinance as fallback (pykrx may not be available on Python 3.14).
    Korean stocks use .KS suffix for yfinance.
    """

    market = "KRX"

    def __init__(self):
        self._yf = YFinanceFetcher()

    def fetch_daily(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        return self._yf.fetch_daily(symbol, start, end)

    def fetch_intraday(self, symbol: str, start: str, end: str,
                       interval: str = "1m") -> pd.DataFrame:
        return self._yf.fetch_intraday(symbol, start, end, interval)

    def get_top_symbols(self, n: int = 100) -> list[str]:
        from tq.data.stock_universe import TOP_KRX_STOCKS
        return TOP_KRX_STOCKS[:n]

    def get_all_symbols(self) -> list[str]:
        from tq.data.stock_universe import TOP_KRX_STOCKS
        return TOP_KRX_STOCKS


class BinanceFetcher(DataFetcher):
    """Fetcher for Binance cryptocurrency exchange."""

    market = "CRYPTO"

    KLINE_INTERVALS = {
        "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
        "1h": "1h", "4h": "4h", "1d": "1d",
    }

    def fetch_daily(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        return self._fetch_interval(symbol, start, end, "1d")

    def fetch_intraday(self, symbol: str, start: str, end: str,
                       interval: str = "1m") -> pd.DataFrame:
        return self._fetch_interval(symbol, start, end, interval)

    def _fetch_interval(self, symbol: str, start: str, end: str,
                        interval: str) -> pd.DataFrame:
        """Fetch klines from Binance REST API."""
        try:
            import urllib.request
            import json

            kline_interval = self.KLINE_INTERVALS.get(interval, interval)
            all_data = []
            start_ts = int(datetime.strptime(start, "%Y-%m-%d").timestamp() * 1000)
            end_ts = int(datetime.strptime(end, "%Y-%m-%d").timestamp() * 1000)

            # Loop to handle pagination (max 1000 per request)
            while start_ts < end_ts:
                url = (
                    f"https://api.binance.com/api/v3/klines?"
                    f"symbol={symbol}&interval={kline_interval}"
                    f"&startTime={start_ts}&endTime={end_ts}&limit=1000"
                )
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode())

                if not data:
                    break

                all_data.extend(data)
                # Move start to after last candle
                start_ts = data[-1][6] + 1  # close_time + 1

                if len(data) < 1000:
                    break

            if not all_data:
                return pd.DataFrame()

            df = pd.DataFrame(all_data, columns=[
                "open_time", "open", "high", "low", "close", "volume",
                "close_time", "quote_vol", "trades", "buy_base_vol",
                "buy_quote_vol", "ignore",
            ])
            df["datetime"] = pd.to_datetime(df["open_time"], unit="ms")
            df.set_index("datetime", inplace=True)
            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = df[col].astype(float)
            df = df[["open", "high", "low", "close", "volume"]]
            logger.info("Fetched %d klines for %s [%s~%s] (%s)",
                        len(df), symbol, start, end, interval)
            return df

        except Exception:
            logger.error("Binance fetch failed for %s", symbol, exc_info=True)
            return pd.DataFrame()

    def get_top_symbols(self, n: int = 100) -> list[str]:
        from tq.data.stock_universe import TOP_CRYPTO_PAIRS
        return TOP_CRYPTO_PAIRS[:n]

    def get_all_symbols(self) -> list[str]:
        from tq.data.stock_universe import TOP_CRYPTO_PAIRS
        return TOP_CRYPTO_PAIRS


def get_fetcher(market: str = "US") -> DataFetcher:
    """Factory: return the appropriate fetcher for a market."""
    market = market.upper()
    if market == "KRX":
        return KRXFetcher()
    elif market == "CRYPTO":
        return BinanceFetcher()
    else:
        return YFinanceFetcher()


def fetch_timeframe(symbol: str, start: str, end: str,
                    granularity: str = "1d",
                    market: str = "US") -> pd.DataFrame:
    """Convenience function: fetch data at any granularity."""
    fetcher = get_fetcher(market)
    return fetcher.fetch_timeframe(symbol, start, end, granularity)
