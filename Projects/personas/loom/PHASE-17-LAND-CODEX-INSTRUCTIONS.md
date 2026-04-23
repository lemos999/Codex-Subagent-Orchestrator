# Phase 17 / Φ-1 Land — Codex Implementation Instructions

> `/spec` 산출물. Codex는 이 파일 + [PHASE-17-LAND-CHARTER.md](PHASE-17-LAND-CHARTER.md) + [PHASE-17-LAND-DECISIONS.md](PHASE-17-LAND-DECISIONS.md) 3건만 읽고 구현 가능.
>
> - 긴급도: **중간** (Φ-2 진입 선결 조건)
> - 선행 조건: Charter(Phase 1), Decisions(Phase 3), 번들 정합성 PASS(Phase 5)
> - 작업 유형: **혼합** — DB/스키마(필드 추가) + 기능(백엔드: 이동/투영/초기화) + 인프라(신규 모듈 2종)
> - DB migration: **없음** (in-memory dataclass만)
> - 외부 의존: **없음** (scipy 미사용. Bridson 자체 구현)

---

## 배경

loom 페르소나 국가 시뮬의 4단계 창발 로드맵 중 **Φ-1 Land** 구현. 페르소나가 2D tile grid 위에서 자유 이동·거주지 선택하며, 기존 Phase 11-16 경제/SNN 불변성을 유지한 채 향후 세력 형성·국가 창발의 물리적 기반 제공.

**로드맵**: Φ-1 Land → Φ-2 Faction → Φ-3 Struggle → Φ-4 Nation

**불변 원칙** (DECISIONS.md 참조):
1. SNN 창발 최우선 — 규칙은 가이드
2. Phase 11-16 무파괴 — 기존 테스트 전부 PASS
3. Φ-1 단순 휴리스틱 — 복잡 로직은 Φ-2 백로그
4. 결정성 — `seed=42` / `self._np_rng` / `sorted(p.id)` tie-break
5. 단방향 SSoT — `persona.territory` 주, `territoryRef` derived
6. 현 체제 방향성 계승 — Phase 11 관례(`JOB_OUTPUT_MAP` dict, `consecutive_*` 임계값, 24틱 주기)

---

## 작업 범위

### [필수]
1. 신규 `Projects/personas/loom/physis/world.py` — `World`, `LandCell`, `set_biome_initial`, `project_territory`, `initialize_world` + 내부 헬퍼
2. 신규 `Projects/personas/loom/physis/poisson.py` — `bridson_poisson_disk` (Bridson O(n) 자체 구현, ~50 LOC)
3. `Projects/personas/loom/ontology/layers.py` — Persona/InnerWorld 필드 추가, 이동·투영 상수, `score_move()`
4. `Projects/personas/loom/ontology/__init__.py` — 신규 심볼 export
5. `Projects/personas/loom/core/multi_tick_engine.py` — `self.world` 보유, 이동 처리, 24틱마다 `project_territory()` 호출, `initialize_world()` 훅
6. 신규 `Projects/personas/loom/test_phase17_land.py` — Decision별 검증 테스트
7. 모든 기존 Phase 16 테스트 PASS 유지 (`test_nomos.py`, `test_class_promotion.py`, `test_phase16_public_works.py`, `test_climate_impact.py`)

### [선택]
- `dashboard/server.py` 및 `dashboard/index.html` 확장 — LandCell 렌더링은 Φ-1 범위 외(Charter "실제 렌더링 미구현" 명시). 데이터만 JSON 출력 추가 가능.

### [금지]
- `persona.region` 필드 제거 금지. 직접 수정은 exodus 동기화 1곳 외 **절대 금지**
- `Territory` 기존 필드(`facilities`, `treasury`, `region` 등) 제거 금지 (Phase 11-16 무파괴)
- `Territory.id` ↔ `territoryRef` 1:1 매핑 깨뜨리기 금지
- Bridson 외부 라이브러리(scipy) 도입 금지
- `@dataclass(slots=True)` → 수동 `__slots__` 리팩토링 금지 (Py 3.14 ValueError 실측)
- `MOVE_CANDIDATE_K=5`, `MOVE_SOFTMAX_T=0.5`, `MIGRATION_COOLDOWN_DEFAULT=6`, `DOMINANCE_RECALC_EVERY=24`, `DOMINANCE_RADIUS_K=3`, `DOMINANCE_VOTE_MARGIN=2`, `INIT_POISSON_FALLBACK=[5,4,3]` 기본값 임의 변경 금지
- `score_reside()` / `RESIDE_WEIGHTS` / `score_cell(mode=...)` 구현 금지 (Φ-2 백로그)
- `INIT_SEED` 별도 상수 도입 금지 (엔진 `seed=42` 단일 진원지)

---

## 프레임워크 제약

### Python 3.14
- `@dataclass(slots=True)` 필수. 수동 `__slots__` + `field(default_factory=dict)` 조합 시 **`ValueError: 'resources' in __slots__ conflicts with class variable` 실측 재현됨** (Decision 1).

