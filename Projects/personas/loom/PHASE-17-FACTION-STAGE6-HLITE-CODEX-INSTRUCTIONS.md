# [기능] Phase 17 Φ-2 Stage 6 — H-lite founder_lineage identity affinity

> 긴급도: 중간  
> 선행 조건: Phase 17 Stage 5 anti-collapse (I+G+D-observe) 완료, last_500_active 3/3 PASS  
> 작업 유형: 기능 (백엔드 — 시뮬레이션 로직)  
> DB migration: 없음  
> 외부 의존: 없음

---

## 배경

Stage 5(I+G)로 collapse가 차단됐고 `last_500_active >= 2` 3/3 PASS. 다음 단계는 founder 계보  
identity affinity(H-lite)로 faction 다양성을 **자발적으로 유지**하는 것이다. 동일 창설자 계보를  
공유하는 faction에 대한 소속 점수를 보정해 drift 방향성에 계보 선호를 반영한다.

근거 문서: `PHASE-17-FACTION-STAGE6-HLITE-MAPPING.md` (4종 매핑 증명 완료)

---

## 작업 범위

### [필수]
1. `layers.py`: `Faction.founder_lineage: tuple[str, ...]` 필드 추가 (slots=True 호환)
2. `layers.py`: `W_LINEAGE = 0.2` 상수 추가 (Phase 17 Stage 6 블록)
3. `multi_tick_engine.py`: `_compute_affiliation_tick`에 lineage_overlap W_LINEAGE 가산
4. `multi_tick_engine.py`: `_init_founder_seeds` 생성 시 `founder_lineage=(founder.id,)` 설정
5. `multi_tick_engine.py`: `_respawn_faction_tick` 1차+2차 Faction 생성 시 `founder_lineage=(founder.id,)` 설정
6. `multi_tick_engine.py`: `W_LINEAGE` import 추가
7. `ontology/__init__.py`: `W_LINEAGE` export 추가
8. 회귀 검증: `py test_phase17_acceptance.py` 통과 + `py observe_phase17_emergence.py` seed 7/13/42 5000틱 `active_factions_end >= 2` 3/3 PASS

### [선택]
- W_LINEAGE 값 조정 (0.1~0.3 범위에서 실험 가능)

### [금지]
- `_change_persona_faction` 시그니처·로직 수정
- `FactionChangeSource` Literal 변경 (4종 그대로: birth_founder/affiliation/drift/conflict)
- AST whitelist 마커 `# noqa: PHASE17_FACTION_SSOT_WRITE` 5건 제거/이동
- `Faction.grace_until_tick` (Stage 5) 수정
- `InnerWorld.residence_ticks` (Stage 5 D) 수정
- SNN 뉴런 300~349 구간 변경
- D10 채널 추가 (5채널 고정)
- `test_class_promotion.py`, `test_nomos.py`, `test_economy.py` 수정

---

## 구체 사양

### 1. `layers.py` — Faction.founder_lineage 필드

**현재 코드 (layers.py:167~183):**

```python
@dataclass(slots=True)
class Faction:
    """Phase 17 faction registry entry."""
    id: str
    name: str
    founder_pid: str
    charter: tuple[str, ...]
    created_tick: int
    grace_until_tick: int = 0

    def __post_init__(self) -> None:
        charter = tuple(self.charter)
        if not (3 <= len(charter) <= 5):
            raise ValueError(f"charter length {len(charter)} out of [3, 5]")
        if len(set(charter)) != len(charter):
            raise ValueError(f"charter has duplicates: {charter!r}")
        self.charter = charter
```

**변경 후 (`grace_until_tick: int = 0` 바로 뒤에 1줄 추가):**

```python
@dataclass(slots=True)
class Faction:
    """Phase 17 faction registry entry."""
    id: str
    name: str
    founder_pid: str
    charter: tuple[str, ...]
    created_tick: int
    grace_until_tick: int = 0
    founder_lineage: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        charter = tuple(self.charter)
        if not (3 <= len(charter) <= 5):
            raise ValueError(f"charter length {len(charter)} out of [3, 5]")
        if len(set(charter)) != len(charter):
            raise ValueError(f"charter has duplicates: {charter!r}")
        self.charter = charter
```

> `field(default_factory=tuple)`은 slots=True 호환. `field`는 이미 import됨.

