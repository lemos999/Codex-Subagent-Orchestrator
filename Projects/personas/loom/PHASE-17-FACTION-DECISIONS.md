# Phase 17 / Φ-2 Faction — Decision Cards

> `/design` Phase 3 산출물. Charter([PHASE-17-FACTION-CHARTER.md](PHASE-17-FACTION-CHARTER.md)) `[보류 해소 현황]`과 Component Map([PHASE-17-FACTION-COMPONENT-MAP.md](PHASE-17-FACTION-COMPONENT-MAP.md)) Core 8개를 확정 결정으로 변환.
> GPT/Codex가 이 문서 + Charter + Map만 읽고 `/spec` 지시서로 번역 가능해야 함.

---

## 목표·목적 3계층 (역산 기준)

**궁극 목적**: 국가 자연 탄생 — 선언 없이 삶·유대·갈등·주권의 인과 사슬로만.
**Phase 17 목적**: Φ-2 Faction — "누구와 뜻이 같은가" 최초 등장.
**Φ-2 고유 역할**: Founder+Charter만 정의하고 멤버십은 kernel 창발. 어떤 파라미터·수식이든 이 세 원칙을 위배하면 기각.

---

## 메타

| 항목 | 값 |
|------|-----|
| 프로젝트 | loom 페르소나 국가 시뮬 |
| Phase | 17 / Φ-2 Faction |
| 선행 | Charter(Phase 1) 2026-04-22 / Component Map(Phase 2) 2026-04-22 |
| Decision 수 | **11개** (Core 8 + Charter #7 SNN Hook + Charter #8 HandoffAPI + v3 Adjacency util) |
| 검증 방식 | Charter [확정 선행 결정] 기반 + Φ-1 관례 계승 + Phase 3.5 `/sub p-charter-consistency` 예정 |
| 날짜 | v1 2026-04-22 / v2 2026-04-22 / **v3 2026-04-23** |

---

## 변경 로그

### v3 (2026-04-23) — 5엔진 재검증 후 Tier 1+2 수정

v2 재검증 세션(`subagent-runs/discuss/phase17-phi2-decisions-v2-verify-2026-04-23-quick/`)에서 Claude + Codex-A + Codex-B + Gemini-A + Gemini-B가 전원 PARTIAL/DISAGREE 판정. 교차 수렴 결함 3건(F1/F2/F3) + 단독 발견 4건 반영.

| # | Tier | Decision | 변경 요지 | 트리거 |
|---|------|----------|----------|-------|
| V1 | 1 | 전 문서 | v2 가정 `self._personas`·`self._territories`·`self._factions`(private, 가정 오류) → **public** `self.personas`·`self.territories`·`self.factions` 일괄 정정. `self._tick` → `self.time.tick` 포함. 실측: `multi_tick_engine.py` public 속성 149회 사용, private 0회. | Claude+Codex-A 수렴: v2 drop-in 즉시 AttributeError |
| V2 | 1 | D9, D10 | `_territory_neighbors(tid)` + `_territories_within(tid, r)` 구현체 스펙을 D9에 **신규 포함**. Territory.cells 기반 Chebyshev 인접. 기존 `_process_movement` 인라인 로직을 util로 추출하는 별도 Decision 11 신설. | Claude+Codex-A 수렴: helper 코드베이스 부재 → NameError |
| V3 | 1 | D9 | SNN bias 0.15/0.08 → **0.05/0.03** 하향. 뉴런 300~349는 이미 경제/정치 스트레스 채널로 점유(food/tool/wealth/job/rel_wealth + political_stress/grievance). 독립 가산이 아닌 "기존 신호 위에 미세 변조"로 재정의. Phase 14-B 회귀 테스트 필수. | Claude+Codex-B+Gemini-A 3관점 수렴: 코드 충돌 + 5ms 예산 초과 + 위장 top-down |
| V4 | 2 | D4 | `_shared_grievance`의 `persona.grievance`·`persona.grievance_lord_id` → `self.inners[persona.id].grievance`·`self.inners[persona.id].grievance_lord_id`로 수정. 실제 필드 소재는 InnerWorld(layers.py:938~941). | Codex-A 단독 포착 |
| V5 | 2 | D8 | walrus 예시 주석 명확화. `(p.faction := X)`는 Python 문법상 **Attribute target에 대한 walrus 대입 불가** — NamedExpr scan은 일반 name target에만 유효. 커버리지는 유지하되 주석 오해 제거. | Codex-A 단독 포착 |
| V6 | 2 | D7 | 성능 수치 재기재: 문서 10μs → 실측 228μs/tick (Codex-B 실측, amortized). 5ms 예산 내. | Codex-B 단독 포착 |
| V7 | 2 | D10 | 질적 동기 API 3종 신규: `faction_wealth_distribution`, `faction_social_matrix`, `faction_grievance_targets`. Charter #8 4종에서 **7종으로 확장**. Φ-3 대립 씨앗(자원/불신/공동 분노) 탐지 필수. | Gemini-B 단독 포착: Φ-3 인계 외형만 지원, 질적 동기 부재 |
| V8 | — | Decision 11 신설 | `_territory_neighbors`/`_territories_within` 공용 util 스펙 명시 (Phase 17 Φ-1 Land util 계승). | V2 자연 귀결 |

### v2 (2026-04-22) — `/discuss --quick` 3엔진 교차 검증 후 수정

Phase 3 초안(v1) 대비 Tier 1+2 수정 반영. 검증 세션: `subagent-runs/discuss/phase17-phi2-decisions-verify-2026-04-22-quick/`.

| # | Tier | Decision | 변경 요지 | 트리거 |
|---|------|----------|----------|-------|
| R1 | 1 | D3 / D5 | `_tick_faction_cooldown` helper 신설 + Stage 1 loop 매 틱 호출. commit loop 내부 AugAssign 제거. | Codex 독립 포착: 48 commits × 48틱 = 2304틱 실제 lock 버그 |
| R2 | 1 | D8 | AST scanner 대상에 `AugAssign`/`AnnAssign`/`NamedExpr`(walrus) 추가. | Claude+Codex 합의 REJECT: `Assign`만 검사 시 Gap 4 구조적 실패 |
| R3 | 1 | D6 | Claude C1(UUID AttributeError) 철회 — `numpy.random.Generator.bytes(n)` 지원 실행 확인. 원안 코드 유지. | Claude 자기 오판 철회 (실행 검증) |
| R4 | 2 | D4 | `_faction_members_cache` tick당 1회 빌드 + `sorted(member_pid)` 고정. 성능 2215μs ≪ 5000μs 예산. | Codex CONCERN: O(N·F·P) + float 합산 순서 재현성 결함 |
| R5 | 2 | D9 / D10 신설 | Charter #7 (SNN 300~349 co-fire) + Charter #8 (HandoffAPI 4종) Decision Card 명시. | Claude MAJOR 지적: Component Map Support 2건 Decision 부재 → /spec 임의 해석 위험 |

### Tier 3 (철학 concern — Phase 5 /spec 후 500틱 실측 판단으로 이관)

Gemini가 단독 포착한 위장 top-down 3종. 파라미터 조정보다 실측이 우선이라는 판단으로 현 설계에서는 보류, [보류 — Phase 5 실측 판단] 섹션에 기록.

- R6: D6 Founder "lord 우선" 규칙 — `source="affiliation"` 창발 가입 비율을 핵심 지표로 모니터링 (Gemini-A v3 재검: "구조 결함이라 실측 조정 불가" concern 유지 — Phase 5 진입 전 재논의 안건으로 **에스컬레이션**)
- R7: D4 `W_TERRITORY=1.0` 동적 감소 (시뮬 중반 이후 `W_TRUST` 점진 증가)
- R8: D5 `THETA_JOIN=2.5` soft-start (초기 100틱 1.5 → 완만히 2.5 상승)

---

## 불변 원칙 (모든 Decision이 준수)

1. **Top-down 금지** — founder+charter만 정의, 멤버십은 kernel 창발
2. **Phase 11-17 무파괴** — Φ-1 23/23 PASS, 경제/SNN 테스트 전부 유지
3. **SNN n_neurons=1000 freeze** — `readout_weights_v1.npy` 호환. 뉴런 추가 금지, 300~349 재사용만
4. **단방향 SSoT** — `persona.faction` 주, `Territory.factionRef` 파생
5. **단일 쓰기 경로** — `_change_persona_faction()` 외 모든 경로 AST whitelist로 차단 (Gap 4 방어)
6. **결정성 계약** — `_derive_rng("faction_*", key_parts)`, `sorted(pid)` tie-break, double-buffer snapshot→compute→commit
7. **Φ-1 관례 계승** — `@dataclass(slots=True)`, 24틱 `_auto_economy_tick` 정렬, `consecutive_*` 24/48틱 관례, `Counter.most_common` 히스테리시스

---

## Decision 1 — FactionRegistry 데이터 구조 [확정]

### 결정

```python
# layers.py, Territory 정의 뒤 (line ~160)
from dataclasses import dataclass, field
from typing import Optional
import uuid

@dataclass(slots=True)
class Faction:
    id: str                           # stable UUID (hex), 이름과 분리
    name: str                         # 표시명, 중복 허용
    founder_pid: str                  # 최초 창시자, 사망해도 유지
    charter: tuple[str, ...]          # norm primitive 3~5개, immutable
    created_tick: int

    def __post_init__(self) -> None:
        if not (3 <= len(self.charter) <= 5):
            raise ValueError(f"charter length {len(self.charter)} out of [3,5]")
        if len(set(self.charter)) != len(self.charter):
            raise ValueError(f"charter has duplicates: {self.charter}")

# FactionRegistry는 MultiTickEngine._factions로 보유 (별도 클래스 아님)
self.factions: dict[str, Faction] = {}
```

### 근거
- **`@dataclass(slots=True)`**: Φ-1 `LandCell` (D1) 패턴 계승. 메모리 절감 + 필드 오타 차단
- **`charter: tuple[str, ...]`**: immutable 강제. `frozenset` 기각 — 순서가 의미를 가질 때가 있음(서약 선언 순서 = 우선순위 신호)
- **id=UUID hex (name과 분리)**: Codex X-DETERM 계약. "같은 이름, 다른 Faction"이 Φ-3 이후 reform 시 필요
- **`__post_init__` 가드**: charter 3~5개 + 중복 금지. Founder 단계에서 잘못된 입력 즉시 FAIL
- **FactionRegistry는 dict만**: 별도 클래스는 과설계. Φ-1에서도 `Territory`는 `_territories: dict`로 관리

### 기각
- `frozenset[str]` charter — 순서 정보 손실
- 별도 `FactionRegistry` 클래스 — Φ-1 패턴(`dict[str, T]`)과 불일치
- UUID4 string "full" (하이픈 포함 36자) — hex 32자가 로그 가독성 좋음
- Hash 기반 id (`hash(name + founder_pid + created_tick)`) — 충돌 가능성 + 재현성에 추가 조건 필요

### 의존
- Charter [확정 선행 결정] #1
- Decision 2 (founder_pid는 Persona.id)

---

## Decision 2 — Persona.faction SSoT 필드군 배치 [확정]

### 결정

```python
# layers.py Persona dataclass (line ~770, 외부 관측 가능 상태)
@dataclass
class Persona:
    # 기존 필드 ...
    faction: Optional[str] = None              # faction.id, 미소속 허용
    faction_cooldown: int = 0                  # 이적 후 쿨다운 잔여 틱

# InnerWorld (line ~700, 내면 상태)
@dataclass
class InnerWorld:
    # 기존 필드 ...
    affiliation_scores: dict[str, float] = field(default_factory=dict)
    # {faction_id: accumulated_kernel_score}

# 상수 (layers.py 상단)
MAX_TRACKED_FACTIONS_PER_PERSONA = 8   # dict 크기 상한
```

### 근거
- **`faction`/`faction_cooldown` → Persona**: 외부 관측 대상(Territory 투영, SNN telemetry, 대시보드 색상). `employment_id` 패턴 유추 (D3 Φ-1과 동일 원리)
- **`affiliation_scores` → InnerWorld**: 내면 심리 상태(유대감 누적). Φ-1 D3에서 `dest/migration_cooldown`을 InnerWorld에 둔 것과 동일 구분
- **dict 크기 상한 8개**: 파벌이 수백 개 뜨는 파국 방지. 초과 시 하위 점수 faction 삭제. 500틱 예상 최대 Faction 수 10개 내외 (territory 수 × 1.5배 여유).
- **`faction = None` 기본값**: 미소속 정합성 — 초기 모든 non-founder는 None

### 기각
- `affiliation_scores → Persona`: 외부 직렬화 불필요한 내면 상태
- dict 크기 무제한: bad-actor faction 생성 공격(Φ-3+) 때 메모리 폭발
- `active_faction_count` derived field: dict len으로 충분
- `SpatialAffiliationState` 별도 dataclass: Φ-1 D3 "과설계 기각" 계승

### 의존
- Decision 1 (faction.id 생성)
- Charter [확정 선행 결정] #2

---

## Decision 3 — SSoT Write Helpers (`_change_persona_faction`, `_tick_faction_cooldown`) [확정 v2]

> **v2 변경 (2026-04-22)**: Codex CRITICAL-1 대응. `_tick_faction_cooldown` helper 신설 — D5 commit loop 내부 `faction_cooldown -= 1` AugAssign(48 commits × 48틱 = 2304틱 lock 버그)을 매 틱 helper 호출로 분리. 단일 쓰기 경로 계약 유지.

### 결정

```python
# core/multi_tick_engine.py, _change_persona_territory() 옆 (line ~897)
from typing import Literal

FactionChangeSource = Literal["birth_founder", "affiliation", "drift", "conflict"]
FACTION_COOLDOWN_TICKS = 48   # (Decision 5 참조)

def _change_persona_faction(
    self,
    pid: str,
    new_faction_id: Optional[str],
    *,
    source: FactionChangeSource,
) -> None:
    """persona.faction 쓰기 유일 경로. AST whitelist로 강제."""
    if source not in ("birth_founder", "affiliation", "drift", "conflict"):
        raise ValueError(f"invalid faction change source: {source!r}")
    if new_faction_id is not None and new_faction_id not in self.factions:
        raise ValueError(f"unknown faction_id: {new_faction_id!r}")

    persona = self.personas[pid]
    prev = persona.faction
    if prev == new_faction_id:
        return  # no-op: 중복 호출 방어 (idempotent)

    persona.faction = new_faction_id  # noqa: PHASE17_FACTION_SSOT_WRITE
    persona.faction_cooldown = FACTION_COOLDOWN_TICKS if prev is not None else 0  # noqa: PHASE17_FACTION_SSOT_WRITE
    # 이탈 또는 이적일 때만 cooldown; 최초 가입(prev=None)은 즉시 활동 가능

    # v3: _emit_event helper는 현 코드베이스에 없음 → event_log 직접 push (기존 패턴)
    self.event_log.append({
        "type": "faction_change",
        "tick": self.time.tick,
        "pid": pid,
        "from_faction": prev,
        "to_faction": new_faction_id,
        "source": source,
    })

def _tick_faction_cooldown(self, pid: str) -> None:
    """persona.faction_cooldown 매 틱 1 감소. D5 commit loop가 이 helper를 호출하지 않고
    직접 AugAssign(`-=`)을 쓰면 D8 AST scanner(AugAssign 포함)가 FAIL시킴.

    호출 위치: Stage 1 loop 내 각 persona별 1회 (행동 처리 이전).
    0 이하 clamp — 음수 방지.
    """
    persona = self.personas[pid]
    if persona.faction_cooldown <= 0:
        return  # idempotent
    persona.faction_cooldown -= 1  # noqa: PHASE17_FACTION_SSOT_WRITE
```

### 근거
- **위치 = `_change_persona_territory()` 바로 옆**: 단일 진원지 두 함수를 한눈에 볼 수 있게 Φ-1/Φ-2 SSoT 계약이 나란히 노출됨
- **`Literal` vs Enum**: Literal 선택. Enum은 `.value` 직렬화 보일러플레이트 추가 + source 태그는 고정 4종이라 type-narrowing만 필요
- **factory validate + `_personas`/`_factions` 존재 체크**: 실패 라인에서 즉시 ValueError (방어적 프로그래밍)
- **Idempotent (prev == new → return)**: 24/48틱 commit 주기에 중복 호출 가능성 높음. no-op 가드로 불필요 event spam 방지
- **cooldown = 최초 가입 시 0, 이적 시 48틱**: 초기 가입은 자연스러운 편입, 이적은 신중한 결정. 쿨다운 없이 최초 가입하면 bottom-up seeding이 가속됨
- **`_tick_faction_cooldown` 별도 helper (v2 신설)**: cooldown 감소가 매 틱 일어나야 "48틱 lock" 의도와 일치. D5 commit loop에 `-=`를 넣으면 48 commits × 48 틱 = 2304틱 lock 버그 (Codex 독립 포착). helper 분리로 단일 쓰기 경로 계약 유지 + AST AugAssign 검사와 양립
- **event schema**: `(tick, pid, from_faction, to_faction, source)` 5종 필드. Φ-1 event 관례(tick 포함)

### 기각
- `FactionChangeSource` as `enum.Enum` — 불필요한 `.value` 변환
- `from_faction` 필드 생략 — 디버깅/재현성에 필수
- Event schema에서 tick 생략 — 재생·재현 불가
- prev == new일 때 event 발행 — noise
- cooldown 감소 inline in D5 commit loop: 48 commits × 48 틱 = 2304틱 lock 버그 (v2에서 기각)
- cooldown 감소를 `_change_persona_faction`에 포함: 함수는 "쓰기 트리거"만, "tick 진행" 별도 관심사

### 의존
- Decision 1 (factions registry)
- Decision 2 (Persona.faction 필드)
- Decision 5 (`_tick_faction_cooldown` 호출 위치 = Stage 1 loop)
- Decision 8 (AST whitelist PHASE17_FACTION_SSOT_WRITE 마커, `ast.AugAssign` 포함)

---

## Decision 4 — AffiliationKernel 수식·가중치·신호 소스 [확정 v3]

> **v2 변경 (2026-04-22)**: Codex CONCERN 대응. (1) `_faction_members()`를 tick당 1회 캐시(`_faction_members_cache`) — O(N·F·P) → O(N·F+P). (2) member 순서 `sorted(member_pid)` 고정 — float 합산 순서 안정 = `seed=42` 재현성 보장. (3) 성능 견적 2215μs ≪ 5000μs 예산 (Codex 측정).
>
> **v3 변경 (2026-04-23)**: Codex-A 단독 포착. `_shared_grievance`의 `persona.grievance`·`m.grievance`·`persona.grievance_lord_id`는 **Persona 필드가 아님** — InnerWorld(layers.py:938~941) 소재. `self.inners[pid].grievance*` 경유로 수정. `_compute_affiliation_tick`의 `persona.inner.affiliation_scores` 경로도 동일(v3 주석에 명시).

### 결정

```python
# 상수 (layers.py)
W_TERRITORY   = 1.0      # 같은 territory 거주 indicator
W_TRUST       = 0.8      # 해당 faction 멤버들과 trust 평균
W_GRIEVANCE   = 0.6      # 공유 불만 (음수도 가능: 같은 상대에 대한 증오)
W_PROXIMITY   = 0.4      # Chebyshev 거리 기반 근접성
DECAY         = 0.92     # ~= 0.92^48 = 0.018, 48틱 후 거의 소멸 (커밋 주기와 일치)
GRIEVANCE_MIN_SHARED = 0.3
PROXIMITY_DECAY_SCALE = 10.0

# v2: tick당 1회 캐시. _compute_affiliation_tick 진입 시 rebuild.
#   self._faction_members_cache: dict[str, list[Persona]]  # {faction_id: sorted by pid}

def _rebuild_faction_members_cache(self) -> None:
    """tick당 1회 호출. faction별 member 리스트를 sorted(pid)로 고정."""
    cache: dict[str, list] = {fid: [] for fid in self.factions}
    for pid in sorted(self.personas):  # 결정성 = 삽입 순서
        p = self.personas[pid]
        if p.faction is not None and p.faction in cache:
            cache[p.faction].append(p)
    self._faction_members_cache = cache

def _faction_members(self, faction_id: str) -> list:
    """캐시 조회. 없으면 빈 list (공허 faction 방어)."""
    return self._faction_members_cache.get(faction_id, [])

# 신호 수식 — 전부 [0.0, 1.0] 정규화, grievance만 [-1.0, 1.0]
def _same_territory(self, persona: Persona, faction_id: str) -> float:
    """1.0 if 같은 territory에 해당 faction 멤버 1명 이상 있음 else 0.0"""
    members = self._faction_members(faction_id)
    return 1.0 if any(m.territory == persona.territory for m in members) else 0.0

def _trust_density(self, persona: Persona, faction_id: str) -> float:
    """persona ↔ faction members Relationship.trust 평균 - 0.5 (중립 기준)
    → 범위 [-0.5, 0.5] → *2로 [-1.0, 1.0] 정규화.
    v2: members는 sorted(pid)라 float 합산 순서 결정적."""
    members = self._faction_members(faction_id)
    if not members:
        return 0.0
    trusts = [
        self._get_relationship_trust(persona.id, m.id)
        for m in members if m.id != persona.id
    ]
    if not trusts:
        return 0.0
    return 2.0 * (sum(trusts) / len(trusts) - 0.5)

def _shared_grievance(self, persona: Persona, faction_id: str) -> float:
    """persona와 faction 멤버가 같은 영주에 대한 grievance > THRESHOLD 공유 비율.
    v3: grievance·grievance_lord_id·grievance_announced는 InnerWorld 필드
    (layers.py:938~941). Persona에는 존재하지 않음 → self.inners[pid] 경유."""
    p_inner = self.inners[persona.id]
    if p_inner.grievance < GRIEVANCE_MIN_SHARED:
        return 0.0
    members = self._faction_members(faction_id)
    if not members:
        return 0.0
    same_target = sum(
        1 for m in members
        if self.inners[m.id].grievance >= GRIEVANCE_MIN_SHARED
        and self.inners[m.id].grievance_lord_id == p_inner.grievance_lord_id
    )
    return same_target / len(members)

def _spatial_proximity(self, persona: Persona, faction_id: str) -> float:
    """faction 멤버 중 최근접 k=5명의 평균 Chebyshev 거리 → [0.0, 1.0]."""
    members = self._faction_members(faction_id)
    # v2: members 이미 sorted(pid). dists 정렬 자체는 거리 기반이라 별개 — 결정적
    dists = sorted(chebyshev(persona.pos, m.pos) for m in members if m.id != persona.id)[:5]
    if not dists:
        return 0.0
    avg = sum(dists) / len(dists)
    return max(0.0, 1.0 - avg / PROXIMITY_DECAY_SCALE)

def _compute_affiliation_tick(self) -> None:
    """매 틱 호출. double-buffer snapshot→compute→commit.
    v3: `_snapshot_personas` helper는 코드베이스에 없음 → sorted(self.personas) 인라인 순회.
    v3: affiliation_scores는 InnerWorld(self.inners[pid]) 소재 — persona.inner 경로 없음."""
    self._rebuild_faction_members_cache()  # v2: tick당 1회
    new_scores: dict[str, dict[str, float]] = {}
    # 결정성: sorted(pid) 순서 고정 (snapshot-by-iteration-order)
    for pid in sorted(self.personas):
        persona = self.personas[pid]
        new_scores[pid] = {}
        prev_scores = self.inners[pid].affiliation_scores
        for fid in sorted(self.factions):   # tie-break
            score = (
                W_TERRITORY * self._same_territory(persona, fid)
                + W_TRUST     * self._trust_density(persona, fid)
                + W_GRIEVANCE * self._shared_grievance(persona, fid)
                + W_PROXIMITY * self._spatial_proximity(persona, fid)
            )
            prev = prev_scores.get(fid, 0.0)
            new_scores[pid][fid] = DECAY * prev + score
    # atomic commit (InnerWorld 경유)
    for pid, scores in new_scores.items():
        self.inners[pid].affiliation_scores = scores
```

### 근거
- **W_TERRITORY=1.0 (최강)**: Φ-1 territory가 공간 기반 "우리"의 최초 proxy. 같은 영지 거주가 유대의 가장 자연스러운 씨앗
- **W_TRUST=0.8**: Phase 15 CommunityMetrics + Phase 14-B Relationship.trust 계승. 1.0보다 낮게 → 신뢰만으론 가입 안 됨(공간 근접 필수)
- **W_GRIEVANCE=0.6 (음수 허용)**: 공유 적은 공유 동지를 만든다(정치 상식). 음수 값은 grievance 대상 불일치 시 발생 → 자연스러운 분화 씨앗
- **W_PROXIMITY=0.4 (최약)**: 같은 territory 이미 포함하므로 중첩. 미소속자의 약한 tug
- **DECAY=0.92**: 커밋 주기(48틱, Decision 5)와 일치 — 한 번 commit 후 새 신호 필요 (stale score 누적 방지)
- **trust 중립 0.5 기준점 차감**: 중립 관계가 "긍정 신호"로 오해되는 것 차단
- **grievance "같은 영주" 조건**: 불만의 대상이 같아야 공유됨 (Phase 14-B `grievance_lord_id` 재사용)
- **proximity k=5**: Φ-1 D4 `MOVE_CANDIDATE_K=5` 계승
- **`PROXIMITY_DECAY_SCALE=10`**: 50×50 grid에서 10셀 ≈ 1/5 지도, 그 이상 거리는 proximity 기여 0
- **member cache tick당 1회 (v2)**: `_faction_members()`를 각 신호 함수가 faction 수×persona 수만큼 반복 호출하면 O(N·F·P). 캐시로 O(N·F+P) 축소. 측정: 수정 후 2215μs (Codex)
- **`sorted(member_pid)` 고정 (v2)**: float 합산은 순서 의존. 미정렬 시 `seed=42` 2회 실행 결과가 미세 불일치 가능. Hard 불변 "결정성" 충족 필수조건

### 기각
- W_TRUST >= 1.0: territory 없이 신뢰만으로 가입 가능 → bottom-up 원칙 약화
- DECAY = 1.0 (무감쇠): 한번 높아진 점수가 영구 보존 → 이적 불가능
- DECAY = 0.5 (빠른 감쇠): 커밋 주기 전에 소멸 → 유대가 쌓이지 않음
- trust 그대로 [0, 1] 사용: 중립 관계가 positive pressure로 오판
- grievance를 faction 간 차이로 계산: 너무 복잡, Φ-3 정치 동역학과 혼재
- k=10 proximity: 50×50 grid에서 전체 인구에 육박, noise

### Φ-2 말기/Φ-3 백로그
- trust_density에 CommunityMetrics(Phase 15) intra_inter_ratio 추가 항
- grievance에 경제 지표(gold disparity, treasury deficit) 연동
- kernel 가중치 동적화 (페르소나 성격별 편향)

### 의존
- Decision 1 (factions registry)
- Decision 2 (Persona.faction, affiliation_scores)
- Phase 14-B (`grievance`, `grievance_lord_id` 필드)
- Phase 15 (Relationship.trust 직접 조회 헬퍼)

---

## Decision 5 — FactionCommitLoop 임계치·쿨다운·주기 [확정 v2]

> **v2 변경 (2026-04-22)**: Codex CRITICAL-1 대응. commit loop 내부 `faction_cooldown -= 1` 제거(실제 2304틱 lock 버그). 대신 Stage 1 loop에서 매 틱 `_tick_faction_cooldown(pid)` helper 호출(Decision 3). commit loop는 `cooldown > 0`일 때 skip만.

### 결정

```python
# 상수 (layers.py)
FACTION_COMMIT_EVERY   = 48       # 틱 주기 (24 기각 근거 참조)
THETA_JOIN             = 2.5      # 최초 가입 누적 점수 임계치
DRIFT_MARGIN           = 1.2      # 이적 = best - current >= 1.2
FACTION_COOLDOWN_TICKS = 48       # 이적 후 쿨다운 (매 틱 -1 감소 — D3 helper)

# core/multi_tick_engine.py, tick() Stage 1 loop 내 각 persona마다 호출
#   (기존 _process_survival_consume(pid) 직전 또는 직후 — 행동 처리 이전)
#   self._tick_faction_cooldown(pid)   # v2: 매 틱 감소, Decision 3 helper

# core/multi_tick_engine.py, _auto_economy_tick() 직후
def _commit_faction_tick(self) -> None:
    """48틱마다 호출. _compute_affiliation_tick() 여러 번 누적 후.
    v2: cooldown 감소는 Stage 1 helper가 담당. 여기서는 skip만.
    v3: affiliation_scores는 self.inners[pid] 경유 (InnerWorld 소재)."""
    if self.time.tick % FACTION_COMMIT_EVERY != 0:
        return
    # snapshot at commit entry (atomic) — persona.faction/cooldown + inners.affiliation_scores
    snapshot = {
        pid: (
            self.personas[pid].faction,
            self.personas[pid].faction_cooldown,
            dict(self.inners[pid].affiliation_scores),
        )
        for pid in self.personas
    }
    # sorted(pid) 순서 = 결정성
    for pid in sorted(snapshot):
        cur_fid, cooldown, scores = snapshot[pid]
        if cooldown > 0:
            continue  # v2: Stage 1 helper가 이미 매 틱 감소시킴 — 여기선 skip
        if not scores:
            continue
        # tie-break: sorted(fid) 사전순 안정화
        sorted_items = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
        best_fid, best_score = sorted_items[0]

        if cur_fid is None:
            if best_score >= THETA_JOIN:
                self._change_persona_faction(pid, best_fid, source="affiliation")
        else:
            if best_fid == cur_fid:
                continue
            current_score = scores.get(cur_fid, 0.0)
            if best_score - current_score >= DRIFT_MARGIN:
                self._change_persona_faction(pid, best_fid, source="drift")
```

### 근거
- **48틱 주기 (24 기각)**: 가입은 정치적 결정, 공간이동보다 무게 있어야 함. Φ-1 D6 dominance projection은 24틱(공간) — Φ-2 faction은 두 배. 또한 `_auto_economy_tick` 주기(24)와 엇갈려 경제 tick과 commit tick이 같은 순간 발생 방지
- **cooldown 매 틱 감소 (v2 결정)**: `FACTION_COOLDOWN_TICKS=48`의 의도는 "이적 후 48틱 lock". commit loop 내부에서 `-=1` 하면 48 commits 필요 = 48×48 = 2304틱 lock — 500틱 시나리오에서 이적 사실상 1회 제한. helper를 Stage 1 loop에 호출하여 정확히 48틱 후 해제
- **THETA_JOIN=2.5**: 단일 틱 max kernel score ≈ W_TERRITORY(1.0) + W_TRUST(0.8)*0.5 + W_PROXIMITY(0.4)*0.5 ≈ 1.6. 이 신호가 2~3틱 지속 누적(DECAY 0.92)되면 ~4.0 도달. 임계 2.5는 "짧은 우연"이 아닌 "지속 유대"만 가입 허용
- **DRIFT_MARGIN=1.2**: 현 faction의 관성 보호. 작은 차이로 이적하면 정치가 불안정. 1.2는 최대 가중치(W_TERRITORY=1.0) + 여분 하나를 이길 수준
- **FACTION_COOLDOWN_TICKS=48 (= 한 commit 주기)**: 이적 후 최소 한 사이클은 재이적 불가 — 단기 진동 차단
- **snapshot-at-entry**: Φ-1 D6 atomicity 계승. 같은 틱 내 순서 의존 제거
- **DRIFT vs JOIN 분리**: `source="drift"` 태그로 Φ-3 갈등 판정 시 "변절자" 감지

### 기각
- 24틱 주기 + 경제 tick 같은 순간: 경제 commit과 faction commit이 같은 틱에 일어나면 snapshot 경쟁 조건
- **commit loop에서 cooldown `-=` inline (v2 기각)**: 48 commits × 48틱 = 2304틱 실제 lock 버그
- THETA_JOIN=1.5 (낮음): 우연한 인접이 가입 유발 → 창발 풍경이 noise
- DRIFT_MARGIN=0.5 (낮음): 모든 틱마다 미세 이적, 안정 분포 불가
- FACTION_COOLDOWN=24: 48틱 주기 내 2번 이적 가능 → 주기 내 진동
- 가입·이적 대칭 로직 (최고 점수 간 margin만): 최초 가입이 너무 느림
- 상수를 commit-step 기준으로 재정의 (`FACTION_COOLDOWN_COMMITS=1`): 직관 위배, 다른 cooldown(`migration_cooldown` 등)과 단위 불일치

### 의존
- Decision 3 (`_change_persona_faction` + `_tick_faction_cooldown` 호출)
- Decision 4 (affiliation_scores 누적)
- Stage 1 loop 통합: `tick()` 내 각 persona별 `self._tick_faction_cooldown(pid)` 1회 호출 필수

---

## Decision 6 — FounderSeedGenerator (Territory당 1개 founder+charter) [확정 v2]

> **v2 변경 (2026-04-22)**: Claude C1(UUID 생성 AttributeError) 주장 철회 — `numpy.random.Generator.bytes(n)`은 실제 지원됨(실행 검증 완료, `rng.bytes(16)` → 16바이트 정상 반환). 원안 코드 그대로 유지. Codex AGREE 판정이 옳았음. Gemini 철학적 concern(lord 우선 → 위장 top-down)은 Tier 3 백로그로 이관 (Phase 5 이후 500틱 실측 판단).


### 결정

```python
# 상수 (layers.py)
NORM_PRIMITIVE_CATALOG: tuple[str, ...] = (
    # 자원·경제 (3)
    "토지_공유", "무역_개방", "재산_개인",
    # 권위·계층 (3)
    "장자_상속", "능력주의", "원로회의",
    # 대외 관계 (3)
    "외세_배척", "이방인_환대", "중립_유지",
    # 종교·문화 (3)
    "선조_숭배", "자연_경외", "지식_추구",
)
# 총 12개 카테고리, Φ-2는 3~5개 샘플
CHARTER_PRIMITIVE_COUNT = (3, 5)  # (min, max) 범위

# core/multi_tick_engine.py
def _init_founder_seeds(self) -> None:
    """tick=0 한 번 호출. Territory당 최대 1 founder seeding."""
    for territory in sorted(self.territories.values(), key=lambda t: t.id):
        candidates = [p for p in self.personas.values() if p.territory == territory.id]
        if len(candidates) < 3:  # 최소 인구 (founder + 잠재 멤버 2)
            continue  # skip

        # founder 선정: lord 우선 → 인구 최고 trust 페르소나 → sorted(pid) tie-break
        founder = self._pick_founder(candidates, territory)
        if founder is None:
            continue

        charter = self._sample_charter(territory.id)
        faction_id = uuid.UUID(
            bytes=self._derive_rng("faction_seed", territory.id).bytes(16)
        ).hex
        faction = Faction(
            id=faction_id,
            name=f"{territory.name}_F1",  # 초기 이름, Φ-2 reform 없음
            founder_pid=founder.id,
            charter=charter,
            created_tick=0,
        )
        self.factions[faction.id] = faction
        # founder만 자동 가입 (bottom-up 원칙)
        self._change_persona_faction(founder.id, faction.id, source="birth_founder")

def _pick_founder(
    self, candidates: list[Persona], territory: Territory
) -> Optional[Persona]:
    """우선순위: lord > 최고 평균 trust > sorted(pid)."""
    if territory.lord_id:
        for p in candidates:
            if p.id == territory.lord_id:
                return p
    # 평균 trust 최고
    def avg_trust(p: Persona) -> float:
        trusts = [
            self._get_relationship_trust(p.id, q.id)
            for q in candidates if q.id != p.id
        ]
        return sum(trusts) / len(trusts) if trusts else 0.5
    ranked = sorted(
        candidates,
        key=lambda p: (-avg_trust(p), p.id),  # 내림차순 trust, tie-break sorted(pid)
    )
    return ranked[0] if ranked else None

def _sample_charter(self, territory_id: str) -> tuple[str, ...]:
    rng = self._derive_rng("faction_charter", territory_id)
    n = rng.integers(CHARTER_PRIMITIVE_COUNT[0], CHARTER_PRIMITIVE_COUNT[1] + 1)
    chosen = rng.choice(NORM_PRIMITIVE_CATALOG, size=int(n), replace=False)
    return tuple(sorted(chosen))  # 순서 안정화
```

### 근거
- **Territory당 최대 1개**: Φ-2 초기 분포를 단순하게. 여러 faction 공존은 kernel 성장으로만(S4)
- **인구 ≥3 조건**: founder 혼자 seed면 kernel 성장 불가, 최소 잠재 멤버 2 필요
- **founder 선정: lord → 최고 trust → sorted(pid)**:
  - lord 우선 = 이미 지역 권력이 있음, top-down이 아니라 자연스러운 creator
  - trust 기반 = Charter 실현의 "유대 중심성" 계승
  - sorted(pid) tie-break = 결정성 필수
- **norm primitive 12개 × 4카테고리**: 자원·권위·대외·문화 기본 분류. Φ-2 초기 12개로 충분. Φ-3 이후 확장
- **charter 3~5개 랜덤 샘플 (sorted)**: 정렬로 순서 안정성. 순서가 의미를 갖는 건 인간 해석에서만, 기계적 재현성을 위해 sorted
- **faction_id = UUID hex from `_derive_rng("faction_seed", territory_id)`**: 결정성 + territory별 독립
- **founder만 자동 가입**: Charter [확정] "S3 전원 자동 seed 거부" 충실 이행

### 기각
- 전원 자동 seed: Charter 거부 (top-down 위장)
- 인구 >= 2: founder+1명으로는 kernel 유의미 결집 불가
- founder = random pick: 지역 컨텍스트 무시
- founder = 최고 gold/influence: 경제 편향, 유대 기반 아님
- charter = 카테고리당 1개 할당: 카테고리 균형 강제는 top-down 인위적
- charter 7~10개: Φ-2 범위에서 과함, Φ-4 언어·문화 풍부화 백로그

### 의존
- Decision 1 (Faction dataclass)
- Decision 3 (`_change_persona_faction` 호출)
- `_derive_rng` (Phase 17 Φ-1 중앙 RNG)
- Territory.lord_id (Phase 13)
- Relationship.trust (Phase 15)

---

## Decision 7 — FactionProjection (Territory.factionRef 투영) [확정 v3]

> **v3 변경 (2026-04-23)**: Codex-B 실측 반영. 성능 근거 수치 기재 (실측 228μs/tick amortized — 실제 projection tick 5.5ms ÷ 24틱). 5ms faction 예산 내. Hard 불변 tick ≤ 250ms 대비 0.09%.

### 결정

```python
# 상수 (layers.py)
FACTION_PROJECT_EVERY = 24   # 틱 주기 (Φ-1 D6 dominance와 정렬)
FACTION_HYSTERESIS    = 2    # 최소 우위 차이

# layers.py Territory dataclass에 추가 필드
@dataclass
class Territory:
    # 기존 필드 ...
    factionRef: Optional[str] = None   # None = 공허(미지배)

# core/multi_tick_engine.py
def _project_faction_tick(self) -> None:
    """24틱마다 호출. FactionCommitLoop 완료 후 실행."""
    if self.time.tick % FACTION_PROJECT_EVERY != 0:
        return
    snapshot = {pid: (p.territory, p.faction)
                for pid, p in sorted(self.personas.items())}
    new_refs: dict[str, Optional[str]] = {}
    for territory in self.territories.values():
        members = [(pid, fid) for pid, (tid, fid) in snapshot.items()
                   if tid == territory.id and fid is not None]
        if not members:
            new_refs[territory.id] = None  # 공허 유지
            continue
        counts = Counter(fid for _, fid in members)
        top, top_count = counts.most_common(1)[0]
        second_count = counts.most_common(2)[1][1] if len(counts) > 1 else 0
        prev_ref = territory.factionRef
        if prev_ref and prev_ref in counts:
            prev_count = counts[prev_ref]
            if top_count - prev_count < FACTION_HYSTERESIS:
                new_refs[territory.id] = prev_ref
                continue
        if top_count - second_count >= FACTION_HYSTERESIS:
            new_refs[territory.id] = top
        else:
            new_refs[territory.id] = prev_ref  # margin 부족: 현상 유지
    # atomic swap
    for tid, ref in new_refs.items():
        self.territories[tid].factionRef = ref
```

### 근거
- **24틱 주기 (Φ-1 D6과 일치)**: Φ-1 territoryRef도 24틱. 같은 주기에 두 투영이 함께 진행되어 하나의 "지도 업데이트" 순간
- **FACTION_HYSTERESIS=2**: Φ-1 D6 DOMINANCE_VOTE_MARGIN=2 계승. 1표 flip 방지
- **공허(None) 허용**: Charter [확정] #3 — "미지배 영토가 있어야 우리가 창발"
- **현 지배자 보호**: prev_ref ∈ counts 인데 top과 차이 2 미만이면 현상 유지 → 정치적 안정성
- **Φ-1 D6 패턴 계승**: snapshot → compute → commit. atomic swap. sorted(persona) 결정성
- **Counter.most_common insertion order**: 같은 count 시 먼저 삽입된 fid 우선 → sorted(personas) 순서가 결정 → 재현성
- **성능 (v3 실측)**: Codex-B 측정 amortized **228μs/tick** (실제 projection tick 5.5ms ÷ 24). 5ms faction 예산 대비 4.6%, Hard 불변 tick ≤ 250ms 대비 0.09%. snapshot dict comprehension + Counter 1회만으로 N·T iteration만 발생, O(N+T)

### 기각
- FACTION_PROJECT_EVERY=48 (commit 주기와 동일): commit 직후 projection이 바로 보이지 않음 → 24~48틱 delay 체감
- HYSTERESIS=1: 1표 flip → 진동
- HYSTERESIS=3: 너무 보수적, 실제 정치 변화가 projection에 늦게 반영
- 공허 자동 대체(가장 많은 persona의 faction 상속): Charter 공허 허용 원칙 위배

### 의존
- Decision 2 (Persona.faction)
- Decision 5 (commit 직후 snapshot)
- Charter [확정 선행 결정] #3 (Territory.factionRef)

---

## Decision 8 — AST Whitelist 확장 [확정 v3]

> **v2 변경 (2026-04-22)**: Codex/Claude REJECT 합의. `ast.AugAssign` 포함 — `faction_cooldown -= 1` 등 증강 대입 우회 차단. `ast.Assign`만 검사하면 D5 내부 `-=` 라인이 AST 통과하며 Gap 4 구멍 유지됨. walrus 구문도 포함.
>
> **v3 변경 (2026-04-23)**: Codex-A 단독 포착 — `(p.faction := X)` walrus 주석이 오해 유발. Python 문법상 **attribute target walrus 대입 불가**(`SyntaxError: cannot use assignment expressions with attribute`). NamedExpr target은 name target에만 유효. 실효 커버리지는 Assign/AugAssign/AnnAssign 3종이 본선이며, NamedExpr 분기는 심층 방어용으로 유지하되 주석만 정정.

### 결정

```python
# Projects/personas/loom/tests/test_phase17_faction.py (신규)
"""Φ-2 Faction AST whitelist. test_phase17_land.py 패턴 계승.
v2: AugAssign + NamedExpr(walrus) 포함으로 우회 경로 차단."""
import ast
import pathlib
import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
LOOM_ROOT = REPO_ROOT / "Projects" / "personas" / "loom"
SCAN_DIRS = ("core", "ontology", "physis", "brain")
WHITELIST_MARKER = "PHASE17_FACTION_SSOT_WRITE"
BANNED_ATTRS = ("faction", "faction_cooldown")

def _targets_from_node(node: ast.AST):
    """Assign / AugAssign / AnnAssign / NamedExpr 에서 attribute target 수집."""
    if isinstance(node, ast.Assign):
        for t in node.targets:
            yield t
    elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
        yield node.target
    elif isinstance(node, ast.NamedExpr):
        # walrus: `(name := expr)` — Python 문법상 target은 name만 허용.
        # `(p.faction := X)`는 SyntaxError라 실제 발견 불가. 분기 유지는 심층 방어
        # (미래 문법 확장/파서 변형/커스텀 AST 주입 대비). 본선 커버리지는 Assign/AugAssign/AnnAssign.
        yield node.target

def _scan_faction_writes(tree: ast.AST, source_lines: list[str]) -> list[tuple[int, str, str]]:
    """persona.faction / persona.faction_cooldown 직접 변경 검출.
    Assign, AugAssign, AnnAssign, NamedExpr 전부 대상."""
    hits = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign, ast.NamedExpr)):
            continue
        for target in _targets_from_node(node):
            if not isinstance(target, ast.Attribute):
                continue
            if target.attr not in BANNED_ATTRS:
                continue
            # 해당 라인 원문에 마커가 있으면 면제
            line_idx = node.lineno - 1
            if line_idx < len(source_lines):
                if WHITELIST_MARKER in source_lines[line_idx]:
                    continue
            kind = type(node).__name__  # "Assign" | "AugAssign" | "AnnAssign" | "NamedExpr"
            hits.append((node.lineno, target.attr, kind))
    return hits

def test_phase17_faction_ssot_write_is_whitelisted():
    violations = []
    for subdir in SCAN_DIRS:
        for path in (LOOM_ROOT / subdir).rglob("*.py"):
            src = path.read_text(encoding="utf-8")
            tree = ast.parse(src)
            lines = src.splitlines()
            for lineno, attr, kind in _scan_faction_writes(tree, lines):
                violations.append(
                    f"{path.relative_to(LOOM_ROOT)}:{lineno}  persona.{attr} [{kind}]"
                )
    assert not violations, (
        "Φ-2 Faction SSoT 위반 — `_change_persona_faction()` / `_tick_faction_cooldown()` 경유 필수.\n"
        "위반 라인에 `# noqa: PHASE17_FACTION_SSOT_WRITE` 마커 추가하거나,\n"
        "helper 함수 경유로 수정하세요. (Assign/AugAssign/AnnAssign/Walrus 모두 검사)\n\n"
        + "\n".join(violations)
    )
