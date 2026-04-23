# Phase 17 / Φ-2 Faction — Component Map

> `/design` Phase 2 산출물. Phase 1 Charter([PHASE-17-FACTION-CHARTER.md](PHASE-17-FACTION-CHARTER.md))를 컴포넌트로 분해.
> 선행: Charter 확정 (2026-04-22) / 쟁점 3개 결정 완료 (S1 삭제·S3 founder+charter only·Gemini 공백 Phase 3.5 유예).

---

## 목표 역산 핸드셰이크

| 계층 | 본 Phase 기여 |
|---|---|
| 궁극 목적 (국가 자연 탄생) | Faction 계층이 선언 없이 유대로 자라야 함 — **단일 진원지 + bottom-up seed** 컴포넌트로 강제 |
| Phase 17 목적 (4단 인과 사슬) | Φ-3의 재료 생성 — **AffiliationKernel · FactionProjection · HandoffAPI**가 Φ-3 진입 조건 노출 |
| Φ-2 고유 역할 ("우리" 최초 등장) | **FounderSeed + AffiliationKernel + FactionCommitLoop** 3개가 "창시 → 누적 → 가입" 인과 체인 실행 |

---

## Core 컴포넌트 (Primary Outcome 직접 기여 순)

| # | 컴포넌트 | 판별 근거 |
|---|---------|---------|
| 1 | **FactionRegistry** | Faction 자료구조·레지스트리 (id/name/founder/charter/created_tick). 없으면 "집합체" 성립 불가 |
| 2 | **Persona.faction SSoT 필드군** | `faction` + `faction_cooldown` + `affiliation_scores`. "우리" 감각 보유 주체 |
| 3 | **`_change_persona_faction()` 단일 변경 함수** | SSoT 쓰기 유일 경로. `source` 태그 4종 (birth_founder/affiliation/drift/conflict). Φ-1 `_change_persona_territory()` 패턴 계승 |
| 4 | **AffiliationKernel (4신호 누적기)** | `territory + trust_density + shared_grievance + spatial_proximity` 매 틱 가중합·감쇠. "유대의 흐름" 동역학 본체 |
| 5 | **FactionCommitLoop (24/48틱 판정기)** | 임계치·히스테리시스·쿨다운 판정 → `_change_persona_faction` 호출. 자발적 가입·이적 실행자 |
| 6 | **FounderSeedGenerator (Founder+Charter 초기화)** | `sorted(pid) + _derive_rng("faction_seed", territory_id)`로 founder 선정, norm primitive tuple 생성. Bottom-up 시작점 |
| 7 | **FactionProjection (Territory.factionRef double-buffer)** | 24틱마다 Counter + 히스테리시스 → `Territory.factionRef` 파생. Φ-1 dominance 패턴 계승 |
| 8 | **AST Whitelist 확장** | `persona.faction = ...` 직접 대입 금지 테스트. Gap 4(helper 외 쓰기 경로) 차단 |

**Core 8개** → 스코프 어댑터 **표준** 자동 선택 (Φ-1과 동일 규모).

---

## Support 컴포넌트

| 컴포넌트 | 판별 근거 |
|---------|---------|
| **FactionHandoffAPI** | S6 Φ-3 인계 4종 (`faction_population_distribution`, `faction_territory_distribution`, `faction_charter_primitives`, `factions_in_contact`). Φ-2 산출물의 외부 노출 |
| **SNN Telemetry Hook (300~349 co-fire)** | faction 신호를 경제 perception 뉴런에 추가 자극. charter v3.1 무변경. S1 거부안의 대체 |
| **결정성 인프라 (`_derive_rng("faction_*", key_parts)`)** | Phase 17 Φ-1 중앙 RNG 재사용. faction_seed·faction_kernel·tie-break 전부 경유 |
| **FactionChangeEvent 방출** | `_emit_event("faction_change", pid, to, source)`. 디버그·재현성 로그 |
| **검증 하네스** | Hard 불변 8건 + AST 테스트 + bottom-up 실증 검증 (founder_count < total_member_count @ 500틱) |
| **trust_density / shared_grievance 신호 소스 어댑터** | Φ-1 spatial 데이터 + Phase 11-16 경제 지표를 kernel 입력으로 변환 |

