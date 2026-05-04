# Phase 17 / Φ-4 Nation — Charter STUB

> 본 문서는 **STUB**이다. Φ-4 Nation의 full Charter가 아니다.
> Φ-3 Struggle 산출물 → Φ-4 Nation 인계 계약(handoff contract)만 기록한다.
> Φ-3 closure 결정 후 별도 `/design` 사이클로 full Charter 작성 필요.
> 본 STUB은 §3.6 (넓이 우선) 적용 — Φ-3·Φ-4 뼈대를 동시 보유하기 위한 골조.

---

## 메타

| 항목 | 값 |
|------|-----|
| 프로젝트 | loom persona life simulator |
| Phase | 17 / Φ-4 Nation |
| 로드맵 | Φ-1 Land → Φ-2 Faction → Φ-3 Struggle → **Φ-4 Nation** |
| 선행 조건 | Φ-3 Struggle Closure Report (예정) |
| 현재 상태 | **STUB** (Φ-3 진행 중, Phase 14B-d1 진단 완료) |

---

## 목표·목적 3계층 (역산 기준)

- **궁극 목적**: 자율 사회 시뮬 + SNN 창발 + PersonaBrain 논문 출판
- **Phase 목적**: 페르소나·faction의 동역학에서 **국가(nation) 자연 탄생** — 주권·통치·경계가 top-down 선언이 아닌 분포 비대칭과 사회 안정도의 임계 현상으로 떠오름
- **고유 역할**: Φ-3가 만든 분포·응결·봉기 결과를 **국가 단위 통치 구조**로 흡수. Φ-2 faction과 Φ-1 territory를 **주권 단위(sovereign)** 의 재료로 사용.

---

## Purpose

Φ-4의 목적은 **국가가 자연 탄생하는 동역학**을 설계하는 것이다. 국가를 top-down 선언하지 않는다. Φ-1 territory 분포, Φ-2 faction 응결, Φ-3 봉기·재분포·응결된 grievance_pairs를 읽어, 어떤 faction-territory 결합이 **주권 선언 임계**를 자연 통과하는지 판정한다.

**핵심 질문**:
- 언제 "국가"가 자연 탄생하는가?
- 주권 = top-down 선언 부재 시, 무엇이 그 자리를 대신하는가?
- Φ-3 산출물 (uprising, dom_share, grievance_pairs)에서 어떻게 nation-level 통합이 자연 발생?

---

## Primary Outcome (가설)

**충분히 큰 단일 faction이 다수 territory를 안정적으로 지배** + **grievance_pairs 응결이 임계 시간 이상 유지** → 그 faction이 **사실상 국가**(de facto sovereign)로 인정. 인접 faction은 (a) 합병 (b) 동맹 (c) 적대 중 하나로 자연 분기.

**또는** 인접 faction 다수가 **공동 charter primitives**를 자연 수렴 → 연맹(federation) 형태로 nation 응결.

---

## Operating Loop (가설)

- **마이크로 (틱 단위)**: 각 faction의 territory 통제율, 멤버 안정도, charter 일관성 관찰. **신규 mechanism 없음** — Φ-1/Φ-2/Φ-3 인프라 관찰만.
- **미들 (수십~수백틱)**: faction-territory 결합의 **주권 강도(sovereignty intensity)** 누적. 임계 돌파 시 **sovereignty_event** 발화. Φ-3 산출물 (`dom_share`, `grievance_pairs`, `uprising_history`)을 **read-only**로 결합.
- **매크로 (수천틱, 목표 지향형)**: 지속적 주권 + 인접 관계 안정화 → **nation_emergence** — 사실상 국가의 자연 인정. Φ-5 (가칭 — 외교·전쟁·문명) 진입 재료.

---

## Φ-3 Handoff Inputs (정의 후보)

Φ-4는 Φ-3을 **read-only** API로만 접근. 후보 (Φ-3 closure 후 확정):

| API (가칭) | Φ-4 사용처 |
|------------|-----------|
| `faction_dom_share_history(faction_id, window)` | 주권 강도 — 다수 territory 안정 지배 |
| `faction_uprising_history(faction_id)` | 봉기 누적 분석 — 분파 발생률, 흡수율 |
| `faction_grievance_pairs_resonance(window)` | 응결 유지 — `grievance_pairs ≥ 1` 시간 비율 |
| `faction_charter_primitives(faction_id)` | charter 일관성 — 합병·연맹 후보 산출 |
| `faction_territory_distribution()` (Φ-2 계승) | territory 통제율 |
| `faction_population_distribution()` (Φ-2 계승) | 인구 비대칭 |
| `factions_in_contact(radius=1)` (Φ-2 계승) | 인접 관계 |

Φ-3 산출물 (`uprising_event`, `branch_factions_total` 등) 텔레메트리는 Φ-4에서 **소비만** — Φ-3 mechanism은 무수정.

---

## Entry Trigger Candidates

Φ-4 design은 다음 read-only 조건 중 최소 1개 충족 시 시작 가능:

1. **dom_share 안정성**: `max(faction_dom_share_history(window=720)) ≥ 0.55` (24틱 × 30사이클 평균)
2. **응결 유지**: `grievance_pairs_resonance_ratio(window=480) ≥ 0.30` (시간 비율 30% 이상)
3. **charter 수렴**: 인접 faction 2개 이상이 `charter_primitives` overlap ≥ 0.7
4. **Φ-3 closure 인정**: Φ-3 closure 보고서가 closure 판정 — **2026-05-03 V3 진단 후 자연 충족**:
   - 원안 (v1, deprecated): "Φ-3 closure 보고서가 PASS 판정 (전제 조건)" — 3/3 acceptance 만족 요구.
   - **2026-05-02 closure-v2 (전이)**: Case B 인정 (1/3 PASS = 자연 결합점 부분 신호) → Trigger 1번만으로 진입 가능. 단 Case C V3 진단 권고.
   - **2026-05-03 V3 적용 (현재)**: V3 PROBE (3 seed × 20,000틱, mechanism 무수정) 완료 → `cross_faction_lord_pair_emerged` = **22/23/19** 자연 발생 PASS, `conflict_pair_at_20000` = **1/1/1** 자연 종결. closure-v2 §7.2 Finding A v3 재판정 addendum 채택.
     - 근거: V3 진단으로 collapse 경로가 mechanism 결손이 아닌 **측정 정의 차원 차이** (territory 점유 vs event_log 누적)로 확정. mechanism 변경 불요 (axis C 가드레일 OQ 7-d 부합).
     - **Trigger 1번(`dom_share` window=720 ≥ 0.55) 자연 충족 시 Φ-4 진입 즉시 가능** — Case C V3 보고서 (`PHASE-17-CASE-C-DIAGNOSIS-REPORT-V3.md`) 인용 의무.
     - acceptance #2 FAIL은 closure-v2 시점 측정 정의에 의한 것이며, V3 정의로는 자연 발생 잠재력 PASS. Φ-4 charter는 자연 발생 mechanism 활용으로 설계 — territory cross-propagation **mechanism 변경 시도 금지** (V3 결과 = 변경 불요 확인됨, axis B/C 거부 사유 계승).

조건 미충족 시 Φ-4 진입 보류, Φ-3 동역학 계속 운용. **2026-05-03 기준: closure-v2 + V3 진단 채택 → Trigger 1번 자연 충족 시 Φ-4 진입은 권고 경로**.

---

## Included Scope Candidates

- 사실상 국가 (de facto sovereignty) 판정 mechanism
- faction 합병 (merge) 자연 발생
- faction 연맹 (federation) 자연 형성
- charter primitives 수렴·갱신 (Φ-3 분파 charter → Φ-4 통합 charter)
- 영주(lord) 교체 — 국가 단위 권력 재편
- 인접 nation 간 contact 관계 (적대·동맹·중립)

---

## Excluded From This Stub

- 전투·약탈·사망 (Φ-5 또는 별도 Charter)
- 외교·교섭 행동 (Φ-5)
- 신규 SNN 뉴런 (Charter v2 D10 — `n_neurons=1000` 절대 고정)
- 신규 FactionChangeSource (4종 freeze 유지)
- Φ-3 mechanism 직접 mutation
- Φ-2 무파괴 9 보장 위반

---

## 무파괴 보장 (Φ-2 v2 + Φ-3 계승)

Φ-4는 다음을 **모두 유지**:
- Charter v2 무파괴 9 보장 (Φ-2)
- 안전 전제 5종 (HYSTERESIS=2, FOUNDER_RESPAWN_EVERY=480, TARGET_ACTIVE=2, COMMIT_EVERY=48, MAX_MEMBERS=2)
- BOOST=0.20 (closure-v2 §7 데이터 정당화)
- D10 7종 API read-only 무수정
- 회귀 테스트 8+종 PASS (Φ-1~Φ-3 누적)
- LOOM-DIRECTION §3.7 데이터 정당화 사슬 6단 표준

---

## Open Questions (Φ-4 design 시 해소)