### NumPy
- RNG는 반드시 `MultiTickEngine._np_rng` 주입받아 사용. 함수 내부에서 `np.random.default_rng()` 호출 금지.
- `rng.choice(len(candidates), p=probs)` 패턴 사용.

### dataclass 순서
- 기본값 있는 필드는 기본값 없는 필드 뒤에 배치. Persona 확장 시 `pos` 는 기본값 없음(필수) vs `offset`/`outfit_id` 는 기본값 있음.
- **해결**: `pos` 기본값을 `(0, 0)` 부여(초기화에서 덮어쓰므로 안전) 또는 `initialize_world()`에서만 생성 허용.
- **채택**: `pos: tuple[int, int] = (0, 0)` 기본값 부여. 이유: 기존 `PERSONA_DEFS` 전부 `pos` 필드 없이 생성되므로 호환.

### 결정성
- `sorted(personas, key=lambda p: p.id)` — dict iteration 순서 의존 금지
- `Counter.most_common(2)` — 동점 시 insertion order 보장 (CPython 3.7+)
- Bridson 내부: 그리드 순회 시 `sorted(candidates)` 또는 명시적 순회 순서

### 성능 예산
- 현 225ms/tick, 상한 250ms/tick(+11% 이내). `project_territory()`는 24틱에 1회(2500셀 × Chebyshev 반경 3 스캔)만 호출되므로 영향 미미 예상. 필요 시 벤치 후 최적화.

---

## 구현 명세

### 1. 신규 `Projects/personas/loom/physis/poisson.py`

```python
"""Bridson Poisson-disk sampling (discrete 2D grid).

scipy 미설치 + numpy 공간 배치 API 부재로 자체 구현.
rng 외부 주입으로 결정성 완전 통제 (Phase 11 self._np_rng 패턴).
"""
from __future__ import annotations
from typing import Callable, Optional
import numpy as np


def bridson_poisson_disk(
    width: int,
    height: int,
    r: int,
    rng: np.random.Generator,
    is_allowed: Optional[Callable[[int, int], bool]] = None,
    k: int = 30,
) -> list[tuple[int, int]]:
    """Bridson O(n) Poisson-disk sampling on integer grid.

    Args:
        width, height: grid 크기
        r: minimum Chebyshev distance between samples
        rng: MultiTickEngine._np_rng 주입
        is_allowed: 셀 필터(biome 등). None이면 전체 허용
        k: 후보 시도 횟수 (Bridson 논문 기본값)

    Returns:
        결정론적 순서로 정렬된 (x, y) 리스트. 같은 rng 상태 → 같은 리스트.

    불변:
        - 모든 난수 소비는 주입된 rng에서만
        - is_allowed 필터는 candidate 생성 직후 적용
        - 동일 rng 상태 2회 주입 → bit-exact 동일 결과 (D8 검증 계약)
    """
    # Bridson 알고리즘 구현:
    # 1. 초기 점: is_allowed 통과하는 랜덤 셀 하나
    # 2. active list에 추가
    # 3. active가 빌 때까지:
    #    - active에서 무작위 선택 (rng.choice)
    #    - 주변 [r, 2r] annulus에서 k개 후보 생성
    #    - 각 후보: grid 범위 내 + is_allowed + 기존 점들과 Chebyshev >= r
    #    - 첫 유효 후보를 active + result에 추가
    #    - k개 전부 실패 시 active에서 제거
    # 4. result 정렬 후 반환 (결정성 위해 sorted((x, y)))
    ...
```

**검증**:
- `bridson_poisson_disk(50, 50, 5, rng1) == bridson_poisson_disk(50, 50, 5, rng2)` 단, rng1/rng2가 같은 seed로 초기화된 경우 (bit-exact)
- r=5, 50×50 grid, 필터 없음 → 최소 20개 반환 (empirical, Poisson disk 밀도 보장)
- r=3, 50×50 grid → 최소 50개 반환

---

### 2. 신규 `Projects/personas/loom/physis/world.py`

모듈 구성:
- `LandCell` dataclass
- `World` 클래스 (`_land`, `get_cell`, `iter_cells`, `width`, `height`)
- `set_biome_initial(cell, biome)` — biome 단일 진입점
- `project_territory(world, personas)` — 24틱마다 호출
- `initialize_world(world, personas, territories, rng)` — 5단계 초기화
- 내부 헬퍼: `_init_biomes`, `_init_territories`, `_place_poisson`, `_assign_personas`
- 거리 헬퍼: `chebyshev(a, b)`

#### LandCell

