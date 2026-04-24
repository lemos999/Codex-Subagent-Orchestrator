# Phase 17 Stage 2 — Faction Collapse Mitigation (Size Tax + Homeostasis)

> 긴급도: 높음
> 선행 조건: `PHASE-17-FACTION-ENGINE-SSOT-FIX-SPEC.md` (SSoT-FIX 완료), `PHASE-17-AFFILIATION-TUNE-SPEC.md` (v5 drift unlock 완료)
> 작업 유형: 기능 (엔진 로직 + 상수) + 회귀 테스트
> DB migration: 없음
> 외부 의존: 없음 (기존 구조 내 수식·상수 추가)

---

## 배경

**Stage 1 결과 (v5 probe)**: drift unlock 성공 (drift ratio 14-33%) but Φ-2 창발 FAIL.

3 seed 전부 5000틱에 active_factions=1로 수렴 (winner-takes-all collapse).

| seed | active_end | contact_pairs | drift | gini | faction_changes |
|------|-----------|---------------|-------|------|-----------------|
| 7 | 1 | 0 | 14% | 0.85 | 44 |
| 13 | 1 | 0 | 28% | 0.82 | 50 |
| 42 | 1 | 0 | 33% | 0.73 | 48 |

**근본 원인**: v5에서 W_TERRITORY 비대칭 완화(1.0→0.3) 이후 territory 고정력 약화 → trust/proximity positive feedback이 지배 → 큰 faction이 더 큰 attractor가 됨. faction_change 이벤트는 활발하나 한 방향으로만 수렴.

**해결 전략**: 두 기제 병행으로 winner-takes-all을 구조적으로 억제.
1. **Faction 규모 tax** — 큰 faction일수록 매 틱 score 가산 약화 (흡수력 감쇠)
2. **Homeostasis** — active_factions ≤ 2일 때 drift 장벽(margin_floor) 완화 (탈출 경로 활성화)

Φ-3 Struggle 진입을 위해 **seed 3 중 최소 1건에서 active_end ≥ 2** 달성 필요.

---

## 작업 범위

### [필수]
1. `layers.py`에 v6 상수 블록 추가 (4개 신규 상수)
2. `_compute_affiliation_tick`에 size tax 수식 삽입 (이번 틱 가산분에만 적용, decay 누적은 불변)
3. `_commit_faction_tick`에 homeostasis 분기 삽입 (margin_floor 동적 교체)
4. `test_phase17_faction_mitigation.py` 신규 (3 케이스 — 수학적 backstop)
5. `data/phase17_probe_v6/` seed 7/13/42 × 5000틱 실행 + SUMMARY.md 생성
6. 기존 회귀 PASS 유지: `test_phase17_faction_drift.py` (3), `test_phase17_faction_reincarnation_safety.py` (1), `test_phase14b_snn_integration.py` (8), `test_phase17_faction_*.py` 기타 (≥16)

### [선택]
- v5 vs v6 비교 markdown (`docs/PHASE-17-COLLAPSE-MITIGATION-REPORT.md`)
- probe 중 acrive_factions 추이 샘플 로그 (1000틱 간격)

### [금지]
- `brain/**` 수정 (Phase 14-B readout 불변 — n_neurons=1000, readout_weights, ACTIONS 6차원 계약 유지)
- `_change_persona_faction` 경로 변경 (SSoT)
- W_TERRITORY / W_TRUST / W_GRIEVANCE / W_PROXIMITY / DECAY / THETA_JOIN 값 변경
- DRIFT_MARGIN_MIN / RATIO 원본 값 변경 (homeostasis는 분기로 교체, 기본값은 불변)
- charter primitive 목록 변경 (3-5 고정)
- 경제/SNN/reincarnation 로직 (본 지시서 범위 밖)

---

## 구체 사양

### A. 상수 추가 (`ontology/layers.py`)

**삽입 위치**: line 214 `DRIFT_MARGIN_RATIO = 0.15` 다음, line 215 `# 하위 호환` 앞.