---

## 의존성 맵 초안

| 컴포넌트 A | → | 컴포넌트 B | 공유 파라미터 |
|-----------|---|-----------|-------------|
| FactionRegistry | 포함 | Faction dataclass | `dict[str, Faction]` (id → record) |
| Persona.faction | 참조 | FactionRegistry.id | `Optional[str]` (None=미소속) |
| `_change_persona_faction` | 쓰기 (유일) | Persona.faction, faction_cooldown | SSoT write path |
| `_change_persona_faction` | 방출 | FactionChangeEvent | `(pid, to, source)` |
| AffiliationKernel | 읽기 | Persona.{territory, pos}, Territory.cells, FactionRegistry.members | spatial + social snapshot |
| AffiliationKernel | 읽기 | trust_density 소스, shared_grievance 소스 | Phase 11-17 기존 지표 |
| AffiliationKernel | 쓰기 | Persona.affiliation_scores | `dict[faction_id, float]` per persona |
| FactionCommitLoop | 읽기 | Persona.affiliation_scores, faction_cooldown, faction | snapshot (tick-frozen) |
| FactionCommitLoop | 호출 | `_change_persona_faction(source="affiliation"/"drift")` | sorted(pid) 순서 |
| FounderSeedGenerator | 호출 | `_change_persona_faction(source="birth_founder")` | 초기 시뮬 시작 시 1회 |
| FounderSeedGenerator | 쓰기 | FactionRegistry (신규 Faction 등록) | 각 Territory당 1개 |
| FactionProjection | 읽기 | Persona.{territory, faction} (snapshot) | Territory별 집계 |
| FactionProjection | 쓰기 | Territory.factionRef (double-buffer swap) | `Optional[str]` (None=공허 허용) |
| SNN Telemetry Hook | 읽기 | Persona.faction, affiliation_scores | 경제 뉴런 300~349 추가 자극 |
| SNN Telemetry Hook | 쓰기 | PersonaBrain input (경제 perception 채널) | readout_weights_v1.npy 무변경 |
| FactionHandoffAPI | 읽기 | FactionRegistry, Persona.faction, Territory.factionRef | 집계 결과만 노출 |
| AST Whitelist | 정적 검사 | 전체 코드베이스 | `persona.faction = ...` 라인 검증 |
| 결정성 인프라 | 공급 | FounderSeedGenerator, AffiliationKernel, FactionCommitLoop tie-break | `_derive_rng("faction_*", key_parts)` |

### 의존성 DAG (실행 순서 제약)

```
시뮬 초기화 (tick=0):
  FounderSeedGenerator
      → FactionRegistry (신규 Faction 등록)
      → _change_persona_faction(source="birth_founder")  ← founder만

매 틱:
  AffiliationKernel
      ├─ 읽기: Persona(snapshot), Territory, FactionRegistry
      └─ 쓰기: Persona.affiliation_scores

24/48틱 주기:
  FactionCommitLoop                              ← snapshot 동결 후
      └─ 호출: _change_persona_faction(source="affiliation"/"drift")

24틱 주기 (FactionCommitLoop 완료 후):
  FactionProjection
      ├─ 읽기: Persona.{territory, faction} (post-commit snapshot)
      └─ 쓰기: Territory.factionRef (double-buffer swap)

PersonaBrain tick 내부:
  SNN Telemetry Hook
      └─ Persona.faction, affiliation_scores → 뉴런 300~349 추가 자극

외부 질의 (Φ-3 진입 판정):
  FactionHandoffAPI (읽기 전용)
```

**Gap 4 방어**: `_change_persona_faction`이 유일한 쓰기 경로. AST Whitelist가 정적으로 강제, 검증 하네스가 런타임으로 감시.

---

## 스코프

**선택: 표준**