```python
from dataclasses import dataclass, field
from typing import Optional

ALLOWED_BIOMES = frozenset({"plain", "forest", "mountain", "water", "desert", "tundra"})

@dataclass(slots=True)  # Py 3.14 ValueError 회피 (수동 __slots__ 금지)
class LandCell:
    x: int
    y: int
    biome: str                                    # mutable, set_biome_initial 또는 기후 엔진만 변경
    elevation: int = 0
    resources: dict = field(default_factory=dict) # {"food": float, "material": float}
    path_cost: float = 1.0
    building: Optional[dict] = None               # {"type": str, "graphic_id": str}
    territoryRef: Optional[str] = None            # project_territory() 결과
    climate: dict = field(default_factory=lambda: {"rainfall": 0.0, "temperature": 20.0})


def set_biome_initial(cell: LandCell, biome: str) -> None:
    """biome 변경 단일 진입점. 초기화 또는 기후 엔진(Φ-3)만 호출.
    일반 코드에서 `cell.biome = ...` 직접 변경 금지."""
    assert biome in ALLOWED_BIOMES, f"Unknown biome: {biome}"
    cell.biome = biome
```

#### World

```python
from typing import Iterator

class World:
    """2D tile grid 컨테이너. MultiTickEngine이 보유."""

    def __init__(self, width: int = 50, height: int = 50):
        self.width = width
        self.height = height
        self._land: list[list[LandCell]] = [
            [LandCell(x=x, y=y, biome="plain") for x in range(width)]
            for y in range(height)
        ]

    def get_cell(self, x: int, y: int) -> LandCell:
        """좌표 단일 조회. 범위 밖이면 IndexError."""
        return self._land[y][x]

    def iter_cells(self) -> Iterator[LandCell]:
        """전체 셀 순회. 순서: row-major (y=0,x=0..) → (y=1,x=0..)."""
        for row in self._land:
            yield from row

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height
```

**금지**: `world.land` 또는 `world._land` 외부 직접 접근. 반드시 `get_cell` / `iter_cells`.

#### 거리 헬퍼

```python
def chebyshev(a: tuple[int, int], b: tuple[int, int]) -> int:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))
```

#### project_territory

```python
from collections import Counter

DOMINANCE_RECALC_EVERY = 24   # tick
DOMINANCE_RADIUS_K = 3         # Chebyshev
DOMINANCE_VOTE_MARGIN = 2      # top - second >= 2


def project_territory(world: World, personas: list) -> None:
    """Territory dominance projection. 24틱마다 호출.

    snapshot-at-entry, compute, commit-at-end (같은 틱 내 순서 독립).
    """
    # 1. snapshot — 결정성 위해 sorted(p.id)
    snapshot = {
        p.id: (p.pos, p.territory)
        for p in sorted(personas, key=lambda p: p.id)
    }
    # 2. compute — 각 셀별 dominance
    updates: dict[tuple[int, int], Optional[str]] = {}
    for cell in world.iter_cells():
        residents = [
            (pid, terr) for pid, (pos, terr) in snapshot.items()
            if chebyshev(pos, (cell.x, cell.y)) <= DOMINANCE_RADIUS_K and terr
        ]
        if not residents:
            updates[(cell.x, cell.y)] = None  # Wild
            continue
        counts = Counter(terr for _, terr in residents)
        top, top_count = counts.most_common(1)[0]
        second_count = counts.most_common(2)[1][1] if len(counts) > 1 else 0
        if top_count - second_count >= DOMINANCE_VOTE_MARGIN:
            updates[(cell.x, cell.y)] = top
        # else: 기존 territoryRef 유지 (히스테리시스)
    # 3. commit
    for (x, y), ref in updates.items():
        if ref is not None or world.get_cell(x, y).territoryRef is None:
            world.get_cell(x, y).territoryRef = ref
        # top < margin 이면서 기존 territoryRef 존재 시 유지
```

**불변**: 
- `updates` dict을 먼저 다 채운 후 commit. 순회 중 수정 금지.
- 히스테리시스: top-second < margin인 셀은 기존 territoryRef 유지.

#### initialize_world

