# Phase 17 / Φ-1 Land — Component Map

> `/design` Phase 2 산출물. Phase 1 Charter(PHASE-17-LAND-CHARTER.md)를 컴포넌트로 분해.
> 선행: Charter 확정(2026-04-20), [미결] 5개 항목 모두 확정.

---

## Core 컴포넌트 (Primary Outcome 직접 기여 순)

| # | 컴포넌트 | 판별 근거 |
|---|---------|---------|
| 1 | **LandCell** | 물리 공간 최소 단위. 없으면 "2D tile grid" 성립 불가 |
| 2 | **World.land** | LandCell 50×50 컨테이너. "tile grid"의 집합 루트 |
| 3 | **Persona.pos** | 이동 주체 좌표. "자유 이동" 불가능 |
| 4 | **이동 로직** | pos 갱신·migration_cooldown. Primary Outcome 동작 주체 |
| 5 | **거주지 선택 휴리스틱** | "거주지 선택" 직접 구현 (resource/path_cost 스캔) |
| 6 | **Territory dominance projection** | Phase 11-16 "무파괴" + Charter 재정의 계약 |
| 7 | **마이그레이션 앵커 (territoryRef)** | Phase 11-16 경제/SNN "무파괴" 필수 조건 |
| 8 | **초기 배치기 (Poisson disk + biome 필터)** | 결정 완료된 사양. 시뮬 시작점 |

Core 8개 → 스코프 어댑터 **표준** 자동 선택.

---

## Support 컴포넌트

| 컴포넌트 | 판별 근거 |
|---------|---------|
| **Biome 초기화 분포** | 6종 biome 배정 규칙. Φ-1은 정적 |
| **기후 엔진 계약 예약** | `climate` 필드만, 로직은 Φ-3 |
| **렌더링 예약 필드** | offset/graphic_id/outfit_id — 데이터 저장만 |
| **SNN spatial perception 매핑** | neuron 300~349 연결 (Phase 3 Decision Card) |
| **결정성 보장 (seed=42)** | 인프라, 모든 Phase 공통 불변 |
| **검증 하네스** | Hard 5지표 + 성능 ≤250ms/tick 회귀 검증 |

---

## 의존성 맵 초안

| 컴포넌트 A | → | 컴포넌트 B | 공유 파라미터 |
|-----------|---|-----------|-------------|
| World.land | 포함 | LandCell | grid dict[tuple[int,int], LandCell] |
| LandCell | 앵커 | Territory | territoryRef (str) |
| Persona.pos | 참조 | LandCell | (x, y) 튜플 |
| 이동 로직 | 읽기 | LandCell.path_cost | float >0 |
| 이동 로직 | 쓰기 | Persona.pos, migration_cooldown | (x,y), int |
| 거주지 선택 | 읽기 | LandCell.resources, biome | dict, str |
| 초기 배치기 | 쓰기 | Persona.pos | (x, y) |
| 초기 배치기 | 읽기 | LandCell.biome | str (water/mountain 제외) |
| Territory dominance | 읽기 | LandCell.territoryRef 집합 | set[tuple[int,int]] |
| Biome 초기화 | 쓰기 | LandCell.biome | 6종 enum |
| 기후 엔진 계약 | 예약 | LandCell.climate | dict (rainfall, temperature) |
| SNN spatial | 읽기 | Persona.pos, dest | (x,y), Optional[(x,y)] |
| 검증 하네스 | 읽기 | 모든 Core 컴포넌트 | Hard 5지표 + perf |

---

## 스코프

**선택: 표준**

근거:
- Core 8개 (표준 어댑터 조건: 4~15인 팀 or Core 8~11개)
- 1인 개발이지만 Core 복잡도 보정 적용
- Support 필수/준필수 포함, Phase 3.5 전체 매트릭스 수행

---

## Phase 2 완료 체크리스트

- [x] 모든 컴포넌트 나열 (Core 8 + Support 6)
- [x] Core/Support 판별 근거 기록
- [x] Core 컴포넌트 순서 확정 (Primary Outcome 기여 순)
- [x] 의존성 맵 초안 작성
- [x] 스코프 어댑터 선택 (표준) + 근거

**결과: PASS → Phase 3 Decision Card 진입 가능**

---

## 다음 단계

Phase 3 Decision Card — 각 Core 컴포넌트에 대한 구현 결정:
1. LandCell — 데이터 구조 (frozen? mutable?), biome setter 계약
2. World.land — 2D array vs dict[(x,y)] (성능/메모리 tradeoff)
3. Persona.pos — 기존 Persona 클래스 확장 vs InnerWorld 추가
4. 이동 로직 — 그리디 vs 가중 랜덤, migration_cooldown 기본값
5. 거주지 선택 휴리스틱 — 점수 함수 정의
6. Territory dominance projection — 매 틱 재계산 vs 캐시
7. 마이그레이션 앵커 — 기존 region 필드 deprecated 경로
8. 초기 배치기 — Poisson disk 알고리즘 구체화