```python
# ── Phase 17 v6: collapse 완화 (size tax + homeostasis, 2026-04-24) ──
# 근거: v5 probe 3 seed 전원 active_end=1 수렴 (PHASE-17-FACTION-COLLAPSE-MITIGATION-SPEC.md)
# 1. Faction 규모 tax: size_ratio가 START를 넘기면 선형 감쇠, MIN이 하한
FACTION_SIZE_TAX_START = 0.3     # 전체 활성 인구 대비 30% 점유부터 tax 적용
FACTION_SIZE_TAX_MIN = 0.3       # tax 하한 (점유 100%에도 30%는 남아 신규 가입 경로 보존)
# 2. Homeostasis: active faction 수에 따라 drift margin_floor 조절
HOMEOSTASIS_LOW_THRESHOLD = 2    # active ≤ 2 → 완화 모드 진입
HOMEOSTASIS_DRIFT_MARGIN_SCALE = 0.5   # 완화 모드일 때 DRIFT_MARGIN_MIN에 곱하는 배수
```

**수학적 의도**:
- `size_ratio ≤ 0.3` → tax=1.0 (변화 없음, 초기 단계 보호)
- `size_ratio = 0.5` → tax ≈ 0.714
- `size_ratio = 0.8` → tax ≈ 0.286 → clamp → 0.3
- `size_ratio = 1.0` → tax = 0.3
- `active_count ≤ 2` → margin_floor = 0.15 (기존 0.3의 절반, drift 이탈 장벽 완화)
- `active_count ≥ 3` → margin_floor = 0.3 (기존 동일, 과분열 방지)

### B. size tax 수식 (`core/multi_tick_engine.py`)

**수정 대상**: `_compute_affiliation_tick` (현 line 1196-1222)

**Before** (현재 line 1199-1220):
```python
def _compute_affiliation_tick(self) -> None:
    """매 틱 affiliation score를 갱신한다."""
    self._rebuild_faction_members_cache()
    new_scores: dict[str, dict[str, float]] = {}
    for pid in sorted(self.personas):
        if pid not in self.inners:
            continue
        persona = self.personas[pid]
        prev_scores = self.inners[pid].affiliation_scores
        scored: dict[str, float] = {}
        for fid in sorted(self.factions):
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
            scored[fid] = DECAY * prev_scores.get(fid, 0.0) + score
```

**After**:
```python
def _compute_affiliation_tick(self) -> None:
    """매 틱 affiliation score를 갱신한다."""
    self._rebuild_faction_members_cache()
    # v6: 활성 인구 집계 (size tax 분모). inners 기준 = 살아있는 페르소나
    total_active = max(1, sum(1 for pid in self.personas if pid in self.inners))
    new_scores: dict[str, dict[str, float]] = {}
    for pid in sorted(self.personas):
        if pid not in self.inners:
            continue
        persona = self.personas[pid]
        prev_scores = self.inners[pid].affiliation_scores
        scored: dict[str, float] = {}
        for fid in sorted(self.factions):
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
            # v6: 규모 tax — 이번 틱 가산분에만 적용 (누적 decay 결과는 불변)
            size_ratio = len(self._faction_members_cache.get(fid, ())) / total_active
            if size_ratio > FACTION_SIZE_TAX_START:
                excess = size_ratio - FACTION_SIZE_TAX_START
                span = 1.0 - FACTION_SIZE_TAX_START
                tax = max(FACTION_SIZE_TAX_MIN, 1.0 - excess / span)
                score *= tax
            scored[fid] = DECAY * prev_scores.get(fid, 0.0) + score
        ranked = sorted(scored.items(), key=lambda kv: (-kv[1], kv[0]))
        new_scores[pid] = dict(ranked[:MAX_TRACKED_FACTIONS_PER_PERSONA])
    for pid, scores in new_scores.items():
        self.inners[pid].affiliation_scores = scores
```

**설계 이유**:
- tax를 `score` (이번 틱 가산)에만 적용 = 기존 소속자의 과거 축적 점수는 보존. 큰 faction이 기존 멤버를 즉시 잃지 않음.
- 분모는 `_faction_members_cache` (이미 1198행에서 rebuild). 추가 조회 비용 없음.
- size_ratio > FACTION_SIZE_TAX_START 조건은 초기 단계(faction 여럿, 각 점유 낮음)에서 tax가 작동하지 않도록 보호.

### C. Homeostasis 분기 (`core/multi_tick_engine.py`)

**수정 대상**: `_commit_faction_tick` (현 line 1224-1254)

**Before** (현재 line 1246-1252):
```python
else:
    if best_fid == cur_fid:
        continue
    current_score = scores.get(cur_fid, 0.0)
    gap = best_score - current_score
    dynamic_margin = max(DRIFT_MARGIN_MIN, gap * DRIFT_MARGIN_RATIO)
    if gap >= dynamic_margin:
        self._change_persona_faction(pid, best_fid, source="drift")
```

