"""Granularity definitions and OHLCV resampling."""
from __future__ import annotations

from enum import Enum
from datetime import date, timedelta
from typing import Optional

import pandas as pd


# ---------------------------------------------------------------------------
# Market holiday calendars
# ---------------------------------------------------------------------------

# US fixed holidays (month, day)
US_HOLIDAYS = {
    (1, 1),   # New Year's Day
    (6, 19),  # Juneteenth
    (7, 4),   # Independence Day
    (12, 25), # Christmas
}

# US variable holidays (approximate — 2024-2027)
US_VARIABLE_HOLIDAYS = {
    "2024-01-15", "2024-02-19", "2024-03-29", "2024-05-27", "2024-09-02",
    "2024-10-14", "2024-11-28", "2024-11-29",
    "2025-01-20", "2025-02-17", "2025-04-18", "2025-05-26", "2025-09-01",
    "2025-10-13", "2025-11-27", "2025-11-28",
    "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25", "2026-09-07",
    "2026-10-12", "2026-11-26", "2026-11-27",
    "2027-01-18", "2027-02-15", "2027-03-26", "2027-05-31", "2027-09-06",
    "2027-10-11", "2027-11-25", "2027-11-26",
}

# KRX fixed holidays (month, day)
KRX_HOLIDAYS = {
    (1, 1), (3, 1), (5, 5), (6, 6), (8, 15), (10, 3), (10, 9), (12, 25),
}

# KRX variable holidays — Lunar New Year, Chuseok, etc. (2024-2027)
KRX_VARIABLE_HOLIDAYS = {
    # 2024
    "2024-02-09", "2024-02-12",  # Lunar New Year
    "2024-04-10",                 # National Assembly election
    "2024-05-15",                 # Buddha's Birthday
    "2024-09-16", "2024-09-17", "2024-09-18",  # Chuseok
    # 2025
    "2025-01-28", "2025-01-29", "2025-01-30",  # Lunar New Year
    "2025-05-05",                 # Children's Day (overlaps fixed, covered)
    "2025-10-05", "2025-10-06", "2025-10-07",  # Chuseok
    # 2026
    "2026-02-16", "2026-02-17", "2026-02-18",  # Lunar New Year
    "2026-09-24", "2026-09-25",                 # Chuseok
    # 2027
    "2027-02-08", "2027-02-09", "2027-02-10",  # Lunar New Year
    "2027-09-14", "2027-09-15", "2027-09-16",  # Chuseok
}


class Granularity(Enum):
    """Supported time granularities."""
    M1 = "1m"
    M5 = "5m"
    M10 = "10m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    M600 = "600m"  # 10 hours
    D1 = "1d"

    @property
    def minutes(self) -> int:
        """Number of minutes in this granularity."""
        mapping = {
            "1m": 1, "5m": 5, "10m": 10, "15m": 15, "30m": 30,
            "1h": 60, "4h": 240, "600m": 600, "1d": 1440,
        }
        return mapping[self.value]

    @property
    def pandas_freq(self) -> str:
        """Pandas-compatible frequency string."""
        mapping = {
            "1m": "1min", "5m": "5min", "10m": "10min",
            "15m": "15min", "30m": "30min",
            "1h": "1h", "4h": "4h", "600m": "600min", "1d": "1D",
        }
        return mapping[self.value]

    @classmethod
    def from_string(cls, s: str) -> "Granularity":
        """Parse a granularity from string like '1m', '5m', '1d'."""
        s = s.lower().strip()
        for g in cls:
            if g.value == s:
                return g
        raise ValueError(f"Unknown granularity: {s}")


# Map of yfinance-compatible intervals
YFINANCE_INTERVALS = {
    "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "1h", "1d": "1d",
}


def resample_ohlcv(df: pd.DataFrame, target: Granularity) -> pd.DataFrame:
    """Resample OHLCV DataFrame to a coarser granularity.

    Expects columns: open, high, low, close, volume with a DatetimeIndex.
    """
    if df.empty:
        return df

    # Normalize column names to lowercase
    df = df.copy()
    df.columns = [c.lower() for c in df.columns]

    agg = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }
    resampled = df.resample(target.pandas_freq).agg(agg).dropna()
    return resampled


def trading_minutes_per_day(market: str = "US") -> int:
    """Return the number of trading minutes per day for a market."""
    market = market.upper()
    if market == "KRX":
        return 360  # 09:00-15:00 (6 hours with lunch)
    elif market == "CRYPTO":
        return 1440  # 24/7
    else:  # US
        return 390  # 09:30-16:00 (6.5 hours)


def is_trading_day(d: date, market: str = "US") -> bool:
    """Check if a date is a trading day (checks weekends and market holidays)."""
    market = market.upper()
    if market == "CRYPTO":
        return True  # crypto trades 24/7
    # Skip weekends for stock markets
    if d.weekday() >= 5:
        return False
    # Check market holidays
    if market == "US":
        if (d.month, d.day) in US_HOLIDAYS:
            return False
        if d.isoformat() in US_VARIABLE_HOLIDAYS:
            return False
    elif market == "KRX":
        if (d.month, d.day) in KRX_HOLIDAYS:
            return False
        if d.isoformat() in KRX_VARIABLE_HOLIDAYS:
            return False
    return True
