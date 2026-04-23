# Phase 17 / Φ-1 Land — Project Charter

> `/design` Phase 1 산출물. GPT/Codex가 이 Charter만 읽고 Phase 2 Component Map 또는 `/spec` 단계로 넘길 수 있는 수준으로 작성.
> 선행: `/discuss` 3엔진 토론 (2026-04-19), 사용자 확정 제약 (2D/2.5D/3D 그래픽).

---

## 메타

| 항목 | 값 |
|------|-----|
| 프로젝트 | loom 페르소나 국가 시뮬 |
| Phase | 17 (Φ-1 Land) |
| 로드맵 위치 | **Φ-1 Land** → Φ-2 Faction → Φ-3 Struggle → Φ-4 Nation |
| 선행 합의 | LandCell + Territory 이원 분리 / Phase 11-16 무파괴 / 2D tile grid 확정 |
| 날짜 | 2026-04-20 |

---

## Primary Outcome

페르소나가 **2D tile grid 위에서 자유 이동·거주지 선택**하며, 기존 경제·SNN 불변성을 유지한 채 향후 세력 형성·국가 창발의 **물리적 기반**을 제공한다.

**핵심 시나리오**: 페르소나 A가 자원 풍부한 LandCell로 이주 → 이웃 페르소나와 공간적 근접성 발생 → 이 spatial 데이터가 Φ-2 Faction 단계에서 SNN 유사성 + 공간 근접성 기반 세력 응집의 **seed**가 된다.

---

## Operating Loop

- **마이크로 (틱 단위)**: LandCell 자원·비용 스캔 → 이동/정주 결정 → `persona.pos` 갱신 → `migration_cooldown` 감쇠
- **미들 (수십~수백 틱)**: 거주지 선호 형성 → 이동 빈도 안정화 → Territory 지배권 동적 재계산 (`LandCell.territoryRef` 집합의 dominance projection)
- **매크로 (수천 틱, 목표 지향형)**: 페르소나 공간 분포 편향 → 세력 seed 출현 → **Φ-2 Faction 진입 조건 충족**

---

## Baseline Expectations

**포함**:
1. 모든 페르소나는 `(x, y)` tile 좌표 + 선택적 `offset(float, float)` 보유
2. LandCell 단위 지형/자원/이동비용 (`biome`, `elevation`, `resources`, `path_cost`)
3. 기존 Territory 개체와 호환 (`LandCell.territoryRef` 앵커로 Phase 11-16 경제 경로 무파괴)
4. 좌표·이동이 SNN·경제·결정성 계약에 부수 효과 없음
5. 2D/2.5D/3D 렌더링 준비 예약 필드 (`elevation`, `graphic_id`, `outfit_id`)
6. 결정론적 이동 (seed=42 재현, 순수 arithmetic)

**제외 (이번 Phase 비범위)**:
- 실제 pathfinding 알고리즘 (A*, Dijkstra 등) → Φ-2
- 전투·약탈 시스템 → Φ-3
- 이념·문화·언어 층 → Φ-4 또는 별도 Charter
- **대체**: Φ-1은 데이터 구조 + 단순 휴리스틱 이동(그리디 또는 랜덤 가중)만. 실제 알고리즘은 Φ-2 이후.

---

## Differentiation Thesis

**"페르소나 국가 시뮬인데, 국가를 top-down 규정이 아닌 공간 위 창발의 산출물로 설계하기 때문에, 자율적 문명 형성의 물리적 씨앗이 생긴다."**

- 기존 Civilization류 게임: 설계자가 도시·국가·유닛을 고정 정의
- loom Φ-1: LandCell과 페르소나만 정의, 영지·세력·국가는 **spatial 분포의 창발적 투영**

---

## Target Audience

| 항목 | 결정 |
|------|------|
| 대상 사용자 | loom 시뮬 개발자(본인), 향후 그래픽 엔진 통합자 |
| 사용 환경 | `MultiTickEngine` (Python 3.x), 500~수천 틱 단위 시뮬 |
| 허용 복잡도 | 중간 — 데이터 구조 도입, 행동 로직 변경 최소화 |
| 기대 사용 빈도 | 매 틱 수천~수만 회 호출 (성능 예산: 현 225ms/tick 내) |
| 핵심 제약 | Phase 11-16 경제/SNN 무파괴, 결정성 유지, 500틱 Hard 5지표 유지 |

---

## Charter 일관성 검증