**After**:
```python
def _commit_faction_tick(self) -> None:
    """48틱마다 faction 가입/이적 commit."""
    if self.time.tick % FACTION_COMMIT_EVERY != 0:
        return
    # v6: homeostasis — active faction 수에 따라 margin_floor 조절
    active_count = sum(
        1 for fid in self.factions
        if len(self._faction_members_cache.get(fid, ())) > 0
    )
    margin_floor = (
        DRIFT_MARGIN_MIN * HOMEOSTASIS_DRIFT_MARGIN_SCALE
        if active_count <= HOMEOSTASIS_LOW_THRESHOLD
        else DRIFT_MARGIN_MIN
    )
    snapshot = {
        pid: (
            self.personas[pid].faction,
            self.personas[pid].faction_cooldown,
            dict(self.inners[pid].affiliation_scores),
        )
        for pid in self.personas
        if pid in self.inners
    }
    for pid in sorted(snapshot):
        cur_fid, cooldown, scores = snapshot[pid]
        if cooldown > 0 or not scores:
            continue
        sorted_items = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
        best_fid, best_score = sorted_items[0]
        if cur_fid is None:
            if best_score >= THETA_JOIN:
                self._change_persona_faction(pid, best_fid, source="affiliation")
        else:
            if best_fid == cur_fid:
                continue
            current_score = scores.get(cur_fid, 0.0)
            gap = best_score - current_score
            dynamic_margin = max(margin_floor, gap * DRIFT_MARGIN_RATIO)  # v6
            if gap >= dynamic_margin:
                self._change_persona_faction(pid, best_fid, source="drift")
    self._rebuild_faction_members_cache()
```

**수정 포인트**: `DRIFT_MARGIN_MIN` 리터럴 사용을 `margin_floor` 동적 변수로 교체. 타 로직 전부 불변.

**설계 이유**:
- active_count 계산 시점은 commit 직전 스냅샷 — 이번 commit에서 바뀔 수 있으나 `_rebuild_faction_members_cache()`가 끝에서 재계산.
- THETA_JOIN 경로(신규 가입)는 homeostasis 미적용 — 무소속자는 항상 `DRIFT_MARGIN_MIN * 0` = 영향 없음 (drift 경로만 수정).
- 복구 역학: collapse 발생(active=1) → margin_floor=0.15 → drift 이탈 쉬워짐 → 신규 faction 생성(founder 경로) 또는 기존 무소속자 가입으로 active 회복.

### D. Import 추가

`core/multi_tick_engine.py`의 layers import 구문에 다음 심볼 추가:
- `FACTION_SIZE_TAX_START`
- `FACTION_SIZE_TAX_MIN`
- `HOMEOSTASIS_LOW_THRESHOLD`
- `HOMEOSTASIS_DRIFT_MARGIN_SCALE`

`ontology/__init__.py`에도 동일하게 re-export 추가 (기존 v5 상수 export 패턴 따름).

### E. 수학적 회귀 테스트 (`test_phase17_faction_mitigation.py`)

```python
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
    """지시서 수식 재현."""
    if size_ratio <= FACTION_SIZE_TAX_START:
        return 1.0
    excess = size_ratio - FACTION_SIZE_TAX_START
    span = 1.0 - FACTION_SIZE_TAX_START
    return max(FACTION_SIZE_TAX_MIN, 1.0 - excess / span)


def test_phase17_size_tax_monotone_and_bounded() -> None:
    """tax는 [MIN, 1.0] 범위, size_ratio 증가에 대해 비증가."""
    ratios = [0.0, 0.1, FACTION_SIZE_TAX_START, 0.35, 0.5, 0.8, 1.0]
    taxes = [_size_tax(r) for r in ratios]
    for t in taxes:
        assert FACTION_SIZE_TAX_MIN <= t <= 1.0, f"범위 이탈: {t}"
    for a, b in zip(taxes, taxes[1:]):
        assert a >= b, f"비증가 위반: {a} → {b}"
    assert _size_tax(FACTION_SIZE_TAX_START) == 1.0, "경계값에서 tax=1.0 유지"
    assert _size_tax(1.0) == FACTION_SIZE_TAX_MIN, "점유 100%에서 tax=MIN 도달"


def test_phase17_homeostasis_margin_relaxed() -> None:
    """active ≤ THRESHOLD일 때 margin_floor는 DRIFT_MARGIN_MIN보다 작다."""
    relaxed = DRIFT_MARGIN_MIN * HOMEOSTASIS_DRIFT_MARGIN_SCALE
    assert 0 < relaxed < DRIFT_MARGIN_MIN, (
        f"homeostasis가 margin을 완화하지 못함: relaxed={relaxed}, min={DRIFT_MARGIN_MIN}"
    )
    assert HOMEOSTASIS_LOW_THRESHOLD >= 1


def test_phase17_tax_guards_startup_phase() -> None:
    """START 이하 점유에서는 tax가 작동하지 않아 초기 faction이 자라날 수 있음."""
    assert _size_tax(0.0) == 1.0
    assert _size_tax(FACTION_SIZE_TAX_START * 0.5) == 1.0
    assert _size_tax(FACTION_SIZE_TAX_START) == 1.0
```

