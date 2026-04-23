# Phase 17 / Φ-1 Land — Decision Cards

> `/design` Phase 3 산출물. Charter([PHASE-17-LAND-CHARTER.md](PHASE-17-LAND-CHARTER.md))의 [보류] 항목을 확정 결정으로 변환.
> 각 Decision은 `/discuss --quick` 3엔진 교차 검증 + 사용자 확정 절차를 거침.
> GPT/Codex가 이 문서 + Charter만 읽고 `/spec` 구현 지시서로 변환 가능해야 함.

---

## 메타

| 항목 | 값 |
|------|-----|
| 프로젝트 | loom 페르소나 국가 시뮬 |
| Phase | 17 / Φ-1 Land |
| 선행 | Charter(Phase 1) / Component Map(Phase 2) |
| Decision 수 | 8개 (전부 확정) |
| 검증 방식 | `/discuss --quick` 3엔진 → Claude 현 체제 방향성 재검증 → 사용자 확정 |
| 날짜 | 2026-04-20 ~ 2026-04-21 |

---

## 불변 원칙 (모든 Decision이 준수)

1. **SNN 창발 최우선** — 규칙은 가이드, 창발은 SNN 내부에서 일어남
2. **Phase 11-16 무파괴** — 기존 경제/SNN 테스트 전부 PASS
3. **Φ-1 단순 휴리스틱** — 복잡한 동적 공식은 Φ-2 이후 백로그
4. **결정성 계약** — `seed=42` / `self._np_rng` / `sorted(p.id)` tie-break
5. **단방향 SSoT** — `persona.territory` 주, `territoryRef` derived
6. **현 체제 방향성 계승** — Phase 11 관례(`JOB_OUTPUT_MAP` dict, `consecutive_*` 임계값, 24틱 `_auto_economy_tick`)

---

## Decision 1 — LandCell 데이터 구조 + biome setter 계약 [확정]

### 결정
```python
@dataclass(slots=True)  # Python 3.10+ 전제. 수동 __slots__ + field(default_factory) 조합 시 Py 3.14 ValueError
class LandCell:
    x: int
    y: int
    biome: str                           # mutable (기후 엔진이 Φ-3 이후 재계산)
    elevation: int = 0
    resources: dict = field(default_factory=dict)
    path_cost: float = 1.0
    building: Optional[dict] = None
    territoryRef: Optional[str] = None
    climate: dict = field(default_factory=lambda: {"rainfall": 0.0, "temperature": 20.0})

def set_biome_initial(cell: LandCell, biome: str) -> None:
    """초기화 또는 기후 엔진 전용. 일반 코드에서 직접 biome = ... 금지."""
    assert biome in {"plain", "forest", "mountain", "water", "desert", "tundra"}
    cell.biome = biome
```

### 근거
- **mutable 채택**: frozen은 id 기반 캐시(SNN fertility_cache) 재빌드 폭발
- **`@dataclass(slots=True)`**: 2500셀 메모리 절감 + 오탈자 필드 방지. 수동 `__slots__` + `field(default_factory)` 조합은 Python 3.14에서 `ValueError` (실측 재현)
- **`set_biome_initial()` 단일 진입점**: biome은 기후 엔진의 파생값이어야 함 (Charter 계약)

### 기각
- frozen dataclass — id 재생성 비용
- `@property` setter로 property 강제 — 오버엔지니어링

### 의존
- Charter 기후 엔진 계약 (Φ-3 이후)

---

## Decision 2 — World.land 컨테이너 [확정]

### 결정
```python
class World:
    def __init__(self, width: int = 50, height: int = 50):
        self._land: list[list[LandCell]] = [[...] for _ in range(height)]  # private

    def get_cell(self, x: int, y: int) -> LandCell:
        return self._land[y][x]

    def iter_cells(self) -> Iterator[LandCell]:
        for row in self._land:
            yield from row
```

