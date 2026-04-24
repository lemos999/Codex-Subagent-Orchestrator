# Phase 17 Φ-2 Faction — Engine SSoT 회복 지시서 (Cache/Identity 결함 수정)

> 긴급도: **높음** (Φ-3 진입 사전 차단 조건)
> 선행 조건: Phase 17 Φ-2 Faction 구현 완료 + Emergence Probe 실행 결과 확인
> 작업 유형: 버그 수정 (root cause) + 회귀 테스트 추가
> DB migration: 없음
> 외부 의존: 없음

---

## 0. 목표 3계층 (loom 불변 원칙)

- **궁극 목적**: 페르소나의 삶 → 유대 → 갈등 → 주권 선언으로 국가 자연 탄생
- **Phase 17 목적**: Φ-1 Land → **Φ-2 Faction** → Φ-3 Struggle → Φ-4 Nation
- **현재 작업의 고유 역할**: Φ-2 Faction API가 "리인카네이션 경로를 거쳐도 안정적으로 Φ-3 재료를 내놓을 수 있는가"를 보장. 관측 스크립트의 fallback(`_safe_grievance_targets`)을 **제거 가능**하게 만들고, 진짜 창발 데이터(gini, contact, shared_pairs)를 stale 오염 없이 수집하도록 엔진 자체의 SSoT를 회복.

---

## 1. 배경 — 근본 원인 2가지

### 결함 A. 리인카네이션 identity 불일치 (ROOT CAUSE)