```

### 근거
- **신규 파일 `test_phase17_faction.py`**: `test_phase17_land.py` (Φ-1) 확장 방식 기각 이유는, 두 Phase가 독립적으로 검증되어야 회귀 범위가 명확함. Φ-2 제거 시 Φ-1 테스트 오염 없음
- **마커 이름 `PHASE17_FACTION_SSOT_WRITE`**: Φ-1 마커 `PHASE17_SSOT_WRITE`와 구분 (혼용 금지)
- **대상 속성 2개 (`faction`, `faction_cooldown`)**: Charter 계약 필드 전부. `affiliation_scores`는 dict 누적이라 AST 정적 검출 어렵고, 대신 `_change_persona_faction()`이 변경하지 않음 → 런타임 검증 불필요
- **scan 범위 4 subdirs** (core/ontology/physis/brain): `tests/`·`dashboard/`는 read-only, `scripts/`는 유틸 → 제외
- **AugAssign 포함 (v2 신설)**: `faction_cooldown -= 1`이 D5 commit loop에 inline으로 있으면 AST `Assign`만 검사 시 우회. `helper _tick_faction_cooldown` + 마커 패턴으로 구조적 강제 + 스캐너 이중 방어
- **AnnAssign 포함**: 타입주석 대입(`persona.faction: str = X`) 우회 경로 차단
- **NamedExpr 포함 (v3 주석 명확화)**: Python 문법상 walrus `(p.faction := X)`는 SyntaxError라 실제 발견 불가 — 실효 커버리지는 name target 한정. 그럼에도 분기 유지 이유는 (a) 미래 AST 노드 확장 방어, (b) 커스텀 AST 변환기·주입 시나리오 대비 심층 방어. 본선 차단은 Assign/AugAssign/AnnAssign 3종

### 기각
- `test_phase17_land.py` 확장 — 책임 분리 원칙
- `PHASE17_SSOT_WRITE` 공유 마커 — Phase별 grep 시 교차 오염
- **`Assign`만 검사 (v2 기각)**: Codex 독점 포착 — D5 AugAssign이 우회, Gap 4 구조적 실패
- 마커만 추가하고 helper 분리 안 함: 마커 의존은 계약 약화, 미래 기여자가 마커 없이 대입할 위험

### 의존
- Decision 2 (필드 이름)
- Decision 3 (helper 2종 마커: `_change_persona_faction`, `_tick_faction_cooldown`)

---

## Decision 9 — SNN Telemetry Hook (Charter #7 구현) [확정 v3]

> **v2 신설 (2026-04-22)**: Claude MAJOR 지적 대응. Charter #7 "SNN 300~349 재사용 + faction telemetry co-fire"가 Component Map `Support` 항목에만 있고 Decision Card 부재 → /spec 단계에서 Codex 임의 해석 위험. 구현 결정 명시.
>
> **v3 변경 (2026-04-23)**: bias 0.15/0.08 → 0.05/0.03 하향. 뉴런 300~349는 이미 eco_base 전 구간 점유(persona_brain.py:100~153 — food/tool/wealth/job/rel_wealth + political_stress/grievance). 독립 가산은 경제/정치 신호 덮어씀 → 경제 의미 파괴. "기존 채널 위 미세 변조(≤10% amplitude)"로 재정의. Phase 14-B 회귀 필수.

### 결정

```python
# brain/persona_brain.py 내 경제 perception 입력 구성 훅 (기존 경제 input 계산 직후)
# Phase 14-B 관례: 뉴런 인덱스 [300, 349] 50뉴런 — 이미 경제/정치 스트레스 채널로 점유(eco_base).
# 본 훅은 "덮어쓰기"가 아니라 "기존 input_current 위에 미세 bias를 가산하는 변조".
# bias 값은 persona_brain.py의 eco_base 채널 amplitude(≈0.5~1.0) 대비 ≤10% 수준으로 제한.
FACTION_TELEMETRY_BIAS_OWN       = 0.05   # v3: 0.15→0.05 (경제 채널 amplitude ≤10%)
FACTION_TELEMETRY_BIAS_NEIGHBOR  = 0.03   # v3: 0.08→0.03 (own_in_neighbors 시 ×0.5 → 0.015)

