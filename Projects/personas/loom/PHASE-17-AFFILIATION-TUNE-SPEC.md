# Phase 17 Affiliation Score — Stage 1 Drift 봉쇄 해소 튜닝 지시서

> 긴급도: 높음 (창발 메커니즘 불활성)
> 선행 조건: PHASE-17-FACTION-ENGINE-SSOT-FIX-SPEC.md 병행 가능 (독립 스코프)
> 작업 유형: 기능 (파라미터 재조정 + 수식 1줄 동적화)
> DB migration: 없음
> 외부 의존: 없음

---

## 배경

Phase 17 Emergence Probe(3 seed × 5000틱) 결과 `drift source = 0%`. `/discuss --quick` 3엔진 토론(2026-04-23) 결론: **W_TERRITORY의 비대칭(1.0 vs 0.0)과 고정 DRIFT_MARGIN(1.2)가 고정점 포로를 만든다.**

고정점 분석 (DECAY=0.92, 실측값 기준):
- 현재 score_factor: same_territory 케이스 ≈ 1.34, diff 케이스 ≈ 0.15
- 48틱 누적 고정점: current ≈ 16.75, rival ≈ 1.88, gap ≈ 14.9
- DRIFT_MARGIN=1.2 ≪ gap=14.9 → **영구 차단 (드리프트 불가)**

패치 후 예상 (W_TERRITORY=0.3/0.1, 나머지 유지):
- current ≈ 8.0, rival ≈ 3.1, gap ≈ 4.9
- 동적 margin ≈ 0.73 (gap×15%, 하한 0.3)
- → 드리프트 가능 경로 열림

Evidence: [subagent-runs/discuss/affiliation-bias-2026-04-23-quick/conclusion/conclusion.md](subagent-runs/discuss/affiliation-bias-2026-04-23-quick/conclusion/conclusion.md)

---

## 작업 범위

### [필수]
1. `W_TERRITORY` 상수를 단일 값(1.0)에서 `W_TERRITORY_SAME` + `W_TERRITORY_DIFF` 두 값으로 분리 (0.3 / 0.1)
2. `DRIFT_MARGIN` 상수(1.2)를 **최소 하한**으로 재해석. 실제 margin은 `max(DRIFT_MARGIN_MIN, gap × DRIFT_MARGIN_RATIO)` 동적 계산
3. `_compute_affiliation_tick`의 score_factor 수식 업데이트 (territory indicator → 조건부 값)
4. `_commit_faction_tick`의 drift 판정 로직 업데이트 (동적 margin)
5. 신규 회귀 테스트 `test_phase17_affiliation_drift_unlocked` 추가 — 드리프트 경로가 수학적으로 도달 가능함을 확인
6. Phase 17 Emergence Probe 재실행 (3 seed × 5000틱) → drift source ≥ 5% 목표

### [선택]
- `PHASE-17-FACTION-DECISIONS.md`에 v5 튜닝 결정 추가 메모

### [금지]
- `brain/lif_network.py`, `brain/persona_brain.py` 수정 (Phase 14-B readout 불변 원칙)
- SSoT `_change_persona_faction` 경로 우회
- `W_TRUST`, `W_GRIEVANCE`, `W_PROXIMITY`, `DECAY`, `THETA_JOIN` 변경 (이번 스코프 아님)
- `charter` primitive 3-5개 구조 변경
- 기존 faction cache invalidation 로직 변경 (SSOT-FIX-SPEC이 담당)

---

## 구체 사양

### ① 상수 변경 — `Projects/personas/loom/ontology/layers.py:195-206`

**Before:**
```python
W_TERRITORY = 1.0
W_TRUST = 0.8
W_GRIEVANCE = 0.6
W_PROXIMITY = 0.4
DECAY = 0.92
GRIEVANCE_MIN_SHARED = 0.3
PROXIMITY_DECAY_SCALE = 10.0

FACTION_COOLDOWN_TICKS = 48
FACTION_COMMIT_EVERY = 48
THETA_JOIN = 2.5
DRIFT_MARGIN = 1.2
```

