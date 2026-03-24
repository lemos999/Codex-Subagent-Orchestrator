"""Quest phases -- progression system."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class QuestPhase(Enum):
    """Quest phases with increasing complexity."""
    PHASE_1 = 1  # Minute-by-minute, single symbol
    PHASE_2 = 2  # Daily batch, multi-symbol
    PHASE_3 = 3  # Full auto, multi-timeframe

    @property
    def label(self) -> str:
        labels = {1: "Exploration", 2: "Expansion", 3: "Mastery"}
        return labels.get(self.value, "Unknown")


@dataclass
class PhaseConfig:
    """Configuration for a quest phase."""
    phase: QuestPhase
    min_days: int = 10
    min_score: float = 0.0
    max_drawdown: float = 0.20
    auto_batch: bool = False
    allow_multi_tf: bool = False

    @classmethod
    def default_configs(cls) -> dict[QuestPhase, "PhaseConfig"]:
        return {
            QuestPhase.PHASE_1: cls(
                phase=QuestPhase.PHASE_1,
                min_days=10,
                min_score=0,
                max_drawdown=0.15,
                auto_batch=False,
                allow_multi_tf=False,
            ),
            QuestPhase.PHASE_2: cls(
                phase=QuestPhase.PHASE_2,
                min_days=10,
                min_score=0,
                max_drawdown=0.20,
                auto_batch=True,
                allow_multi_tf=False,
            ),
            QuestPhase.PHASE_3: cls(
                phase=QuestPhase.PHASE_3,
                min_days=10,
                min_score=0,
                max_drawdown=0.25,
                auto_batch=True,
                allow_multi_tf=True,
            ),
        }


class PhaseManager:
    """Manages quest phase transitions."""

    def __init__(self, visible_start: date, phase1_end_date: Optional[date] = None):
        self.visible_start = visible_start
        self.phase1_end_date = phase1_end_date or (visible_start + timedelta(days=365))
        self.current_phase = QuestPhase.PHASE_1
        self.configs = PhaseConfig.default_configs()
        self.phase_days: dict[QuestPhase, int] = {p: 0 for p in QuestPhase}
        self.phase_scores: dict[QuestPhase, float] = {p: 0.0 for p in QuestPhase}
        self.transition_log: list[dict] = []

    def record_day(self, score: float, drawdown: float) -> Optional[QuestPhase]:
        """Record a day's result and check for phase transition.

        Returns new phase if transition occurred, None otherwise.
        """
        self.phase_days[self.current_phase] += 1
        self.phase_scores[self.current_phase] += score

        new_phase = self._check_transition(score, drawdown)
        if new_phase and new_phase != self.current_phase:
            old = self.current_phase
            self.current_phase = new_phase
            self.transition_log.append({
                "from": old.value,
                "to": new_phase.value,
                "day_count": sum(self.phase_days.values()),
            })
            logger.info("Phase transition: %s -> %s", old.label, new_phase.label)
            return new_phase
        return None

    def _check_transition(self, score: float, drawdown: float) -> QuestPhase:
        """Check if current phase should transition."""
        config = self.configs[self.current_phase]
        days = self.phase_days[self.current_phase]
        total_score = self.phase_scores[self.current_phase]
        meets_score = config.min_score <= 0 or total_score >= config.min_score

        if drawdown > config.max_drawdown:
            return self.current_phase  # stay, too risky

        if days >= config.min_days and meets_score:
            # Promote
            if self.current_phase == QuestPhase.PHASE_1:
                return QuestPhase.PHASE_2
            elif self.current_phase == QuestPhase.PHASE_2:
                return QuestPhase.PHASE_3
        return self.current_phase

    def get_config(self) -> PhaseConfig:
        """Get current phase config."""
        return self.configs[self.current_phase]

    def to_dict(self) -> dict:
        return {
            "current_phase": self.current_phase.value,
            "phase_label": self.current_phase.label,
            "phase_days": {p.value: d for p, d in self.phase_days.items()},
            "phase_scores": {p.value: s for p, s in self.phase_scores.items()},
            "transitions": self.transition_log,
        }