# MultiTickEngine._build_persona_snn_input(pid) 내부에서 호출
def _apply_faction_telemetry(self, pid: str, input_current: np.ndarray) -> None:
    """경제 perception 뉴런 300~349에 faction 신호 co-fire.
    readout_weights_v1.npy 무변경. n_neurons=1000 freeze.
    input_current[300:350] 범위에만 가산 (다른 뉴런 건드리지 않음)."""
    persona = self.personas[pid]
    # (1) 자기 faction 존재 신호 — 경제 맥락에 "집단 압력" 추가
    if persona.faction is not None:
        # 300~324: 내부 결속 뉴런 (25개)
        input_current[300:325] += FACTION_TELEMETRY_BIAS_OWN
    # (2) 이웃 territory faction 분포 편향 — 거래 상대 편향 뉴런
    neighbor_fids = self._collect_neighbor_faction_ids(persona.territory)
    if neighbor_fids:
        own_in_neighbors = persona.faction in neighbor_fids if persona.faction else False
        bias = FACTION_TELEMETRY_BIAS_NEIGHBOR * (1.0 if not own_in_neighbors else 0.5)
        # 325~349: 거래 편향 뉴런 (25개)
        input_current[325:350] += bias

def _collect_neighbor_faction_ids(self, territory_id: str) -> set:
    """인접 territory의 factionRef 집합. 공허(None) 제외."""
    refs = set()
    for nid in self._territory_neighbors(territory_id):
        ref = self.territories[nid].factionRef
        if ref is not None:
            refs.add(ref)
    return refs
