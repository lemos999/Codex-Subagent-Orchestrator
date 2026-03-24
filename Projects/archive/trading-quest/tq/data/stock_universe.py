"""Stock universe management."""
from __future__ import annotations

import logging
import random
from typing import Optional

from tq.data.cache import DataCache

logger = logging.getLogger(__name__)

# Curated top US stocks
TOP_US_STOCKS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B",
    "JPM", "V", "JNJ", "WMT", "PG", "MA", "UNH", "HD", "DIS", "BAC",
    "XOM", "PFE", "CSCO", "ADBE", "CRM", "NFLX", "AMD", "INTC", "QCOM",
    "TXN", "COST", "NKE", "PYPL", "ABBV", "MRK", "TMO", "DHR", "LLY",
    "AVGO", "PEP", "KO", "MCD", "ORCL", "ABT", "CVX", "ACN", "CMCSA",
    "VZ", "T", "NEE", "PM", "RTX", "LOW", "UPS", "HON", "IBM",
    "SBUX", "GS", "MS", "BLK", "AMAT", "CAT", "ISRG", "MDLZ", "GE",
    "NOW", "AXP", "SPGI", "TJX", "MMC", "ADI", "REGN", "VRTX", "SYK",
    "LMT", "ZTS", "GILD", "BKNG", "PANW", "SNPS", "CDNS", "KLAC",
    "CME", "MCO", "LRCX", "ADP", "MU", "MELI", "ABNB", "SQ", "CRWD",
    "DDOG", "NET", "ZS", "COIN", "SNOW", "PLTR", "SOFI", "RIVN", "LCID",
]

# Curated top KRX stocks
TOP_KRX_STOCKS = [
    "005930.KS", "000660.KS", "035420.KS", "051910.KS", "006400.KS",
    "035720.KS", "068270.KS", "028260.KS", "105560.KS", "012330.KS",
    "055550.KS", "066570.KS", "003670.KS", "096770.KS", "034730.KS",
    "017670.KS", "000270.KS", "032830.KS", "003490.KS", "009150.KS",
    "018260.KS", "033780.KS", "030200.KS", "011170.KS", "086790.KS",
    "036570.KS", "034020.KS", "004020.KS", "010950.KS", "003550.KS",
    "005380.KS", "000810.KS", "001570.KS", "005490.KS", "316140.KS",
    "259960.KS", "247540.KS", "352820.KS", "005935.KS", "373220.KS",
]

# Curated top crypto pairs
TOP_CRYPTO_PAIRS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "ADAUSDT", "DOTUSDT", "DOGEUSDT", "AVAXUSDT", "MATICUSDT",
    "LINKUSDT", "UNIUSDT", "ATOMUSDT", "LTCUSDT", "NEARUSDT",
    "APTUSDT", "ARBUSDT", "OPUSDT", "SUIUSDT", "SEIUSDT",
]


class StockUniverse:
    """Manages the stock universe for trading quests."""

    def __init__(self, cache: Optional[DataCache] = None):
        self.cache = cache or DataCache()

    def build(self, market: str = "US") -> list[str]:
        """Build a universe: top 100 + random 100 symbols.

        For markets with fewer curated symbols, uses what's available.
        """
        market = market.upper()
        curated = self._get_curated(market)
        top = curated[:100]

        # Random picks from remaining, if any
        remaining = curated[100:]
        random_picks = random.sample(remaining, min(100, len(remaining))) if remaining else []

        universe = top + random_picks

        # Save to cache
        entries = [{"symbol": s, "category": "top100" if s in top else "random100"}
                   for s in universe]
        self.cache.save_universe(entries, market)

        logger.info("Built universe for %s: %d symbols", market, len(universe))
        return universe

    def load(self, market: str = "US") -> list[str]:
        """Load universe from cache."""
        market = market.upper()
        entries = self.cache.load_universe(market)
        if entries:
            return [e["symbol"] for e in entries]
        # Fallback: build it
        return self.build(market)

    def get_all_symbols(self, market: str = "US") -> list[str]:
        """Get all available symbols for a market."""
        market = market.upper()
        return self._get_curated(market)

    def _get_curated(self, market: str) -> list[str]:
        """Return the curated symbol list for a market."""
        market = market.upper()
        if market == "KRX":
            return TOP_KRX_STOCKS
        elif market == "CRYPTO":
            return TOP_CRYPTO_PAIRS
        else:
            return TOP_US_STOCKS
