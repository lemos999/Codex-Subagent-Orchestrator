# Phase 17 / Φ-2 Faction — Codex 구현 지시서

> 긴급도: 중간
> 선행 조건: Phase 17 / Φ-1 Land CLOSED (23/23 PASS, 154.4ms/tick, 2026-04-22)
> 작업 유형: 기능 (Python 시뮬 백엔드 + 새 dataclass + 새 테스트)
> DB migration: 없음 (파일 기반 시뮬, DB 없음)
> 외부 의존: 없음 (기존 `numpy`, `dataclass` 사용)

---

## 배경

loom 페르소나 시뮬의 Phase 17 4단계 로드맵(Land → **Faction** → Struggle → Nation) 중 Φ-2. Φ-1이 공간(어디)을 완성했으므로, Φ-2는 "누구와 뜻이 같은가"를 최초로 등장시킨다. Faction은 top-down 선언이 아닌 페르소나의 유대에서 자라나야 하며, Founder+Charter만 정의하고 멤버십은 affiliation kernel로 창발한다.

관련 설계 문서 (**구현자는 반드시 함께 읽을 것**):
- Charter: [PHASE-17-FACTION-CHARTER.md](Projects/personas/loom/PHASE-17-FACTION-CHARTER.md) v2 2026-04-23
- Decisions: [PHASE-17-FACTION-DECISIONS.md](Projects/personas/loom/PHASE-17-FACTION-DECISIONS.md) v3 2026-04-23
- Φ-1 Charter: [PHASE-17-LAND-CHARTER.md](Projects/personas/loom/PHASE-17-LAND-CHARTER.md) (배경 참조)

---

## 작업 범위

### [필수]
1. **Decision 1**: `Faction` dataclass + `MultiTickEngine.factions: dict[str, Faction]`
2. **Decision 2**: `Persona.faction` / `Persona.faction_cooldown` / `InnerWorld.affiliation_scores` 필드 추가 + 상수 `MAX_TRACKED_FACTIONS_PER_PERSONA=8`
3. **Decision 3**: SSoT write helper `_change_persona_faction()` + 매 틱 helper `_tick_faction_cooldown()`
4. **Decision 4**: `AffiliationKernel` — 4신호(territory/trust/grievance/proximity) 가중합 + `_faction_members_cache` + DECAY 누적
5. **Decision 5**: `FactionCommitLoop` — 48틱 주기, `THETA_JOIN=2.5`, `DRIFT_MARGIN=1.2`, snapshot→compute→commit
6. **Decision 6**: `FounderSeedGenerator` — tick=0 1회, Territory당 최대 1 founder+charter (인구 ≥3 + lord 우선)
7. **Decision 7**: `FactionProjection` — 24틱 주기, `Territory.factionRef` 투영, `FACTION_HYSTERESIS=2`
8. **Decision 8**: AST whitelist 테스트 `test_phase17_faction.py` — Assign/AugAssign/AnnAssign/NamedExpr 4종 커버
9. **Decision 9**: SNN telemetry hook `_apply_faction_telemetry()` — bias 0.05/0.03, 뉴런 300~349 co-fire
10. **Decision 10**: Φ-3 인계 API 7종 read-only
11. **Decision 11**: Adjacency util `_territory_neighbors()` / `_territories_within()` + 24틱 캐시 무효화
12. **Hard 불변 검증**: Phase 16 Hard 5지표 + Φ-1 23/23 + 4개 핵심 테스트 + SNN 1000 freeze + 결정성 + 성능 ≤250ms/tick 전부 통과

### [선택]
- Bottom-up 검증 지표 `founder_count < total_member_count` 로깅 (Charter line 325). 필수는 아니지만 디버깅 용이
- `faction_change` 이벤트 `source` 분포 로깅 (`birth_founder` vs `affiliation` vs `drift`)