```

### 근거
- **뉴런 범위 [300,349] 재사용**: Charter #7 명시. `readout_weights_v1.npy` 1000폭 절대 고정 — SNN 구조 변경 0
- **50뉴런 2분할 (300~324 / 325~349)**: 자기 faction 소속(내부 결속) vs 이웃 faction 분포(외부 거래 편향) 신호를 구분. 기존 경제 perception 해석은 그대로 유지되며 상단에 미세 bias만 가산
- **bias 값 0.05 / 0.03 (v3 하향)**: `persona_brain.py:100~153` 실측 확인 — 300~309(food), 310~319(tool), 320~329(wealth), 330~339(job+grievance), 340~349(rel_wealth)가 `stimulate()` 호출로 이미 [0, 1+] amplitude 점유. v2 0.15/0.08은 경제 신호를 평탄화하여 기존 Phase 14-B readout_weights 학습 의미 파괴. 0.05 이하로 묶어 "미세 변조(≤10% amplitude)"로 재정의
- **"변조" 의미 엄밀화**: 경제 채널의 상대적 비교(food vs tool vs wealth)는 bias 상수 가산에 불변 (영점 이동이므로 비율 불변). 단 SNN 비선형성(LIF threshold crossing)으로 인해 경계 근처 뉴런은 발화 타이밍이 변할 수 있음 → bias 0.05 수준에서 Phase 14-B 회귀 필수 확인
- **own_in_neighbors 시 bias 감소(×0.5)**: 이웃에도 자기 faction 있으면 "확장된 우리" → 거래 편향 약화 (자연스러운 완화)
- **`_collect_neighbor_faction_ids` 헬퍼 분리**: 테스트 용이성. Decision 11이 제공하는 `_territory_neighbors(tid)` 위에 얇게 래핑 → faction ref 수집만 전담
- **input_current만 변경**: 경제 Decision Layer 가중치(readout) 건드리지 않음 → F-cluster 확장 없음 (Charter `personabrain-snn-charter v3.1` 불변)

### 기각
- 뉴런 350~369 추가 — Charter #7 명시 거부(`n_neurons` freeze)
- readout_weights_v1.npy에 faction-specific 행 추가 — 가중치 파일 재생성 필요, Phase 14-B 회귀 위험
- bias ≥ 0.1 — 경제 perception signal amplitude 대비 ≥20%가 되며 경제 의사결정(work/trade) 회귀 위험
- bias = 0.0 (훅 자체 제거) — Charter #7 위배 (co-fire 자체 생략)
- 별도 "F-cluster" 뉴런군 — Charter #7 직접 위배

### 구현 적응 메모 (v4, 2026-04-23 Codex 적용 후 Claude 리뷰 반영)

**실제 주입 경로**: `_build_persona_snn_input(pid)`는 지시서 계약대로 `input_current` ndarray의 [300:350]에 bias를 가산하여 반환. 그러나 최종 주입은 `multi_tick_engine.py:419-424`에서 **`brain.snn.v`(membrane potential)에 직접 가산** 후 `brain.tick()` 호출:

```python
faction_input = self._build_persona_snn_input(pid)
faction_idx = np.flatnonzero(faction_input)
if faction_idx.size:
    brain.snn.v[faction_idx] += faction_input[faction_idx]
