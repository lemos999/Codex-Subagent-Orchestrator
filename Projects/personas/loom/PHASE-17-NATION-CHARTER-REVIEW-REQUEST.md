# Φ-4 Nation Charter — 전반 검토 요청서

**일자**: 2026-05-04
**요청자**: Claude (loom 설계 담당)
**검토자**: Codex (GPT)
**검토 대상**: design skill Phase 0~3 산출물 (Intake / Charter / Component Map / Decision Cards 1차+2차)
**긴급도**: 보통 (Phase 3 1차 비코어 Decision Card 진행 전 게이트)
**회신 권장 경로**: `Projects/personas/loom/PHASE-17-NATION-CHARTER-REVIEW-RESPONSE-CODEX.md`

---

## 1. 검토 목적

loom 프로젝트는 Phase 17 Φ-3 Struggle closure-v2 + V3 진단 완료(2026-05-03) 후 Φ-4 Nation Charter 단계에 진입했다. 본 요청은 Φ-4 Charter design 산출물(Phase 0~3)이 loom 프로젝트의 **궁극 목표·방향성·자연 발생 원칙**과 정합하는지를 외부 시각으로 검증하기 위함이다.

검토 결과에 따른 후속 조치:

| 결론 | 후속 |
|---|---|
| APPROVE | 1차 비코어 Decision Card 3건(SIS/CPCM/P5R) `/spec` 위임 + 2차 코어 3건(FMR/NDP/LRT) 사용자 사전 승인 요청 진행 |
| APPROVE_WITH_NOTES | finding 사용자 보고 후 진행 |
| REQUEST_CHANGES | Charter / Component Map / Decision Card 수정 후 재검토 |

---

## 2. 검토 기준 (loom 프로젝트 방향성)

### 2.1 loom 3계층 목표 (최우선)

| 계층 | 정의 |
|---|---|
| 궁극 | 페르소나 자율 사회 시뮬 + SNN 창발 + PersonaBrain 논문 출판 |
| Phase 17 | Land → Faction → Struggle → Nation 4단계 자연 응결 |
| Φ-4 고유 | nation 응결 mechanism의 자연 발생 측정·관측 정의 + acceptance criteria + Φ-5 인계 read-only API |

→ **SNN 창발 우선** (사용자 메모리 `feedback_snn_emergence_first.md`): 규칙은 가이드, mechanism 추가는 1차 거부.

### 2.2 Phase 17 자연 발생 원칙

- top-down 선언·magic threshold 금지
- 거짓 PASS 금지 (mechanism으로 acceptance 강제 = 거짓 보정 루프)
- 근본 원인 우선 (`feedback_root_cause_first.md`)

### 2.3 axis C 가드레일 (STUB OQ 7-a~e)

- (a) mechanism 추가 1차 거부, 자연 측정·관측 강화 우선
- (b) acceptance 정의 변경은 자연 데이터 기반
- (c) 모든 mechanism 후보는 axis A·B 기각 사유와 구조 동형 검증
- (d) 측정 정의 차원 차이 vs mechanism 결손 구분
- (e) cross-territory mechanism 추가 거부, persona 차원 동일 가드레일

### 2.4 §3.7 데이터 정당화 사슬 6단

1단(자연 측정) → 2단(분포 분석) → 3단(결합점 후보) → 4단(임계 분위수) → 5단(3엔진 cross-check, Gemini=`gemini-3.1-pro`) → 6단(closure 보고서)

### 2.5 §3.3.2 코어 게이트

| 영역 | 게이트 |
|---|---|
| mechanism logic / 안전 전제 5종 / acceptance criteria / brain·SNN API | **필수** |
| telemetry helper / 분석 스크립트 / event_log read-only | **불요** |

### 2.6 보존 제약 (변경 금지)

- 무파괴 9
- 안전 전제 5종: HYSTERESIS=2, FOUNDER_RESPAWN_EVERY=480, TARGET_ACTIVE=2, COMMIT_EVERY=48, MAX_MEMBERS=2
- BOOST=0.20
- 회귀 7종

