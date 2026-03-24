"""Quest state -- save/load quest progress."""
from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from tq.config import QUESTS_DIR

logger = logging.getLogger(__name__)


@dataclass
class QuestState:
    """Serializable quest state."""
    quest_id: str
    market: str
    symbols: list[str]
    initial_capital: float
    current_capital: float
    start_date: str
    current_date: str
    current_day: int = 0
    phase: int = 1
    strategy_name: str = ""
    total_score: float = 0.0
    trade_log: list[dict] = field(default_factory=list)
    daily_results: list[dict] = field(default_factory=list)
    positions: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

    def save(self, quests_dir: Optional[Path] = None) -> Path:
        """Save state to JSON file."""
        path = quests_dir or QUESTS_DIR
        path.mkdir(parents=True, exist_ok=True)
        filepath = path / f"{self.quest_id}.json"
        data = self.to_dict()
        filepath.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        logger.info("Quest state saved to %s", filepath)
        return filepath

    @classmethod
    def load(cls, quest_id: str, quests_dir: Optional[Path] = None) -> "QuestState":
        """Load state from JSON file."""
        path = quests_dir or QUESTS_DIR
        filepath = path / f"{quest_id}.json"
        if not filepath.exists():
            raise FileNotFoundError(f"Quest state not found: {filepath}")
        data = json.loads(filepath.read_text(encoding="utf-8"))
        return cls.from_dict(data)

    def checkpoint(self, quests_dir: Optional[Path] = None) -> Path:
        """Save a checkpoint copy."""
        path = quests_dir or QUESTS_DIR
        path.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = path / f"{self.quest_id}_checkpoint_{ts}.json"
        data = self.to_dict()
        filepath.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        logger.info("Checkpoint saved to %s", filepath)
        return filepath

    def archive(self, quests_dir: Optional[Path] = None) -> Path:
        """Archive the quest state."""
        path = quests_dir or QUESTS_DIR
        archive_dir = path / "archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        src = path / f"{self.quest_id}.json"
        dst = archive_dir / f"{self.quest_id}_{ts}.json"
        if src.exists():
            shutil.copy2(str(src), str(dst))
            logger.info("Quest archived to %s", dst)
        return dst

    def to_dict(self) -> dict:
        return {
            "quest_id": self.quest_id,
            "market": self.market,
            "symbols": self.symbols,
            "initial_capital": self.initial_capital,
            "current_capital": self.current_capital,
            "start_date": self.start_date,
            "current_date": self.current_date,
            "current_day": self.current_day,
            "phase": self.phase,
            "strategy_name": self.strategy_name,
            "total_score": self.total_score,
            "trade_log": self.trade_log,
            "daily_results": self.daily_results,
            "positions": self.positions,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "QuestState":
        return cls(
            quest_id=data["quest_id"],
            market=data["market"],
            symbols=data.get("symbols", []),
            initial_capital=data["initial_capital"],
            current_capital=data["current_capital"],
            start_date=data["start_date"],
            current_date=data["current_date"],
            current_day=data.get("current_day", 0),
            phase=data.get("phase", 1),
            strategy_name=data.get("strategy_name", ""),
            total_score=data.get("total_score", 0.0),
            trade_log=data.get("trade_log", []),
            daily_results=data.get("daily_results", []),
            positions=data.get("positions", {}),
            metadata=data.get("metadata", {}),
        )