---

## 변경 파일

| 파일 | 작업 | 유형 |
|------|------|:---:|
| `Projects/personas/loom/ontology/layers.py` | v6 상수 블록 추가 (line 214 뒤) | 수정 |
| `Projects/personas/loom/ontology/__init__.py` | 4개 상수 re-export | 수정 |
| `Projects/personas/loom/core/multi_tick_engine.py` | `_compute_affiliation_tick`·`_commit_faction_tick` 수정 + import | 수정 |
| `Projects/personas/loom/test_phase17_faction_mitigation.py` | 3 케이스 수학적 backstop | 추가 |
| `Projects/personas/loom/data/phase17_probe_v6/seed-{7,13,42}/` | probe 실행 산출물 | 생성 |
| `Projects/personas/loom/data/phase17_probe_v6/SUMMARY.md` | 3 seed 요약 | 생성 |

**변경 없음 (금지)**:
- `Projects/personas/loom/brain/**` (Phase 14-B 불변성)
- `Projects/personas/loom/core/snn_*.py`
- `Projects/personas/loom/core/multi_tick_engine.py`의 `_change_persona_faction`, `_rekey_*`, `_process_economy`, 경제·SNN 계열 메서드
- `layers.py`의 기존 상수 값 (DECAY, THETA_JOIN, W_*, DRIFT_MARGIN_MIN, RATIO 등 — **추가만** 허용)
- charter primitive 목록, CHARTER_PRIMITIVE_COUNT

---

## 검증

### 기계 검증 (필수)
```bash
cd Projects/personas/loom && py -m pytest test_phase17_faction_mitigation.py -q
cd Projects/personas/loom && py -m pytest test_phase17_faction_drift.py -q
cd Projects/personas/loom && py -m pytest test_phase17_faction_reincarnation_safety.py -q
cd Projects/personas/loom && py -m pytest test_phase14b_snn_integration.py -q
cd Projects/personas/loom && py -m pytest test_phase17_faction_emergence.py -q       # 존재 시
cd Projects/personas/loom && py -m pytest test_phase17_faction_api_guards.py -q      # 존재 시
```

**기대**: 31건 이상 PASS, 0건 FAIL.

### 기능 검증 (Acceptance) — v6 probe

```bash
cd Projects/personas/loom && py scripts/phase17_probe.py --seed 7 --ticks 5000 --out data/phase17_probe_v6/seed-7
cd Projects/personas/loom && py scripts/phase17_probe.py --seed 13 --ticks 5000 --out data/phase17_probe_v6/seed-13
cd Projects/personas/loom && py scripts/phase17_probe.py --seed 42 --ticks 5000 --out data/phase17_probe_v6/seed-42
```

**Acceptance (필수)**:
| 기준 | 임계 | 측정 | 근거 |
|------|------|------|------|
| Φ-2 창발 복구 | seed 3 중 **최소 1건**에서 active_factions_end ≥ 2 | SUMMARY.md 표 | v5 = 0/3 → v6 = ≥1/3 |
| Drift 유지 | seed 전원 drift_ratio ≥ 5% | v5 대비 기능 후퇴 방지 | Stage 1 성과 보존 |
| 가입 활발 | seed 전원 faction_change_events ≥ 20 | 이탈 장벽이 과도하게 낮아 모두 가입/이탈하지 않도록 | 동역학 건강성 |
| 경제 불변 | seed 전원 gini_end ≥ 0.4 | 경제 시스템 회귀 없음 | Phase 11 보호 |