---

### 2. `layers.py` — W_LINEAGE 상수

**삽입 위치:** `RESPAWN_GRACE_TICKS = 200` (L237) 바로 다음 줄.

```python
# ── Phase 17 Stage 6: H-lite founder lineage affinity (2026-04-26) ──
# founder_lineage 공유 faction에 대한 소속 점수 가산. FactionChangeSource 4종 불변.
W_LINEAGE = 0.2   # W_TRUST/W_TERRITORY_SAME(0.5)의 40% 수준
```

---

### 3. `multi_tick_engine.py` — W_LINEAGE import

**현재 import 블록 (L60~66 근처, W_TRUST, W_TERRITORY_SAME 등 import 줄):**

```python
from ontology import (
    ...
    W_TRUST,
    W_TERRITORY_SAME, W_TERRITORY_DIFF,
    W_GRIEVANCE, W_PROXIMITY, DECAY,
    RESPAWN_GRACE_TICKS,
    ...
)
```

**변경 후 (`RESPAWN_GRACE_TICKS` 바로 뒤에 W_LINEAGE 추가):**

```python
from ontology import (
    ...
    W_TRUST,
    W_TERRITORY_SAME, W_TERRITORY_DIFF,
    W_GRIEVANCE, W_PROXIMITY, DECAY,
    RESPAWN_GRACE_TICKS,
    W_LINEAGE,
    ...
)
```

> 단일 import 줄에 있으면 같은 줄에 `, W_LINEAGE` 추가해도 됨. 정확한 라인은 직접 확인.

---

### 4. `multi_tick_engine.py` — `_compute_affiliation_tick` lineage_overlap 가산

**현재 코드 (L1239, `scored[fid] = ...` 줄):**

```python
                # Stage 3 B: minority persistence boost (2026-04-24)
                member_count = len(self._faction_members_cache.get(fid, ()))
                if 0 < member_count <= MINORITY_PERSISTENCE_MAX_MEMBERS:
                    if self._same_territory(persona, fid) > 0.5:
                        score += MINORITY_PERSISTENCE_BOOST
                scored[fid] = DECAY * prev_scores.get(fid, 0.0) + score
```

**변경 후 (`scored[fid] = ...` 바로 앞에 블록 삽입):**

```python
                # Stage 3 B: minority persistence boost (2026-04-24)
                member_count = len(self._faction_members_cache.get(fid, ()))
                if 0 < member_count <= MINORITY_PERSISTENCE_MAX_MEMBERS:
                    if self._same_territory(persona, fid) > 0.5:
                        score += MINORITY_PERSISTENCE_BOOST
                # Stage 6 H-lite: founder lineage identity affinity (2026-04-26)
                if W_LINEAGE > 0 and persona.faction:
                    cur_faction = self.factions.get(persona.faction)
                    cand_faction = self.factions.get(fid)
                    if cur_faction and cand_faction:
                        lineage_a = set(cur_faction.founder_lineage) | {cur_faction.founder_pid}
                        lineage_b = set(cand_faction.founder_lineage) | {cand_faction.founder_pid}
                        overlap = len(lineage_a & lineage_b) / max(len(lineage_a), len(lineage_b), 1)
                        score += W_LINEAGE * overlap
                scored[fid] = DECAY * prev_scores.get(fid, 0.0) + score
```

**의미:** `lineage_a`와 `lineage_b`는 각각 현재 소속 faction과 후보 faction의 founder_pid 집합.  
교집합 비율만큼 score 가산 → 같은 창설자 계보 faction에 대한 친밀도 상승.  
`persona.faction`이 None(미소속)이면 lineage affinity 미적용 (신규 가입은 affiliation 경로로만).

---

### 5. `multi_tick_engine.py` — `_init_founder_seeds` founder_lineage 초기화

**현재 코드 (L1451~1458, Faction 생성 부분):**

```python
            faction = Faction(
                id=faction_id,
                name=f"{territory.name}_F1",
                founder_pid=founder.id,
                charter=charter,
                created_tick=0,
            )
```

**변경 후 (`founder_lineage` 필드 추가):**

```python
            faction = Faction(
                id=faction_id,
                name=f"{territory.name}_F1",
                founder_pid=founder.id,
                charter=charter,
                created_tick=0,
                founder_lineage=(founder.id,),
            )
```