`MultiTickEngine._process_death_and_reincarnation` ([multi_tick_engine.py:4600-4685](Projects/personas/loom/core/multi_tick_engine.py#L4600-L4685))에서:

```python
new_pid = ...                                      # 새 id 발급
new_persona = Persona(id=new_pid, ...)             # 객체의 id = new_pid
new_inner = InnerWorld(persona_id=new_pid)
...
self.personas[pid] = new_persona                   # dict key = old pid
self.inners[pid] = new_inner                       # dict key = old pid
```

→ **dict key는 old pid, 객체 내부 id는 new_pid**로 **영구 불일치**.

파급:
- `_rebuild_faction_members_cache` ([:1086-1095](Projects/personas/loom/core/multi_tick_engine.py#L1086-L1095))가 `for pid in sorted(self.personas)` 순회 후 `persona = self.personas[pid]`로 **객체 취득** → cache에 new_persona (id=new_pid) 저장
- `faction_grievance_targets` ([:1463-1464](Projects/personas/loom/core/multi_tick_engine.py#L1463-L1464))의 `inner = self.inners[member.id]` 조회 → `self.inners[new_pid]` 접근 → **KeyError** (inners의 key는 여전히 old pid)

### 결함 B. faction_* API 가드 불균일

같은 위험에 대해 API별 방어 수준이 다름:
- `faction_wealth_distribution` ([:1415](Projects/personas/loom/core/multi_tick_engine.py#L1415)): `if m.id in self.wallets` **있음**
- `faction_grievance_targets` ([:1464](Projects/personas/loom/core/multi_tick_engine.py#L1464)): 가드 **없음** → 위 KeyError 경로
- `faction_social_matrix` ([:1448](Projects/personas/loom/core/multi_tick_engine.py#L1448)): trust 내부에서 간접 접근, 결과 미정
- `_faction_members_cache`가 stale Persona 객체를 담는 동안 가드 없는 API는 즉시 crash

### 관측 증거
- Probe seed 13: tick 2500 gini 0.41 → tick 5000 gini 0.00 (reincarnation 시 faction 필드 미전승 → 멤버 풀림 → wealth 총합 0)
- Probe seed 42: contact 1 → 0 (territory 상실 + reincarnation 결합)
- 3 seed 모두 `_safe_grievance_targets` fallback 경로 사용 추정 (KeyError 빈발)

---

## 2. 작업 범위

### [필수]
1. **결함 A 수정** — reincarnation에서 dict key를 new_pid로 rekey (또는 동등한 identity 복구)
2. **결함 B 수정** — faction_* 조회 API 전체에 `if member.id not in self.inners: continue` 가드 균일 적용
3. **invalidation 훅** — reincarnation 완료 시 `self._faction_members_cache = {}` 호출 (다음 틱 rebuild 강제)
4. **회귀 테스트** — `test_phase17_faction_reincarnation_safety` 1건 신규 (리인카네이션 직후 faction API 6종 전체 호출 무오류)
5. **probe fallback 제거 검증** — 수정 후 `observe_phase17_emergence.py` 실행 시 `_safe_grievance_targets`의 `except KeyError` 경로가 **단 한 번도 진입하지 않음**을 확인 (stderr/로그 플래그 추가)

### [선택]
- `_on_persona_lifecycle_change(pid, event)` 헬퍼로 invalidation 훅 중앙화 (코드 정돈, 기능 동일)
- reincarnation 시 **faction 계승 여부** 정책 결정 — 본 지시서는 **기본값 "소속 해제"** (new_persona.faction=None)으로 고정. 계승 정책은 /discuss 별도 주제

### [금지]
- `affiliation_score` 계산 로직 변경 (`_compute_affiliation_tick`, `_same_territory`, `_trust_density`, `_shared_grievance`, `_spatial_proximity`, 상수 W_* / DECAY / DRIFT_MARGIN / THETA_JOIN) — **이는 /discuss 별도 주제**
- `brain/**`, `readout_weights_v1.npy` 수정
- Phase 14-B 경제 readout 관련 경로 변경
- `Persona`/`InnerWorld` dataclass 시그니처 변경
- 기존 reincarnation의 **의미론**(성격 70% 전승, 기억 소실 등) 변경 — 키 정합성만 고침
- 기존 faction_* API의 **반환 shape** 변경

---

## 3. 구체 사양

### 3.1 결함 A 수정 — 두 가지 옵션 중 **옵션 1 (Rekey)** 선택

#### 옵션 1 (권장, 의미 보존): dict key를 new_pid로 rekey

[multi_tick_engine.py:4661-4672](Projects/personas/loom/core/multi_tick_engine.py#L4661-L4672) 블록을 다음과 같이 교체:

**Before:**
```python
# 기존 대체
self.personas[pid] = new_persona
self.inners[pid] = new_inner
self._work_reward_history[pid] = []

# ── food_knowledge 70% 이식 ──
self._inherit_food_knowledge(new_pid, old_inner)

# ── 태생 지역 초기 지식 추가 ──
self._init_regional_food_knowledge(pid)
self.brains[pid] = new_brain
```

**After:**
```python
# ── identity rekey: pid → new_pid ──────────────────────
# 관계망은 old pid 기준으로 생성되었으므로 유지 (비밀 처리와 동일 패턴)
# dict key를 new_pid로 이전. 동일 dict의 기존 old pid 항목은 삭제.
# ───────────────────────────────────────────────────────
del self.personas[pid]
del self.inners[pid]
if pid in self.brains:
    del self.brains[pid]
if pid in self._work_reward_history:
    del self._work_reward_history[pid]

self.personas[new_pid] = new_persona
self.inners[new_pid] = new_inner
self.brains[new_pid] = new_brain
self._work_reward_history[new_pid] = []

# faction cache invalidate (다음 _rebuild에서 stale Persona 제거)
self._faction_members_cache = {}

# ── food_knowledge 70% 이식 ──
self._inherit_food_knowledge(new_pid, old_inner)

# ── 태생 지역 초기 지식 추가 ──
self._init_regional_food_knowledge(new_pid)

# 비밀은 소실 — known_by만 신 id로 치환
if pid in self.secrets:
    self.secrets[pid].known_by = {new_pid}
    self.secrets[pid].revealed_tick = None
    # secrets dict 자체의 key는 secret_id 또는 pid인지 구현 확인 후 동일 패턴 처리
    if pid in self.secrets:
        self.secrets[new_pid] = self.secrets.pop(pid)
```

**주의**:
- 기존 코드의 `self._init_regional_food_knowledge(pid)`는 **old pid 사용 — 아마 버그** (new_pid여야 자연). rekey하면서 new_pid로 정정. 기존 동작이 의도된 것인지 확인 후 조치.
- `self.secrets` 처리는 기존 코드가 `self.secrets[pid].known_by = {new_pid}`만 수정하고 dict key는 안 바꿨음. rekey 동일 패턴 적용이 일관적이지만, 다른 경로에서 `self.secrets[pid]` 조회하는 코드 있으면 영향. **grep으로 확인 후 반영**.
- 관계 dict (`self.relationships`)의 key는 `Relationship(persona_a=X, persona_b=Y).key()` 기반. reincarnation 시 관계 유지 정책이면 **relationship key rewriting이 필요**. 이번 지시서에서는 **보류** — 대신 faction API가 inners 존재 여부로 안전 가드 (§3.2) 수행.

#### 옵션 1 체크리스트
- [ ] `self.personas`, `self.inners`, `self.brains`, `self._work_reward_history` 모두 rekey
- [ ] `self._faction_members_cache = {}` 호출
- [ ] `self.secrets` rekey 동반 (grep으로 확인)
- [ ] 기존 `_init_regional_food_knowledge(pid)` → `_init_regional_food_knowledge(new_pid)` 정정
- [ ] 관계(`self.relationships`)는 본 지시서 범위 외. 리인카네이션 후에도 old pid 기반 relationship key가 남아 있을 수 있음 — faction API는 §3.2 가드로 방어
- [ ] reincarnation 전후 `len(self.personas)` 불변 확인 (pop 후 set이므로 동일)

### 3.2 결함 B 수정 — faction_* 가드 균일화

다음 6개 API 모두 `member.id not in self.inners` 체크로 stale 방어:

#### `_rebuild_faction_members_cache` ([:1086-1095](Projects/personas/loom/core/multi_tick_engine.py#L1086-L1095))
현재:
```python
for pid in sorted(self.personas):
    if pid not in self.inners:
        continue
    persona = self.personas[pid]
    if persona.faction is not None and persona.faction in cache:
        cache[persona.faction].append(persona)
```
→ 변경: `persona.id` 기준 재검증 추가 (옵션 1 rekey 적용 후에는 `pid == persona.id`가 보장되지만, 방어적 가드 유지):
```python
for pid in sorted(self.personas):
    if pid not in self.inners:
        continue
    persona = self.personas[pid]
    if persona.id != pid:
        continue  # identity mismatch defensive guard (post-fix 이후 사실상 unreachable)
    if persona.faction is not None and persona.faction in cache:
        cache[persona.faction].append(persona)
```

#### `faction_grievance_targets` ([:1457-1468](Projects/personas/loom/core/multi_tick_engine.py#L1457-L1468))
```python
for member in self._faction_members(fid):
    if member.id not in self.inners:  # NEW guard
        continue
    inner = self.inners[member.id]
    ...
```

#### `faction_social_matrix` ([:1435-1455](Projects/personas/loom/core/multi_tick_engine.py#L1435-L1455))
```python
mem_a_valid = [pa for pa in mem_a if pa.id in self.inners]
mem_b_valid = [pb for pb in mem_b if pb.id in self.inners]
trusts = [
    self._get_relationship_trust(pa.id, pb.id)
    for pa in mem_a_valid
    for pb in mem_b_valid
]
```

#### `faction_wealth_distribution` ([:1406-1433](Projects/personas/loom/core/multi_tick_engine.py#L1406-L1433))
기존 `if m.id in self.wallets` 있음. **추가로** `if m.id in self.inners` 체크하여 consistency 보장.

#### `faction_population_distribution` ([:1363-1370](Projects/personas/loom/core/multi_tick_engine.py#L1363-L1370))
현재는 `persona.faction`만 봄. rekey 적용 후 자연히 일관. 가드 필요 없음 — **그러나** probe 중 inners와의 불일치가 문제되면 정책 결정 필요 (이 지시서 범위 외).

#### `faction_territory_distribution`, `factions_in_contact`, `faction_charter_primitives`
territory/charter는 persona 테이블 의존 없음. 가드 불필요.

### 3.3 Invalidation 훅

**최소 구현**: §3.1 옵션 1에 `self._faction_members_cache = {}` 포함 이미 있음. 추가 훅 불필요.

**선택 구현 (권장, 향후 확장성)**: `_on_persona_lifecycle_change(old_pid, new_pid, event)` 헬퍼 도입. 호출 위치는 일단 reincarnation 한곳. 사망만 발생 (reincarnation 없는 경로)이 있다면 동일 훅 재사용.

```python
def _on_persona_lifecycle_change(
    self, *, old_pid: str, new_pid: str | None, event: str
) -> None:
    """페르소나 사망/리인카네이션 시 SSoT cache를 무효화한다.

    event:
      - "reincarnated": old_pid -> new_pid rekey 완료 직후
      - "died": 완전 제거 (향후 확장)
    """
    self._faction_members_cache = {}
    # affiliation_scores는 new_inner 생성자에서 {} 초기화되므로 추가 작업 불필요
```

### 3.4 회귀 테스트 추가

**파일**: `Projects/personas/loom/test_phase17_faction.py`
**위치**: 파일 말미, 기존 12 테스트 이후

```python
def test_phase17_faction_reincarnation_safety() -> None:
    """리인카네이션 발생 후 faction_* API 6종 전부 KeyError 없이 반환."""
    engine = _fresh_engine(seed=42)
    # faction 생성 + 멤버 할당
    engine._init_founder_seeds()
    # 하나라도 faction이 있어야 의미 있음
    assert engine.factions, "precondition: factions exist"
    fid = next(iter(engine.factions))
    pids = list(engine.personas)
    assert pids, "precondition: personas exist"
    pid = pids[0]
    engine._change_persona_faction(pid, fid, source="affiliation")

    # 사망 & 리인카네이션 시뮬 — 실제 경로 호출
    # (엔진의 reincarnation 조건을 만족시키기 위해 inner 상태 조작)
    inner = engine.inners[pid]
    inner.vitality = 0.0
    inner.oyok[0] = 1.0  # starvation marker
    # 엔진의 사망 처리 메서드를 직접 호출 (private 경로여도 contract test 허용)
    engine._process_death_and_reincarnation()

    # API 6종 순차 호출 — 모두 예외 없이 반환해야 함
    pop = engine.faction_population_distribution()
    assert isinstance(pop, dict)
    terr = engine.faction_territory_distribution()
    assert isinstance(terr, dict)
    contact = engine.factions_in_contact(radius=1)
    assert isinstance(contact, list)
    wealth = engine.faction_wealth_distribution()
    assert isinstance(wealth, dict)
    social = engine.faction_social_matrix()
    assert isinstance(social, dict)
    grievance = engine.faction_grievance_targets()
    assert isinstance(grievance, dict)

    # identity 정합성 — rekey 이후 모든 persona의 dict key == object.id
    for key_pid, persona in engine.personas.items():
        assert key_pid == persona.id, \
            f"identity mismatch: key={key_pid} obj.id={persona.id}"
```

**주의**: `_process_death_and_reincarnation`의 실제 시그니처 확인 후 호출 방식 조정 (인자 없을 것으로 추정). 필요하면 `_inner.vitality`, `_inner.chronic_stress` 등 실제 사망 조건을 만족시키도록 조정.

### 3.5 Probe fallback 검증

`observe_phase17_emergence.py`의 `_safe_grievance_targets`에 **stderr 로그** 1줄 추가:

```python
def _safe_grievance_targets(engine: MultiTickEngine) -> dict[str, dict[str, int]]:
    try:
        return engine.faction_grievance_targets()
    except KeyError as exc:
        import sys
        print(f"[WARN] fallback triggered tick={engine.time.tick} pid_key={exc}",
              file=sys.stderr, flush=True)
        result: dict[str, dict[str, int]] = {fid: {} for fid in sorted(engine.factions)}
        ...
```

수정 후 probe 재실행(`--quick` 500틱 스모크)에서 **stderr에 [WARN] 0회 출력**이면 §3.1-3.3 수정이 목표 달성.

최종 목표: observe 스크립트에서 `_safe_grievance_targets` 자체를 **삭제**하고 직접 `engine.faction_grievance_targets()` 호출 가능 — 이번 지시서 완료의 최종 수용 기준.

---

## 4. 변경 파일

| 파일 | 작업 | 유형 |
|------|------|:---:|
| `Projects/personas/loom/core/multi_tick_engine.py` | §3.1 rekey + §3.2 가드 6곳 + §3.3 훅(선택) | 수정 |
| `Projects/personas/loom/test_phase17_faction.py` | §3.4 회귀 테스트 1건 추가 | 수정 |
| `Projects/personas/loom/observe_phase17_emergence.py` | §3.5 stderr 로그 추가 (단기), fallback 제거(최종) | 수정 |

**변경 없음 (금지)**:
- `ontology/layers.py`
- `brain/**`
- `physis/**`
- `data/models/readout_weights_v1.npy`
- 모든 기존 테스트 (수정 없이 통과해야 함)

---

## 5. 검증

### 5.1 기계 검증
```bash
cd Projects/personas/loom && py -m py_compile core/multi_tick_engine.py test_phase17_faction.py observe_phase17_emergence.py
cd Projects/personas/loom && py -m pytest test_phase17_faction.py -v    # 기존 12 + 신규 1 = 13 PASS
cd Projects/personas/loom && py -m pytest test_phase14b_snn_integration.py -v  # 8/8 PASS 회귀 없음
cd Projects/personas/loom && py -m pytest test_phase17_acceptance.py -v
cd Projects/personas/loom && py -m pytest test_phase12b_perf_npc.py -v   # reincarnation 원 경로 회귀 방지
```

### 5.2 기능 검증
- [ ] `observe_phase17_emergence.py --quick` 실행 → **stderr에 [WARN] 0회**
- [ ] probe 결과 seed 42 smoke: `active_factions_end >= initial`, KeyError 흔적 없음

### 5.3 Acceptance (최종 수용)
- [ ] `observe_phase17_emergence.py`에서 `_safe_grievance_targets` 함수와 try/except 블록 **완전 삭제** 가능 (직접 `engine.faction_grievance_targets()` 호출) 상태
- [ ] 전체 seed 3개 × 5000틱 재실행 결과 KeyError 0건

### 5.4 보고 형식
완료 시 사용자에게 보고:
```markdown
## Phase 17 Engine SSoT Fix — 실행 결과

### 수정 요약
- rekey 적용: reincarnation 시 dict key → new_pid (§3.1)
- 가드 균일화: faction_* API 6종 (§3.2)
- invalidation 훅 위치: `_process_death_and_reincarnation` 마지막 (§3.3)

### 테스트
- test_phase17_faction: 13 PASS (기존 12 + 신규 1)
- test_phase14b_snn_integration: 8 PASS (회귀 없음)
- test_phase12b_perf_npc: PASS (reincarnation 경로 원 회귀 없음)

### Probe 재실행 결과
- --quick stderr [WARN] 횟수: 0
- fallback 제거 가능 여부: YES/NO

### 특이사항
- ...
```

---

## 6. Rollback

```bash
git diff HEAD -- Projects/personas/loom/core/multi_tick_engine.py
git diff HEAD -- Projects/personas/loom/test_phase17_faction.py
git checkout HEAD -- Projects/personas/loom/core/multi_tick_engine.py Projects/personas/loom/test_phase17_faction.py
```

영향 범위: reincarnation 키 처리를 이전 상태(dict key mismatch)로 되돌림. 기존 동작과 동일하므로 롤백 안전.

---

## 7. Invariants (구현자 **반드시** 지킬 것)

1. **affiliation_score 로직 미변경** — /discuss 결과 반영 전까지 `_compute_affiliation_tick`과 상수(W_*, DECAY, DRIFT_MARGIN, THETA_JOIN) 건드리지 말 것
2. **Persona/InnerWorld dataclass 불변** — 필드 추가/삭제 금지
3. **reincarnation 의미론 보존** — 성격 70%·기억 소실 등 기존 동작 그대로. 키 정합성만 수정
4. **관계망(`relationships`) 처리 범위 외** — 이번 지시서에서 relationship key rewriting 시도 금지. faction API는 `self.inners` 가드로 방어
5. **모든 기존 테스트 통과** — 수정 없이 PASS 해야 함
6. **fallback stderr 로그는 단기 measurement 용** — 최종 단계에서 `observe_phase17_emergence.py`의 `_safe_grievance_targets` 전체 제거가 완료 조건

---

## 8. GPT/Codex 전달용 한 문장

> loom 워크스페이스 `Projects/personas/loom/` 에서 `PHASE-17-FACTION-ENGINE-SSOT-FIX-SPEC.md` 를 **그대로** 따라 `multi_tick_engine.py`의 reincarnation rekey + faction_* 가드 균일화를 적용하고 `test_phase17_faction.py`에 reincarnation safety 회귀 테스트 1건 추가 후 pytest 전 영역(test_phase17_faction, test_phase14b_snn_integration, test_phase12b_perf_npc, test_phase17_acceptance) 통과 + probe `--quick` 실행 시 stderr [WARN] 0회를 확증하고 보고한다. affiliation_score 로직·brain·ontology 수정 금지.