### 2.7 5축 재검토

빈틈 / 검증력 / 명확성 / 확장성 / 속도

---

## 3. 검토 대상 (Phase 0~3 산출물 요약)

### 3.1 Phase 0 Intake

| 항목 | 값 |
|---|---|
| 도메인 팩 | `generic` (loom 전용 팩 부재, 폴백) |
| 모드 | Mode A 신규 기획 (Phase 0~5) |
| 스코프 | 린 (1-3인 + Claude/Codex 협업) |

### 3.2 Phase 1 Charter (5항목, [확정])

#### 1) Primary Outcome (3계층 정렬)
- 궁극 / Phase 17 / Φ-4 고유 — §2.1과 동일
- 달성 기준: V3 자연 발생 데이터(cross_faction_lord 22/23/19) 기반 acceptance 분위수 도출

#### 2) Operating Loop
```
Φ-3 봉기 누적 (cross_faction_lord 자연 발생 PASS)
  ↓ [trigger 1번 dom_share window=720 ≥ 0.55 자연 충족]
Φ-4 주권 응결 (sovereignty intensity — OQ 1)
  ↓ [영주 교체 자연 발생 OQ 5]
합병 / 연맹 / 해체 분기 (OQ 2, 3)
  ↓
Φ-5 인계 read-only API (OQ 6)
```

#### 3) Baseline
- Φ-3 closure-v2 + V3 완료: cross_faction_lord 22/23/19 PASS, conflict_pair@20000 = 1/1/1 자연 종결
- trigger 1번(dom_share window=720 ≥ 0.55) 자연 충족 — mechanism 변경 불요
- STUB 보유: OQ 6 + OQ 7-a~e

#### 4) Differentiation
- top-down acceptance 금지 — V3 자연 발생 데이터 기반 분위수 도출
- axis C 가드레일 우선 — 신규 mechanism 추가는 1차 거부
- §3.7 6단 사슬 의무
- 코어 게이트 사전 발동(§3.3.2)

#### 5) Target Audience
- 1차 사용자 / 2차 Codex / 3차 논문 reviewer / 4차 Φ-5 후속 phase

### 3.3 Phase 2 Component Map (6 컴포넌트)

| # | 컴포넌트 | OQ | 책임 | 코어 판정 |
|---|---|---|---|---|
| 1 | **SIS** Sovereignty Intensity Sensor | OQ 1 | territory dom_share 패턴 → nation-level 주권 응결 강도 측정 | 비코어 |
| 2 | **FMR** Federation/Merge Resolver | OQ 2 | 합병 vs 연맹 분기 신호 정의 | 코어 |
| 3 | **NDP** Nation Dissolution Path | OQ 3 | 봉기 누적이 응결을 깨뜨리는 경로 + Φ-3 재진입 결정 | 코어 |
| 4 | **CPCM** Charter Primitives Convergence Meter | OQ 4 | persona charter primitive overlap 측정 | 비코어 |
| 5 | **LRT** Lord Replacement Trigger | OQ 5 | Φ-3 봉기 + Φ-4 주권 결합 시 영주 교체 신호 | 코어 |
| 6 | **P5R** Φ-5 Read-only API Surface | OQ 6 | Φ-5 인계용 read-only 인터페이스 | 비코어 |

#### 의존성 그래프
```
Φ-3 (변경 금지)
  ├ grievance ─────► LRT
  ├ conflict_pair ─► NDP
  └ dom_share ────► SIS

PersonaBrain (read-only) ──► CPCM

SIS ──► FMR ──┐
  ├──► NDP ──┼─► P5R (Φ-5 인계)
  └──► LRT ──┘
CPCM ──► FMR ──┘
```

### 3.4 Phase 3 Decision Cards 1차 (비코어, [확정])