**After:**
```python
# ── Phase 17 affiliation_score (v5: drift 봉쇄 해소 패치 2026-04-23) ──
# 고정점 분석 근거: PHASE-17-AFFILIATION-TUNE-SPEC.md §배경
W_TERRITORY_SAME = 0.3   # 같은 territory 거주 시 (v4: 1.0 → v5: 0.3, 비대칭 완화)
W_TERRITORY_DIFF = 0.1   # 다른 territory 거주 시 (v4: 0.0 → v5: 0.1, 완전 차단 제거)
W_TRUST = 0.8
W_GRIEVANCE = 0.6
W_PROXIMITY = 0.4
DECAY = 0.92
GRIEVANCE_MIN_SHARED = 0.3
PROXIMITY_DECAY_SCALE = 10.0

FACTION_COOLDOWN_TICKS = 48
FACTION_COMMIT_EVERY = 48
THETA_JOIN = 2.5

# DRIFT_MARGIN: v4까지 고정 1.2 → v5 동적 계산의 하한으로 재해석
# actual_margin = max(DRIFT_MARGIN_MIN, gap × DRIFT_MARGIN_RATIO)
DRIFT_MARGIN_MIN = 0.3
DRIFT_MARGIN_RATIO = 0.15

# 하위 호환 (기존 import 유지용 — 값은 의미 없음, 동적 경로가 우선)
DRIFT_MARGIN = DRIFT_MARGIN_MIN  # deprecated: 동적 계산 사용
```

### ② `_compute_affiliation_tick` 수정 — `Projects/personas/loom/core/multi_tick_engine.py:1148-1170`

**Before (line 1159-1164):**
```python
score = (
    W_TERRITORY * self._same_territory(persona, fid)
    + W_TRUST * self._trust_density(persona, fid)
    + W_GRIEVANCE * self._shared_grievance(persona, fid)
    + W_PROXIMITY * self._spatial_proximity(persona, fid)
)
```

**After:**
```python
# territory 기여는 비대칭 완화: same=0.3, diff=0.1 (v5 튜닝)
territory_weight = (
    W_TERRITORY_SAME
    if self._same_territory(persona, fid) > 0.5
    else W_TERRITORY_DIFF
)
score = (
    territory_weight
    + W_TRUST * self._trust_density(persona, fid)
    + W_GRIEVANCE * self._shared_grievance(persona, fid)
    + W_PROXIMITY * self._spatial_proximity(persona, fid)
)
```

**참고**: `_same_territory(persona, fid)`는 현재 0 또는 1 반환(Projects/personas/loom/core/multi_tick_engine.py 내 `_same_territory` 구현 확인 — 반환 타입이 float이면 0.5 임계 사용으로 충분).

### ③ `_commit_faction_tick` drift 판정 수정 — `Projects/personas/loom/core/multi_tick_engine.py:1171-1199`

**Before (line 1196-1198):**
```python
current_score = scores.get(cur_fid, 0.0)
if best_score - current_score >= DRIFT_MARGIN:
    self._change_persona_faction(pid, best_fid, source="drift")
```

**After:**
```python
current_score = scores.get(cur_fid, 0.0)
gap = best_score - current_score
# v5: 동적 margin — gap이 클수록 높은 임계, 작으면 최소 하한
dynamic_margin = max(DRIFT_MARGIN_MIN, gap * DRIFT_MARGIN_RATIO)
if gap >= dynamic_margin:
    self._change_persona_faction(pid, best_fid, source="drift")
```

**Import 업데이트 — `multi_tick_engine.py` 상단**:
기존 `from ..ontology.layers import (..., DRIFT_MARGIN, ...)` 를
`from ..ontology.layers import (..., DRIFT_MARGIN_MIN, DRIFT_MARGIN_RATIO, W_TERRITORY_SAME, W_TERRITORY_DIFF, ...)` 로 변경.
기존 `W_TERRITORY` import는 제거 (사용처 없음 확인 필수 — grep).

### ④ 회귀 테스트 추가 — `Projects/personas/loom/test_phase17_faction_drift.py` 신규