brain.tick(climate_vec=..., energy_pool=..., ...)
```

**적응 이유**: 지시서 [금지]에 `brain/persona_brain.py` 수정 명시 + `PersonaBrain.tick()` signature가 외부 `input_current` 파라미터를 받지 않음 → engine 측에서 brain.tick() 내부 input_signal 조립에 개입 불가. **snn.v 직접 주입이 engine-only 제약 하에 기술적으로 가능한 유일한 경로**.

**역학 차이 (중요)**:
| 경로 | 의미 | 효과 |
|---|---|---|
| 원 의도 (`input_current` 전달) | brain.tick()이 7 sim_steps에 지속 인가 | 지속 자극 (bias × 7 × R/tau) |
| 실제 (`snn.v` +=) | brain.tick() 시작 직전 1회 kick | 첫 sim_step에 v 점프, 이후 leak 감쇠 |

효과 크기는 동일(±0.05/0.03, 경제 amplitude ≤10%). 지속성만 다름. LIF v 범위 [-0.5, v_threshold≈1.0] 기준 3~5%이므로 경제 의사결정 dynamics를 훼손하지 않음.

**검증 상태**:
- `test_phase17_faction.test_d9`: `input_current` ndarray 조작 계약만 검증 ✅
- `test_phase14b_snn_integration`: 7/7 PASS — 경제 readout 회귀 없음 ✅
- 500틱 결정성 digest 일치 ✅
- **end-to-end snn.v kick 경로 회귀 테스트는 후속 과제** — Φ-3 진입 전 1건 추가 권고

**후속 복원 경로 (Φ-3 Struggle 이후)**:
Phase 17 이후에 `brain.tick()` signature를 `tick(..., external_input: np.ndarray | None = None)`로 확장 허용하면 원래 계약(`input_current` 지속 주입)으로 복원 가능. Struggle 신호가 추가되는 Φ-3에서 brain 수정이 불가피해질 시점에 함께 처리 권고.

### 의존
- Decision 2 (Persona.faction)
- Decision 7 (Territory.factionRef)
- Decision 11 (`_territory_neighbors` 공용 adjacency util)
- Phase 14-B SNN structure (`persona_brain.py:100~153`, n_neurons=1000, readout_weights_v1.npy)
- Phase 14-B `test_phase14b_snn_integration` 회귀 PASS (bias 하향 이후 필수)

---

## Decision 10 — Φ-3 HandoffAPI 7종 (Charter #8 v3 확장) [확정 v3]

> **v2 신설 (2026-04-22)**: Claude MAJOR 지적 대응. Charter #8 "Φ-3 인계 API 4종"이 Component Map Support에만 있고 구현 결정 부재. Codex가 임의 해석하지 않도록 시그니처·반환·결정성 명시.
>
> **v3 확장 (2026-04-23)**: Gemini-B 단독 포착. v2 4종은 외형(population/territory/charter/contact)만 전달하고 Φ-3 갈등 동역학에 필요한 **질적 동기**(wealth 계급 갈등, social matrix 연합/대립, grievance targets 공동 적)가 부재. 3종 신규 추가 → 4종 → **7종**. Charter #8 범위 확장(Phase 3.5에서 Charter 측 재확정 필요).

### 결정

```python
# core/multi_tick_engine.py, Φ-3 진입 조건 판정 + 갈등 씨앗 탐지용 read-only API.
# 모든 반환은 dict/list 신규 객체 (호출자 mutate가 내부 state 오염 없도록).