```python
from .poisson import bridson_poisson_disk

INIT_POISSON_FALLBACK = [5, 4, 3]  # r 축소 순서
ALLOWED_INIT_BIOMES = frozenset({"plain", "forest", "desert", "tundra"})  # water/mountain 제외


def initialize_world(
    world: World,
    personas: list,
    territories: dict,
    rng: np.random.Generator,
) -> None:
    """5단계 초기화. rng는 engine._np_rng 주입.

    RNG draw 순서 (결정성):
      Phase 1: biome init  — 2500회 draw
      Phase 2: territory   — 0회
      Phase 3: Poisson     — bridson 내부 (가변, r에 따라 다름)
      Phase 4: region 할당 — persona 수 기준 shuffle
      Phase 5: 첫 project  — 0회
    """
    # 1. biome 초기화 (Whittaker + Perlin 단순판. Φ-3 이전은 랜덤)
    _init_biomes(world, rng)

    # 2. Territory 객체는 기존 factory(layers.py:172 create_default_territory)로 이미 존재.
    #    이 단계는 no-op. Territory id ↔ LandCell.territoryRef 매핑은 project_territory()가 담당.

    # 3. Poisson disk 배치
    positions = _place_poisson(world, n=len(personas), rng=rng)

    # 4. 페르소나에 pos 할당 (`PERSONA_DEFS` region 분포 계승)
    _assign_personas(personas, positions, rng)

    # 5. 첫 project_territory 호출
    project_territory(world, personas)


def _init_biomes(world: World, rng: np.random.Generator) -> None:
    """Φ-1 단순판: water 10% / mountain 10% / plain 40% / forest 25% / desert 10% / tundra 5%.
    Whittaker chart 기반. Perlin noise는 Φ-3 기후 엔진으로 이관."""
    distribution = [
        ("water", 0.10), ("mountain", 0.10), ("plain", 0.40),
        ("forest", 0.25), ("desert", 0.10), ("tundra", 0.05),
    ]
    biomes, weights = zip(*distribution)
    for cell in world.iter_cells():
        biome = rng.choice(biomes, p=weights)
        set_biome_initial(cell, biome)
        # resources 기본값: food/material 분포는 biome에 따라
        cell.resources = _default_resources(biome)


def _default_resources(biome: str) -> dict:
    """biome별 초기 자원. 수치는 Φ-2에서 튜닝."""
    return {
        "plain":    {"food": 2.0, "material": 1.0},
        "forest":   {"food": 1.5, "material": 2.5},
        "desert":   {"food": 0.3, "material": 0.5},
        "tundra":   {"food": 0.2, "material": 0.4},
        "water":    {"food": 1.0, "material": 0.0},  # 거주 불가, fishing Φ-2
        "mountain": {"food": 0.1, "material": 3.0},  # 거주 불가
    }[biome]


def _place_poisson(world: World, n: int, rng: np.random.Generator) -> list[tuple[int, int]]:
    """Bridson fallback 3단계. 실패 시 RuntimeError."""
    import warnings
    for r in INIT_POISSON_FALLBACK:
        is_allowed = lambda x, y: world.get_cell(x, y).biome in ALLOWED_INIT_BIOMES
        positions = bridson_poisson_disk(
            world.width, world.height, r=r, rng=rng, is_allowed=is_allowed
        )
        if len(positions) >= n:
            return positions[:n]
        warnings.warn(
            f"Poisson r={r} 실패 ({len(positions)}/{n}), 다음 반경으로 재시도"
        )
    raise RuntimeError(
        f"초기 배치 실패 — ALLOWED_INIT_BIOMES({ALLOWED_INIT_BIOMES}) 분포 재검토"
    )


def _assign_personas(
    personas: list,
    positions: list[tuple[int, int]],
    rng: np.random.Generator,
) -> None:
    """`PERSONA_DEFS` region 분포를 그대로 둔 채 sorted(p.id) tie-break."""
    assert len(positions) == len(personas)
    # 결정성: persona id 정렬
    sorted_personas = sorted(personas, key=lambda p: p.id)
    # position 인덱스 셔플 (결정성 유지 — rng 주입)
    indices = np.arange(len(positions))
    rng.shuffle(indices)
    for p, idx in zip(sorted_personas, indices):
        p.pos = positions[idx]
        # region은 기존 PERSONA_DEFS(claude 7 / codex 7 / gemini 6)와 이미 일치 → 수정 불필요
```

---

### 3. `Projects/personas/loom/ontology/layers.py` — 필드 + 상수 추가

#### 3-A. Persona 클래스 ([layers.py:747](Projects/personas/loom/ontology/layers.py#L747)) 에 필드 추가

기존 마지막 필드 `personality` 뒤 (line ~786)에 추가:

```python
    # ── Phase 17 / Φ-1 Land: spatial 필드 ────────────────────
    pos: tuple[int, int] = (0, 0)                       # tile 좌표. initialize_world()에서 덮어씀
    offset: tuple[float, float] = (0.0, 0.0)            # 렌더링 smooth animation 예약
    outfit_id: Optional[str] = None                     # 그래픽 예약
```

#### 3-B. InnerWorld 클래스 ([layers.py:792](Projects/personas/loom/ontology/layers.py#L792)) 에 필드 추가

기존 마지막 필드 뒤에 추가:

```python
    # ── Phase 17 / Φ-1 Land: 이동 계획 ───────────────────────
    dest: Optional[tuple[int, int]] = None              # 이동 목적지 (현 체제 미사용, Φ-2 경로 계획 예약)
    migration_cooldown: int = 0                         # 틱 단위. 0 이상이면 이동 불가
```

#### 3-C. 이동 상수 + score_move (파일 하단 `FOOD_CRISIS_COUNTER_DECAY` 등 기존 상수 다음)

```python
# ── Phase 17 / Φ-1 Land: 이동 상수 ──────────────────────────
MOVE_CANDIDATE_K = 5              # 후보 셀 수 (Chebyshev 8방향 중 biome 필터 후)
MOVE_SOFTMAX_T = 0.5              # 정적 temperature. 동적 T는 Φ-2 백로그
MIGRATION_COOLDOWN_DEFAULT = 6    # 틱. 이동 후 대기. Phase 11 consecutive_* 관례
MOVE_DISALLOWED_BIOMES = frozenset({"water", "mountain"})  # Decision 4 정합

MOVE_WEIGHTS: dict[str, float] = {
    "food": 2.0, "material": 1.0, "path_cost": -1.5, "dist": -0.5,
}


def score_move(cell, persona) -> float:
    """이동 후보 셀 스코어. Φ-1은 이동만 다루며, 정주 재평가는 Φ-2 백로그.

    Args:
        cell: LandCell
        persona: Persona (pos 필요)

    Returns:
        실수. 높을수록 선호.
    """
    w = MOVE_WEIGHTS
    # chebyshev 계산은 physis.world에서 import하지 않고 내부 계산 (순환 import 회피)
    dx = abs(persona.pos[0] - cell.x)
    dy = abs(persona.pos[1] - cell.y)
    dist = dx if dx > dy else dy
    return (
        w["food"] * cell.resources.get("food", 0.0)
        + w["material"] * cell.resources.get("material", 0.0)
        + w["path_cost"] * cell.path_cost
        + w["dist"] * dist
    )
```