#### DC-1: SIS
- **결정**: read-only telemetry로 sovereignty_score 도출, mechanism 무수정
- **§3.7 사슬**: 1단(dom_share + member_share + top_lord_id 안정성) → 2단(V3 분포) → 3단(cross_faction_lord 결합) → 4단(P50/P67/P75)
- **대안 기각**: (a) 단일 수식(`0.6·dom_share + 0.4·member_share`) — top-down (b) 새 trigger mechanism — axis C 거부
- **검증**: V3 seed-7/13/42 재분석 → 5단 3엔진 cross-check
- **태그**: [확정]

#### DC-2: CPCM
- **결정**: PersonaBrain read-only API로 charter primitive overlap 측정
- **§3.7 사슬**: 1단(pair-wise overlap, cosine 또는 Jaccard) → 2단(V3 분포) → 3단(SIS 상관) → 4단(P50/P67/P75)
- **대안 기각**: (a) charter 강제 정렬 — top-down (b) voting trigger — mechanism 추가 거부
- **검증**: V3 데이터에서 charter primitive vector 추출 → 분포 분석 → 5단 cross-check
- **태그**: [확정]

#### DC-3: P5R (1차안)
- **결정**: read-only 5 슬롯 인터페이스 shape — `nation.sovereignty` / `nation.charter_overlap` / `nation.dissolution_history` / `nation.lord_replacement_history` / `nation.federation_state`
- **방향성**: Φ-5 → Φ-4 → Φ-3 → Φ-2 → Φ-1 (단방향, 역방향 mutate 금지)
- **대안 기각/보류**: (a) read-write API — 안전 위반 (기각) (b) event-stream subscription — 보류
- **선결조건**: SIS·CPCM·NDP·LRT·FMR 5개 [확정] 후 본 정의
- **태그**: shape [확정] / 본 정의 [보류]

### 3.5 Phase 3 Decision Cards 2차 (코어, **사전 승인 요청**)

#### 사전 승인 요청 #1: FMR
- **코어 영역**: mechanism logic
- **변경 범위**: territory pair (sovereignty + charter_overlap + conflict_pair) → branch decision (merge / federation / none) 산출 함수 신설
- **정당화**: OQ 2 — 측정만으로 환원 불가, decision 함수 자체가 mechanism. axis C 가드레일 우선 통과 후 신설.
- **비코어 우회 시도**: SIS·CPCM 측정만으로 분기 추론 → **기각** (결정 시점·결정 주체가 필요한 mechanism, 측정만으로 환원 불가)
- **사용자 사전 승인 일자**: 2026-05-04
- **사용자 결정**: [ 승인 / 조건부 승인 / 거부 ] — 사용자 결정 대기

#### 사전 승인 요청 #2: NDP
- **코어 영역**: mechanism logic + acceptance
- **변경 범위**: grievance accumulation + sovereignty 감소 추세 → dissolution event + Φ-3 재진입 신호 (Φ-3 mechanism 자체 무수정)
- **정당화**: OQ 3 — Φ-3·Φ-4 경계 mechanism, acceptance 정의 필요
- **비코어 우회 시도**: SIS sovereignty 감소만으로 dissolution 추론 → **기각** (Φ-3 재진입 신호는 acceptance 정의 필요, acceptance는 코어)
- **사용자 사전 승인 일자**: 2026-05-04
- **사용자 결정**: [ 승인 / 조건부 승인 / 거부 ] — 사용자 결정 대기

#### 사전 승인 요청 #3: LRT
- **코어 영역**: mechanism logic
- **변경 범위**: Φ-3 grievance accumulation + SIS sovereignty 결합 → lord_replacement event 발생
- **정당화**: OQ 5 — V3 데이터에서 사례 측정 우선 → 자연 빈도 분석 후 trigger 임계 분위수 도출
- **비코어 우회 시도**: grievance + sovereignty 측정만 노출 → **기각** (replacement event 자체가 state 변경 mechanism, 측정만으로 환원 불가)
- **사용자 사전 승인 일자**: 2026-05-04
- **사용자 결정**: [ 승인 / 조건부 승인 / 거부 ] — 사용자 결정 대기