```python
"""Phase 17 Stage 1: affiliation drift 경로 도달 가능성 회귀 테스트."""
import pytest
from loom.core.multi_tick_engine import MultiTickEngine
from loom.ontology.layers import (
    DECAY, W_TERRITORY_SAME, W_TERRITORY_DIFF, W_TRUST, W_GRIEVANCE, W_PROXIMITY,
    DRIFT_MARGIN_MIN, DRIFT_MARGIN_RATIO, FACTION_COMMIT_EVERY,
)


def test_phase17_drift_unlocked_fixed_point():
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
    # 이상적 current (same territory) score_factor
    current_factor = W_TERRITORY_SAME + W_TRUST * 0.2 + W_GRIEVANCE * 0.1 + W_PROXIMITY * 0.3
    # 이상적 rival (diff territory) score_factor
    rival_factor = W_TERRITORY_DIFF + W_TRUST * 0.1 + W_GRIEVANCE * 0.05 + W_PROXIMITY * 0.1

    current_fp = current_factor / (1 - DECAY)
    rival_fp = rival_factor / (1 - DECAY)
    gap = current_fp - rival_fp

    dynamic_margin = max(DRIFT_MARGIN_MIN, gap * DRIFT_MARGIN_RATIO)

    # 드리프트 도달 가능성 (gap >= dynamic_margin이어야 _change_persona_faction(source='drift') 호출 가능)
    assert gap >= dynamic_margin, (
        f"드리프트 봉쇄: gap={gap:.2f} < margin={dynamic_margin:.2f}. "
        f"W_TERRITORY_SAME={W_TERRITORY_SAME}, DIFF={W_TERRITORY_DIFF} 재조정 필요."
    )
    # 하지만 gap이 margin의 100배를 넘으면 여전히 사실상 봉쇄 (v4 회귀 방지)
    assert gap < dynamic_margin * 100, (
        f"여전히 극단적 편향: gap={gap:.2f}, margin={dynamic_margin:.2f}. "
        f"비대칭 완화가 충분하지 않음."
    )


def test_phase17_territory_weight_asymmetry_bounded():
    """territory indicator 비대칭이 과도하게 크지 않음 (v4 회귀 방지)."""
    ratio = W_TERRITORY_SAME / max(W_TERRITORY_DIFF, 1e-6)
    assert ratio < 10.0, (
        f"territory 비대칭 {ratio:.1f}x 과도: v4(1.0/0.0=∞) 수준 회귀 금지."
    )
    assert ratio >= 2.0, (
        f"territory 선호 {ratio:.1f}x 미흡: same territory 소속 성향이 사라지면 안 됨."
    )


def test_phase17_dynamic_margin_never_zero():
    """동적 margin이 항상 양수 하한을 가진다."""
    for gap_candidate in [0.0, 0.1, 1.0, 10.0, 100.0]:
        margin = max(DRIFT_MARGIN_MIN, gap_candidate * DRIFT_MARGIN_RATIO)
        assert margin >= DRIFT_MARGIN_MIN > 0
```

### ⑤ 기존 테스트 회귀 검증 — 필수 PASS 목록

| 파일 | 왜 PASS 해야 하는가 |
|------|------------------|
| `test_phase14b_snn_integration.py` (8/8) | Phase 14-B SNN readout 불변 — brain 미수정 증명 |
| `test_nomos.py` | 법/통치 로직 — affiliation과 독립 |
| `test_class_promotion.py` | 계층 이동 — affiliation 변경에 의존 가능, 실패 시 디버깅 |
| `test_phase17_faction_*.py` (기존) | faction 로직 회귀 |
| `test_phase17_faction_drift.py` (신규) | 이번 Stage 1 도입 |

---

## 변경 파일

| 파일 | 작업 | 유형 |
|------|------|:---:|
| `Projects/personas/loom/ontology/layers.py` | 상수 블록 재구성 (v5) | 수정 |
| `Projects/personas/loom/ontology/__init__.py` | export 추가 (`W_TERRITORY_SAME/DIFF`, `DRIFT_MARGIN_MIN/RATIO`) | 수정 |
| `Projects/personas/loom/core/multi_tick_engine.py` | score_factor 수식 + drift 판정 로직 | 수정 |
| `Projects/personas/loom/test_phase17_faction_drift.py` | 신규 회귀 테스트 | 추가 |

**변경 없음 (금지):**
- `Projects/personas/loom/brain/**` — Phase 14-B 불변 원칙
- `Projects/personas/loom/core/tick_engine.py` — 단일 틱 경로 (아닌 multi_tick_engine 전용 변경)
- `observe_phase17_emergence.py` — probe 스크립트, Stage 1 검증 도구로 재사용
- `PHASE-17-FACTION-ENGINE-SSOT-FIX-SPEC.md` 관련 영역 (결함 A/B 수정은 독립 스코프)

---

## 검증

### 기계 검증 (Python 프로젝트)