**금지**: `score_reside()`, `RESIDE_WEIGHTS`, `score_cell(mode=...)` 구현 금지 (Φ-2 백로그).

---

### 4. `Projects/personas/loom/ontology/__init__.py` — Export 추가

기존 import / `__all__`에 추가:

```python
# layers.py from ... import 블록에 추가
MOVE_CANDIDATE_K, MOVE_SOFTMAX_T, MIGRATION_COOLDOWN_DEFAULT,
MOVE_DISALLOWED_BIOMES, MOVE_WEIGHTS, score_move,
```

```python
# __all__ 리스트에 추가
"MOVE_CANDIDATE_K", "MOVE_SOFTMAX_T", "MIGRATION_COOLDOWN_DEFAULT",
"MOVE_DISALLOWED_BIOMES", "MOVE_WEIGHTS", "score_move",
```

Note: `World`, `LandCell`, `initialize_world`, `project_territory` 등은 `physis/world.py`에 있으므로 `ontology/__init__.py`에 export하지 않음. Codex는 `from Projects.personas.loom.physis.world import World` 형태로 import.

---

### 5. `Projects/personas/loom/core/multi_tick_engine.py` — World 통합

#### 5-A. `__init__` ([multi_tick_engine.py:162](Projects/personas/loom/core/multi_tick_engine.py#L162))

`self._np_rng` 초기화 **다음 줄**에 `World` 생성 + `initialize_world` 호출 추가 (line 165 뒤, line 166 `self.creator` 앞):

```python
        # ── Phase 17 / Φ-1 Land ──────────────────────────────
        from Projects.personas.loom.physis.world import World  # 지연 import (순환 회피)
        self.world = World(width=50, height=50)
```

`Persona`, `InnerWorld` 생성 루프 **이후** (line 204 뒤, "적성 맵 계산" 직전 or 루프 종료 시점)에 initialize_world 호출:

```python
        # Φ-1: 모든 페르소나 생성 완료 후 world 초기화
        from Projects.personas.loom.physis.world import initialize_world
        initialize_world(
            world=self.world,
            personas=list(self.personas.values()),
            territories=None,  # 기존 territory dict (layers.py create_default_territory)
            rng=self._np_rng,
        )
```

**주의**: 적성 맵 계산 루프와 initialize_world의 RNG draw 순서 의존성 검토 필요. 현재 적성 맵은 `pdef["seed"]` 별도 seed 사용 → `self._np_rng` 미소비 → 영향 없음. 그대로 진행.

#### 5-B. 이동 처리 — `_process_movement(pid)` 신규 메서드

