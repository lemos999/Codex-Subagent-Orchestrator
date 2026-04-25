# [기능] Phase 17 Stage 3 — Anti-Collapse (B+C: Minority Persistence + Founder Respawn)

> 긴급도: 높음 (Stage 2 v6 3/3 seed FAIL)
> 선행 조건: Stage 1 (v5) + Stage 2 (v6) 머지됨 (commit `5217e39` 기준)
> 작업 유형: 기능 (백엔드 로직 추가, brain/** 무수정)
> DB migration: 없음
> 외부 의존: 없음 (numpy 기존)
> 사용자: Codex (gpt-5.5, reasoning_effort=xhigh)

---

## 배경

v6 probe (seed 7/13/42 × 5000 tick) 결과 drift_ratio가 v5 대비 3배 급증(14-33% → 42-55%)했음에도 **전원 active_factions_end=1** 수렴. drift/gini/faction_change 3개 acceptance는 PASS, `active_factions_end >= 2`만 FAIL (3/3).

**근본 원인 진단** (6엔진 /discuss 합의):
1. **Absorbing state**: faction 멤버=0이 되면 영구 소멸, 재탄생 경로 없음
2. **Size tax 복구 무력**: 우세 faction score 가산을 낮추나 열등 faction 멸종 후 복구 불가 (`s(t+1) = DECAY * s(t) → 0` for extinct faction)
3. **Homeostasis 시점 미스매치**: trigger `active <= 2`는 이미 작은 faction 소멸 후 발동 → 너무 늦음

**해결 방향** (6엔진 합의, `subagent-runs/discuss/phase17-stage3-anti-collapse-2026-04-24-quick/` 증거):
- **B (Minority persistence)**: 소규모 faction에 territory 기반 score boost로 **소멸 직전 저지**
- **C (Founder respawn)**: K틱마다 active<target 감지 시 territory lord 기반 **신규 faction 생성 → 소멸 후 복구**

B는 예방, C는 치료. Stage 2의 tax+homeostasis 구조(이탈 쉽게)가 "탈출" 축이었다면 Stage 3의 B+C는 "씨앗 유지" 축.

**기각된 후보**:
- A (Stage 2 임계값 상향) — Stage 1/2 상수 고정 조항 위반
- D (Territory 재결합) — charter primitive 3-5 위반, brain/** 인터페이스 전파 위험 (v7+ defer)
- E (Contact 유지 보정) — SNN readout 14-B 회귀 위험, 재검증 선행 필요
- F (Join/leave asymmetry) — 선택적 보완 (본 Stage에서는 제외)

---

## 작업 범위

### [필수]
1. `layers.py`에 Stage 3 상수 4개 추가 (Stage 1/2 상수 **미변경**)
2. `multi_tick_engine.py` `_compute_affiliation_tick`에 **B boost** 블록 추가 (기존 size tax 직후)
3. `multi_tick_engine.py`에 신규 메서드 `_respawn_faction_tick()` 추가 (**C respawn**)
4. 신규 메서드를 `tick()` 내 `_commit_faction_tick()` 직후에 호출
5. RNG는 반드시 `self._derive_rng("faction_respawn", territory_id, tick)` 사용 (재현성 격리)
6. 신규 faction 생성 시 반드시 `self._change_persona_faction(founder.id, fid, source="birth_founder")` SSoT 경로
7. 신규 테스트 파일 `test_phase17_faction_stage3.py` 추가 (단위 + 수식 backstop)
8. `observe_phase17_emergence.py` probe 재실행 (seed 7/13/42 × 5000 tick) + 결과 기록

### [선택]
- Acceptance secondary 지표 (`min_faction_size_p50`, `respawn_event_count`, `last_500_ticks active>=2 ratio`)를 probe에 추가 — primary만 PASS하면 선택 사항
- SNN readout 14-B 회귀 재검증 (8/8 PASS) — 본 Stage의 요구 검증이나 별도 commit 분리 가능

### [금지]
- **brain/** 디렉토리 수정** — Phase 14-B 계약 불변
- **Stage 1/2 상수 값 변경** — `W_TERRITORY_SAME/DIFF`, `W_TRUST/GRIEVANCE/PROXIMITY`, `DECAY`, `DRIFT_MARGIN_MIN/RATIO`, `FACTION_SIZE_TAX_START/MIN`, `HOMEOSTASIS_*` 모두 동결
- **SSoT 우회** — `persona.faction = X` 직접 대입 금지 (AST whitelist로 강제됨). 반드시 `_change_persona_faction` 경유
- **FactionChangeSource 추가** — `"birth_founder" | "affiliation" | "drift" | "conflict"` 4종 고정, 신규 source **금지** (e.g. "respawn" 같은 새 값 추가 **금지**, 반드시 "birth_founder" 재사용)
- **`np.random.default_rng(...)` 직접 호출** — grep guard로 차단됨. 반드시 `_derive_rng` 경유
- **`charter primitive 3-5` 범위 수정** — `CHARTER_PRIMITIVE_COUNT = (3, 5)` 동결
- **기존 `_init_founder_seeds()` 수정** — tick=0 초기화 경로, 재사용만 허용

---

## 구체 사양

### 1. 상수 추가 — `Projects/personas/loom/ontology/layers.py`

**삽입 위치**: line 222 뒤 (기존 Stage 2 상수 섹션 직후), line 224 "하위 호환" 섹션 앞.

**추가 코드**:
```python
# ── Phase 17 Stage 3: anti-collapse (minority persistence + founder respawn, 2026-04-24) ──
# 근거: v6 probe 3 seed 전원 active_end=1 수렴 (absorbing state). B+C 조합으로 예방+치료.
# B. Minority persistence: 소규모 faction에 territory 동거 가산 → 멸종 직전 저지
MINORITY_PERSISTENCE_MAX_MEMBERS = 2      # members <= 2일 때 boost 적용
MINORITY_PERSISTENCE_BOOST = 0.15         # score 가산값 (= DRIFT_MARGIN_MIN * HOMEOSTASIS_DRIFT_MARGIN_SCALE 와 동일 규모)
# C. Founder respawn: active < target일 때 K틱 주기로 territory lord 기반 신규 faction 생성
FOUNDER_RESPAWN_EVERY = 480               # FACTION_COMMIT_EVERY * 10 (48 * 10). commit 주기와 정합
FOUNDER_RESPAWN_TARGET_ACTIVE = 2         # active 수 2 미만일 때만 발동 (overspawn 방지)
```

**제약**:
- 위 4개 상수명을 **그대로** 사용 (테스트가 import하므로 이름 변경 금지)
- 값도 위 숫자 그대로 (튜닝은 후속 Stage에서)

---

### 2. B 구현 — `multi_tick_engine.py` `_compute_affiliation_tick`

**현재 코드** (line 1216-1229):
```python
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
```

**After — line 1228 (`score *= tax`) 직후, line 1229 (`scored[fid] = ...`) 앞에 신규 블록 삽입**:
```python
# Stage 3 B: minority persistence boost — size <= MAX_MEMBERS 이고 같은 territory 거주 멤버 있으면 가산
member_count = len(self._faction_members_cache.get(fid, ()))
if 0 < member_count <= MINORITY_PERSISTENCE_MAX_MEMBERS:
    if self._same_territory(persona, fid) > 0.5:
        score += MINORITY_PERSISTENCE_BOOST
```

**완성된 블록** (삽입 결과):
```python
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
# Stage 3 B: minority persistence boost (2026-04-24)
member_count = len(self._faction_members_cache.get(fid, ()))
if 0 < member_count <= MINORITY_PERSISTENCE_MAX_MEMBERS:
    if self._same_territory(persona, fid) > 0.5:
        score += MINORITY_PERSISTENCE_BOOST
scored[fid] = DECAY * prev_scores.get(fid, 0.0) + score
```

**주의사항**:
- `member_count > 0` 조건 필수 (멸종 faction은 boost 받지 않음 — C의 respawn 영역)
- `same_territory > 0.5`는 기존 `_same_territory` 메서드 반환값 (0.0 또는 1.0)
- boost는 가산 (`+=`), 곱셈(`*=`) 아님
- tax 이후 적용 (작은 faction에 대한 tax는 어차피 1.0이므로 순서 무관하나, 의미 명확성을 위해 tax 다음)

**상수 import 추가** (`multi_tick_engine.py` 상단 import 블록):
기존 layers import에 다음 4개 추가:
```python
MINORITY_PERSISTENCE_MAX_MEMBERS,
MINORITY_PERSISTENCE_BOOST,
FOUNDER_RESPAWN_EVERY,
FOUNDER_RESPAWN_TARGET_ACTIVE,
```

---

### 3. C 구현 — `multi_tick_engine.py` 신규 메서드

**삽입 위치**: `_commit_faction_tick()` 메서드 종료 후 (line 1275 직후), `_pick_founder` 메서드 앞.

**신규 메서드 코드**:
```python
def _respawn_faction_tick(self) -> None:
    """Stage 3 C: active faction 수가 TARGET 미만이면 K틱 주기로 territory lord 기반 신규 faction 생성.

    **Absorbing state 탈출 유일 경로**. 기존 `_init_founder_seeds`(tick=0)와 달리 매 K틱 검사.
    불변 제약:
        - RNG는 반드시 `_derive_rng("faction_respawn", ...)`로 격리 (기존 seed 스트림 오염 방지)
        - SSoT: `_change_persona_faction(..., source="birth_founder")` 재사용 (신규 source 금지)
        - 기존 territory의 lord를 founder로 재사용. lord 없으면 최고 trust persona.
    """
    if self.time.tick == 0:
        return
    if self.time.tick % FOUNDER_RESPAWN_EVERY != 0:
        return

    active_count = sum(
        1 for fid in self.factions
        if len(self._faction_members_cache.get(fid, ())) > 0
    )
    if active_count >= FOUNDER_RESPAWN_TARGET_ACTIVE:
        return

    # territory 우선순위: lord 존재 > faction 없는 거주자 수 많음 > sorted(id)
    territory_priority: list[tuple[int, int, str]] = []
    for territory in self.territories.values():
        free_residents = [
            persona for persona in self.personas.values()
            if persona.territory == territory.id
            and persona.faction is None
            and persona.id in self.inners
        ]
        if len(free_residents) < 3:
            continue
        has_lord = 1 if territory.lord_id else 0
        # 우선순위 키: lord 있음 우선(-has_lord), 거주자 많음 우선(-count), id 오름차순(territory.id)
        territory_priority.append((-has_lord, -len(free_residents), territory.id))

    territory_priority.sort()

    for _, _, territory_id in territory_priority:
        if active_count >= FOUNDER_RESPAWN_TARGET_ACTIVE:
            return  # 목표 달성 시 즉시 중단 (한 틱에 하나만 생성해도 target 도달하면 끝)
        territory = self.territories[territory_id]
        free_residents = [
            persona for persona in self.personas.values()
            if persona.territory == territory.id
            and persona.faction is None
            and persona.id in self.inners
        ]
        if len(free_residents) < 3:
            continue
        founder = self._pick_founder(free_residents, territory)
        if founder is None:
            continue
        charter = self._sample_charter(territory.id)
        # 격리된 RNG 스트림 사용 (기존 seed 결과 비호환 최소화)
        rng = self._derive_rng("faction_respawn", territory.id, self.time.tick)
        faction_id = uuid.UUID(bytes=rng.bytes(16)).hex
        faction_name = f"{territory.name}_R{self.time.tick}"
        faction = Faction(
            id=faction_id,
            name=faction_name,
            founder_pid=founder.id,
            charter=charter,
            created_tick=self.time.tick,
        )
        self.factions[faction.id] = faction
        self._change_persona_faction(founder.id, faction.id, source="birth_founder")
        active_count += 1

    self._rebuild_faction_members_cache()
```

**구현 주의사항**:
- `FOUNDER_RESPAWN_EVERY = 480`는 `FACTION_COMMIT_EVERY = 48`의 10배 — commit 10회 후 재검사
- `self.time.tick == 0` 가드: `_init_founder_seeds`와 충돌 방지
- `active_count` 재계산은 `_rebuild_faction_members_cache` 직후여야 정확. `_commit_faction_tick` 끝에서 cache가 갱신되므로 그 직후 호출.
- 한 틱에 **여러 territory에서 동시 respawn 가능** (극단적 흡수상태 탈출 보장). 단, `active_count >= TARGET` 달성 시 즉시 중단.
- `free_residents < 3` 필터: `_init_founder_seeds`와 동일 조건 — founder 1명이 고립되지 않도록
- `_pick_founder`, `_sample_charter` 재사용 — 독립 메서드 추가 금지

---

### 4. tick() 루프 통합 — `multi_tick_engine.py` line 2024

**현재 코드** (line 2024-2025):
```python
        self._commit_faction_tick()
        self._project_faction_tick()
```

**After**:
```python
        self._commit_faction_tick()
        self._respawn_faction_tick()  # Stage 3 C: absorbing state 탈출
        self._project_faction_tick()
```

**제약**:
- `_commit_faction_tick` **직후**, `_project_faction_tick` **직전**이어야 함. 이유:
  - commit이 cache를 갱신한 직후 active_count가 정확
  - project는 territoryRef를 갱신하므로 respawn으로 새 faction이 생겨도 다음 project에서 반영

---

### 5. 신규 테스트 — `Projects/personas/loom/test_phase17_faction_stage3.py`

**파일 내용**:
```python
"""Phase 17 Stage 3: anti-collapse (B+C) 수학적 backstop + 통합 behavior."""
from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from Projects.personas.loom.ontology.layers import (
    DRIFT_MARGIN_MIN,
    FACTION_COMMIT_EVERY,
    FOUNDER_RESPAWN_EVERY,
    FOUNDER_RESPAWN_TARGET_ACTIVE,
    HOMEOSTASIS_DRIFT_MARGIN_SCALE,
    HOMEOSTASIS_LOW_THRESHOLD,
    MINORITY_PERSISTENCE_BOOST,
    MINORITY_PERSISTENCE_MAX_MEMBERS,
)
from Projects.personas.loom.core.multi_tick_engine import MultiTickEngine


def test_stage3_minority_boost_constants_bounded() -> None:
    """MAX_MEMBERS는 HOMEOSTASIS_LOW_THRESHOLD와 정합. BOOST는 DRIFT_MARGIN과 동일 규모."""
    assert MINORITY_PERSISTENCE_MAX_MEMBERS == HOMEOSTASIS_LOW_THRESHOLD, (
        "boost 적용 범위는 homeostasis trigger 범위와 정합해야 한다"
    )
    assert 0 < MINORITY_PERSISTENCE_BOOST < 1.0, "boost는 score 스케일 내"
    # boost ≈ relaxed drift margin (0.15)
    relaxed = DRIFT_MARGIN_MIN * HOMEOSTASIS_DRIFT_MARGIN_SCALE
    assert abs(MINORITY_PERSISTENCE_BOOST - relaxed) < 1e-9, (
        f"boost={MINORITY_PERSISTENCE_BOOST}는 relaxed margin={relaxed}과 동일 규모여야 한다"
    )


def test_stage3_respawn_constants_sane() -> None:
    """respawn은 commit 주기의 정수배. target은 minimum active 수."""
    assert FOUNDER_RESPAWN_EVERY % FACTION_COMMIT_EVERY == 0, (
        f"respawn 주기는 commit 주기의 정수배: every={FOUNDER_RESPAWN_EVERY}, commit={FACTION_COMMIT_EVERY}"
    )
    assert FOUNDER_RESPAWN_EVERY >= FACTION_COMMIT_EVERY * 5, (
        "respawn 주기가 너무 빈번하면 churn 위험"
    )
    assert FOUNDER_RESPAWN_TARGET_ACTIVE >= 2, "목표 active 수는 최소 2 (다수 공존)"


def test_stage3_respawn_rng_determinism() -> None:
    """같은 seed → _derive_rng('faction_respawn', ...) 결과 동일."""
    engine1 = MultiTickEngine(seed=7)
    engine2 = MultiTickEngine(seed=7)
    rng1 = engine1._derive_rng("faction_respawn", "T0", 500)
    rng2 = engine2._derive_rng("faction_respawn", "T0", 500)
    a = rng1.bytes(16)
    b = rng2.bytes(16)
    assert a == b, "격리된 respawn RNG는 동일 seed에서 재현 가능해야 한다"


def test_stage3_respawn_rng_isolation() -> None:
    """다른 tag → 다른 RNG 스트림 (기존 seed 스트림과 격리)."""
    engine = MultiTickEngine(seed=7)
    rng_respawn = engine._derive_rng("faction_respawn", "T0", 500)
    rng_seed = engine._derive_rng("faction_seed", "T0")
    a = rng_respawn.bytes(16)
    b = rng_seed.bytes(16)
    assert a != b, "tag가 다르면 독립 스트림"


def test_stage3_respawn_skips_tick_zero() -> None:
    """tick=0에서는 _init_founder_seeds가 담당, respawn 발동 금지."""
    engine = MultiTickEngine(seed=7)
    # tick=0 상태에서 respawn 메서드 직접 호출 — no-op
    before = len(engine.factions)
    engine._respawn_faction_tick()
    after = len(engine.factions)
    assert before == after, "tick=0에서 respawn은 no-op"


def test_stage3_respawn_skips_when_active_sufficient() -> None:
    """active >= TARGET이면 respawn no-op."""
    engine = MultiTickEngine(seed=7)
    # 초기화 실행 → faction 생성
    # tick을 FOUNDER_RESPAWN_EVERY로 강제 이동
    # active_count 조작 불가능하면 integration 테스트에서 검증
    # 여기서는 함수가 early-return 분기 있음만 smoke check
    engine.time.tick = FOUNDER_RESPAWN_EVERY
    # 정상 호출로 예외 미발생 확인 (integration은 probe에서)
    engine._respawn_faction_tick()
```

**제약**:
- 통합 시뮬레이션 테스트 (실제 5000틱 실행)는 **포함하지 말 것** — `observe_phase17_emergence.py` probe가 그 역할
- 위 5개 테스트만 작성. 추가 테스트는 선택 사항
- `test_phase17_faction_mitigation.py`는 **수정 금지** (Stage 2 backstop 불변)

---

### 6. 기존 테스트 회귀 확인

다음 테스트는 **모두 통과** 유지 필수 (Stage 1/2 계약):
- `test_phase17_faction.py`
- `test_phase17_faction_drift.py`
- `test_phase17_faction_mitigation.py` (Stage 2 수식)
- `test_phase17_faction_regression.py`
- `test_phase17_faction_reincarnation_safety.py`
- `test_phase17_land.py`
- `test_phase17_acceptance.py`

만약 회귀 발생 시:
- B의 `member_count > 0` 가드가 제대로 동작하는지 확인
- C의 tick=0 가드가 제대로 동작하는지 확인
- C가 생성하는 신규 faction이 `_init_founder_seeds`의 가정을 깨지 않는지 확인
- 문제 지속 시 즉시 중단하고 사용자에게 보고

---

## 변경 파일

| 파일 | 작업 | 유형 |
|------|------|:---:|
| `Projects/personas/loom/ontology/layers.py` | 상수 4개 추가 (line 222 뒤) | 수정 |
| `Projects/personas/loom/core/multi_tick_engine.py` | B 블록 삽입 (_compute_affiliation_tick), C 메서드 신설 (_respawn_faction_tick), tick() 호출 추가, import 추가 | 수정 |
| `Projects/personas/loom/test_phase17_faction_stage3.py` | 신규 (5 테스트) | 추가 |

**변경 없음 (금지)**:
- `Projects/personas/loom/brain/**` (Phase 14-B 계약 절대 불변)
- `Projects/personas/loom/ontology/layers.py` — Stage 1/2 상수 (W_*, DRIFT_MARGIN_*, FACTION_SIZE_TAX_*, HOMEOSTASIS_*, CHARTER_PRIMITIVE_COUNT, NORM_PRIMITIVE_CATALOG)
- `Projects/personas/loom/core/multi_tick_engine.py` — `_change_persona_faction` 서명, `_init_founder_seeds`, `_commit_faction_tick` 본문 (호출 순서만 tick()에서 조정)
- 기존 Phase 17 테스트 파일 전부 (stage3 신규 파일만 추가)
- `observe_phase17_emergence.py` (기존 probe 그대로 재실행)

---

## 검증

### 기계 검증 (필수)
1. Python 구문 체크: `cd Projects/personas/loom && python -m py_compile core/multi_tick_engine.py ontology/layers.py test_phase17_faction_stage3.py`
2. 기존 테스트 회귀: `cd Projects/personas/loom && python -m pytest test_phase17_faction.py test_phase17_faction_drift.py test_phase17_faction_mitigation.py test_phase17_faction_regression.py test_phase17_faction_reincarnation_safety.py test_phase17_land.py test_phase17_acceptance.py -v`
3. Stage 3 신규 테스트: `cd Projects/personas/loom && python -m pytest test_phase17_faction_stage3.py -v` → **5/5 PASS**
4. AST guard 통과 (persona.faction 직접 대입 없음): 기존 guard가 detect하면 `noqa: PHASE17_FACTION_SSOT_WRITE` 없이 실패 → **발생 시 즉시 중단하고 원인 분석**

### 기능 검증 (필수, Acceptance)

**primary acceptance** (이 하나만 PASS하면 수렴 판정):
```bash
cd Projects/personas/loom && python observe_phase17_emergence.py --seeds 7,13,42 --ticks 5000
```

**기대 결과**:
- seed 7/13/42 중 **최소 2개 seed에서 `active_factions_end >= 2`** (Stage 2 v6: 0/3 → Stage 3 target: 2/3)
- drift_ratio >= 0.05 유지 (v6에서 이미 PASS)
- contact_pairs_end >= 1 유지 (v6에서 이미 PASS)
- gini_end > gini_500 유지 (v6에서 이미 PASS)

**secondary (선택, 보조 판정)**:
- `respawn_event_count <= 3 per 5000 tick per seed` — `event_log`에서 `source="birth_founder"` 중 `tick > 0` 건수로 계산 (C의 overspawn 방지 확인)
- `min_faction_size_p50 >= 2` — B의 작동 증거 (소멸 직전 저지 실제 발생)

### 계약 검증
- `event_log`에 `source="birth_founder"`의 tick > 0 이벤트가 최소 1건 존재 (C 발동 확인)
- `_change_persona_faction` 호출 수와 faction 생성 수가 1:1 대응 (SSoT 무결성)

---

## Rollback

### 코드 롤백
```bash
git revert <stage3_commit_hash>
```

### 데이터/상태 롤백
- RNG 격리 (`"faction_respawn"` tag) 덕분에 **기존 seed 7/13/42 probe 결과 재현성은 유지됨**: Stage 3 코드가 없는 상태에서도 v6 결과와 동일 (respawn RNG를 소비하지 않음)
- 단, Stage 3 적용 후 발생한 event_log/probe 결과는 해당 run 전용

### 실패 시 fallback 경로
- **단위 테스트만 실패, probe PASS**: 테스트 코드 버그 — Stage 3 원복 말고 테스트 수정
- **단위 테스트 PASS, probe FAIL (여전히 1/3)**: B만 유효하고 C 미발동 가능성. `_respawn_faction_tick` 호출 순서·조건 재확인
- **단위 PASS, probe FAIL (0/3)**: RNG 격리 미작동으로 기존 seed 경로 오염 의심 → Stage 3 전체 원복 후 /discuss 재소집

---

## 구현자 체크리스트 (Codex 보고 시 필수)

- [ ] `layers.py`에 상수 4개 추가 완료, Stage 1/2 상수 1자도 변경 없음 (`git diff`로 확인)
- [ ] `multi_tick_engine.py` import에 4개 상수 추가
- [ ] `_compute_affiliation_tick`에 B boost 블록 삽입 완료
- [ ] `_respawn_faction_tick` 신규 메서드 추가, `tick()`에서 올바른 위치에서 호출
- [ ] `test_phase17_faction_stage3.py` 5/5 PASS
- [ ] 기존 Phase 17 테스트 전부 PASS (회귀 없음)
- [ ] `observe_phase17_emergence.py --seeds 7,13,42 --ticks 5000` 실행 완료
- [ ] probe 결과 표 (seed별 active_factions_end, drift_ratio, gini, verdict) 보고
- [ ] primary acceptance (2/3 seed active>=2) PASS 여부 명시
- [ ] secondary 지표 (respawn event count, 발동 tick 목록) 보고
- [ ] brain/** 변경 없음 확인 (`git diff --stat | grep brain` 결과 공백)

---

## GPT/Codex 전달 프롬프트 템플릿

```
당신은 loom (persona life simulator)의 시니어 파이썬 개발자입니다.

## 프로젝트 경로
c:/Users/haj/projects/subagent-orchestrator (Windows), Projects/personas/loom이 대상 디렉토리

## 작업 지시서
Projects/personas/loom/PHASE-17-STAGE3-ANTI-COLLAPSE-SPEC.md 파일을 그대로 따라 구현하세요.

## 선행 학습 (필수)
1. `Projects/personas/loom/PHASE-17-FACTION-COLLAPSE-MITIGATION-SPEC.md` (Stage 2 v6 스펙)
2. `Projects/personas/loom/ontology/layers.py` line 210-238 (Stage 1/2 상수 구조)
3. `Projects/personas/loom/core/multi_tick_engine.py`:
   - line 1044-1081 (_change_persona_faction SSoT)
   - line 1198-1275 (_compute_affiliation_tick, _commit_faction_tick)
   - line 1277-1323 (_pick_founder, _sample_charter, _init_founder_seeds)
   - line 1552-1577 (_derive_rng)

## 규칙 (절대 준수)
1. 지시서의 [필수] 항목 100% 구현. [금지] 항목 절대 건드리지 말 것.
2. Stage 1/2 상수 단 하나도 수정 금지 (값 확인: layers.py line 197-226)
3. brain/** 디렉토리 변경 금지 (Phase 14-B 계약)
4. FactionChangeSource에 신규 값 추가 금지 (4종 고정)
5. `np.random.default_rng(...)` 직접 호출 금지, 반드시 `self._derive_rng(...)` 경유
6. 지시서에 포함된 코드 블록은 복사해서 반영. "해석" 금지.

## 검증 순서
a. `cd Projects/personas/loom && python -m py_compile core/multi_tick_engine.py ontology/layers.py test_phase17_faction_stage3.py`
b. `python -m pytest test_phase17_faction*.py test_phase17_land.py test_phase17_acceptance.py -v` → 모두 PASS
c. `python observe_phase17_emergence.py --seeds 7,13,42 --ticks 5000` → 결과 저장
d. 결과 테이블에서 active_factions_end >= 2 인 seed 수 확인

검증 실패 시 재작업, 통과할 때까지 반복.

## 보고 내용
- 변경 파일 목록 (git diff --stat)
- 각 검증 단계 통과 여부
- probe 결과 표 (seed × (active_end, drift_ratio, contact_pairs, gini, verdict))
- primary acceptance (seed 중 몇 개가 active>=2 달성) 명시
- respawn 발동 이력 (tick 목록, 총 건수)
- brain/** 무변경 확인
- [필수] 항목 전체 이행 여부 + [선택] 항목 구현 여부
```