**Acceptance (선택)**:
- 3 seed 전원 active_factions_end ≥ 2 (이상 케이스)
- 접촉 쌍 ≥ 1 at tick 5000 (Φ-3 진입 재료)

**실패 시 보고 형식** (부분 실패도 데이터):
```
seed 7: active_end=X, drift=Y%, events=Z
seed 13: ...
seed 42: ...
해석: <winner-takes-all 완화 정도 / 잔여 병리 / 다음 단계 제안>
```

### 계약 검증 (Phase 14-B)
- `test_phase14b_snn_integration.py` 8/8 PASS 유지 (readout 계약 불변)
- 이번 변경이 brain/** 미접촉 → 기본적으로 보장, but 테스트로 명시 확인

---

## Rollback

```bash
git diff HEAD -- Projects/personas/loom/ontology/layers.py | head -60   # v6 블록 위치 확인
git checkout HEAD -- Projects/personas/loom/ontology/layers.py \
                     Projects/personas/loom/ontology/__init__.py \
                     Projects/personas/loom/core/multi_tick_engine.py
rm Projects/personas/loom/test_phase17_faction_mitigation.py
rm -rf Projects/personas/loom/data/phase17_probe_v6
```

롤백 후 v5 상태(drift unlock + collapse)로 복귀. 데이터 손실 없음 (probe는 재실행 가능).

---

## 설계 근거 (이전 단계 발췌)

**Stage 1 결과 (PHASE-17-AFFILIATION-TUNE-SPEC.md 후속)**:
> W_TERRITORY 비대칭을 1.0/0.0 → 0.3/0.1로 완화하자 drift 경로가 열렸으나(drift_ratio 14-33%), 같은 완화가 winner-takes-all의 제동 장치도 함께 제거. trust/proximity positive feedback이 지배 → seed 3/3에서 active_factions=1 수렴.

**왜 size tax + homeostasis 병행인가**:
- size tax **단독**: 큰 faction의 흡수력만 약화. 이미 발생한 collapse는 복구 불가 (active=1에서 새 faction 생길 경로 없음).
- homeostasis **단독**: collapse 후 drift 장벽만 낮춤. 애초의 쏠림 자체는 방지 못함. 여전히 1→2→1 oscillation 가능.
- **병행**: 쏠림 진행 시 tax가 감속(예방), 그럼에도 collapse에 도달하면 homeostasis가 복구(치료) → 두 단계 방어.

---

## GPT/Codex 전달 프롬프트 템플릿

```
당신은 Personas/Loom 프로젝트의 시니어 백엔드 개발자입니다.

## 프로젝트 경로
c:\Users\haj\projects\subagent-orchestrator

## 기술 스택
- Python 3.12, numpy, pytest
- SNN(LIF) + Phase 11~17 경제/사회 시뮬레이터
- brain/** 수정 금지 (Phase 14-B readout 불변)

## 작업 지시서
Projects/personas/loom/PHASE-17-FACTION-COLLAPSE-MITIGATION-SPEC.md 파일을 그대로 따라 구현하세요.

## 규칙 (절대 준수)
1. [필수] 6항 100% 구현. [금지] 항목 절대 건드리지 말 것.
2. 지시서의 코드 블록은 "해석"하지 말고 직접 이식 (변수명·상수명·배치 순서 보존).
3. 검증 순서:
   a. py -m pytest test_phase17_faction_mitigation.py -q (신규)
   b. py -m pytest test_phase17_faction_drift.py test_phase17_faction_reincarnation_safety.py -q (Stage 1 회귀)
   c. py -m pytest test_phase14b_snn_integration.py -q (readout 불변)
   d. data/phase17_probe_v6/seed-{7,13,42} 실행 + SUMMARY.md 생성
   e. Acceptance 표 4개 기준 (필수) 전부 통과 여부 확인
4. 검증 실패 시 재작업. 단 Acceptance 부분 실패는 "이것이 알려주는 것:" 해석 동반해 보고 (임의 수정 금지).
5. 보고 내용:
   - 변경 파일 목록 + diff 요약
   - 각 검증 단계 PASS/FAIL 건수
   - v6 probe SUMMARY 표 인용
   - Acceptance 4개 기준 달성 여부 (YES/NO + 증거)
   - [선택] 항목 구현 여부
```