def faction_population_distribution(self) -> dict[str, int]:
    """{faction_id: member_count}. 공허 faction은 0으로 포함.
    Φ-3 진입 조건(population 임계치) 판정용."""
    dist = {fid: 0 for fid in sorted(self.factions)}
    for pid in sorted(self.personas):
        fid = self.personas[pid].faction
        if fid is not None and fid in dist:
            dist[fid] += 1
    return dist

def faction_territory_distribution(self) -> dict[str, list[str]]:
    """{faction_id: [territory_id, ...]} — Territory.factionRef 기준.
    지리적 집중도 측정용. 리스트는 sorted(territory_id)."""
    result: dict[str, list[str]] = {fid: [] for fid in sorted(self.factions)}
    for tid in sorted(self.territories):
        ref = self.territories[tid].factionRef
        if ref is not None and ref in result:
            result[ref].append(tid)
    return result

def faction_charter_primitives(self, faction_id: str) -> tuple[str, ...]:
    """Faction의 norm primitive 반환. 존재하지 않는 faction_id → KeyError.
    Φ-3 charter 대립 판정용. immutable tuple이므로 caller mutation 불가."""
    if faction_id not in self.factions:
        raise KeyError(f"unknown faction_id: {faction_id!r}")
    return self.factions[faction_id].charter

def factions_in_contact(self, radius: int = 1) -> list[tuple[str, str]]:
    """근접 Territory 간 서로 다른 factionRef 쌍. Φ-3 갈등 씨앗 후보.
    radius=1 기본(Chebyshev 1셀 인접). 반환은 sorted pairs (각 쌍은 (a,b) with a<b, 전체 sorted)."""
    if radius < 1:
        raise ValueError(f"radius must be >= 1, got {radius}")
    pairs: set[tuple[str, str]] = set()
    for tid in sorted(self.territories):
        ref_a = self.territories[tid].factionRef
        if ref_a is None:
            continue
        for nid in self._territories_within(tid, radius):
            if nid <= tid:
                continue  # 중복 제거 (symmetric pair)
            ref_b = self.territories[nid].factionRef
            if ref_b is None or ref_b == ref_a:
                continue
            a, b = sorted((ref_a, ref_b))
            pairs.add((a, b))
    return sorted(pairs)

# ── v3 신규: 질적 동기 API 3종 (Φ-3 갈등 동역학 전달) ──

