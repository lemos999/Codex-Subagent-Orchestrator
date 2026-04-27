"""Phase 17 Stage 2: collapse 완화 기제(size tax + homeostasis) 수학적 backstop."""
from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from Projects.personas.loom.ontology.layers import (
    DRIFT_MARGIN_MIN,
    FACTION_SIZE_TAX_MIN,
    FACTION_SIZE_TAX_START,
    HOMEOSTASIS_DRIFT_MARGIN_SCALE,
    HOMEOSTASIS_LOW_THRESHOLD,
)


def _size_tax(size_ratio: float) -> float:
    """지시서 수식 표현."""
    if size_ratio <= FACTION_SIZE_TAX_START:
        return 1.0
    excess = size_ratio - FACTION_SIZE_TAX_START
    span = 1.0 - FACTION_SIZE_TAX_START
    return max(FACTION_SIZE_TAX_MIN, 1.0 - excess / span)


def test_phase17_size_tax_monotone_and_bounded() -> None:
    """tax는 [MIN, 1.0] 범위, size_ratio 증가에 따라 비증가."""
    ratios = [0.0, 0.1, FACTION_SIZE_TAX_START, 0.35, 0.5, 0.8, 1.0]
    taxes = [_size_tax(r) for r in ratios]
    for t in taxes:
        assert FACTION_SIZE_TAX_MIN <= t <= 1.0, f"범위 이탈: {t}"
    for a, b in zip(taxes, taxes[1:]):
        assert a >= b, f"비증가 위반: {a} < {b}"
    assert _size_tax(FACTION_SIZE_TAX_START) == 1.0, "경계값에서 tax=1.0 유지"
    assert _size_tax(1.0) == FACTION_SIZE_TAX_MIN, "점유 100%에서 tax=MIN 도달"


def test_phase17_homeostasis_margin_relaxed() -> None:
    """active 수 THRESHOLD 이하일 때 margin_floor는 DRIFT_MARGIN_MIN보다 작다."""
    relaxed = DRIFT_MARGIN_MIN * HOMEOSTASIS_DRIFT_MARGIN_SCALE
    assert 0 < relaxed < DRIFT_MARGIN_MIN, (
        f"homeostasis가 margin을 완화하지 못함: relaxed={relaxed}, min={DRIFT_MARGIN_MIN}"
    )
    assert HOMEOSTASIS_LOW_THRESHOLD >= 1


def test_phase17_tax_guards_startup_phase() -> None:
    """START 이하 점유율에서는 tax가 작동하지 않아 초기 faction이 말라죽지 않음."""
    assert _size_tax(0.0) == 1.0
    assert _size_tax(FACTION_SIZE_TAX_START * 0.5) == 1.0
    assert _size_tax(FACTION_SIZE_TAX_START) == 1.0