1. **주권 강도(sovereignty intensity)** 정의 — 단일 수식? 복합 임계? 분위수 기반(§3.7)?
2. **합병 vs 연맹 분기** — 어떤 신호가 합병으로, 어떤 신호가 연맹으로 induce?
3. **국가 해체** 경로 — 봉기 누적이 다시 응결을 깨는 시나리오 처리. Φ-3 mechanism 재진입?
4. **charter primitives 수렴** 측정 — overlap 계산 방법, 임계 분위수
5. **영주 교체 자연 발생** — Φ-3 봉기 누적 + Φ-4 주권 결합 시 영주 신규 induce 경로
6. **Φ-5 (가칭) 인계 계약** — Φ-4가 Φ-5 (외교·전쟁·문명)에 어떤 read-only API를 제공할지
7. **axis C 안티패턴 가드레일 (2026-05-02 closure-v2 §10.3 추가)** — Φ-3 axis A/B가 모두 mechanism 추가 시도로 거부됨. Φ-4 charter 작업이 새로운 axis C(예: 가상의 sovereignty boost mechanism)로 발화 가능성 차단:
   - **(7-a)** Φ-4 charter의 모든 신규 mechanism은 §3.7 6단 사슬 재진입 의무. 4단 (임계 분위수 + 시뮬) 통과 후 5단 (3엔진 cross-check) 발동 — closure-v2 §3 Phase 14B-B 동일 절차 적용.
   - **(7-b)** axis A 기각 사유 (magic threshold) + axis B 기각 사유 (anger 임계 mechanism = "더 정교한 거짓 보정") **자체 검증 의무**. 신규 mechanism이 두 거부 사유와 구조 동형 여부를 cross-check 응답에서 명시 확인.
   - **(7-c)** 차별 정당화 명시 의무 — "axis C가 axis A/B와 다른 이유"를 cross-check 입력 자료에 포함. axis A 거부 시점 (2026-04-28 hotfix v1) + axis B 거부 시점 (2026-05-02 cross-check) 결과를 새 PROBE input-brief에 인용.
   - **(7-d)** 거짓 PASS 절대 금지 (closure-v2 §0 vL.1 계승) — acceptance 만족을 위한 mechanism 추가는 자연 발생 mechanism일 때만 허용. top-down 보정 패턴 (gate, threshold, dampen 등 외부 강제 식)은 axis A/B 동형으로 자동 거부.
   - **(7-e)** Case C 진단 v3 결과(`PHASE-17-CASE-C-DIAGNOSIS-REPORT-V3.md`) 의무 인용 — V3 PROBE (2026-05-03 완료) 결과로 갱신:
     - `cross_faction_lord_pair_emerged` 누적 22/23/19 = 자연 발생 PASS, `conflict_pair_at_20000` = 1/1/1 자연 종결 — Φ-4 Trigger 1 충족 사실 명시.
     - V3 가설 H1~H5 결과: collapse 경로는 mechanism 결손이 아닌 **측정 정의 차원 차이** (territory 점유 vs event_log 누적). axis C 가드레일 OQ 7-d 부합 — territory cross-propagation **mechanism 변경 시도 자체가 거부 대상**.
     - Φ-4 charter 1번 작업: territory cross-propagation 자연 강화(P3) **시도 금지** (mechanism 변경 = axis B 거부 사유 동형). 대신 자연 발생 mechanism의 **측정·관측 강화** (telemetry, 분석 helper) 우선.
     - persona 차원 (P5/P6) 옵션도 동일 가드레일 적용 — 신규 mechanism은 §3.7 6단 사슬 처음부터 재진입 의무.

---

## §3.7 데이터 정당화 사슬 적용 의무

Φ-4의 모든 SNN gate / 결합점 / 임계값은 LOOM-DIRECTION §3.7 6단 사슬을 거친 데이터 정당화 필수:

1. 자연 측정 (Φ-3 closure 후 5000~10000틱 × 5+ seed)
2. 분포 분석 (n, avg, median, 분위수)
3. 결합점 후보 (어떤 SNN 출력 / 분포 → 어떤 mechanism 변수)
4. 임계 분위수 (P50/P67/P75 후보 + 시뮬)
5. 3엔진 cross-check (`/discuss --quick` Claude+Codex+Gemini)
6. closure 보고서 (verdict matrix + 데이터 사슬)

한 단이라도 비면 안티패턴 #3 (SNN gate 정당화 부재)으로 거부.

---

## 다음 단계

1. **Φ-3 closure** — Phase 14B-B axis spec 진행 + acceptance 자연 측정 → Φ-3 PASS 판정
2. **Φ-4 full Charter design** — `/design` 사이클로 Open Questions 해소
3. **3엔진 토론** — `/discuss`로 주권 강도 정의 합의
4. **Φ-4 spec 작성** — `/spec` 후 `/spec-review` 후 구현 진입

본 STUB은 §3.2 (인계 계약 검증) 위해 Φ-3 진행 중에 작성 — Φ-3 산출물이 Φ-4 재료로 자연 결합되는지 검증 가능 상태로 보유.

---

## 메모: 본 STUB의 위치

| 비교 항목 | Φ-3 STUB | Φ-4 STUB (본 문서) |
|-----------|----------|-------------------|
| 작성 시점 | Φ-2 Stage 4 closure 직후 | Φ-3 진행 중 (Phase 14B-d1 진단 후) |
| Handoff inputs | Φ-2 read-only 7 API | Φ-3 후보 7 API + Φ-2 계승 |
| Entry trigger | 3 후보 (Φ-2 결과 기반) | 4 후보 (Φ-3 acceptance 포함) |
| Open questions | 5 | 6 |
| 무파괴 의무 | Charter v2 무파괴 9 | Φ-2 + Φ-3 누적 + §3.7 |

**핵심 한 줄**: 국가가 **자연 탄생**해야 한다. Φ-4는 Φ-3 응결·봉기·재분포의 결과를 주권으로 흡수하는 동역학만 설계 — 국가를 만들지 않고, 만들어지도록 한다.