### [금지]
- **SNN 구조 변경**: `n_neurons` ≠ 1000, `readout_weights_v1.npy` 수정, 뉴런 추가(350~369 등), F-cluster 뉴런군 신설 — 전부 금지
- **`persona.faction` 직접 대입**: `_change_persona_faction()` 외 경로로 `persona.faction = X` 또는 `persona.faction_cooldown = X` 절대 금지. `test_phase17_faction.py`가 AST로 차단함
- **Top-down 자동 seed**: `_init_founder_seeds()`에서 non-founder 페르소나에 `_change_persona_faction` 호출 금지 (Charter [확정] #2)
- **기존 테스트 파손**: `test_nomos.py`, `test_class_promotion.py`, `test_phase14b_snn_integration.py`, `test_phase16_public_works.py`, `test_phase17_land.py`, `test_phase17_acceptance.py` 단 한 건도 FAIL 금지
- **Phase 11~17 경제/SNN 파일 구조 변경**: `Wallet`, `InnerWorld`(신규 필드 외), `PersonaBrain`, `Territory`(factionRef 외), `Persona`(faction/faction_cooldown 외) — 기존 필드 제거/리네이밍 금지
- **norm primitive 카탈로그 확장**: 12개 고정. 초과 시 Φ-4 백로그
- **범위 밖 리팩토링**: 본 지시서에 명시되지 않은 파일 수정 금지. 특히 `dashboard/`, `scripts/` 디렉토리 수정 금지

---

## 불변 원칙 (모든 구현이 준수)

1. **Top-down 금지** — founder+charter만 정의, 멤버십은 kernel 창발
2. **Phase 11-17 무파괴** — Φ-1 23/23 PASS, 경제/SNN 테스트 전부 유지
3. **SNN `n_neurons=1000` freeze** — `readout_weights_v1.npy` 호환. 뉴런 추가 금지, 300~349 재사용만
4. **단방향 SSoT** — `persona.faction` 주, `Territory.factionRef` 파생
5. **단일 쓰기 경로** — `_change_persona_faction()` / `_tick_faction_cooldown()` 외 모든 경로 AST whitelist로 차단
6. **결정성 계약** — `_derive_rng("faction_*", key_parts)`, `sorted(pid)` tie-break, double-buffer snapshot→compute→commit
7. **Φ-1 관례 계승** — `@dataclass(slots=True)`, 24틱 `_auto_economy_tick` 정렬, `Counter.most_common` 히스테리시스

---

## 프레임워크 제약

### Python 3.14
- `@dataclass(slots=True)`는 수동 `__slots__` + `field(default_factory=...)` 조합 시 **ValueError** 발생. Φ-1 D1 실측 근거 (Land Charter §1 주석). 본 지시서의 모든 `@dataclass(slots=True)` 사용은 `field(default_factory=...)` 없이도 안전한 필드만 포함(Faction은 전부 scalar/tuple).

### numpy RNG
- `numpy.random.Generator.bytes(n)` **지원됨** — `rng.bytes(16)` → 16 바이트 반환. Decision 6의 `uuid.UUID(bytes=...)` 호출에서 사용. Claude v1의 AttributeError 우려는 철회됨(v2 실측 검증 완료).

### AST walrus 제약
- `(p.faction := X)` 같은 **attribute target walrus는 SyntaxError**. Decision 8 NamedExpr 분기는 심층 방어용으로만 유지. 실효 커버리지는 Assign/AugAssign/AnnAssign 3종.

### 속성 접근
- `MultiTickEngine`의 dict 속성은 **public** — `self.personas`, `self.territories`, `self.factions`, `self.inners`. **private 접두 `_` 금지** (실측: v2의 `_personas`/`_territories` 가정은 AttributeError 원인이었음).
- tick 카운터 접근은 `self.time.tick` (단, `_tick_faction_cooldown`처럼 메서드명에 `_tick_` 접두가 등장하는 것과 혼동 금지).

---

## 참조 코드 위치 (기존 구현 접지)

| 역할 | 파일:라인 | 용도 |
|------|-----------|------|
| `MultiTickEngine.tick()` / Stage 1 loop | [core/multi_tick_engine.py](Projects/personas/loom/core/multi_tick_engine.py) | D3 cooldown tick, D5 commit, D7 projection 호출 삽입 지점 |
| `_change_persona_territory()` | [core/multi_tick_engine.py](Projects/personas/loom/core/multi_tick_engine.py) (Φ-1 SSoT) | D3 `_change_persona_faction` 바로 옆 배치 |
| `_auto_economy_tick()` | [core/multi_tick_engine.py](Projects/personas/loom/core/multi_tick_engine.py) | D5 `_commit_faction_tick` / D7 `_project_faction_tick` 호출 후속 배치 |
| `_derive_rng()` | [core/multi_tick_engine.py](Projects/personas/loom/core/multi_tick_engine.py) (Φ-1 중앙 RNG) | D6 founder seed 생성 |
| `_process_movement` 8-neighbor 인라인 | [core/multi_tick_engine.py](Projects/personas/loom/core/multi_tick_engine.py) | D11 공용 util 추출 원본 |
| `Territory` dataclass | [ontology/layers.py:118](Projects/personas/loom/ontology/layers.py#L118) | D7 `factionRef` 필드 추가 지점 |
| `Persona` dataclass | [ontology/layers.py](Projects/personas/loom/ontology/layers.py) | D2 `faction` / `faction_cooldown` 필드 추가 지점 |
| `InnerWorld` dataclass + grievance | [ontology/layers.py:938-941](Projects/personas/loom/ontology/layers.py#L938-L941) | D2 `affiliation_scores`, D4 grievance 접근 (Persona가 아닌 InnerWorld) |
| SNN 뉴런 300~349 초기화 | [brain/persona_brain.py:100-153](Projects/personas/loom/brain/persona_brain.py#L100-L153) | D9 co-fire 대상 확인 (eco_base 전 구간 점유) |
| `World.iter_cells / get_cell / in_bounds` | [physis/world.py:52-60](Projects/personas/loom/physis/world.py#L52-L60) | D11 adjacency 계산 기반 |
| Φ-1 AST 테스트 | [test_phase17_land.py](Projects/personas/loom/test_phase17_land.py) | D8 테스트 패턴 계승 |

---

## 구현 순서 (DAG)

```
Phase A (스키마 선행) — D1, D2, D7 Territory.factionRef 필드
Phase B (쓰기 경로)  — D3 helper 2종
Phase C (AST 게이트) — D8 테스트 (빈 상태에서 먼저 통과)
Phase D (계산)       — D11 → D4 (adjacency가 kernel 일부 수식에 전제 아님, 독립 가능)
                            → D6 (founder seed, tick=0 진입 전)
Phase E (커밋·투영)  — D5 commit → D7 projection (24틱 정렬)
Phase F (SNN)        — D9 telemetry (bias 0.05/0.03 하향, 300~349 co-fire)
Phase G (인계)       — D10 7종 API
Phase H (검증)       — Hard 불변 통과, 기능 테스트, 500틱 결정성
```

**의존 그래프 요약** (Decisions v3 line 1077~1127 발췌):
- D1 → D2, D3, D6, D10
- D2 → D3, D4, D8, D9, D10
- D3 → D5, D6, D8
- D4 → D5
- D5 → D7
- D6 → D1, D3
- D7 → D9, D10
- D9 → D11
- D10 → D11
- D11 → Φ-1 LandCell.territoryRef, Φ-1 D6 `_project_territory_tick` (캐시 무효화 hook)

---

## Decision 1 — `Faction` dataclass + `factions` dict

**위치**: [ontology/layers.py:118](Projects/personas/loom/ontology/layers.py#L118) `Territory` 정의 뒤 (line ~160).

```python
from dataclasses import dataclass, field
from typing import Optional
import uuid

@dataclass(slots=True)
class Faction:
    id: str                           # stable UUID hex, 이름과 분리
    name: str                         # 표시명, 중복 허용
    founder_pid: str                  # 최초 창시자, 사망해도 유지
    charter: tuple[str, ...]          # norm primitive 3~5개, immutable
    created_tick: int

    def __post_init__(self) -> None:
        if not (3 <= len(self.charter) <= 5):
            raise ValueError(f"charter length {len(self.charter)} out of [3,5]")
        if len(set(self.charter)) != len(self.charter):
            raise ValueError(f"charter has duplicates: {self.charter}")
```

**`MultiTickEngine.__init__`에 추가**: `self.factions: dict[str, Faction] = {}`

**근거**: `@dataclass(slots=True)` Φ-1 `LandCell` 패턴 계승. `charter: tuple`은 immutable 강제 + 순서 의미 보존(선언 순위). id=UUID hex는 이름과 분리하여 동명 faction 공존 가능.

---

## Decision 2 — Persona 필드 + InnerWorld 필드

**위치**: [ontology/layers.py](Projects/personas/loom/ontology/layers.py) `Persona`와 `InnerWorld` dataclass.

```python
# Persona dataclass에 추가 (외부 관측 대상)
faction: Optional[str] = None              # faction.id, 미소속 허용
faction_cooldown: int = 0                  # 이적 후 쿨다운 잔여 틱

# InnerWorld dataclass에 추가 (내면 상태)
affiliation_scores: dict[str, float] = field(default_factory=dict)
# {faction_id: accumulated_kernel_score}

# layers.py 상수 섹션에 추가
MAX_TRACKED_FACTIONS_PER_PERSONA = 8   # dict 크기 상한 (bad-actor 방어)
```

**근거**:
- `faction`/`faction_cooldown` → Persona: 외부 관측 대상(Territory 투영, SNN telemetry, 대시보드).
- `affiliation_scores` → InnerWorld: 내면 심리 상태. Φ-1 `migration_cooldown`이 InnerWorld에 있는 것과 동일 구분. `dict` 상한 8은 파벌 폭발(수백) 방어.

---

## Decision 3 — SSoT write helpers

**위치**: [core/multi_tick_engine.py](Projects/personas/loom/core/multi_tick_engine.py) `_change_persona_territory()` 바로 옆 (line ~897).

```python
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

    self.event_log.append({
        "type": "faction_change",
        "tick": self.time.tick,
        "pid": pid,
        "from_faction": prev,
        "to_faction": new_faction_id,
        "source": source,
    })

def _tick_faction_cooldown(self, pid: str) -> None:
    """persona.faction_cooldown 매 틱 1 감소. commit loop에서 AugAssign inline하면
    48 commits × 48 tick = 2304틱 lock 버그. Stage 1 loop에서 매 틱 호출.
    """
    persona = self.personas[pid]
    if persona.faction_cooldown <= 0:
        return  # idempotent
    persona.faction_cooldown -= 1  # noqa: PHASE17_FACTION_SSOT_WRITE
```

**tick() 통합**: Stage 1 loop의 각 persona 처리 시작 부에서 `self._tick_faction_cooldown(pid)` 1회 호출 (행동 처리 이전).

**근거**: `prev == new → return` idempotent로 중복 event spam 방지. `cooldown = 최초 가입 시 0, 이적 시 48틱` — 초기 가입은 자연스러운 편입, 이적은 신중한 결정. helper 분리 이유는 48 commits lock 버그 회피.

---

## Decision 4 — AffiliationKernel

**위치**: [core/multi_tick_engine.py](Projects/personas/loom/core/multi_tick_engine.py), [ontology/layers.py](Projects/personas/loom/ontology/layers.py) 상수.

```python
# 상수 (layers.py)
W_TERRITORY   = 1.0      # 같은 territory 거주 indicator
W_TRUST       = 0.8      # 해당 faction 멤버들과 trust 평균
W_GRIEVANCE   = 0.6      # 공유 불만 (음수도 가능: 같은 상대에 대한 증오)
W_PROXIMITY   = 0.4      # Chebyshev 거리 기반 근접성
DECAY         = 0.92     # ~= 0.92^48 = 0.018, 48틱 후 거의 소멸
GRIEVANCE_MIN_SHARED = 0.3
PROXIMITY_DECAY_SCALE = 10.0

# MultiTickEngine.__init__에 추가:
# self._faction_members_cache: dict[str, list] = {}

def _rebuild_faction_members_cache(self) -> None:
    """tick당 1회 호출. faction별 member 리스트를 sorted(pid)로 고정."""
    cache: dict[str, list] = {fid: [] for fid in self.factions}
    for pid in sorted(self.personas):
        p = self.personas[pid]
        if p.faction is not None and p.faction in cache:
            cache[p.faction].append(p)
    self._faction_members_cache = cache

def _faction_members(self, faction_id: str) -> list:
    return self._faction_members_cache.get(faction_id, [])

def _same_territory(self, persona, faction_id: str) -> float:
    members = self._faction_members(faction_id)
    return 1.0 if any(m.territory == persona.territory for m in members) else 0.0

def _trust_density(self, persona, faction_id: str) -> float:
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

def _shared_grievance(self, persona, faction_id: str) -> float:
    """v3: grievance·grievance_lord_id는 InnerWorld 소재(layers.py:938~941).
    self.inners[pid] 경유 필수 (persona.grievance 직접 접근 금지)."""
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

def _spatial_proximity(self, persona, faction_id: str) -> float:
    members = self._faction_members(faction_id)
    dists = sorted(chebyshev(persona.pos, m.pos) for m in members if m.id != persona.id)[:5]
    if not dists:
        return 0.0
    avg = sum(dists) / len(dists)
    return max(0.0, 1.0 - avg / PROXIMITY_DECAY_SCALE)

def _compute_affiliation_tick(self) -> None:
    """매 틱 호출. double-buffer snapshot→compute→commit.
    v3: affiliation_scores는 InnerWorld(self.inners[pid]) 경유 (persona.inner 경로 아님)."""
    self._rebuild_faction_members_cache()
    new_scores: dict[str, dict[str, float]] = {}
    for pid in sorted(self.personas):
        persona = self.personas[pid]
        new_scores[pid] = {}
        prev_scores = self.inners[pid].affiliation_scores
        for fid in sorted(self.factions):
            score = (
                W_TERRITORY * self._same_territory(persona, fid)
                + W_TRUST     * self._trust_density(persona, fid)
                + W_GRIEVANCE * self._shared_grievance(persona, fid)
                + W_PROXIMITY * self._spatial_proximity(persona, fid)
            )
            prev = prev_scores.get(fid, 0.0)
            new_scores[pid][fid] = DECAY * prev + score
    for pid, scores in new_scores.items():
        self.inners[pid].affiliation_scores = scores
```

**근거**:
- W 계수: territory(1.0) > trust(0.8) > grievance(0.6) > proximity(0.4). territory가 최강인 이유는 공간이 유대의 최초 proxy.
- DECAY=0.92 ↔ 48틱 commit 주기: 한 번 commit 후 새 신호가 있어야 점수 유지.
- `_faction_members_cache` 캐시: O(N·F·P) → O(N·F+P). sorted(pid) 고정은 float 합산 순서 결정성 필수.
- `_shared_grievance`는 InnerWorld 경유 필수 (Persona 필드 아님).

**tick() 통합**: Stage 1 cooldown helper 직후 또는 `_auto_economy_tick` 내 — 매 틱 1회.

---

## Decision 5 — FactionCommitLoop

**위치**: [core/multi_tick_engine.py](Projects/personas/loom/core/multi_tick_engine.py), 상수는 [ontology/layers.py](Projects/personas/loom/ontology/layers.py).

```python
# 상수 (layers.py)
FACTION_COMMIT_EVERY   = 48
THETA_JOIN             = 2.5
DRIFT_MARGIN           = 1.2
# FACTION_COOLDOWN_TICKS = 48   (D3와 공유)

def _commit_faction_tick(self) -> None:
    """48틱마다 호출. _compute_affiliation_tick() 여러 번 누적 후.
    cooldown 감소는 Stage 1 helper가 담당 — 여기선 skip만."""
    if self.time.tick % FACTION_COMMIT_EVERY != 0:
        return
    snapshot = {
        pid: (
            self.personas[pid].faction,
            self.personas[pid].faction_cooldown,
            dict(self.inners[pid].affiliation_scores),
        )
        for pid in self.personas
    }
    for pid in sorted(snapshot):
        cur_fid, cooldown, scores = snapshot[pid]
        if cooldown > 0:
            continue
        if not scores:
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
            if best_score - current_score >= DRIFT_MARGIN:
                self._change_persona_faction(pid, best_fid, source="drift")
```

**tick() 통합**: `_auto_economy_tick` 직후 호출.

**근거**: 48틱 = 24틱(공간, Φ-1)의 2배 — 정치 결정은 공간이동보다 무게 있어야. `THETA_JOIN=2.5` = 2~3틱 지속 유대만 가입 허용. `DRIFT_MARGIN=1.2` = 작은 차이로 이적 방지(관성 보호). cooldown inline 금지(2304틱 lock 버그).

---

## Decision 6 — FounderSeedGenerator (tick=0 1회)

**위치**: [core/multi_tick_engine.py](Projects/personas/loom/core/multi_tick_engine.py), 상수는 [ontology/layers.py](Projects/personas/loom/ontology/layers.py).

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
CHARTER_PRIMITIVE_COUNT = (3, 5)   # (min, max) 범위

def _init_founder_seeds(self) -> None:
    """tick=0 한 번 호출. Territory당 최대 1 founder seeding."""
    for territory in sorted(self.territories.values(), key=lambda t: t.id):
        candidates = [p for p in self.personas.values() if p.territory == territory.id]
        if len(candidates) < 3:
            continue

        founder = self._pick_founder(candidates, territory)
        if founder is None:
            continue

        charter = self._sample_charter(territory.id)
        faction_id = uuid.UUID(
            bytes=self._derive_rng("faction_seed", territory.id).bytes(16)
        ).hex
        faction = Faction(
            id=faction_id,
            name=f"{territory.name}_F1",
            founder_pid=founder.id,
            charter=charter,
            created_tick=0,
        )
        self.factions[faction.id] = faction
        self._change_persona_faction(founder.id, faction.id, source="birth_founder")

def _pick_founder(self, candidates, territory):
    """우선순위: lord > 최고 평균 trust > sorted(pid)."""
    if territory.lord_id:
        for p in candidates:
            if p.id == territory.lord_id:
                return p
    def avg_trust(p):
        trusts = [
            self._get_relationship_trust(p.id, q.id)
            for q in candidates if q.id != p.id
        ]
        return sum(trusts) / len(trusts) if trusts else 0.5
    ranked = sorted(
        candidates,
        key=lambda p: (-avg_trust(p), p.id),
    )
    return ranked[0] if ranked else None

def _sample_charter(self, territory_id: str) -> tuple[str, ...]:
    rng = self._derive_rng("faction_charter", territory_id)
    n = rng.integers(CHARTER_PRIMITIVE_COUNT[0], CHARTER_PRIMITIVE_COUNT[1] + 1)
    chosen = rng.choice(NORM_PRIMITIVE_CATALOG, size=int(n), replace=False)
    return tuple(sorted(chosen))
```

**tick() 통합**: `MultiTickEngine.__init__` 또는 `tick` 첫 호출 시 `if self.time.tick == 0: self._init_founder_seeds()`.

**근거**: Territory당 1개 — 여러 faction 공존은 kernel 창발(S4)만 허용. 인구 ≥3 = founder + 잠재 멤버 2. founder: lord 우선(이미 지역 권력) → 최고 trust(유대 중심) → sorted(pid)(결정성). founder만 자동 가입 (전원 seed는 Charter [확정] #2 거부).

---

## Decision 7 — FactionProjection (Territory.factionRef 투영)

**위치**: [ontology/layers.py:118](Projects/personas/loom/ontology/layers.py#L118) Territory에 `factionRef` 필드 추가 + [core/multi_tick_engine.py](Projects/personas/loom/core/multi_tick_engine.py) 메서드.

```python
# layers.py Territory dataclass에 추가
factionRef: Optional[str] = None   # None = 공허(미지배)

# 상수
FACTION_PROJECT_EVERY = 24
FACTION_HYSTERESIS    = 2

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
            new_refs[territory.id] = None
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
            new_refs[territory.id] = prev_ref
    for tid, ref in new_refs.items():
        self.territories[tid].factionRef = ref
    # D11 캐시 무효화 (LandCell.territoryRef 변경 안 해도 factionRef 변경은 adjacency에 영향 없지만
    # D6 _project_territory_tick과 동일 24틱 타이밍 정렬 유지를 위해 여기서는 miss invalidate)
```

**tick() 통합**: `_commit_faction_tick` 직후 호출 (48틱 commit의 2배 주기 24틱이지만 동일한 24틱 순간엔 commit 전후 모두 안전).

**근거**: 24틱 = Φ-1 D6 dominance projection과 일치. `HYSTERESIS=2` = Φ-1 DOMINANCE_VOTE_MARGIN 계승. 공허(None) 허용 (Charter [확정] #3). 성능 v3 실측 **amortized 228μs/tick** (5.5ms ÷ 24).

---

## Decision 8 — AST Whitelist 테스트

**위치 (신규)**: `Projects/personas/loom/test_phase17_faction.py`

```python
"""Φ-2 Faction AST whitelist. test_phase17_land.py 패턴 계승.
AugAssign + NamedExpr(walrus) 포함으로 우회 경로 차단."""
import ast
import pathlib
import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
LOOM_ROOT = REPO_ROOT / "Projects" / "personas" / "loom"
SCAN_DIRS = ("core", "ontology", "physis", "brain")
WHITELIST_MARKER = "PHASE17_FACTION_SSOT_WRITE"
BANNED_ATTRS = ("faction", "faction_cooldown")

def _targets_from_node(node: ast.AST):
    if isinstance(node, ast.Assign):
        for t in node.targets:
            yield t
    elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
        yield node.target
    elif isinstance(node, ast.NamedExpr):
        # walrus: target은 name만 허용. `(p.faction := X)`는 SyntaxError.
        # 분기 유지는 심층 방어(미래 AST 확장/주입 대비). 본선은 Assign/AugAssign/AnnAssign.
        yield node.target

def _scan_faction_writes(tree: ast.AST, source_lines: list[str]) -> list[tuple[int, str, str]]:
    hits = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign, ast.NamedExpr)):
            continue
        for target in _targets_from_node(node):
            if not isinstance(target, ast.Attribute):
                continue
            if target.attr not in BANNED_ATTRS:
                continue
            line_idx = node.lineno - 1
            if line_idx < len(source_lines):
                if WHITELIST_MARKER in source_lines[line_idx]:
                    continue
            kind = type(node).__name__
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

**근거**: 신규 파일 (Φ-1 확장 기각 — 책임 분리). 마커 `PHASE17_FACTION_SSOT_WRITE` (Φ-1 `PHASE17_SSOT_WRITE`와 구분). 4가지 AST 노드 전부 커버. `tests/`·`dashboard/`·`scripts/` 제외. D3 helper 2종에만 마커 허용.

---

## Decision 9 — SNN Telemetry Hook

**위치**: [brain/persona_brain.py:100-153](Projects/personas/loom/brain/persona_brain.py#L100-L153) 분석 후 [core/multi_tick_engine.py](Projects/personas/loom/core/multi_tick_engine.py) `_build_persona_snn_input(pid)` 내.

```python
# 상수 (layers.py)
FACTION_TELEMETRY_BIAS_OWN       = 0.05   # 경제 채널 amplitude ≤10%
FACTION_TELEMETRY_BIAS_NEIGHBOR  = 0.03

def _apply_faction_telemetry(self, pid: str, input_current: np.ndarray) -> None:
    """경제 perception 뉴런 300~349에 faction 신호 co-fire.
    readout_weights_v1.npy 무변경. n_neurons=1000 freeze.
    input_current[300:350] 범위에만 가산."""
    persona = self.personas[pid]
    if persona.faction is not None:
        input_current[300:325] += FACTION_TELEMETRY_BIAS_OWN
    neighbor_fids = self._collect_neighbor_faction_ids(persona.territory)
    if neighbor_fids:
        own_in_neighbors = persona.faction in neighbor_fids if persona.faction else False
        bias = FACTION_TELEMETRY_BIAS_NEIGHBOR * (1.0 if not own_in_neighbors else 0.5)
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

**호출 위치**: `_build_persona_snn_input(pid)`가 기존 경제 input을 계산한 직후. `input_current` ndarray의 [300:350]만 수정, 다른 뉴런은 건드리지 않음.

**근거 (v3 bias 하향)**: persona_brain.py:100~153은 eco_base=300에서 food/tool/wealth/job/rel_wealth(+political_stress/grievance)가 300+0/10/20/30/40 각 10뉴런 폭으로 이미 stimulate. v2의 bias 0.15/0.08은 경제 신호 평탄화 → readout_weights 의미 파괴. v3 0.05/0.03로 "기존 채널 위 미세 변조(≤10% amplitude)"로 재정의. **`test_phase14b_snn_integration.py` 회귀 필수 확인**.

---

## Decision 10 — Φ-3 HandoffAPI 7종 (외형 4 + 질적 3)

**위치**: [core/multi_tick_engine.py](Projects/personas/loom/core/multi_tick_engine.py) read-only 공개 메서드.

```python
def faction_population_distribution(self) -> dict[str, int]:
    """{faction_id: member_count}. 공허 faction은 0으로 포함."""
    dist = {fid: 0 for fid in sorted(self.factions)}
    for pid in sorted(self.personas):
        fid = self.personas[pid].faction
        if fid is not None and fid in dist:
            dist[fid] += 1
    return dist

def faction_territory_distribution(self) -> dict[str, list[str]]:
    """{faction_id: [territory_id, ...]} sorted."""
    result: dict[str, list[str]] = {fid: [] for fid in sorted(self.factions)}
    for tid in sorted(self.territories):
        ref = self.territories[tid].factionRef
        if ref is not None and ref in result:
            result[ref].append(tid)
    return result

def faction_charter_primitives(self, faction_id: str) -> tuple[str, ...]:
    """Faction의 norm primitive. unknown → KeyError. immutable tuple."""
    if faction_id not in self.factions:
        raise KeyError(f"unknown faction_id: {faction_id!r}")
    return self.factions[faction_id].charter

def factions_in_contact(self, radius: int = 1) -> list[tuple[str, str]]:
    """근접 Territory 간 서로 다른 factionRef 쌍. sorted pairs (a<b)."""
    if radius < 1:
        raise ValueError(f"radius must be >= 1, got {radius}")
    pairs: set[tuple[str, str]] = set()
    for tid in sorted(self.territories):
        ref_a = self.territories[tid].factionRef
        if ref_a is None:
            continue
        for nid in self._territories_within(tid, radius):
            if nid <= tid:
                continue
            ref_b = self.territories[nid].factionRef
            if ref_b is None or ref_b == ref_a:
                continue
            a, b = sorted((ref_a, ref_b))
            pairs.add((a, b))
    return sorted(pairs)

def faction_wealth_distribution(self) -> dict[str, dict[str, float]]:
    """{faction_id: {"total", "mean", "gini", "top_decile_share"}}. Φ-3 계급 갈등 씨앗."""
    result: dict[str, dict[str, float]] = {}
    for fid in sorted(self.factions):
        members = self._faction_members(fid)
        if not members:
            result[fid] = {"total": 0.0, "mean": 0.0, "gini": 0.0, "top_decile_share": 0.0}
            continue
        gold_sorted = sorted(m.wallet.gold for m in members)
        n = len(gold_sorted)
        total = float(sum(gold_sorted))
        mean = total / n
        if total > 0:
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
    """{(fid_a, fid_b): avg_trust}. sorted pair (a<b). 동일 쌍 제외."""
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
    """{faction_id: {lord_id: member_count}}. InnerWorld.grievance ≥ GRIEVANCE_MIN_SHARED + lord_id!=None."""
    result: dict[str, dict[str, int]] = {}
    for fid in sorted(self.factions):
        counts: dict[str, int] = {}
        for m in self._faction_members(fid):
            inner = self.inners[m.id]
            if (inner.grievance >= GRIEVANCE_MIN_SHARED
                    and inner.grievance_lord_id is not None):
                counts[inner.grievance_lord_id] = counts.get(inner.grievance_lord_id, 0) + 1
        result[fid] = dict(sorted(counts.items()))
    return result
```

**근거**: 전 7종 read-only. 모든 반환은 신규 dict/list/tuple(호출자 mutation 격리). `sorted()` 전구간 — 결정성. 공허 faction 포함(소멸/평화 관찰 가능). 질적 3종은 Φ-3 "왜 싸우는가" 입력 (외형만으로 부족).

---

## Decision 11 — Adjacency util (Chebyshev, 24틱 캐시)

**위치**: [core/multi_tick_engine.py](Projects/personas/loom/core/multi_tick_engine.py). `__init__`에 `self._territory_neighbors_cache: Optional[dict[str, set[str]]] = None` 선언 필요.

```python
def _territory_neighbors(self, tid: str) -> set[str]:
    """territory tid에 Chebyshev=1 인접한 territory id 집합.
    캐시 기반 O(1) lookup."""
    if self._territory_neighbors_cache is None:
        self._rebuild_territory_adjacency_cache()
    return self._territory_neighbors_cache.get(tid, set())

def _territories_within(self, tid: str, radius: int) -> set[str]:
    """Chebyshev radius 내 territory id 집합. radius<1 → ValueError.
    radius=1은 캐시 재사용, radius>=2는 on-demand."""
    if radius < 1:
        raise ValueError(f"radius must be >= 1, got {radius}")
    if tid not in self.territories:
        return set()
    if radius == 1:
        return set(self._territory_neighbors(tid))
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
    O(W·H·8). Land 50×50 기준 ~20k iter, <1ms/rebuild
    (확장 시 150×150 상한도 <2ms — Codex-B 실측)."""
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
```

**캐시 무효화**: Φ-1 `_project_territory_tick` 말미(또는 `_auto_economy_tick` 24틱 hook)에서 `self._territory_neighbors_cache = None` 호출 — LandCell.territoryRef 변경 시점.

**근거**: Territory.cells 필드 없음(layers.py:117~163 확인) → World.iter_cells() 역산. 8-neighbor Chebyshev = Φ-1 D5 movement 규범 일치. tick당 1회 rebuild + O(1) lookup. radius>=2는 드물어 on-demand로 충분.

---

## 변경 파일

| 파일 | 작업 | 유형 |
|------|------|:---:|
| [ontology/layers.py](Projects/personas/loom/ontology/layers.py) | Faction dataclass 추가, Persona/InnerWorld 필드 추가, Territory.factionRef 추가, 상수 추가 (W_*, DECAY, THETA_JOIN, DRIFT_MARGIN, FACTION_COMMIT_EVERY, FACTION_COOLDOWN_TICKS, FACTION_PROJECT_EVERY, FACTION_HYSTERESIS, FACTION_TELEMETRY_BIAS_*, NORM_PRIMITIVE_CATALOG, CHARTER_PRIMITIVE_COUNT, MAX_TRACKED_FACTIONS_PER_PERSONA, GRIEVANCE_MIN_SHARED, PROXIMITY_DECAY_SCALE) | 수정 |
| [ontology/__init__.py](Projects/personas/loom/ontology/__init__.py) | Faction export 추가 (`from .layers import Faction`) | 수정 |
| [core/multi_tick_engine.py](Projects/personas/loom/core/multi_tick_engine.py) | `self.factions`, `self._faction_members_cache`, `self._territory_neighbors_cache` 초기화. helper 16개 추가 (`_change_persona_faction`, `_tick_faction_cooldown`, `_rebuild_faction_members_cache`, `_faction_members`, `_same_territory`, `_trust_density`, `_shared_grievance`, `_spatial_proximity`, `_compute_affiliation_tick`, `_commit_faction_tick`, `_init_founder_seeds`, `_pick_founder`, `_sample_charter`, `_project_faction_tick`, `_apply_faction_telemetry`, `_collect_neighbor_faction_ids`, `_territory_neighbors`, `_territories_within`, `_rebuild_territory_adjacency_cache`), 7종 HandoffAPI 추가 (`faction_*`). tick() Stage 1 loop에 `_tick_faction_cooldown(pid)` 호출. `_auto_economy_tick` 경로에 `_compute_affiliation_tick` / `_commit_faction_tick` / `_project_faction_tick` 호출. `__init__` 진입 직후 `_init_founder_seeds` 호출. `_build_persona_snn_input` 내 `_apply_faction_telemetry` 호출. `_project_territory_tick` 말미에 `self._territory_neighbors_cache = None` 추가 | 수정 |
| `Projects/personas/loom/test_phase17_faction.py` | 신규 AST whitelist 테스트 | 추가 |

**변경 없음 (금지):**
- `Projects/personas/loom/dashboard/` 전 파일
- `Projects/personas/loom/scripts/` 전 파일
- `Projects/personas/loom/brain/persona_brain.py` — SNN 구조 변경 금지. D9 훅은 **engine 측 `_apply_faction_telemetry`에서 `input_current` 수정만** 수행, persona_brain.py 자체는 건드리지 않음
- `Projects/personas/loom/readout_weights_v1.npy` — 가중치 파일 수정 금지
- 기존 test_*.py (test_phase17_faction.py 추가 외)
- Φ-1 관련 파일 (`test_phase17_land.py`, `PHASE-17-LAND-*.md`, `physis/world.py` — D11은 기존 메서드 **호출만**, 수정 없음)

---

## 검증

### 기계 검증 (필수 순서)
1. **타입 체크**: loom은 mypy/pyright 설정 없음 (실측). 수동 확인 대신 아래 2~5로 대체
2. **기존 테스트 전부 PASS**:
   ```bash
   cd Projects/personas/loom
   python -m pytest test_phase17_land.py -v          # Φ-1 23/23 유지
   python -m pytest test_phase14b_snn_integration.py -v   # SNN 회귀 (D9 bias 하향 영향)
   python -m pytest test_phase16_public_works.py test_nomos.py test_class_promotion.py -v   # Phase 16/15/13
   python -m pytest test_phase17_acceptance.py -v    # Phase 17 통합
   ```
3. **신규 테스트 PASS**:
   ```bash
   python -m pytest test_phase17_faction.py -v       # AST whitelist
   ```
4. **전체 스위트**:
   ```bash
   python -m pytest -v
   ```

### 기능 테스트 시나리오 (구현자가 수동 또는 pytest 추가로 확인)

- [ ] `Faction(id="x", name="n", founder_pid="p1", charter=("a","b"), created_tick=0)` → **ValueError** (charter 길이 2)
- [ ] `Faction(..., charter=("a","a","b"))` → **ValueError** (중복)
- [ ] `engine._change_persona_faction(pid, fid, source="birth_founder")` 호출 후 `persona.faction == fid`, `faction_cooldown == 0` (최초 가입)
- [ ] 같은 호출 중복 → `event_log`에 2번 push **안 됨** (idempotent)
- [ ] 이미 `faction=fid_A`인 persona에 `_change_persona_faction(pid, fid_B, source="drift")` → `faction_cooldown == 48`
- [ ] `_tick_faction_cooldown`을 48회 호출 → `faction_cooldown == 0`; 49번째 호출은 no-op
- [ ] `_change_persona_faction(pid, "unknown_fid", source="affiliation")` → **ValueError**
- [ ] `_change_persona_faction(pid, fid, source="invalid")` → **ValueError**
- [ ] `_init_founder_seeds` 후 Territory당 faction 0 또는 1개 (인구 <3 영토는 0)
- [ ] tick 48 이후 commit loop에서 kernel 2.5 이상 누적된 persona에 `source="affiliation"` event 발생
- [ ] tick 48 이후 cooldown>0 persona는 commit skip됨 (event 없음)
- [ ] `_project_faction_tick` 후 Territory.factionRef가 해당 영토 멤버 분포 최빈값 (단, HYSTERESIS=2 미만 시 prev 유지)
- [ ] `_apply_faction_telemetry` 호출 후 `input_current[300:325] += 0.05` (persona.faction!=None일 때)
- [ ] `faction_population_distribution()`: 공허 faction(멤버 0)도 dict에 키로 존재 (value=0)
- [ ] `faction_charter_primitives("unknown")` → **KeyError**
- [ ] `factions_in_contact(radius=0)` → **ValueError**
- [ ] `faction_wealth_distribution()` 공허 faction → `{"total": 0, "mean": 0, "gini": 0, "top_decile_share": 0}`
- [ ] `faction_social_matrix()` 키는 모두 `(a, b)` with `a < b`
- [ ] `_territories_within(tid, radius=0)` → **ValueError**
- [ ] `_territory_neighbors(unknown_tid)` → `set()` (빈 set, KeyError 아님)

### 계약 검증 (Hard 불변)

- [ ] Phase 16 Hard 5지표 전부 유지 (persona gold, public_works, food_stockpile, total_wealth, deaths)
- [ ] Phase 17 Φ-1 23/23 테스트 PASS 유지
- [ ] SNN `n_neurons=1000` 고정 (readout_weights_v1.npy 호환)
- [ ] **결정성**: `seed=42`, 500틱 2회 실행 snapshot 일치
  - 비교 대상: `persona.faction`, `faction_cooldown`, `affiliation_scores` (InnerWorld 경유), Faction registry (id/founder_pid/charter/created_tick), `Territory.factionRef`
  - 검증 명령 (수동):
    ```bash
    python -c "
    from core.multi_tick_engine import MultiTickEngine
    e1 = MultiTickEngine(seed=42); e1.tick_many(500)
    e2 = MultiTickEngine(seed=42); e2.tick_many(500)
    assert sorted((p.faction, p.faction_cooldown) for p in e1.personas.values()) == sorted((p.faction, p.faction_cooldown) for p in e2.personas.values())
    assert sorted((t.id, t.factionRef) for t in e1.territories.values()) == sorted((t.id, t.factionRef) for t in e2.territories.values())
    assert sorted(e1.factions) == sorted(e2.factions)
    print('determinism OK')
    "
    ```
- [ ] AST whitelist: `persona.faction =` 직접 대입 라인이 `PHASE17_FACTION_SSOT_WRITE` 마커 없이 존재하면 `test_phase17_faction.py` FAIL
- [ ] **성능**: ≤ 250ms/tick. 현 154.4ms 기준, faction kernel 예산 ≤ 5ms
  - 측정 예: `python -m pytest test_phase17_acceptance.py -v` 로그 또는 500틱 실행 wall clock
- [ ] **Bottom-up seed**: 500틱 시점에 `founder_count < total_member_count` (총 멤버 수 > founder 수)
  - 검증: `sum(1 for p in personas.values() if p.faction is not None) > len(factions)` (단, factions 수 == founder 수)

### Rollback

전부 새 필드·신규 helper·신규 테스트. 롤백은 간단:
1. `ontology/layers.py`에서 Faction dataclass 제거, Persona/InnerWorld 신규 필드 제거, Territory.factionRef 제거, 상수 블록 제거
2. `ontology/__init__.py`에서 Faction export 제거
3. `core/multi_tick_engine.py`에서 신규 helper/HandoffAPI 제거, tick() / `_auto_economy_tick` / `_build_persona_snn_input` / `_project_territory_tick`의 호출 삽입 제거, `__init__` 초기화 제거
4. `test_phase17_faction.py` 삭제

데이터 손실: 없음 (DB/파일 상태 변경 없음).

---

## 금지 사항 요약 (scope creep 방지)

- `MultiTickEngine`의 dict 속성 private 접두사 금지: `self.personas`·`self.territories`·`self.factions`·`self.inners` 모두 public
- `persona.grievance` 직접 접근 금지: **InnerWorld 필드**이므로 `self.inners[pid].grievance`/`.grievance_lord_id` 경유
- `persona.inner.affiliation_scores` 경로 금지: `self.inners[pid].affiliation_scores` 사용 (Persona에 inner 참조 없음)
- `self._tick` 금지: `self.time.tick` 사용
- `persona.faction = X` 직접 대입 금지 (`_change_persona_faction()` 경유 + `# noqa: PHASE17_FACTION_SSOT_WRITE` 마커)
- `persona.faction_cooldown -= 1` inline 금지 (`_tick_faction_cooldown()` 경유)
- `NORM_PRIMITIVE_CATALOG` 12개 초과 금지
- `FACTION_TELEMETRY_BIAS_OWN/NEIGHBOR` 값 0.05/0.03 고정 (v3 하향 결정)
- `FACTION_COMMIT_EVERY=48`, `FACTION_PROJECT_EVERY=24` 고정 (Φ-1 D6 주기 정렬)
- 신규 SNN 뉴런 추가·readout_weights 수정 금지
- `_territory_neighbors` / `_territories_within`을 public API로 노출 금지 (private helper 유지)
- 캐시 영구 유지 금지 (`_project_territory_tick` 말미 None 리셋 필수)

---

## 참고 사항

- **Φ-1 관례 확인 권장**: 구현 착수 전 `_change_persona_territory`, `_project_territory_tick`, `_derive_rng`, Φ-1 AST 테스트 `test_phase17_land.py` 패턴을 먼저 훑어 관례를 맞추라. Φ-2 Charter/Decisions가 전부 Φ-1 관례 계승을 전제로 설계됨.
- **5엔진 재검증 로그**: `subagent-runs/discuss/phase17-phi2-decisions-v2-verify-2026-04-23-quick/` — v3 변경 이유(V1~V8)의 증거. 구현 중 의심 발생 시 참조.
- **3엔진 토론 로그**: `subagent-runs/discuss/phase17-phi2-step-chain-2026-04-22/` — Charter [확정] #1~#7 근거.
- **Tier 3 백로그**: Gemini 단독 포착 R6~R8(D6 lord 우선, D4 W_TERRITORY 동적, D5 THETA_JOIN soft-start) — **Phase 5 이후 500틱 실측 판단으로 이관**. 이번 구현 스코프 아님.