---

### 6. `multi_tick_engine.py` — `_respawn_faction_tick` 1차 Faction 생성 시 founder_lineage

**현재 코드 (L1348~1354, 1차 respawn Faction 생성):**

```python
            faction = Faction(
                id=faction_id,
                name=faction_name,
                founder_pid=founder.id,
                charter=charter,
                created_tick=self.time.tick,
                grace_until_tick=self.time.tick + RESPAWN_GRACE_TICKS,
            )
```

**변경 후:**

```python
            faction = Faction(
                id=faction_id,
                name=faction_name,
                founder_pid=founder.id,
                charter=charter,
                created_tick=self.time.tick,
                grace_until_tick=self.time.tick + RESPAWN_GRACE_TICKS,
                founder_lineage=(founder.id,),
            )
```

---

### 7. `multi_tick_engine.py` — `_respawn_faction_tick` 2차(fallback) Faction 생성 시 founder_lineage

**현재 코드 (L1399~1405, 2차 fallback Faction 생성):**

```python
            faction = Faction(
                id=faction_id,
                name=faction_name,
                founder_pid=founder.id,
                charter=charter,
                created_tick=self.time.tick,
                grace_until_tick=self.time.tick + RESPAWN_GRACE_TICKS,
            )
```

**변경 후:**

```python
            faction = Faction(
                id=faction_id,
                name=faction_name,
                founder_pid=founder.id,
                charter=charter,
                created_tick=self.time.tick,
                grace_until_tick=self.time.tick + RESPAWN_GRACE_TICKS,
                founder_lineage=(founder.id,),
            )
```

---

### 8. `ontology/__init__.py` — W_LINEAGE export

**현재 코드 (L5, L47 근처, W_TRUST 등 export 줄):**

```python
    W_TERRITORY, W_TERRITORY_SAME, W_TERRITORY_DIFF, W_TRUST, W_GRIEVANCE, W_PROXIMITY, DECAY,
```

```python
    "W_TERRITORY", "W_TERRITORY_SAME", "W_TERRITORY_DIFF", "W_TRUST", "W_GRIEVANCE", "W_PROXIMITY", "DECAY",
```

**변경 후 (W_LINEAGE를 각각 추가):**

```python
    W_TERRITORY, W_TERRITORY_SAME, W_TERRITORY_DIFF, W_TRUST, W_GRIEVANCE, W_PROXIMITY, DECAY,
    W_LINEAGE,
```

```python
    "W_TERRITORY", "W_TERRITORY_SAME", "W_TERRITORY_DIFF", "W_TRUST", "W_GRIEVANCE", "W_PROXIMITY", "DECAY",
    "W_LINEAGE",
```

---

## 변경 파일

| 파일 | 작업 | 유형 |
|------|------|:---:|
| `Projects/personas/loom/ontology/layers.py` | Faction.founder_lineage 필드 + W_LINEAGE 상수 | 수정 |
| `Projects/personas/loom/core/multi_tick_engine.py` | lineage_overlap 가산 + 3곳 Faction 생성 시 founder_lineage 설정 | 수정 |
| `Projects/personas/loom/ontology/__init__.py` | W_LINEAGE export 추가 | 수정 |

**변경 없음 (금지):**
- `Projects/personas/loom/core/multi_tick_engine.py` 내 `_change_persona_faction` 함수 본체
- `Projects/personas/loom/core/multi_tick_engine.py:88` FactionChangeSource Literal
- AST 마커 `# noqa: PHASE17_FACTION_SSOT_WRITE` 5건
- `test_class_promotion.py`, `test_nomos.py`, `test_economy.py`
- `data/phase17_probe_stage5/` 이하 모든 파일

---

## 에러 케이스 및 경계 조건

| 상황 | 처리 | 비고 |
|------|------|------|
| `persona.faction = None` (미소속) | lineage_overlap 블록 진입 안 함 (`if persona.faction` 가드) | 미소속은 affiliation 경로로만 |
| `self.factions.get(fid)` None (faction 삭제된 경우) | `if cur_faction and cand_faction` 가드로 skip | 레이스 컨디션 방어 |
| `founder_lineage = ()` (기존 Faction 객체, default) | `lineage_a = set() | {founder_pid}` → `{founder_pid}` | 이전 코드 하위 호환 유지 |
| W_LINEAGE = 0.0 | 블록 진입 안 함 | 완전 비활성화 가능 |
| 두 faction 모두 `founder_lineage = ()` | `lineage_a = {a_founder_pid}`, `lineage_b = {b_founder_pid}` | 창설자 달라도 계산 안정 |