### 근거
- **`list[list[LandCell]]`**: 50×50 dense grid, 2500셀 고정. NumPy 이득 미측정
- **`get_cell(x, y)` 전용 API**: `world.land[(x,y)]` 직접 접근 금지 → 내부 자료구조 교체 여지 확보
- **dict[tuple, LandCell] 기각**: dense grid에서 해시 오버헤드

### 기각
- `dict[tuple[int, int], LandCell]` — sparse 가정 불필요
- `numpy object array` — 이중 소스 동기화 리스크

### 의존
- Decision 1 (LandCell)

---

## Decision 3 — Persona spatial 필드 위치 [확정]

### 결정
```python
@dataclass
class Persona:
    # 기존 필드 ...
    pos: tuple[int, int]
    offset: tuple[float, float] = (0.0, 0.0)
    outfit_id: Optional[str] = None

@dataclass
class InnerWorld:
    # 기존 필드 ...
    dest: Optional[tuple[int, int]] = None
    migration_cooldown: int = 0
```

### 근거
- **`pos/offset/outfit_id` → Persona**: 외부 관측 가능한 불변 상태. `employment_id` 패턴 유추
- **`dest/migration_cooldown` → InnerWorld**: 심리/계획 상태. `consecutive_hunger_ticks` 패턴 유추
- **SpatialState 별도 클래스 기각**: 현 시점 과설계

### 기각
- `DynamicRenderOverride` 패턴 — 컨벤션(outfit_id)으로 충분
- 별도 `SpatialState` dataclass — Persona/InnerWorld 양분으로 충분