- [x] Primary Outcome 1가지 확정
- [x] 3레이어 Operating Loop 한 문장씩
- [x] Baseline 포함/제외 결정
- [x] Differentiation Thesis 한 문장
- [x] Target Audience 환경/제약 확정
- [x] Primary Outcome ↔ Operating Loop 양립? — 마이크로 이동이 매크로 세력 seed에 피드
- [x] Differentiation ↔ Baseline 모순 없음? — "창발 지향 vs 무파괴 원칙" 잠재 상충 → 해소: LandCell은 **추가 레이어**, Territory는 **의미 재해석만** (구조 파괴 아님)
- [x] Target 허용 복잡도 ↔ Primary Outcome 일치? — 중간 복잡도로 spatial agency만 도입, 창발 로직은 Φ-2 이후
- [x] 3레이어 모두 Primary Outcome 강화? — 마이크로(이동) → 미들(정주) → 매크로(분포 편향) 전부 세력 seed 방향
- [x] 마이크로 → 미들 → 매크로 피드 연결? — `pos` 갱신 → 정주 안정화 → 분포 편향
- [x] 매크로가 순환형? — **목표 지향형** (Φ-2 진입 조건이 최종 goal)

**결과**: **PASS**

---

## [확정 선행 결정] — Phase 2/3 스텁

다음 Phase(Component Map, Decision Card)에서 확장되지만 Charter 단계에서 이미 결정된 사항.

### 1. LandCell 스키마 (최소 필드)

```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass(slots=True)  # Py 3.14 수동 __slots__ + field(default_factory) ValueError 회피 (Decision 1 실측 근거)
class LandCell:
    x: int
    y: int
    biome: str                                # "plain" | "forest" | "mountain" | "water" | "desert" | "tundra"
    elevation: int = 0                        # 3D 확장 예약 + 기후 모델 입력
    resources: dict = field(default_factory=dict)  # {"food": 2.0, "material": 1.0}
    path_cost: float = 1.0                    # 이동비용 (>0)
    building: Optional[dict] = None           # {"type": "house", "graphic_id": "..."}
    territoryRef: Optional[str] = None        # dominance projection 결과 (동적)
    # ── 기후 엔진 계약 예약 (Φ-3 이후) ────────────────────
    climate: dict = field(default_factory=lambda: {
        "rainfall": 0.0,                      # 누적 강수량 (기후 엔진 입력)
        "temperature": 20.0,                  # 평균 온도
    })
    # biome은 mutable — 기후 엔진이 climate 기반으로 재계산 가능
    # Φ-1: 정적 초기화만, climate 필드는 데이터만 저장 (미사용)
```

### 2. Persona spatial 필드 (추가)

```python
# Persona or InnerWorld
pos: tuple[int, int]                          # tile 좌표
offset: tuple[float, float] = (0.0, 0.0)      # 렌더링 smooth animation 예약
dest: Optional[tuple[int, int]] = None        # 이동 목적지
migration_cooldown: int = 0                   # 틱 단위, 0 미만 이동 불가
outfit_id: Optional[str] = None               # 그래픽 예약
```

### 3. Territory 재정의 — dominance projection