---

## 검증

### 기계 검증

```bash
# Python type check
py -m mypy Projects/personas/loom/ontology/layers.py Projects/personas/loom/core/multi_tick_engine.py --ignore-missing-imports

# Ruff lint
py -m ruff check Projects/personas/loom/ontology/ Projects/personas/loom/core/
```

### 기능 검증 (필수)

**Step 1 — Stage 5 회귀 없음 확인:**

```bash
py Projects/personas/loom/test_phase17_acceptance.py
```

기대 출력:
```
[PASS] stable_perf_median_p95
[PASS] faction_kernel_0_960
[PASS] seed42_perf_line
[PASS] five_channel_determinism
```

`five_channel_determinism` FAIL → `founder_lineage` field_factory 문제. `field(default_factory=tuple)` 확인.

**Step 2 — Stage 6 acceptance probe:**

```bash
py Projects/personas/loom/observe_phase17_emergence.py --seed 7 --ticks 5000
py Projects/personas/loom/observe_phase17_emergence.py --seed 13 --ticks 5000
py Projects/personas/loom/observe_phase17_emergence.py --seed 42 --ticks 5000
```

결과를 `data/phase17_probe_stage6/` 디렉토리에 저장.

**Stage 6 Primary Acceptance 기준:**

| seed | 기준 | 필수 |
|:----:|------|:----:|
| 7 | `active_factions_end >= 2` | PASS |
| 13 | `active_factions_end >= 2` | PASS |
| 42 | `active_factions_end >= 2` | PASS |

3/3 미통과 시 Stage 6 FAIL.

**Step 3 — 기존 회귀 테스트:**

```bash
# Phase 14 (계급 승급) — 환생 페르소나 KeyError 수정됨. exit 0 확인
rtk proxy "py Projects/personas/loom/test_class_promotion.py"

# Phase 13 (Nomos)
py Projects/personas/loom/test_nomos.py

# Phase 11 (경제)
py Projects/personas/loom/test_economy.py
```

**Step 4 — Charter v2 무파괴 grep 검증:**

```bash
# AST 마커 5건 그대로인지 확인
grep -c "PHASE17_FACTION_SSOT_WRITE" Projects/personas/loom/core/multi_tick_engine.py
# 기대: 5

# FactionChangeSource 정의 무수정
grep "FactionChangeSource" Projects/personas/loom/core/multi_tick_engine.py
# 기대: Literal["birth_founder", "affiliation", "drift", "conflict"] 그대로

# W_LINEAGE 상수 존재 확인
grep "W_LINEAGE" Projects/personas/loom/ontology/layers.py
# 기대: W_LINEAGE = 0.2 1건
```

---

## 추가 관찰 지표 (보고 시 포함)

Stage 6 probe 완료 후 다음 지표를 비교표로 보고:

| 지표 | Stage 5 기준값 | Stage 6 측정값 |
|------|:---:|:---:|
| `active_factions_end` seed 7 | 3 | ? |
| `active_factions_end` seed 13 | 3 | ? |
| `active_factions_end` seed 42 | 3 | ? |
| `drift_ratio` seed 7 | 61% | ? |
| `drift_ratio` seed 13 | 17% | ? |
| `drift_ratio` seed 42 | 26% | ? |
| `gini_mean_end` seed 7 | 0.54 | ? |
| `gini_mean_end` seed 13 | 0.53 | ? |
| `gini_mean_end` seed 42 | 0.46 | ? |

drift_ratio 변화 방향: H-lite 도입 후 affiliation 비율 증가, drift 비율 감소 예상.

---

## Rollback

`layers.py` + `multi_tick_engine.py` + `__init__.py` 변경이 **동일 커밋**에 있으면:

```bash
git revert HEAD --no-edit
```

**데이터 영향 없음.** 시뮬 상태 변경 없음. 기존 `data/phase17_probe_stage5/` 손상 없음.  
Stage 6 probe 결과(`data/phase17_probe_stage6/`)만 재실행 필요.