### 의존
- 기존 Persona/InnerWorld ([layers.py:747](Projects/personas/loom/ontology/layers.py#L747))

---

## Decision 4 — 이동 로직 (softmax + cooldown) [확정]

### 결정
```python
# 상수 (layers.py)
MOVE_CANDIDATE_K = 5              # 후보 셀 수
MOVE_SOFTMAX_T = 0.5              # temperature (정적)
MIGRATION_COOLDOWN_DEFAULT = 6    # 틱

def move_persona(p: Persona, world: World, rng: np.random.Generator) -> None:
    if p.inner.migration_cooldown > 0:
        p.inner.migration_cooldown -= 1
        return
    candidates = _pick_move_candidates(p.pos, world, k=MOVE_CANDIDATE_K)
    # water/mountain 제외 (Charter Decision 4 정합)
    candidates = [c for c in candidates if c.biome not in {"water", "mountain"}]
    scores = np.array([score_move(c, p) for c in candidates])
    probs = softmax(scores / MOVE_SOFTMAX_T)
    idx = rng.choice(len(candidates), p=probs)
    p.pos = (candidates[idx].x, candidates[idx].y)
    p.inner.migration_cooldown = MIGRATION_COOLDOWN_DEFAULT
```

### 근거
- **Softmax T=0.5 정적**: 그리디는 창발 억제. 동적 T는 Φ-2 백로그
- **K=5 후보**: 50×50 grid / Chebyshev 인접 8셀 중 biome 필터 후 후보
- **cooldown=6 고정**: Phase 11 `consecutive_*` 관례 계승. 파라미터화는 Φ-2
- **water/mountain 제외**: biome 필터로 단순화

### 기각
- 그리디 (max score) — 창발 억제
- 동적 w_food (food_deficit_ratio 연동) — Phase 11 `hunger_ticks` 로직과 중복
- `max(4, avg_travel_to_food)` 파라미터화 — Φ-1 범위 이탈

### 의존
- Decision 5 (score_cell 함수)

---

## Decision 5 — 이동 스코어 함수 (score_move) [확정]

### 결정
```python
# Phase 11 JOB_OUTPUT_MAP 패턴 계승
MOVE_WEIGHTS: dict[str, float] = {
    "food": 2.0, "material": 1.0, "path_cost": -1.5, "dist": -0.5,
}

def score_move(cell: LandCell, persona: Persona) -> float:
    """이동 후보 셀 스코어. Φ-1은 이동만 다루며, 정주 재평가(reside)는 Φ-2에서 재도입."""
    w = MOVE_WEIGHTS
    dist = chebyshev(persona.pos, (cell.x, cell.y))
    return (
        w["food"] * cell.resources.get("food", 0.0)
        + w["material"] * cell.resources.get("material", 0.0)
        + w["path_cost"] * cell.path_cost
        + w["dist"] * dist
    )
```

### 근거
- **단일 함수 `score_move`**: Phase 11 `JOB_OUTPUT_MAP` dict 패턴 계승, 이동 전용으로 단순화
- **사회성 항 제거**: Phase 11 SNN relationship_score와 중복. 창발은 SNN 내부에서
- **mode 분기 제거**: Φ-1 호출자는 D4 `move_persona()` 단독 → `mode="reside"` 경로는 dead code. 정주 의미는 `MIGRATION_COOLDOWN_DEFAULT=6`의 수동 유지로 충분

### 기각
- `score_cell(mode='move'|'reside')` 통합 함수 — 정주 재평가 호출자 없음
- `RESIDE_WEIGHTS` 상수 — Φ-1 미사용 (Φ-2 재도입 시 정의)
- 사회성 가중치 `w_social` — SNN 중복

### Φ-2 백로그
- 정주 재평가 트리거 경로 (Charter Operating Loop 미들 레이어 능동화)
- `score_reside()` 함수 + `RESIDE_WEIGHTS` 재도입
- 재평가 주기 (매 N틱 또는 조건 기반)

### 의존
- Decision 4 (이동 로직)

---

## Decision 6 — Territory dominance 재계산 [확정]

### 결정
```python
DOMINANCE_RECALC_EVERY = 24       # _auto_economy_tick 주기
DOMINANCE_RADIUS_K = 3            # Chebyshev
DOMINANCE_VOTE_MARGIN = 2         # 최소 우위 차이

def project_territory(world: World, personas: list[Persona]) -> None:
    """24틱마다 호출. snapshot-at-entry, commit-at-tick-end."""
    snapshot = {p.id: (p.pos, p.territory) for p in sorted(personas, key=lambda p: p.id)}
    updates: dict[tuple[int, int], Optional[str]] = {}
    for cell in world.iter_cells():
        residents = [
            (pid, terr) for pid, (pos, terr) in snapshot.items()
            if chebyshev(pos, (cell.x, cell.y)) <= DOMINANCE_RADIUS_K and terr
        ]
        if not residents:
            updates[(cell.x, cell.y)] = None
            continue
        counts = Counter(terr for _, terr in residents)
        top, top_count = counts.most_common(1)[0]
        second_count = counts.most_common(2)[1][1] if len(counts) > 1 else 0
        if top_count - second_count >= DOMINANCE_VOTE_MARGIN:
            updates[(cell.x, cell.y)] = top
        # else: 기존 territoryRef 유지 (히스테리시스)
    for (x, y), ref in updates.items():
        world.get_cell(x, y).territoryRef = ref
```

### 근거
- **24틱 주기**: Phase 11 `_auto_economy_tick` 정렬. 매 틱 50000 ops 과잉
- **거주 다수결**: Charter "Territory=지배 투영" 정의 충실. Voronoi는 영주 pos 기준이라 실체 없음
- **K=3 Chebyshev**: Decision 4 K+2=r=5와 일관, Decision 5 정주 반경보다 좁음
- **2표 우위**: 1표 차 flip 방지. Phase 11 `consecutive_*` 히스테리시스 관례
- **atomicity**: snapshot → compute → commit (같은 틱 내 순서 의존 제거)
- **결정성**: `sorted(p.id)` + `Counter` insertion order

### 기각
- Voronoi (영주 pos 기준) — 영주 떠나면 지배 공허
- Dynamic hysteresis (밀도/인접 context-sensitive) — Φ-2 백로그
- `territory_class` (SETTLED/CONTESTED/WILD) derived field — Φ-2 팩션 seed 로직과 혼재 위험

### 의존
- Charter `LandCell.territoryRef`

---

## Decision 7 — region 필드 마이그레이션 [확정]

### 결정
```
Φ-1 (now):  region 쓰기 경로는 exodus 동기화 1곳만 허용.
            persona.territory 변경 시 persona.region을 목적지 territory.region으로 원자 동기화.
            다른 직접 persona.region 쓰기는 계속 금지.
            단방향 SSoT: persona.territory(주) → persona.region(legacy mirror, exodus sync)
                       persona.territory(주) → territoryRef(derived)
Φ-2:        persona.region @deprecated 주석. 신규 코드 금지 룰.
            WILD_FOODS_BY_REGION → WILD_FOODS_BY_BIOME 이전 시작.
Φ-3:        region 필드 최종 삭제. Territory.region 삭제.
            birth_region은 유지 (출생 기록 = 별개 개념).
```

### 근거
- **Φ-1 region 단일 sync 경로**: Phase 11-16 region read path가 여전히 남아 있으므로 split-state를 막으려면 exodus 동기화 1곳이 필요
- **단방향 SSoT**: `persona.territory`가 주 상태. `persona.region`은 exodus 경로에서만 따라가는 legacy mirror. `territoryRef`는 읽기 전용
- **3단계 점진**: 빅뱅은 SNN history 단절 위험. birth_region은 SNN 학습 근거로 Φ-3에서도 유지
- **Dashboard region 색상**: Φ-2 Faction 시스템이 region을 흡수할 때 함께 이전

### 기각
- Φ-2 빅뱅 (region 한 번에 제거) — Phase 11-16 테스트 대량 실패
- `territoryRef` Φ-2로 연기 (Codex 제안) — Charter Φ-1 앵커 계약 위반
- territory 변경마다 여러 곳에서 `persona.region` 동기화 — write path가 흩어져 다시 drift 위험

### 의존
- Decision 6 (territoryRef 투영)
- 별도 `/sub`: `multi_tick_engine.py:900` split-state 버그 수정 (2026-04-21 완료)

---

## Decision 8 — 초기 배치기 (Poisson disk) [확정]

### 결정
```python
# 상수 — INIT_SEED는 MultiTickEngine.__init__(seed=42)가 단일 진원지 (불변 원칙 #4)
INIT_POISSON_FALLBACK = [5, 4, 3]                          # Decision 6 K=3 + 2 = 5, 실패 시 축소
ALLOWED_INIT_BIOMES = {"plain", "forest", "desert", "tundra"}
def initialize_world(world: World, personas: list[Persona],
                     rng: np.random.Generator) -> None:
    """5단계 초기화 — RNG draw 순서 고정.
    rng는 engine._np_rng를 주입받음 (Phase 11 관례 계승, 결정성 단일 진원지)."""
    # 1. biome 초기화 (Whittaker + Perlin)        ── rng ×2500
    _init_biomes(world, rng)

    # 2. Territory 객체 생성                        ── rng 소비 없음
    _init_territories(world)

    # 3. Poisson disk 배치 (실제 persona 수 기준)   ── rng 주입
    positions = _place_poisson(world, n=len(personas), rng=rng,
                               allowed=ALLOWED_INIT_BIOMES,
                               fallback_radii=INIT_POISSON_FALLBACK)

    # 4. persona 배치 (`PERSONA_DEFS` region 분포 계승) ── rng shuffle 1회
    _assign_personas(personas, positions, rng)

    # 5. 첫 project_territory() 호출                ── rng 소비 없음
    project_territory(world, personas)


def _place_poisson(world, n, rng, allowed, fallback_radii) -> list[tuple[int, int]]:
    """Bridson O(n) 자체 구현 (physis/poisson.py ~50 LOC).
    scipy 미설치 + numpy에 공간 배치 API 없음 → 외부 의존성 추가 대신 자체 구현."""
    for r in fallback_radii:
        positions = bridson_poisson_disk(
            world, r=r, filter=allowed, rng=rng  # rng 주입으로 결정성 완전 통제
        )
        if len(positions) >= n:
            return positions[:n]
        warnings.warn(f"Poisson r={r} 실패 ({len(positions)}/{n}), r={r-1}로 재시도")
    raise RuntimeError("초기 배치 실패 — biome 분포 재검토 필요")
```

### 근거
- **r=5**: Decision 6 K=3 + 2 = 영토 분리 최소값
- **rng 외부 주입 (engine._np_rng)**: Phase 11 관례 + 불변 원칙 #4 (rng 단일 진원지). `INIT_SEED` 별도 상수는 `MultiTickEngine.__init__(seed=42)`와 이중 소스가 되므로 제거
- **biome 4종 필터**: Charter 6종 enum과 분리 개념. Decision 4 water/mountain 제외와 정합
- **region 분포**: `PERSONA_DEFS`가 진실. obsolete quota 상수보다 실제 roster를 그대로 따른다
- **5단계 순서 + RNG draw 주석**: 결정성 재현 문서화
- **fallback r=5→4→3 / 시도 횟수 기준**: 단순 휴리스틱. 실패 시 WARN 로그
- **Bridson 자체 구현**: scipy 미설치 + numpy 공간 배치 API 부재. ~50 LOC. `Projects/personas/loom/physis/poisson.py` 신규

### 기각
- `INIT_SEED=42` 별도 상수 — engine의 seed와 중복 (불변 원칙 #4 위배)
- obsolete hard-coded quota 상수 유지 — 실제 `PERSONA_DEFS`와 drift 발생, spec과 구현이 다시 분리됨
- `failure_count ≥ 3 per radius` fallback — overspec (Φ-1 단순 휴리스틱 위반)
- scipy 의존성 추가 — 50 LOC 자체 구현이 더 가벼움
- RNG draw sequence 단위 테스트 — Φ-2 백로그 (과보호). 단, Bridson 결정성 테스트 1건은 필수 (아래 검증 계약)
- Dynamic biome 필터 — 기후 엔진 Φ-3 이후

### 의존
- Decision 1 (LandCell biome)
- Decision 6 (K=3 → r=5)
- `MultiTickEngine._np_rng` (Phase 11)

---

## Decision 간 의존 그래프

```
Decision 1 (LandCell)
    ├─→ Decision 2 (World.land)
    ├─→ Decision 4 (이동 로직: biome 필터)
    └─→ Decision 8 (초기 배치: biome 필터)

Decision 3 (Persona spatial)
    └─→ Decision 4 (이동 로직: pos 갱신)

Decision 4 (이동 로직)
    ├─→ Decision 5 (score_move 단일 함수)
    └─→ Decision 6 (K=3 ↔ r=5 일관성)

Decision 5 (score_move)
    └─→ Decision 4 (호출)

Decision 6 (Territory projection)
    ├─→ Decision 7 (territoryRef 단방향 SSoT)
    └─→ Decision 8 (r = K + 2)

Decision 7 (region 마이그레이션)
    └─→ 별도 /sub (split-state 버그 수정 완료)
```

---

## [보류 — Φ-2 백로그]

| 항목 | 사유 |
|------|------|
| Dynamic softmax T (Decision 4) | 정적 T=0.5 sweep 데이터 수집 후 |
| Dynamic w_food (Decision 4) | Phase 11 hunger_ticks와 중복 |
| `avg_travel_to_food` cooldown 공식 (Decision 4) | 실측 데이터 필요 |
| `score_reside()` + `RESIDE_WEIGHTS` 재도입 (Decision 5) | Charter Operating Loop 미들 레이어 능동화 |
| 정주 재평가 트리거 경로 (Decision 5) | Φ-2 Faction 분기 조건 정의 후 |
| Dynamic hysteresis (Decision 6) | 밀도/인접 context-sensitive 복잡도 |
| `territory_class` SETTLED/CONTESTED/WILD (Decision 6) | 팩션 seed 로직은 Φ-2 |
| CONTESTED 차등 경제 규칙 (Decision 6) | Φ-2 팩션 경제 분화 |
| WILD_FOODS_BY_REGION → BY_BIOME (Decision 7) | Φ-2 이전 작업 |
| region 필드 최종 삭제 (Decision 7) | Φ-3 |
| Dashboard region 색상 제거 (Decision 7) | Φ-2 Faction 시스템 통합 |
| RNG draw sequence 단위 테스트 (Decision 8) | 과보호, 현 체제 self._np_rng 결정성으로 충분 |
| Dynamic biome 필터 (Decision 8) | 기후 엔진 Φ-3 이후 |
| SNN neuron 매핑 (Charter [보류]에서 이관) | spatial perception ↔ 경제 neuron 300~349, Φ-2 Faction 분기 조건 정의 후 설계 |

---

## 검증 계약 (구현 후 필수 PASS)

### Hard 불변 (Charter 계약)
- [ ] Phase 16 Hard 5지표 (gold, public_works, food_stockpile, total_wealth, deaths)
- [ ] `test_class_promotion.py`, `test_nomos.py`, `test_phase16_public_works.py` ALL PASS
- [ ] `test_climate_impact.py` PASS (region 필드 불변 확인)
- [ ] 결정성: `seed=42`, 500틱 2회 snapshot 일치
- [ ] 성능: ≤ 250ms/tick (현 225ms, +11% 이내)

### Decision별 검증
- [ ] **D1**: `set_biome_initial()` assert 가드 작동 (6종 biome만)
- [ ] **D2**: `get_cell(x, y)` 단독 API, `world.land[...]` 직접 접근 grep 0건
- [ ] **D3**: `Persona.pos` / `InnerWorld.migration_cooldown` 필드 존재
- [ ] **D4**: softmax T=0.5 확률 분포 재현성 (같은 seed → 같은 선택)
- [ ] **D5**: `score_move()` 호출부 존재 (D4 `move_persona()` 내부), `score_cell(..., mode="reside")` 패턴 grep 0건
- [ ] **D6**: snapshot-commit 원자성 — 같은 틱 내 순서 바꿔도 결과 동일
- [ ] **D7**: `persona.territory` 변경 시 `persona.region` 동기 갱신 (split-state 버그 재발 방지)
- [ ] **D8**: `len(PERSONA_DEFS)`명 배치 성공 (r=5 또는 fallback), region 분포가 `Counter(p["region"] for p in PERSONA_DEFS)` 와 정확히 일치
- [ ] **D8 Bridson 결정성**: 같은 rng 상태 2회 주입 → 동일한 `positions` 리스트 반환 (bit-exact)

---

## 다음 단계

1. **Phase 3.5 Cross-Impact Analysis** — Decision 간 충돌/중복 최종 검증
2. **Phase 4 Verify** — Charter ↔ Decision Cards ↔ Phase 11-16 계약 3자 정합성
3. **Phase 5 Package** — GPT/Codex에게 넘길 수 있는 형태로 번들
4. **`/spec` 전환** — Codex 구현 지시서 작성 (`PHASE-17-LAND-CODEX-INSTRUCTIONS.md`)

---

## 참조

- Charter: [PHASE-17-LAND-CHARTER.md](PHASE-17-LAND-CHARTER.md)
- 기존 Territory: [layers.py:118](Projects/personas/loom/ontology/layers.py#L118)
- 기존 Persona: [layers.py:747](Projects/personas/loom/ontology/layers.py#L747)
- split-state 버그 수정: [multi_tick_engine.py:897-923](Projects/personas/loom/core/multi_tick_engine.py#L897-L923)
- 토론 로그: `discussions/1-land-*/discussion-summary.md` (8건)