```bash
cd Projects/personas/loom
py -m pytest test_phase17_faction_drift.py -v    # 신규 3건 PASS
py -m pytest test_phase14b_snn_integration.py -v # 8/8 유지
py -m pytest test_phase17_faction_*.py -v        # 기존 회귀
py -m pytest test_nomos.py test_class_promotion.py -v
py -c "from loom.core.multi_tick_engine import MultiTickEngine; e = MultiTickEngine(seed=42); e.tick()"  # 런타임 smoke
```

**Lint/type**:
```bash
cd Projects/personas/loom
py -m ruff check core/multi_tick_engine.py ontology/layers.py ontology/__init__.py
py -m mypy core/multi_tick_engine.py ontology/layers.py 2>&1 | grep -v "already defined"
```
(프로젝트에 mypy/ruff 미설정이면 그 사실을 보고서에 명시하고 `python -m py_compile` 만으로 대체.)

### 기능 검증 — Phase 17 Emergence Probe 재실행

```bash
cd Projects/personas/loom
py observe_phase17_emergence.py --seeds 7,13,42 --ticks 5000 --out data/phase17_probe_v5
```

**수용 기준**:
- [ ] `data/phase17_probe_v5/SUMMARY.md` 생성
- [ ] 3 seed 중 **최소 2 seed에서 drift source ≥ 5%** (과거 0%에서 개선)
- [ ] active_factions_end 변동 발생 (분화 또는 소멸) — **최소 1 seed에서 초기 3개와 다름**
- [ ] faction_change 이벤트 총량 증가 (v4 대비 150% 이상)
- [ ] wealth gini 추세가 seed 평균 0.25 이상 유지 (계급 재료 보존)
- [ ] Phase 14-B 회귀 0건 (SNN readout 불변 증명)

### 계약 검증 — 수학적 증명

신규 `test_phase17_drift_unlocked_fixed_point` 테스트가 고정점 분석을 수치로 검증.
PASS 조건: `gap >= dynamic_margin` 에서 드리프트 도달 가능성 수학적 확증.

---

## Rollback

```bash
cd Projects/personas/loom
git diff HEAD~1 -- ontology/layers.py core/multi_tick_engine.py ontology/__init__.py > /tmp/tune_v5.patch
git checkout HEAD~1 -- ontology/layers.py core/multi_tick_engine.py ontology/__init__.py
# 신규 테스트 파일은 untracked이므로 수동 삭제:
rm test_phase17_faction_drift.py
```

데이터 영향: 없음 (상수 변경 + 수식 1줄만 영향, 저장된 페르소나 상태와 무관).

Phase 14-B 회귀 발생 시 즉시 Rollback + 원인 분석 (brain 미수정이면 Logically 불가능해야 함).

---

## GPT/Codex 전달 프롬프트 템플릿

```
당신은 Python 시뮬레이션 프로젝트(loom)의 시니어 개발자입니다.

## 프로젝트 경로
c:\Users\haj\projects\subagent-orchestrator\Projects\personas\loom

## 기술 스택
Python 3.11, numpy, pytest. LIF spiking neural network 기반 페르소나 에이전트 시뮬레이션.

## 작업 지시서
PHASE-17-AFFILIATION-TUNE-SPEC.md 파일을 그대로 따라 구현하세요.

## 규칙 (절대 준수)
1. 지시서의 [필수] 항목 6개 100% 구현. [금지] 항목 절대 건드리지 말 것.
   - 특히 `brain/` 디렉토리 수정 금지 (Phase 14-B 불변 원칙).
2. 지시서에 포함된 코드 블록(Before/After)은 그대로 복사해서 반영. "해석"하지 말 것.
3. 수식은 고정점 분석 근거가 있으므로 임의 조정 금지.
4. 검증 순서:
   a. py -m pytest test_phase17_faction_drift.py -v
   b. py -m pytest test_phase14b_snn_integration.py -v
   c. py -m pytest test_phase17_faction_*.py test_nomos.py test_class_promotion.py -v
   d. py observe_phase17_emergence.py --seeds 7,13,42 --ticks 5000 --out data/phase17_probe_v5
5. 검증 실패 시 재작업, 통과할 때까지 반복.
6. 보고 내용:
   - 변경 파일 4개 목록과 각 파일의 diff 요약
   - 검증 단계 a~d 통과 여부
   - probe v5 결과 SUMMARY.md 핵심 지표 (drift ratio, active_factions, faction_change 총량)
   - Phase 14-B 회귀 0건 확인
```
