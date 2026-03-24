"""Central configuration for Trading Quest."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# --- Paths ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
QUESTS_DIR = PROJECT_ROOT / "quests"
SCRIPTS_DIR = PROJECT_ROOT / "tq" / "strategy" / "scripts"
DB_PATH = DATA_DIR / "cache.sqlite"

# --- Markets ---
MARKETS = ("KRX", "US", "CRYPTO")

DEFAULT_CAPITAL = {
    "KRX": 100_000_000,
    "US": 100_000,
    "CRYPTO": 10_000,
}

COMMISSION_RATE = {
    "KRX": 0.00015,
    "US": 0.001,
    "CRYPTO": 0.001,
}

SLIPPAGE_RATE = {
    "KRX": 0.0005,
    "US": 0.0005,
    "CRYPTO": 0.0002,
}

# --- Quest tuning ---
DAILY_TARGET_SCORE = 0.01
MAX_CONSECUTIVE_FAILS = 3
CHECKPOINT_INTERVAL = 5
MAX_DRAWDOWN_LIMIT = 0.20

# --- Alerts ---
TELEGRAM_BOT_TOKEN = os.environ.get("TQ_TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TQ_TELEGRAM_CHAT_ID", "")
# --- Binance ---
BINANCE_API_KEY = os.environ.get("TQ_BINANCE_API_KEY", "")
BINANCE_API_SECRET = os.environ.get("TQ_BINANCE_API_SECRET", "")
BINANCE_TESTNET = os.environ.get("TQ_BINANCE_TESTNET", "true").lower() in ("true", "1", "yes")


@dataclass
class QuestConfig:
    """Configuration for a single quest run."""

    quest_id: str = "default"
    market: str = "US"
    symbols: list[str] = field(default_factory=lambda: ["AAPL", "MSFT"])
    initial_capital: float = 100_000.0
    start_date: str = "2024-01-01"
    days: int = 30
    strategy_name: str = "ma_crossover"
    commission_rate: Optional[float] = None
    slippage_rate: Optional[float] = None

    def __post_init__(self) -> None:
        self.market = self.market.upper()
        if self.commission_rate is None:
            self.commission_rate = COMMISSION_RATE.get(self.market, 0.001)
        if self.slippage_rate is None:
            self.slippage_rate = SLIPPAGE_RATE.get(self.market, 0.0005)
        if self.initial_capital <= 0:
            self.initial_capital = DEFAULT_CAPITAL.get(self.market, 100_000)