`_auto_economy_tick` 정의 ([multi_tick_engine.py:1090](Projects/personas/loom/core/multi_tick_engine.py#L1090)) 근처에 추가:

```python
    def _process_movement(self, pid: str) -> None:
        """Φ-1 이동 처리. 매 틱 페르소나별 호출."""
        from Projects.personas.loom.physis.world import chebyshev
        from Projects.personas.loom.ontology.layers import (
            MOVE_CANDIDATE_K, MOVE_SOFTMAX_T, MIGRATION_COOLDOWN_DEFAULT,
            MOVE_DISALLOWED_BIOMES, score_move,
        )
        persona = self.personas[pid]
        inner = self.inners[pid]
        if inner.migration_cooldown > 0:
            inner.migration_cooldown -= 1
            return
        # Chebyshev 8방향 + 제자리 → 9후보 중 범위·biome 필터
        x, y = persona.pos
        candidates = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                nx, ny = x + dx, y + dy
                if not self.world.in_bounds(nx, ny):
                    continue
                c = self.world.get_cell(nx, ny)
                if c.biome in MOVE_DISALLOWED_BIOMES:
                    continue
                candidates.append(c)
        if not candidates:
            return  # 섬 고립 — Φ-2에서 처리
        # 상위 K개 (스코어 기준)
        candidates.sort(key=lambda c: score_move(c, persona), reverse=True)
        candidates = candidates[:MOVE_CANDIDATE_K]
        scores = np.array([score_move(c, persona) for c in candidates], dtype=np.float64)
        # softmax with temperature
        scaled = scores / MOVE_SOFTMAX_T
        scaled -= scaled.max()  # 수치 안정성
        probs = np.exp(scaled)
        probs /= probs.sum()
        idx = int(self._np_rng.choice(len(candidates), p=probs))
        chosen = candidates[idx]
        if (chosen.x, chosen.y) != persona.pos:
            persona.pos = (chosen.x, chosen.y)
            inner.migration_cooldown = MIGRATION_COOLDOWN_DEFAULT
        # 제자리 선택 시 cooldown 부여하지 않음 (재시도 허용)
```

#### 5-C. tick 루프에 movement + project_territory 훅

기존 페르소나 tick 루프(매 틱 각 persona 처리) 내 적절 지점에 삽입:

```python
        for pid in sorted(self.personas.keys()):
            # ... 기존 행동 선택·에너지 갱신 ...
            self._process_movement(pid)
            # ... 기존 경제·SNN 처리 ...
```

**호출 순서 주의**: 기존 `_process_*` 메서드 중 `pos` 의존하는 메서드 없음 → 순서 자유. 일단 경제 처리 전에 배치.

`_auto_economy_tick` 주기(24틱) 호출부(line ~711) 근처에 `project_territory` 호출 추가:

```python
            if self.tick_count % DOMINANCE_RECALC_EVERY == 0:
                from Projects.personas.loom.physis.world import project_territory
                project_territory(self.world, list(self.personas.values()))
```

**상수 import**: 상단 `from Projects.personas.loom.physis.world import DOMINANCE_RECALC_EVERY` 또는 직접 `24` 상수 쓰지 말고 import.

---

### 6. 신규 `Projects/personas/loom/test_phase17_land.py`

Decision별 검증 테스트:

```python
"""Phase 17 / Φ-1 Land — Decision 검증.

실행:
    cd Projects/personas/loom && py test_phase17_land.py
"""
import numpy as np
import sys
import traceback


def test_d1_landcell_slots():
    """D1: @dataclass(slots=True) 작동, 6 biome assert."""
    from Projects.personas.loom.physis.world import LandCell, set_biome_initial
    c = LandCell(x=0, y=0, biome="plain")
    # slots: __dict__ 없음
    assert not hasattr(c, "__dict__"), "slots=True 필수"
    # biome 필터
    try:
        set_biome_initial(c, "invalid_biome")
        assert False, "6 biome 외 허용 — assert 가드 실패"
    except AssertionError:
        pass
    # 정상 6종
    for b in ("plain", "forest", "mountain", "water", "desert", "tundra"):
        set_biome_initial(c, b)
        assert c.biome == b


def test_d2_world_api():
    """D2: get_cell/iter_cells API, world._land 직접 접근 감시."""
    from Projects.personas.loom.physis.world import World
    w = World(width=50, height=50)
    assert w.width == 50 and w.height == 50
    c = w.get_cell(0, 0)
    assert (c.x, c.y) == (0, 0)
    total = sum(1 for _ in w.iter_cells())
    assert total == 2500
    assert w.in_bounds(49, 49) and not w.in_bounds(50, 50)


def test_d3_persona_fields():
    """D3: Persona.pos/offset/outfit_id + InnerWorld.dest/migration_cooldown."""
    from Projects.personas.loom.ontology.layers import Persona, InnerWorld
    p = Persona(id="t", name="t", full_name="t")
    assert hasattr(p, "pos") and p.pos == (0, 0)
    assert hasattr(p, "offset") and p.offset == (0.0, 0.0)
    assert hasattr(p, "outfit_id") and p.outfit_id is None
    iw = InnerWorld(persona_id="t")
    assert hasattr(iw, "dest") and iw.dest is None
    assert hasattr(iw, "migration_cooldown") and iw.migration_cooldown == 0


def test_d4_d5_score_move():
    """D4/D5: score_move 계산 일관성 + MOVE_WEIGHTS."""
    from Projects.personas.loom.ontology.layers import score_move, MOVE_WEIGHTS, Persona
    from Projects.personas.loom.physis.world import LandCell
    p = Persona(id="t", name="t", full_name="t")
    p.pos = (5, 5)
    c = LandCell(x=5, y=5, biome="plain")
    c.resources = {"food": 2.0, "material": 1.0}
    c.path_cost = 1.0
    expected = 2.0 * 2.0 + 1.0 * 1.0 + (-1.5) * 1.0 + (-0.5) * 0
    assert abs(score_move(c, p) - expected) < 1e-6


def test_d6_project_territory_atomicity():
    """D6: project_territory snapshot-commit, 순서 독립, 2표 우위 히스테리시스."""
    from Projects.personas.loom.physis.world import World, project_territory
    from Projects.personas.loom.ontology.layers import Persona
    w = World(10, 10)
    personas = [
        Persona(id=f"p{i}", name=f"p{i}", full_name=f"p{i}", territory="T1")
        for i in range(3)
    ]
    for i, p in enumerate(personas):
        p.pos = (5, 5)  # 전부 같은 위치 → 3표 → T1 승
    project_territory(w, personas)
    # (5,5) 주변 K=3 내 전부 T1 (3:0 → margin>=2)
    assert w.get_cell(5, 5).territoryRef == "T1"
    # 순서 바꿔도 같은 결과
    project_territory(w, list(reversed(personas)))
    assert w.get_cell(5, 5).territoryRef == "T1"


def test_d7_region_unchanged():
    """D7: region 값은 유효한 legacy label만 유지."""
    from Projects.personas.loom.core.multi_tick_engine import MultiTickEngine
    eng = MultiTickEngine(seed=42)
    for p in eng.personas.values():
        assert p.region in {"claude", "codex", "gemini"}, f"region 오염: {p.region}"


def test_d8_bridson_determinism():
    """D8: Bridson bit-exact 결정성 — 같은 seed → 같은 positions."""
    from Projects.personas.loom.physis.poisson import bridson_poisson_disk
    rng1 = np.random.default_rng(42)
    rng2 = np.random.default_rng(42)
    pos1 = bridson_poisson_disk(50, 50, r=5, rng=rng1)
    pos2 = bridson_poisson_disk(50, 50, r=5, rng=rng2)
    assert pos1 == pos2, "같은 seed → 다른 결과. Bridson 결정성 위반"


def test_d8_region_quota():
    """D8: 실제 PERSONA_DEFS region 분포와 일치."""
    from Projects.personas.loom.core.multi_tick_engine import MultiTickEngine
    eng = MultiTickEngine(seed=42)
    positions = [p.pos for p in eng.personas.values()]
    assert len(set(positions)) == len(positions), f"중복 배치: {len(positions) - len(set(positions))}건"
    # region 분포는 PERSONA_DEFS가 ground truth
    from collections import Counter
    region_counts = Counter(p.region for p in eng.personas.values())
    assert region_counts["claude"] == 7 and region_counts["codex"] == 7 and region_counts["gemini"] == 6


def test_determinism_500ticks():
    """Hard 불변: seed=42, 500틱 2회 실행 → 동일 snapshot."""
    from Projects.personas.loom.core.multi_tick_engine import MultiTickEngine
    e1 = MultiTickEngine(seed=42)
    e2 = MultiTickEngine(seed=42)
    for _ in range(500):
        e1.tick()
        e2.tick()
    s1 = {pid: (p.pos, p.territory) for pid, p in sorted(e1.personas.items())}
    s2 = {pid: (p.pos, p.territory) for pid, p in sorted(e2.personas.items())}
    assert s1 == s2, "500틱 재현성 실패"


if __name__ == "__main__":
    tests = [
        test_d1_landcell_slots, test_d2_world_api, test_d3_persona_fields,
        test_d4_d5_score_move, test_d6_project_territory_atomicity,
        test_d7_region_unchanged, test_d8_bridson_determinism,
        test_d8_region_quota, test_determinism_500ticks,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception:
            failed += 1
            print(f"FAIL {t.__name__}")
            traceback.print_exc()
    sys.exit(0 if failed == 0 else 1)
```

---

## 변경 파일

| 파일 | 작업 | 유형 | 비고 |
|------|------|:---:|------|
| `Projects/personas/loom/physis/poisson.py` | 추가 | 신규 | Bridson ~80 LOC |
| `Projects/personas/loom/physis/world.py` | 추가 | 신규 | World/LandCell/project_territory/initialize_world ~250 LOC |
| `Projects/personas/loom/ontology/layers.py` | 수정 | 필드 + 상수 + score_move | Persona/InnerWorld 각 ~3 line, 하단 상수 블록 ~30 line |
| `Projects/personas/loom/ontology/__init__.py` | 수정 | export | ~10 line |
| `Projects/personas/loom/core/multi_tick_engine.py` | 수정 | self.world + _process_movement + project hook | ~50 line |
| `Projects/personas/loom/test_phase17_land.py` | 추가 | 신규 테스트 | ~150 LOC |

**변경 없음 (금지)**:
- `Projects/personas/loom/ontology/layers.py` 내 기존 `Territory`, `Wallet`, `Job`, `Employment`, 경제 상수 블록
- `Projects/personas/loom/physis/climate_engine.py`, `planet.py`, `regions.py`
- `Projects/personas/loom/core/tick_engine.py` (single-tick engine, Φ-1 범위 외)
- 기존 테스트 `test_nomos.py`, `test_class_promotion.py`, `test_phase16_public_works.py`, `test_climate_impact.py`

---

## 검증

### 기계 검증 (필수 순서)

```bash
cd Projects/personas/loom
# 1. 타입/구문 체크
py -c "from Projects.personas.loom.physis.world import World, LandCell; from Projects.personas.loom.physis.poisson import bridson_poisson_disk; print('import OK')"
# 2. Phase 17 전용 테스트
py test_phase17_land.py
# 3. 기존 Phase 11-16 회귀
py test_nomos.py
py test_class_promotion.py
py test_phase16_public_works.py
py test_climate_impact.py
```

**모두 통과해야 완료 허용.**

### Decision별 기능 테스트 (test_phase17_land.py 체크리스트)

- [ ] D1: `LandCell` slots 작동, 6 biome assert
- [ ] D2: `World.get_cell`/`iter_cells` 작동, 2500셀, in_bounds
- [ ] D3: Persona `pos/offset/outfit_id` + InnerWorld `dest/migration_cooldown` 필드 존재
- [ ] D4/D5: `score_move` 수식 일관, MOVE_WEIGHTS 값 정확
- [ ] D6: `project_territory` snapshot-commit 순서 독립, 2표 우위 히스테리시스
- [ ] D7: 엔진 초기화 후 `persona.region ∈ {claude,codex,gemini}` 유지
- [ ] D8 결정성: 같은 seed → Bridson bit-exact 동일 positions
- [ ] D8 분포: region 분포가 `PERSONA_DEFS`와 일치
- [ ] Hard 결정성: seed=42, 500틱 2회 → 같은 스냅샷

### 계약 검증 (Charter Hard 5지표)

- [ ] `test_phase16_public_works.py` 내 `persona gold`, `public_works`, `food_stockpile`, `total_wealth`, `deaths` 전부 기존 임계값 유지
- [ ] 성능 회귀: 500틱 실행 시간 측정, ≤ 250ms/tick (현 225ms +11% 이내)

### 계약 검증 (Decisions 불변 원칙)

- [ ] `persona.region` 쓰기 경로는 exodus 동기화 1곳만 존재
- [ ] `persona.territory` 변경 시 `territoryRef` 투영만 변화 (단방향 SSoT)
- [ ] `world.land` 문자열 grep 0건 (`_land` 직접 접근 없음). 외부 코드는 `get_cell/iter_cells`만 사용
- [ ] `score_reside`, `RESIDE_WEIGHTS`, `score_cell(mode=` 문자열 grep 0건 (Φ-2 백로그)

---

## Rollback

모든 변경은 in-memory dataclass만. DB migration 없음.

```bash
# 신규 파일 제거
rm Projects/personas/loom/physis/poisson.py
rm Projects/personas/loom/physis/world.py
rm Projects/personas/loom/test_phase17_land.py
# 수정 파일 revert (git)
git checkout -- Projects/personas/loom/ontology/layers.py
git checkout -- Projects/personas/loom/ontology/__init__.py
git checkout -- Projects/personas/loom/core/multi_tick_engine.py
```

롤백 영향:
- 페르소나 `pos/offset` 필드 사라짐. Φ-1 이후 저장된 시뮬 상태 있으면 reload 실패.
- 기존 Phase 11-16 경제/SNN는 완전 유지 (무파괴 원칙).
- SNN brain weights(`brains/*.npz`) 영향 없음.

---

## Φ-2 진입 선결 검증 (구현 후 보고 필수)

다음 데이터를 500틱 실행 후 보고:
- 페르소나 공간 분포 (`pos` 히스토그램)
- `territoryRef` 커버리지 (Wild 비율, SETTLED 셀 수)
- 이동 빈도 (틱당 pos 변경 건수 평균)
- 성능 (tick 평균/최악 ms)

Φ-2 Faction 진입 조건은 이 데이터 기반으로 별도 Charter에서 결정.

---

## GPT/Codex 전달 프롬프트 템플릿

```
당신은 loom 페르소나 시뮬의 시니어 Python 개발자입니다.

프로젝트 경로: c:/Users/haj/projects/subagent-orchestrator
기술 스택: Python 3.14, NumPy, dataclass(slots), SNN 페르소나 시뮬

작업 지시서: Projects/personas/loom/PHASE-17-LAND-CODEX-INSTRUCTIONS.md
배경 문서: Projects/personas/loom/PHASE-17-LAND-CHARTER.md
결정 근거: Projects/personas/loom/PHASE-17-LAND-DECISIONS.md

3개 문서를 모두 읽고 INSTRUCTIONS 그대로 구현하세요.

절대 준수:
1. 지시서 [필수] 7항 100% 구현, [금지] 항목 절대 건드리지 말 것.
2. 수치 상수(MOVE_CANDIDATE_K=5, MIGRATION_COOLDOWN_DEFAULT=6 등) 임의 변경 금지.
3. @dataclass(slots=True) 필수. 수동 __slots__ 금지 (Py 3.14 ValueError).
4. rng는 반드시 self._np_rng 주입. 함수 내부 np.random.default_rng() 금지.
5. persona.region 필드는 exodus 동기화 1곳 외 절대 수정 금지 (Decision 7).

검증 순서:
  a. py -c "from Projects.personas.loom.physis.world import World; print('import OK')"
  b. cd Projects/personas/loom && py test_phase17_land.py  # 9건 전부 PASS
  c. py test_nomos.py && py test_class_promotion.py && py test_phase16_public_works.py && py test_climate_impact.py
  d. 실패 시 원인 분석 후 재작업. 통과할 때까지 반복.

보고 내용:
  - 변경 파일 목록 (6개)
  - 신규 파일 LOC 수 (poisson.py ~80, world.py ~250, test_phase17_land.py ~150 예상)
  - 각 검증 단계 통과 여부
  - Φ-2 진입 선결 검증 데이터 (500틱 실행 결과)
```