- **기존** ([layers.py:118](Projects/personas/loom/ontology/layers.py#L118)): 고정 배치된 개체, facilities·treasury 등 보유
- **신규**: 위 필드 유지 + **LandCell 집합의 동적 투영**
  ```python
  @property
  def cells(self) -> set[tuple[int, int]]:
      return {(c.x, c.y) for c in world.iter_cells() if c.territoryRef == self.id}  # Decision 2: world.land dict 직접 접근 금지, iter_cells() 전용
  ```
- 초기 마이그레이션: 기존 `region` 필드로부터 `territoryRef` 할당 → 기존 동작 유지

### 4. Phase 11-16 마이그레이션 앵커

- `LandCell.territoryRef` = 기존 `Territory.id`와 1:1 매핑
- 공공근로·식량정책·SNN 신호: 전부 `territory_id`로 조회 유지 → **무파괴**
- `Territory.region` (legacy): deprecated 표시, 제거는 **Φ-2 이후**
- `persona.region` 쓰기: exodus 시 `territory` 변경과 함께 원자 동기화. 그 외 직접 쓰기 금지.

### 5. 그래픽 확장 예약 필드 (렌더링 계약)

| 필드 | 렌더링 용도 |
|------|-------------|
| `LandCell.biome` | 지형 sprite/terrain mesh 매핑 키 |
| `LandCell.elevation` | 3D height / 2.5D isometric stacking |
| `LandCell.building.graphic_id` | 건물 모델 ID |
| `Persona.outfit_id` | 캐릭터 sprite overlay |
| `Persona.offset` | 타일 내 smooth 이동 애니메이션 |

이 필드들은 **Phase 17에서는 데이터만 저장**하고 렌더링은 미구현.

### 6. 검증 계약 (Hard 불변)

Phase 17 구현 후 반드시 통과:
- [ ] Phase 16 Hard 5지표 전부 유지 (persona gold, public_works, food_stockpile, total_wealth, deaths)
- [ ] `test_class_promotion.py`, `test_nomos.py`, `test_phase16_public_works.py` ALL PASS
- [ ] 결정성: seed=42, 500틱 2회 실행 snapshot 일치
- [ ] 성능 회귀: ≤ 250ms/tick (현재 225ms 대비 +11% 이내)

---

## [보류 해소 현황] — Phase 5 Package 시점

| 항목 | 해소 위치 |
|------|-----------|
| `World.land` 격자 컨테이너 | Decision 2 (50×50 dense `list[list[LandCell]]`) |
| 이동 휴리스틱 | Decision 4 (softmax T=0.5) + Decision 5 (score_move) |
| `migration_cooldown` 기본값·감쇠율 | Decision 4 (기본 6틱, 매 틱 -1) |
| 초기 페르소나 배치 | Decision 8 (Poisson disk r=5→4→3 fallback) |
| 영지 수·크기 | 기존 Territory factory 위임 ([layers.py:172](Projects/personas/loom/ontology/layers.py#L172)) — Φ-1 신규 결정 없음 |
| SNN neuron 매핑 (spatial ↔ neuron 300~349) | **Φ-2 백로그** — Faction 분기 조건 정의 후 설계 ([PHASE-17-LAND-DECISIONS.md](PHASE-17-LAND-DECISIONS.md) `[보류 — Φ-2 백로그]`) |
| Φ-2 Faction seed 출력 형식 | **별도 Charter** (Φ-2 진입 시) |

---

## [확정] — 사용자 결정 완료 (2026-04-20)

1. **world size**: **50×50 (2500 tiles)**
   - 근거: 현재 `PERSONA_DEFS` 10명 기준 tile/persona=250. Φ-2에서 roster 확장 시 world size 재평가 가능

2. **biome 종류**: **6종 — plain / forest / mountain / water / desert / tundra**
   - 근거: Whittaker biome chart 기반 지구 생태계 대표
   - **기후 엔진 계약 (중요)**: biome은 **mutable** — 기후 엔진의 결과물이어야 함
     - 사막에 비 계속 오면 사막 아님 → biome은 강수/온도/고도의 파생값
     - Φ-1: biome은 정적 초기화 + **mutable 계약만 예약** (기후 엔진은 Φ-3 이후)
     - LandCell에 `climate: dict = field(default_factory=lambda: {"rainfall": 0.0, "temperature": 20.0})` 추가 (기후 입력 예약)
     - `biome` setter는 기후 엔진만 호출 (향후 계약)

3. **좌표 연속성**: **혼합 — pos(정수 tile) + offset(소수 렌더링용)**
   - 시뮬 로직: 정수 tile만 (결정성·성능)
   - 렌더링: offset으로 tile 내 부드러운 이동 표현 (Stardew Valley·RimWorld 방식)

4. **초기 페르소나 배치**: **Poisson disk sampling + biome 필터**
   - 거주 불가 biome (water/mountain) 제외
   - 최소 거리 3 tile 보장
   - 무작위성 유지 + 병리적 쏠림 차단

5. **Φ-2 진입 트리거**: **보류** — Φ-1 운영 데이터 쌓은 후 Φ-2 Charter에서 결정

---

## 다음 단계

1. **사용자 Charter 검증** — 본 문서 수정 요청 or 확정
2. **[미결] 5개 항목 사용자 결정** — 특히 #1 world size, #2 biome 종류, #4 초기 배치
3. **Phase 2 Component Map 진입** — `World.land` 컨테이너 + 이동 인터페이스 + 렌더링 계약 분해
4. Phase 2 후 Phase 3 Decision Card → Phase 3.5 Cross-Impact → Phase 4 Verify → Phase 5 Package
5. Package 완료 후 `/spec`으로 Codex 전달용 구현 지시서 작성