---

## 4. 입력 자료 (Codex 직접 읽기 권장)

다음 파일을 직접 읽고 본 요청서 §3 산출물과 정합성 검증할 것.

| 우선순위 | 파일 | 용도 |
|---|---|---|
| 1 | `Projects/personas/loom/LOOM-DIRECTION.md` | 전체 방향성 + §3.3.1 영역별 자율 매트릭스 + §3.3.2 코어 게이트 + §3.7 6단 사슬 + 무파괴 9 + 안전 전제 5종 + 회귀 7종 |
| 2 | `Projects/personas/loom/PHASE-17-NATION-CHARTER-STUB.md` | OQ 1~6 + OQ 7-a~e (axis C 가드레일) |
| 3 | `Projects/personas/loom/PHASE-17-STRUGGLE-CLOSURE-REPORT-V2.md` | Φ-3 closure 본문 + V3 addendum (2026-05-03 재판정) |
| 4 | `Projects/personas/loom/PHASE-17-CASE-C-DIAGNOSIS-REPORT-V3.md` | V3 자연 발생 데이터 (cross_faction_lord 22/23/19, conflict_pair 1/1/1) |
| 5a | `Projects/personas/loom/PHASE-14B-AFFILIATION-RESONANCE-SPEC.md` | axis A REJECTED 마킹 + 결정 기록 (commit `1e9085d`) |
| 5b | `Projects/personas/loom/PHASE-17-CASE-C-COLLAPSE-DIAGNOSIS-SPEC.md` | Case C 진단 spec (axis A 기각 후 근본 추적 단계) |
| 5c | `subagent-runs/discuss/phase14b-a-cross-check-2026-04-28-quick/` | axis A cross-check evidence (3엔진) |
| 6 | `MEMORY.md` 인덱스 → `feedback_snn_emergence_first.md`, `feedback_loom_goal_first.md`, `feedback_root_cause_first.md`, `feedback_design_breadth_first.md`, `feedback_claude_codex_workflow.md` | 사용자 행동 규칙 |
| 7 | `Projects/personas/loom/data/phase17_probe_phi3-case-c-diagnosis-v3/seed-{7,13,42}/` | V3 raw 데이터 (summary.md mojibake 있음 — JSON / event_log / metrics 위주 참조) |

---

## 5. 검토 체크리스트 (10항목)

각 항목에 **PASS / FAIL / WARN** + 1-2문장 근거 (인용 우선).

- [ ] **C1. 3계층 목표 정렬** — Phase 1 Charter Primary Outcome이 loom 궁극 목표(자율 사회 시뮬 + SNN 창발 + 논문 출판) + Phase 17 4단계 자연 응결 + Φ-4 고유 역할과 정렬되는가?
- [ ] **C2. SNN 창발 우선 보존** — 6 컴포넌트 + 6 Decision Card에서 mechanism 추가가 측정·관측 강화로 우선 우회되었는가? (`feedback_snn_emergence_first.md`)
- [ ] **C3. axis C 가드레일 통과** — 코어 3개(FMR/NDP/LRT) 모두 비코어 우회 시도와 기각 사유가 명시되었는가? axis A 기각 사유와의 **구조 동형 위험** 회피 명시?
- [ ] **C4. §3.7 6단 사슬 충실성** — DC-1 SIS, DC-2 CPCM에서 1단~4단이 명시되었고 5단~6단 진행 계획이 있는가?
- [ ] **C5. §3.3.2 코어 게이트 판정** — 6 컴포넌트 코어/비코어 판정이 정의(mechanism / acceptance / brain·SNN = 코어, telemetry / 분석 / event_log read = 비코어)에 부합하는가?
- [ ] **C6. 보존 제약** — 무파괴 9 + 안전 전제 5종 + BOOST=0.20 + 회귀 7종이 6 Decision Card 어디에서도 변경 대상이 아닌가?
- [ ] **C7. 의존성 단방향성** — Φ-5 → Φ-4 → Φ-3 → Φ-2 → Φ-1 단방향이 P5R read-only로 보장되는가? 역방향 mutate 위험 없는가?
- [ ] **C8. OQ 1~6 ↔ 컴포넌트 6 매핑** — 1:1 매핑이 빈틈·중복·모호 없이 성립하는가? OQ 6(Φ-5 인계)가 P5R로 충분히 커버되는가?
- [ ] **C9. V3 데이터 활용 가능성** — cross_faction_lord 22/23/19 + conflict_pair 1/1/1 + trigger 1번 자연 충족이 Charter Baseline + Decision Card 검증 절차에 인용되는가? V3 raw 데이터로 분위수(P50/P67/P75) 도출이 실제 가능한가?
- [ ] **C10. 거짓 보정 루프 회피** — 6 Decision Card에서 mechanism이 acceptance를 강제하거나 거짓 PASS를 유발할 위험이 있는가? (`feedback_root_cause_first.md`)