def faction_wealth_distribution(self) -> dict[str, dict[str, float]]:
    """{faction_id: {"total": X, "mean": Y, "gini": Z, "top_decile_share": W}}.
    멤버 Wallet.gold 통계. 공허 faction은 전부 0. Φ-3 계급 갈등 씨앗 탐지."""
    result: dict[str, dict[str, float]] = {}
    for fid in sorted(self.factions):
        members = self._faction_members(fid)
        if not members:
            result[fid] = {"total": 0.0, "mean": 0.0, "gini": 0.0, "top_decile_share": 0.0}
            continue
        gold_sorted = sorted(m.wallet.gold for m in members)  # 결정성 + Gini 계산 전제
        n = len(gold_sorted)
        total = float(sum(gold_sorted))
        mean = total / n
        if total > 0:
            # Gini (0 균등 ~ 1 극단). 표준 공식: (2·Σ(i·x_i) / (n·Σx)) - (n+1)/n
            cum = sum(i * g for i, g in enumerate(gold_sorted, 1))
            gini = (2.0 * cum) / (n * total) - (n + 1) / n
            top_decile_n = max(1, n // 10)
            top_decile_share = sum(gold_sorted[-top_decile_n:]) / total
        else:
            gini = 0.0
            top_decile_share = 0.0
        result[fid] = {
            "total": total, "mean": mean,
            "gini": gini, "top_decile_share": top_decile_share,
        }
    return result

def faction_social_matrix(self) -> dict[tuple[str, str], float]:
    """{(fid_a, fid_b): avg_trust} — 서로 다른 faction 간 평균 trust. sorted pair (a<b).
    동일 faction 쌍 제외. 멤버 부재 시 키 생략. Φ-3 연합/대립 씨앗."""
    result: dict[tuple[str, str], float] = {}
    fids_sorted = sorted(self.factions)
    for i, fa in enumerate(fids_sorted):
        mem_a = self._faction_members(fa)
        if not mem_a:
            continue
        for fb in fids_sorted[i + 1:]:
            mem_b = self._faction_members(fb)
            if not mem_b:
                continue
            trusts = [
                self._get_relationship_trust(pa.id, pb.id)
                for pa in mem_a for pb in mem_b
            ]
            if trusts:
                result[(fa, fb)] = sum(trusts) / len(trusts)
    return result

def faction_grievance_targets(self) -> dict[str, dict[str, int]]:
    """{faction_id: {lord_id: member_count}} — faction 별 공유 분노 대상 카운트.
    InnerWorld.grievance ≥ GRIEVANCE_MIN_SHARED + lord_id not None 조건.
    Φ-3 공동 적 기반 연합 씨앗. 분노 대상 없는 faction은 `{}`."""
    result: dict[str, dict[str, int]] = {}
    for fid in sorted(self.factions):
        counts: dict[str, int] = {}
        for m in self._faction_members(fid):
            inner = self.inners[m.id]
            if (inner.grievance >= GRIEVANCE_MIN_SHARED
                    and inner.grievance_lord_id is not None):
                counts[inner.grievance_lord_id] = counts.get(inner.grievance_lord_id, 0) + 1
        result[fid] = dict(sorted(counts.items()))  # lord_id sorted 결정성
    return result
```

### 근거
- **전 7종 read-only**: Φ-3가 이 API만으로 관찰 → 결정. Φ-2 내부 state를 mutate할 경로 없음 → SSoT 보호
- **반환은 dict/list/set 신규 객체**: 호출자 mutation으로 내부 state 오염 방지 (Python mutable default 함정 차단)
- **`sorted()` 전구간**: Φ-3 테스트 결정성. seed 동일 시 반환 순서 재현
- **공허 faction 포함 (population=0, wealth=0, grievance_targets={})**: Φ-3가 "소멸 감지" + "평화로운 faction"을 명시적으로 관찰 가능
- **`factions_in_contact` 쌍 정렬 규칙**: `(a, b)` with `a < b` + 전체 `sorted()` → 중복/순서 혼란 원천 차단. social_matrix 키도 동일 규칙
- **`radius >= 1` 가드**: 0이나 음수 입력은 의미 없음, 즉시 ValueError
- **`_territories_within(tid, radius)` 헬퍼 재사용**: Decision 11이 정의하는 공용 Chebyshev util (D9/D10 공유). `radius=1`은 `_territory_neighbors` 캐시 경유 O(1), `radius≥2`는 on-demand 계산
- **질적 동기 3종 (v3 신설)**: Charter #8 4종(외형)만으로는 Φ-3 "왜 싸우는가" 부재. wealth(계급) + social matrix(연합/대립) + grievance targets(공동 적)가 Φ-3 갈등 동역학의 1차 입력
- **Gini + top_decile_share**: Phase 16 public_works/treasury 맥락 유지. 경제 불평등 지표는 표준 요약 통계만 반환(Φ-3가 raw 배열 재처리 부담 없음)
- **social_matrix sorted pair**: D10 `factions_in_contact`와 동일 규칙 → API 일관성
- **grievance_targets lord_id sorted**: 같은 faction 내에서도 동일 lord_id 순서 보장 → 결정성

### 기각
- `dict_keys`/`dict_values` 뷰 반환: caller가 collection type이라고 오인 가능
- `KeyError` 대신 `return ()`: 존재하지 않는 faction_id 호출은 Φ-3 로직 버그 신호 → 조기 FAIL이 안전
- radius 기본값 ≥ 2: 인접(1)이 표준, 멀리 떨어진 faction은 접촉이 아님
- 같은 faction 쌍 포함: 갈등 씨앗 아님(노이즈)
- wealth raw 배열 전달: Φ-3가 Gini 등 재계산 비용 부담 → 요약 통계 4종 제공이 적절
- social_matrix 대칭 행렬 전달: 데이터 2배 중복, sorted pair로 충분
- faction_wealth_distribution에 median/std 추가: Φ-3 결정 기준으로 필요 증명 없음, 필요 시 Φ-3 백로그

### 의존
- Decision 1 (Faction registry + charter 접근)
- Decision 2 (Persona.faction → population count)
- Decision 4 (`_get_relationship_trust` — social_matrix), `_faction_members` cache
- Decision 7 (Territory.factionRef → territory distribution / contact)
- Decision 11 (공용 Chebyshev adjacency util — `_territories_within` 구현체)
- Phase 14-B InnerWorld.grievance / grievance_lord_id (layers.py:938~941)
- Phase 16 Wallet.gold (wealth_distribution)

---

## Decision 11 — Adjacency util `_territory_neighbors` / `_territories_within` [확정 v3-신설]

> **v3 신설 (2026-04-23)**: Claude + Codex-A 수렴 포착 — D9 `_collect_neighbor_faction_ids`와 D10 `factions_in_contact`가 호출하는 `_territory_neighbors`/`_territories_within` 헬퍼가 실제 코드베이스에 **부재** (grep 0건). `multi_tick_engine.py:779~812 _process_movement`는 8-neighbor grid를 내부 인라인으로 처리하고 별도 util 미제공. v2 drop-in 시 NameError 확정. Φ-1 LandCell.territoryRef를 역산하여 공용 util로 추출.

### 결정

```python
# core/multi_tick_engine.py
# Φ-1 LandCell.territoryRef 기반 Chebyshev 인접 공용 util (D9·D10 공유).
# Territory dataclass에 `cells` 필드 없음(layers.py:117~163 확인) → World.iter_cells() 역산.

# __init__ 내 선언:
# self._territory_neighbors_cache: Optional[dict[str, set[str]]] = None

def _territory_neighbors(self, tid: str) -> set[str]:
    """territory tid에 Chebyshev=1 인접한 territory id 집합 (자기·None 제외).
    캐시 기반 O(1) lookup. 첫 호출 또는 무효화 이후에만 rebuild."""
    if self._territory_neighbors_cache is None:
        self._rebuild_territory_adjacency_cache()
    return self._territory_neighbors_cache.get(tid, set())

def _territories_within(self, tid: str, radius: int) -> set[str]:
    """Chebyshev radius 내 territory id 집합. radius<1 → ValueError.
    radius=1은 캐시 재사용, radius>=2는 on-demand(D10 호출 빈도 낮음)."""
    if radius < 1:
        raise ValueError(f"radius must be >= 1, got {radius}")
    if tid not in self.territories:
        return set()
    if radius == 1:
        return set(self._territory_neighbors(tid))  # 캐시 재사용 (복사본 반환)
    result: set[str] = set()
    source_cells = [(cell.x, cell.y) for cell in self.world.iter_cells()
                    if cell.territoryRef == tid]
    for (x0, y0) in source_cells:
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x0 + dx, y0 + dy
                if not self.world.in_bounds(nx, ny):
                    continue
                ref = self.world.get_cell(nx, ny).territoryRef
                if ref is not None and ref != tid:
                    result.add(ref)
    return result

def _rebuild_territory_adjacency_cache(self) -> None:
    """모든 territory의 Chebyshev=1 인접 테이블 1회 빌드.
    LandCell.territoryRef는 Φ-1 D6 `_project_territory_tick`에서 24틱 주기로만 변경 →
    그 직후 cache invalidate(= None) 후 다음 접근 시 rebuild.
    O(W·H·8). Land 50×50 기준 ~20k iter, <1ms/rebuild (확장 시 150×150 상한도 <2ms 여유 — Codex-B 실측)."""
    cache: dict[str, set[str]] = {tid: set() for tid in self.territories}
    for cell in self.world.iter_cells():
        tid = cell.territoryRef
        if tid is None:
            continue
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = cell.x + dx, cell.y + dy
                if not self.world.in_bounds(nx, ny):
                    continue
                nref = self.world.get_cell(nx, ny).territoryRef
                if nref is not None and nref != tid:
                    cache[tid].add(nref)
    self._territory_neighbors_cache = cache

# Φ-1 _project_territory_tick 말미(혹은 _auto_economy_tick 24틱 hook) 에서:
#   self._territory_neighbors_cache = None   # LandCell.territoryRef 변경 → 캐시 무효화
```

### 근거
- **Territory.cells 필드 미존재 → LandCell 역산**: layers.py:117~163 확인 — Territory dataclass에 `cells` 없음. `world.iter_cells()` 순회로 `territoryRef == tid`인 셀만 수집하는 역산만 가능. Φ-1 Charter 계약 유지(LandCell이 공간 SSoT)
- **8-neighbor Chebyshev**: Φ-1 D5 movement와 동일 규범 (Moore neighborhood). 정치적 "접촉"은 기울어진 경계까지 포함해야 자연
- **tick당 1회 rebuild 캐시**: D9 SNN telemetry가 모든 persona 매 틱 호출 → 100 persona × 50 territory × 900 cells ≈ 4.5M op/tick 재계산은 5ms 예산 초과. 1회 build + O(1) lookup으로 상환
- **캐시 무효화 24틱 주기**: LandCell.territoryRef는 Φ-1 D6 `_project_territory_tick`(24틱)에서만 변경. 그 사이는 adjacency 불변 → cache 재사용 안전
- **`_territories_within(r=1)`는 캐시 경유**: D10 `factions_in_contact(radius=1)` 기본 경로도 동일 캐시 사용 → 일관성
- **`_territories_within(r>=2)`는 on-demand**: D10 factions_in_contact(radius≥2)는 드물고(Φ-3 실험 단계), r>=2용 캐시는 메모리·빌드 비용 불균형
- **`radius >= 1` 가드**: D10 factions_in_contact 계약과 동일 (ValueError)
- **tid 미등록 시 빈 set**: `dict.get(tid, set())` — Φ-1 삭제된 territory 참조 시 graceful fail (Φ-3 설계 단순화)
- **반환은 set (불변 계약 아님)**: caller가 mutate 불가. `_territory_neighbors`는 캐시 내부 참조를 그대로 반환하지 않고 `_territories_within`이 `set(...)` 복사본 생성 — caller mutation이 cache 오염하지 않도록 안전장치

### 기각
- Territory에 `cells` 필드 신설 — Phase 17 Φ-1 Charter 계약 변경. LandCell SSoT 위배. Territory cell 집합 동기화 비용
- A* / 경로 기반 인접성 — 이동 경로와 정치적 접촉은 다른 개념. 과공학
- 캐시 없이 매번 재계산 — 5ms faction 예산 초과 확정
- `radius=0` 자기 포함 허용 — D10 factions_in_contact 자기 쌍 제외 원칙과 모순
- public API (`territory_neighbors`) — Φ-3가 접근할 공개 API는 D10 HandoffAPI 7종으로 제한. private helper로 유지
- 캐시 영구 유지 (무효화 없음) — Φ-1 D6 이후 Territory 재영토화 반영 불가

### 의존
- Φ-1 World (`iter_cells`, `get_cell`, `in_bounds`) — physis/world.py:52~60
- Φ-1 LandCell.territoryRef — physis/world.py:22~31
- Decision 7 (cache invalidation 타이밍은 `_project_faction_tick`과 동일 24틱 정렬)
- Phase 17 Φ-1 D6 `_project_territory_tick` (cache invalidate hook 부착 지점)

### Φ-2 말기/Φ-3 백로그
- `_territories_within(r>=2)` 캐시화 (D10 factions_in_contact(radius≥2) 사용 빈도 상승 시)
- Territory 생성/삭제 시 incremental cache update (현재는 24틱 전체 rebuild)

---

## Decision 간 의존 그래프 (v3)

```
Decision 1 (FactionRegistry dataclass)
    ├─→ Decision 2 (Persona.faction type = str id)
    ├─→ Decision 3 (faction_id 존재 검증)
    ├─→ Decision 6 (Faction 생성)
    └─→ Decision 10 (charter 접근)

Decision 2 (Persona 필드군)
    ├─→ Decision 3 (필드 쓰기 대상)
    ├─→ Decision 4 (affiliation_scores 누적)
    ├─→ Decision 8 (AST 검사 속성)
    ├─→ Decision 9 (faction telemetry 소스)
    └─→ Decision 10 (population count)

Decision 3 (SSoT Write Helpers — change + tick_cooldown)
    ├─→ Decision 5 (commit loop 호출 + Stage 1 매 틱 cooldown helper)
    ├─→ Decision 6 (founder birth 호출)
    └─→ Decision 8 (whitelist 마커 2종)

Decision 4 (AffiliationKernel + member cache v2)
    └─→ Decision 5 (score 읽기)

Decision 5 (FactionCommitLoop)
    └─→ Decision 7 (commit 후 projection)

Decision 6 (FounderSeed)
    ├─→ Decision 1 (Faction 등록)
    └─→ Decision 3 (birth_founder 호출)

Decision 7 (FactionProjection)
    ├─→ Territory.factionRef (Charter 계약)
    ├─→ Decision 9 (neighbor faction telemetry 소스)
    └─→ Decision 10 (territory distribution / contact 판정)

Decision 8 (AST Whitelist v2 — Assign + AugAssign + AnnAssign + Walrus)
    └─→ Decision 2, 3 참조

Decision 9 (SNN Telemetry Hook — Charter #7)
    ├─→ Decision 11 (`_territory_neighbors` 캐시 lookup)
    └─→ Phase 14-B SNN (input_current 변조만, readout 무변경)

Decision 10 (Φ-3 HandoffAPI 7종 — Charter #8 v3 확장)
    ├─→ Decision 11 (`_territories_within(radius)` 호출)
    └─→ Φ-3 진입 조건 판정 / 갈등 씨앗 탐지 (외형 4 + 질적 동기 3)

Decision 11 (Adjacency util v3)
    ├─→ Φ-1 LandCell.territoryRef (adjacency source)
    └─→ Φ-1 D6 `_project_territory_tick` (24틱 캐시 무효화 hook)
```

---

## [보류 — Φ-2 말기/Φ-3 백로그]

### Phase 5 /spec 후 500틱 실측 판단 (v2 Tier 3 이관)

| 항목 | 출처 | 모니터링 지표 |
|------|------|----------|
| R6. D6 Founder "lord 우선" 규칙 재검토 | Gemini concern (위장 top-down) | `source="affiliation"` event 비율 / `founder_count` vs `total_member_count` |
| R7. D4 `W_TERRITORY=1.0` 동적 감소 + `W_TRUST` 점진 증가 | Gemini concern (공간 결정론) | 파벌 경계 vs Φ-1 영지 경계 일치율 |
| R8. D5 `THETA_JOIN=2.5` soft-start (초기 100틱 1.5 → 2.5) | Gemini concern (유령 파벌) | 500틱 시점 `source="affiliation"` 발생 수 |

### 기존 백로그

| 항목 | 사유 |
|------|------|
| Founder 사망 시 Faction 소멸/계승 규칙 | Φ-2 말기 백로그 (Charter 제외) |
| Charter 수정·reform 메커니즘 | Φ-3 (Φ-2는 immutable) |
| 페르소나 성격별 kernel 가중치 개인화 | Φ-3 이후 (창발 복잡도 상승) |
| CommunityMetrics intra_inter_ratio를 trust_density에 반영 | Φ-2 말기 검증 후 |
| 경제 지표 기반 grievance 신호 (gold gap, treasury deficit) | Φ-3 갈등 동역학과 통합 설계 |
| Faction 간 alliance 구조 | Φ-3 |
| norm primitive 카탈로그 확장 (12→30+) | Φ-4 언어·문화 풍부화 |
| kernel 비용 최적화 (벡터화, O(N·F) → O(N+F)) | 성능 예산 초과 시 |
| Faction 소멸 시 멤버 affiliation_scores 초기화 규칙 | Φ-2 말기 |

---

## 검증 계약 (구현 후 필수 PASS)

### Hard 불변 (Charter #9 계약)
- [ ] Phase 16 Hard 5지표 전부 유지 (gold, public_works, food_stockpile, total_wealth, deaths)
- [ ] Phase 17 Φ-1 전체 23/23 테스트 PASS 유지
- [ ] `test_class_promotion.py`, `test_nomos.py`, `test_phase16_public_works.py`, `test_phase14b_snn_integration.py` ALL PASS
- [ ] SNN `n_neurons=1000` 고정 (`readout_weights_v1.npy` 호환 확인)
- [ ] 결정성: `seed=42`, 500틱 2회 snapshot 일치
  - 비교 대상: `persona.faction`, `faction_cooldown`, `affiliation_scores`, `Faction registry (id/founder_pid/charter/created_tick)`, `Territory.factionRef`
- [ ] 성능 회귀: ≤ 250ms/tick (현 154.4ms, faction 예산 ≤ 5ms)

### Decision별 검증
- [ ] **D1**: `Faction.__post_init__` charter 길이 가드 작동 (2개 또는 6개 입력 시 ValueError)
- [ ] **D1**: `faction.id`와 `faction.name` 독립 (같은 name 다른 id 허용)
- [ ] **D2**: `Persona.faction`, `faction_cooldown`, `InnerWorld.affiliation_scores` 필드 존재 + 기본값 확인
- [ ] **D3**: `_change_persona_faction` 외 경로로 `persona.faction =` 대입 grep 0건
- [ ] **D3**: invalid source 태그(`"xxx"`) 입력 시 ValueError
- [ ] **D3**: 최초 가입(prev=None) 시 cooldown=0 설정
- [ ] **D4**: DECAY 적용 확인 (48틱 연속 신호 없는 score가 0.018 수준으로 감쇠)
- [ ] **D4**: trust 0.5 중립 입력 시 trust_density 기여 0
- [ ] **D5**: FACTION_COMMIT_EVERY=48, 24틱째 commit 호출 0건
- [ ] **D5**: DRIFT_MARGIN 미달 시 source="drift" event 발생 0건
- [ ] **D6**: territory 인구 < 3이면 founder seeding 스킵
- [ ] **D6**: `_derive_rng("faction_seed", "T_claude_1")` 두 번 호출 시 동일 UUID
- [ ] **D6**: charter 길이 ∈ [3, 5], 중복 primitive 0건
- [ ] **D7**: FACTION_PROJECT_EVERY=24, 매 24틱마다 Territory.factionRef 갱신
- [ ] **D7**: HYSTERESIS=2 미만 우위일 때 기존 factionRef 유지
- [ ] **D7**: 모든 persona 해당 territory에서 faction=None 시 factionRef=None 유지
- [ ] **D8**: `persona.faction = X` 마커 없는 라인 심은 위조 파일 → `test_phase17_faction_ssot_write_is_whitelisted` FAIL 확인
- [ ] **D8 v2**: AugAssign(`persona.faction_cooldown -= 1`) 마커 없이 심은 위조 파일 → FAIL 확인 (v1 우회 경로 폐쇄 검증)
- [ ] **D9**: SNN input_current[300:350] 범위 외 값 변경 0건 (diff로 확인)
- [ ] **D9**: `readout_weights_v1.npy` SHA256 무변경 (Phase 14-B 기저 불변)
- [ ] **D9**: persona.faction=None + 이웃 territory factionRef 모두 None 시 bias 가산 0
- [ ] **D9 v3**: bias 상수 `FACTION_TELEMETRY_BIAS_OWN ≤ 0.05`, `..._NEIGHBOR ≤ 0.03` (경제 channel amplitude ≤10% 변조 보장)
- [ ] **D9 v3**: `test_phase14b_snn_integration` bias 하향 이후 PASS (경제 의사결정 회귀 없음)
- [ ] **D10**: `faction_population_distribution()` 반환에 공허 faction(멤버 0) 포함
- [ ] **D10**: `faction_charter_primitives("unknown")` → KeyError
- [ ] **D10**: `factions_in_contact(radius=0)` → ValueError
- [ ] **D10**: `factions_in_contact(radius=1)` 반환 쌍 전부 `(a, b)` with `a < b`, 전체 sorted
- [ ] **D10 v3**: `faction_wealth_distribution()` 공허 faction → `{"total":0, "mean":0, "gini":0, "top_decile_share":0}` 엔트리 포함
- [ ] **D10 v3**: `faction_wealth_distribution()` 동일 gold 전원 보유 시 `gini ≈ 0.0`
- [ ] **D10 v3**: `faction_social_matrix()` 키 전부 `(a, b)` with `a < b`, 동일 faction 쌍 포함 0건
- [ ] **D10 v3**: `faction_social_matrix()` 공허 faction 쌍은 키 생략 (None 대신 누락)
- [ ] **D10 v3**: `faction_grievance_targets()` 공허 또는 조건 미달 시 `{}` 반환
- [ ] **D10 v3**: `faction_grievance_targets()` lord_id 순서가 sorted (결정성)
- [ ] **D11**: `_territory_neighbors(tid)` Chebyshev=1 정합 (테스트용 3×3 grid에서 수동 계산 결과와 일치)
- [ ] **D11**: `_territories_within(tid, 0)` → ValueError
- [ ] **D11**: `_territories_within(tid, 1)` == `_territory_neighbors(tid)` (radius=1 캐시 경로 정합)
- [ ] **D11**: `_territories_within("unknown_tid", 1)` → 빈 set (graceful fail)
- [ ] **D11**: 공허 territory(LandCell.territoryRef=None만 존재) → `_territory_neighbors` 빈 set
- [ ] **D11**: cache rebuild ≤ 2ms (150×150 grid), `_project_territory_tick` 직후 무효화 → 다음 `_territory_neighbors` 호출 시 재빌드
- [ ] **D11**: caller의 반환 set mutation이 cache 오염 불가 (복사본 반환 확인)

### Bottom-up 실증
- [ ] **500틱 시점**: `founder_count < total_member_count` (진짜 유대 기반 성장 입증)
- [ ] **500틱 시점**: `source="affiliation"` event ≥ `source="birth_founder"` event (가입이 창시보다 많음)
- [ ] **Φ-3 재료**: `factions_in_contact(radius=1)` 호출 시 ≥2 pair 반환 (갈등 씨앗 존재)

---

## 다음 단계

1. **사용자 Decision Cards 검증** — 본 문서 수정 요청 or 확정
2. **Phase 3.5 Cross-Impact Analysis** —
   - Decision 간 충돌/중복 최종 검증 (특히 D4/D5 주기 엇갈림, D6 founder 선정과 Phase 13 lord 정의 간 정합)
   - `/sub p-charter-consistency` — society/secret-rumor/humanity/constitution ↔ Φ-2 Faction 정합성 검증 (Gemini G-WORLDVIEW 공백 해소)
3. **Phase 4 Verify** — Charter ↔ Component Map ↔ Decision Cards ↔ Phase 11-17 계약 4자 정합성
4. **Phase 5 Package** — `/spec`으로 `PHASE-17-FACTION-CODEX-INSTRUCTIONS.md` 작성 (Codex 구현 지시서)

---

## 참조

- Charter: [PHASE-17-FACTION-CHARTER.md](PHASE-17-FACTION-CHARTER.md)
- Component Map: [PHASE-17-FACTION-COMPONENT-MAP.md](PHASE-17-FACTION-COMPONENT-MAP.md)
- Φ-1 Decision Cards 선례: [PHASE-17-LAND-DECISIONS.md](PHASE-17-LAND-DECISIONS.md)
- Faction 토론 로그: `subagent-runs/discuss/phase17-phi2-step-chain-2026-04-22/`
- 기존 Persona/InnerWorld: [layers.py:747](Projects/personas/loom/ontology/layers.py#L747)
- 기존 Territory: [layers.py:118](Projects/personas/loom/ontology/layers.py#L118)
- 기존 Relationship.trust: [layers.py:1386](Projects/personas/loom/ontology/layers.py#L1386)
- Phase 14-B grievance/grievance_lord_id: [layers.py:938](Projects/personas/loom/ontology/layers.py#L938)
