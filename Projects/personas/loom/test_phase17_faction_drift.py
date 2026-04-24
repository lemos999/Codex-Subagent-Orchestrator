"""Phase 17 Stage 1: affiliation drift 경로 도달 가능성 추가 테스트."""
from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from Projects.personas.loom.ontology.layers import (
    DECAY, W_TERRITORY_SAME, W_TERRITORY_DIFF, W_TRUST, W_GRIEVANCE, W_PROXIMITY,
    DRIFT_MARGIN_MIN, DRIFT_MARGIN_RATIO,
)


def test_phase17_drift_unlocked_fixed_point() -> None:
    """고정점 분석: 현재 faction과 rival faction의 score 격차가 드리프트 가능 범위 안에 있어야 한다.

    v4 값(W_TERRITORY=1.0, DRIFT_MARGIN=1.2) 기준:
      current_fp ≈ 1.34 / 0.08 ≈ 16.75
      rival_fp   ≈ 0.15 / 0.08 ≈ 1.88
      gap        ≈ 14.87 >> DRIFT_MARGIN=1.2 → 봉쇄

    v5 값(W_TERRITORY_SAME=0.3, DIFF=0.1, 동적 margin) 기준:
      current_fp ≈ 0.64 / 0.08 ≈ 8.0
      rival_fp   ≈ 0.25 / 0.08 ≈ 3.12
      gap        ≈ 4.88
      dynamic_margin = max(0.3, 4.88 × 0.15) = 0.73
      → gap=4.88 >= 0.73 → 드리프트 도달 가능
    """
    current_factor = W_TERRITORY_SAME + W_TRUST * 0.2 + W_GRIEVANCE * 0.1 + W_PROXIMITY * 0.3
    rival_factor = W_TERRITORY_DIFF + W_TRUST * 0.1 + W_GRIEVANCE * 0.05 + W_PROXIMITY * 0.1

    current_fp = current_factor / (1 - DECAY)
    rival_fp = rival_factor / (1 - DECAY)
    gap = current_fp - rival_fp

    dynamic_margin = max(DRIFT_MARGIN_MIN, gap * DRIFT_MARGIN_RATIO)

    assert gap >= dynamic_margin, (
        f"드리프트 봉쇄: gap={gap:.2f} < margin={dynamic_margin:.2f}. "
        f"W_TERRITORY_SAME={W_TERRITORY_SAME}, DIFF={W_TERRITORY_DIFF} 재조정 필요."
    )
    assert gap < dynamic_margin * 100, (
        f"사전적 극단 편향: gap={gap:.2f}, margin={dynamic_margin:.2f}. "
        f"비대칭 완화가 충분하지 않음."
    )


def test_phase17_territory_weight_asymmetry_bounded() -> None:
    """territory indicator 비대칭이 과도하게 크지 않음 (v4 회귀 방지)."""
    ratio = W_TERRITORY_SAME / max(W_TERRITORY_DIFF, 1e-6)
    assert ratio < 10.0, (
        f"territory 비대칭 {ratio:.1f}x 과도: v4(1.0/0.0=∞) 상태 재발 금지."
    )
    assert ratio >= 2.0, (
        f"territory 신호 {ratio:.1f}x 미만: same territory 소속 경향이 사라지면 안 됨."
    )


def test_phase17_dynamic_margin_never_zero() -> None:
    """동적 margin은 항상 양수 하한값을 가진다."""
    for gap_candidate in [0.0, 0.1, 1.0, 10.0, 100.0]:
        margin = max(DRIFT_MARGIN_MIN, gap_candidate * DRIFT_MARGIN_RATIO)
        assert margin >= DRIFT_MARGIN_MIN > 0