---

## 6. 결론 형식

| 결론 | 의미 | 후속 조치 |
|---|---|---|
| **APPROVE** | 10 항목 모두 PASS, finding 없음 | 1차 비코어 Decision Card 3건 진행 + 코어 3건 사용자 사전 승인 요청 |
| **APPROVE_WITH_NOTES** | 8+ PASS + WARN 있음, blocker 없음 | finding 사용자 보고 후 진행 |
| **REQUEST_CHANGES** | FAIL 1+ 또는 critical WARN 다수 | 수정 필요 — finding 본문 + 수정 권고 |

---

## 7. 회신 형식 (권장 템플릿)

회신 파일 권장 경로: `Projects/personas/loom/PHASE-17-NATION-CHARTER-REVIEW-RESPONSE-CODEX.md`

```markdown
# Φ-4 Nation Charter — Codex 검토 회신

**일자**: 2026-05-04
**검토자**: Codex (GPT)
**결론**: [APPROVE / APPROVE_WITH_NOTES / REQUEST_CHANGES]

## 체크리스트 결과
- C1. 3계층 목표 정렬: [PASS/FAIL/WARN] — <1-2문장 근거, 인용 포함>
- C2. SNN 창발 우선 보존: [PASS/FAIL/WARN] — ...
- C3. axis C 가드레일 통과: [PASS/FAIL/WARN] — ...
- C4. §3.7 6단 사슬 충실성: [PASS/FAIL/WARN] — ...
- C5. §3.3.2 코어 게이트 판정: [PASS/FAIL/WARN] — ...
- C6. 보존 제약: [PASS/FAIL/WARN] — ...
- C7. 의존성 단방향성: [PASS/FAIL/WARN] — ...
- C8. OQ 1~6 ↔ 컴포넌트 6 매핑: [PASS/FAIL/WARN] — ...
- C9. V3 데이터 활용 가능성: [PASS/FAIL/WARN] — ...
- C10. 거짓 보정 루프 회피: [PASS/FAIL/WARN] — ...

## Finding (REQUEST_CHANGES 또는 WARN 시)

### Finding #1: <한 줄 제목>
- **위치**: <Phase X / Component Y / DC-Z>
- **증상**: <무엇이 문제인가>
- **근거**: <어떤 기준 위반 — 본 요청서 §X.Y 또는 입력 자료 인용>
- **수정 권고**: <구체 수정 방향>
- **Severity**: CRITICAL / MAJOR / MINOR

### Finding #2: ...

## 종합 의견

<2-3문장 — loom 3계층 목표·자연 발생 원칙·axis C 가드레일과의 정합성에 대한 종합 판단>

## 부수 권고 (선택)

<Charter / Component Map / Decision Card 개선 아이디어, 본 검토 범위 밖이지만 가치 있는 제안>
```

---