근거:
- Core 8개 (표준 어댑터 조건: Core 8~11개) — Φ-1과 동일 규모
- 1인 개발이지만 Core 복잡도 보정 적용 (kernel 수식 + double-buffer + AST 확장)
- Support 필수/준필수 6개 포함
- **Phase 3.5 Cross-Impact 전체 매트릭스 수행 + `/sub p-charter-consistency` 외부 Charter 충돌 검증**

---

## Charter ↔ Component Map 정합성 점검

| Charter `[확정 선행 결정]` 항목 | 대응 컴포넌트 |
|---|---|
| 1. Faction 스키마 | FactionRegistry (#1) |
| 2. Persona 필드 추가 | Persona.faction SSoT 필드군 (#2) |
| 3. Territory.factionRef 파생 | FactionProjection (#7) |
| 4. 단일 변경 함수 계약 | `_change_persona_faction()` (#3) |
| 5. Affiliation Kernel | AffiliationKernel (#4) + FactionCommitLoop (#5) |
| 6. Territory.factionRef 투영 | FactionProjection (#7) |
| 7. SNN 300~349 재사용 | SNN Telemetry Hook (Support) |
| 8. S6 Φ-3 인계 API | FactionHandoffAPI (Support) |
| 9. 검증 계약 | AST Whitelist (#8) + 검증 하네스 (Support) |

**누락 없음**. Charter 전 항목이 Component Map에 매핑됨.

---

## Phase 2 완료 체크리스트

- [x] 모든 컴포넌트 나열 (Core 8 + Support 6)
- [x] Core/Support 판별 근거 기록
- [x] Core 컴포넌트 순서 확정 (Primary Outcome 기여 순 / 궁극 목적 기여 순)
- [x] 의존성 맵 초안 작성
- [x] 의존성 DAG (실행 순서) 명시
- [x] 스코프 어댑터 선택 (표준) + 근거
- [x] Charter ↔ Component Map 정합성 점검 (누락 0)
- [x] Gap 4(helper 외 쓰기 경로) 방어 컴포넌트 포함

**결과: PASS → Phase 3 Decision Card 진입 가능**

---

## 다음 단계

Phase 3 Decision Card — 각 Core 컴포넌트에 대한 구현 결정:

1. **FactionRegistry** — `@dataclass(slots=True)` 사용 여부 / `charter: tuple` vs `frozenset` / id 생성 방식 (UUID4 vs hash 기반)
2. **Persona.faction SSoT 필드군** — 기존 `Persona`/`InnerWorld` 어느 쪽 확장 / `affiliation_scores` dict 크기 제한
3. **`_change_persona_faction()`** — 함수 위치 (Φ-1 `_change_persona_territory` 옆) / `source` enum vs Literal / Event schema
4. **AffiliationKernel** — `W_TERRITORY / W_TRUST / W_GRIEVANCE / W_PROXIMITY` 초기값 / `DECAY` 계수 / 매 틱 vs 나눠 계산 / `trust_density` 구체 수식 / `shared_grievance` 신호 소스
5. **FactionCommitLoop** — `THETA_JOIN`, `DRIFT_MARGIN`, `FACTION_COOLDOWN_TICKS`, commit 주기 24 vs 48틱 확정
6. **FounderSeedGenerator** — founder 선정 규칙 (최고 trust? 최고 pos 근접도? 결정론적 tie-break 기준) / norm primitive 초기 카탈로그 (카테고리 5~10개에서 3~5개 샘플) / Territory당 1개 vs 조건부
7. **FactionProjection** — `FACTION_HYSTERESIS` margin / 집계 주기 24틱 고정 vs 파라미터화 / 공허(None) 유지 규칙
8. **AST Whitelist** — `test_phase17_land.py:525` 확장 vs 신규 `test_phase17_faction.py` / 마커 이름 (`PHASE17_FACTION_SSOT_WRITE`) / 검사 대상 파일 범위

병행 과제:
- Phase 3.5 예비 — `/sub p-charter-consistency` 의뢰서 초안 (society/secret-rumor/humanity/constitution ↔ Φ-2 Faction 정합 검증)