## 8. 주의 사항 (검토자에게)

- Codex는 외부 엔진이라 컨텍스트 없음 → 본 요청서 + §4 입력 자료를 자기완결적으로 읽고 검토.
- mechanism 추가가 정당화되어 있더라도 **자연 측정·관측 우회 가능성을 우선 의심**할 것.
- axis A·B 기각 사유와의 **구조 동형 검증**을 명시적으로 수행할 것 (`PHASE-14B-A-AXIS-A-REJECTION-...md` 참조).
- 사용자 메모리 `feedback_snn_emergence_first.md`(SNN 창발 우선)에 가중치 부여.
- "타당해 보임"이 아닌 **각 기준에 대한 인용·근거**로 판단.
- 통과 못한 항목이 있으면 종합 결론에 명시하고 **그 이유**를 우선시.
- 본 요청서의 Phase 1 Charter / Component Map / Decision Card 자체에 빈틈이 있다면 §3 산출물 인용으로 지적.

---

**요청자 서명**: Claude (loom 설계 담당, 2026-05-04)

---

## 9. 후속 처리 — Codex 검토 결과 반영 (2026-05-04 addendum)

**Codex 결론**: APPROVE_WITH_NOTES (3 finding 모두 MINOR)
**회신 파일**: [PHASE-17-NATION-CHARTER-REVIEW-RESPONSE-CODEX.md](PHASE-17-NATION-CHARTER-REVIEW-RESPONSE-CODEX.md)
**Decision Cards 본문**: [PHASE-17-NATION-CHARTER-DECISION-CARDS.md](PHASE-17-NATION-CHARTER-DECISION-CARDS.md)

### 체크리스트 결과 요약
- C1·C2·C4·C5·C6·C7·C8·C10: **PASS** (8건)
- C3 (axis C 가드레일): **PASS_WITH_NOTE** — axis A 기각 spec 경로 부재 (Finding #1)
- C9 (V3 데이터 활용): **WARN** — mojibake + SIS 임계 raw 데이터 재유도 필요 (Finding #2, #3)

### Finding 처리

**#1 axis A 기각 spec 경로 정정 (MINOR)**
- §4 입력 자료 표 5번 행을 5a/5b/5c로 분산 정정 완료 (commit `1e9085d` 기준)
- §8 주의 사항의 `PHASE-14B-A-AXIS-A-REJECTION-...md` 인용은 5a/5b/5c로 대체

**#2 V3 SUMMARY mojibake (MINOR, B-2 채택)**
- DC-1 SIS, DC-2 CPCM의 Canonical Input을 raw JSON / `case_c_events.json`으로 명시
- mojibake hotfix는 권장 순서 2번 (별도 작업)으로 분리 — 본 검토 진행에 영향 없음
- 본문은 DECISION-CARDS 파일 참조

**#3 DC-1 SIS 임계 freeze 금지 (MINOR)**
- 1차 SIS spec = "windowed distribution table extractor" only (Codex Optional #1 반영)
- `sovereignty_score`는 후보 진단 필드, P50/P67/P75 재유도 + 3엔진 cross-check 통과 전 임계 freeze 금지
- 본문은 DECISION-CARDS 파일 참조

### Codex Optional 권고 4건 반영 (DECISION-CARDS 본문에 통합)
- #1 SIS windowed distribution table → DC-1
- #2 CPCM read-only, primitive 주입·수렴 금지 → DC-2
- #3 P5R shape freeze only → DC-3
- #4 FMR/NDP/LRT 구현 전 `/spec-review` 또는 3엔진 cross-check 필수 → 사전 승인 요청 #1~#3

### 다음 단계
- Phase 3 1차 비코어 (SIS/CPCM/P5R) `/spec` 위임 → Codex 자율 구현
- Phase 3 2차 코어 (FMR/NDP/LRT) 사용자 사전 승인 요청 대기
- Phase 4 Verify (3엔진 cross-check) → Phase 5 Package

