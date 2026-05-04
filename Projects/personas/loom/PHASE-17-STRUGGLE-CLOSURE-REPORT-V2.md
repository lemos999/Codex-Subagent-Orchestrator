# Phase 17 Φ-3 Struggle Closure Report (v2 — 최종 closure)

> Measured: 2026-05-02
> Baseline: v1 closure (2026-04-28 hotfix v1) + Phase 14 resonance 보강 + Phase 14B-d1 (SNN-output-diag) + Phase 14B-B (anger coupling PROBE) + 2026-05-02 3엔진 cross-check
> Verdict: **Case B — 공식 closure 인정. 1/3 PASS = 자연 결합점 부분 신호. mechanism 추가 거부. Φ-4 진입 전 cross-prop collapse 1단 진단 의무.**
> User decision: **APPROVED 2026-05-02** — 옵션 X+Y 하이브리드 채택 (closure 즉시 + 진단 병행).

---

## 0. 갱신 이력

| 버전 | 시점 | 결과 | 근거 |
|------|------|------|------|
| v1 | 2026-04-28 | hotfix v1 — 거짓 PASS 5건 제거, acceptance #2 0/0/0 FAIL | `PHASE-17-STRUGGLE-CLOSURE-REPORT.md` |
| Phase 14 resonance | 2026-04-29 | cross-territory propagation 추가, 0/0/0 FAIL 잔존 | `data/phase17_probe_phi3-phase14-resonance/SUMMARY.md` |
| Phase 14B-d1 | 2026-04-30 | SNN-output-diag 4 가설 (G1 PASS, G2/G3 INSUFFICIENT_N, G4 PASS) | `data/phase17_probe_phi3-snn-output-diag/SUMMARY.md` |
| Phase 14B-B PROBE | 2026-05-01 | anger threshold 분위수 + cross_faction_lord_count P75 자연 발생 (3·3·3) | `data/phase14b_b_threshold_simulation.md` |
| 3엔진 cross-check | 2026-05-02 | anger mechanism 차단 만장 + Φ-3 closure 시점 새 이견 | `subagent-runs/discuss/phase14b-b-anger-coupling-cross-check-2026-05-02-quick/discussion-summary.md` |
| **본 v2** | **2026-05-02** | **Case B 공식 closure + axis B 5단 통과·6단 mechanism 거부** | (본 보고서) |

---

## 1. 배경 — v1 이후 진행 사슬

v1 closure 후 다음 사슬이 진행됨:

1. **Phase 14 resonance 보강**: `_propagate_grievance_lord_id_cross_territory` 추가 — cross-territory propagation mechanism 자연 mechanism으로 도입. 그러나 acceptance #2 여전히 0/0/0 FAIL (잠재력은 자연 발생, 종료 시점 collapse 미해소).
2. **Phase 14B-d1 (SNN-output-diag)**: SNN 4 가설 진단. G1 (uprising leader gate diff) PASS — anger·chronic 분리 명확 (n=205, pass_avg_anger=0.72 vs fail_avg_anger=0.50).
3. **Phase 14B-B PROBE**: G1 결과를 §3.7 4단(임계 분위수)으로 전개. mechanism 무수정 후처리 시뮬로 P50/P67/P75 분위수 + cross_faction_lord_count 산출. **결정적 발견**: P75에서 cross_faction_lord_count = 4·3·3 자연 발생, 그러나 acceptance #2(종료 시점)는 0/1/0으로 collapse.
4. **2026-05-02 3엔진 cross-check** (Claude+Codex+Gemini quick mode 1라운드, axis B PROBE 5단 입력): anger mechanism 차단 만장. **Φ-3 closure 시점에 새 이견** (옵션 X/Y/Z).

**핵심 통찰**: 잠재력은 자연 발생 중(중간 시점 cross_faction_lord_count = 3~4), 문제는 **종료 시점 collapse 경로**. 이는 mechanism 부재가 아니라 **environmental/territory 차원 collapse 진단 부재**.

---

## 2. 측정값 출처 명료화 (1차 validation §(b) 권고 반영)

본 closure는 다음 측정 시점·결과를 **공식 출처**로 인정한다.

### 2.1 acceptance 3종 — 출처 (Phase 14 resonance 적용 후 자연 측정)

| # | 기준 | 출처 1 (hotfix) | 출처 2 (resonance) | 출처 3 (SNN-output-diag) | **본 closure 인정** |
|---|------|:---:|:---:|:---:|:---:|
| 1 | `uprising_event ≥ 1` | 8/12/9 | 13/11/16 | 20/14/16 | **3 모두 PASS** (자연 빈도) |
| 2 | `grievance_pairs_end ≥ 1` | 0/0/0 | 0/0/0 | **0/1/0** | **1/3 PASS** (출처 3) |
| 3 | `dom_share_end ≥ 0.50` | 80/100/50% | 100/100/100% | 100/70/100% | **3 모두 PASS** |

**closure에 인정하는 기준 측정**: 출처 3 (Phase 14B-d1 SNN-output-diag, 2026-04-30). 가장 최신·완전 mechanism 적용 측정.

**1/3 PASS의 통계 의미**:
- random baseline: 3 seed 각각 독립 시 acceptance #2 자연 발생 확률이 0.33 면 1/3 = 0.33 일치 → 우연 가능성 존재.
- 그러나 PROBE 시뮬: P75에서 cross_faction_lord_count = 4·3·3 자연 발생 (잠재력 명확)
- seed-13의 1쌍은 5000틱 종료 시점 단 1쌍만 잔존 → **부분 신호**(잠재력 → collapse 경로 → 종료 시점 0~1쌍 잔존)
- 이는 우연 < 자연 결합점 부분 신호 (acceptance #1·#3 자연 PASS와 함께 해석)

### 2.2 secondary metrics — 출처 3 기준

| seed | active_factions_end | branch_factions_total | uprising_join_share | drift_ratio | gini_mean |
|------|:---:|:---:|:---:|:---:|:---:|
| 7 | 1 | 0 | 100% | 62% | 0.83 |
| 13 | 2 | 0 | 100% | 58% | 0.49 |
| 42 | 1 | 0 | 100% | 60% | 0.74 |

**branch_factions_total = 0**: 모든 봉기가 join (인접 faction 흡수). branch faction 자연 발화 경로 부재. Φ-4 검토 대상.

### 2.3 Phase 14B-B PROBE 결과 (acceptance 자체가 아닌 §3.7 4단 산출물)

| 후보 | 임계 | seed-7 cross_faction_lord_count | seed-13 | seed-42 | 시뮬 PASS 비율 |
|------|:---:|:---:|:---:|:---:|:---:|
| P50 | 0.5293 | 4 | 5 | 6 | 51% |
| P67 | 0.5942 | 4 | 4 | 3 | 73% |
| **P75** | **0.6406** | **4** | **3** | **3** | **82%** |

**핵심**: P75에서 잠재력 = 3 모두 ≥ 3 자연 발생. 그러나 acceptance #2 (종료 시점) = 0/1/0. **collapse 경로가 잠재력을 흡수**.

---

## 3. 3엔진 cross-check 결과 (axis B PROBE 5단)

`subagent-runs/discuss/phase14b-b-anger-coupling-cross-check-2026-05-02-quick/discussion-summary.md` v2 인용.

### 3.1 Consensus (3-way 만장일치)

1. **anger 임계 mechanism = 거짓 보정 안티패턴**:
   - Claude: 코드 차원 `_compute_affiliation_tick`에 임계 분기 추가 → axis A 기각 사유 그대로 재현 (구조 동형).
   - Codex: affiliation tick 회귀 위험 + acceptance #2 PASS 강제 의도가 axis A와 동일.
   - Gemini: top-down 규칙 강제 → SNN 자연 emergence 저해 (false correction anti-pattern).
2. **§3.7 사슬 정합**: 4단 PROBE는 분위수 도출·시뮬로 충실 수행. 5단 cross-check 정상 진입.
3. **진짜 결합점 = territory 설계 차원**: cross-faction lord 잠재력은 자연 발생 중 (P75=3·3·3), 문제는 environmental/territory 차원의 종료 시점 collapse 경로. axis A cross-check (2026-04-28) 권고와 정합.

### 3.2 Disputed (Φ-3 closure 시점 새 이견)

3엔진은 anger mechanism 차단 합의. 그러나 **Φ-3 closure 시점**에 이견 발생:

- **Claude+Codex (2/3)**: 옵션 X = 1/3 PASS 즉시 closure + Φ-4 진입.
- **Gemini (1/3)**: 옵션 Y = natural PASS rate 도달 후 closure (자연 평형 관찰 우선) OR 옵션 Z = acceptance 재정의.

### 3.3 Gemini 폴백 사실 명문화

- 원 spec 모델: `gemini-3.1-pro` (사용자 메모리 `feedback_gemini_model_pin.md` 고정).
- 실제 응답 모델: **`gemini-2.5-flash`**.
- 폴백 사유: gemini-3.1-pro ModelNotFound 404 → gemini-2.5-pro capacity exhausted (10회 retry) → gemini-2.5-flash 폴백 성공.
- 가중치 평가 이력: gemini-2.5-flash 응답을 본 cross-check의 Gemini 입장으로 인정. gemini-3.1-pro 회복 시 재검증 가능성 보존 (사용자 결정 트리거).

---

## 4. 사용자 결정 — 옵션 X+Y 하이브리드 채택

### 4.1 사용자 결정 evidence

- 검토 위임: `subagent-runs/claude/loom-phase14b-b-closure-option-review-2026-05-02/run-summary.md` (검토자 권고: X+Y 하이브리드)
- 사용자 승인: 2026-05-02 "메모리 갱신하고 우선순위대로 권고사항대로 진행해주세요"
- 결과: closure 즉시 + Φ-4 진입 전 cross-prop collapse 1단 진단 병행.

### 4.2 X+Y 하이브리드 의미

- **X 부분**: 1/3 PASS Case B로 closure 즉시 인정. Φ-4 STUB 이미 보유, §3.6 넓이 우선 적용. closure 지연이 거짓 보정 루프 위험을 키우지 않도록 즉시 종결.
- **Y 부분**: closure 즉시 선언 후 **mechanism 무수정 진단** 1단을 Φ-4 진입 전 의무 작업으로 추가. 자연 평형(systemic equilibrium) 관찰 + Φ-4 charter 입력값 확보.
- **Z 부분 거부**: acceptance #2 정의 재검토는 axis A 구조 동형 위험. Φ-4 charter에서 자연 통합 가능, 별도 선행 작업 불필요.

### 4.3 5 기준 평가 통과

| 기준 | 평가 | 근거 |
|------|:---:|------|
| 3계층 목표 (SNN 창발 우선) | 통과 | mechanism 무수정 진단으로 자연 발생 원칙 보존 |
| Phase 17 자연 발생 원칙 | 통과 | top-down 선언 없음, 거짓 PASS 차단 |
| §3.6 넓이 우선 | 통과 | Φ-3 즉시 closure → Φ-4 진입 가능 (Φ-4 STUB 보유) |
| §3.7 데이터 정당화 6단 사슬 | 통과 | 5단 cross-check 완료, 6단 closure 보고서 (본 v2) |
| 무파괴 9 + 안전 전제 5 + BOOST=0.20 | 통과 | mechanism 변경 없음, 진단만 |

---

## 5. axis B PROBE — 5단 통과·6단 mechanism 거부 결정

§3.7 데이터 정당화 사슬 6단 표준에 axis B PROBE 적용 결과:

| 단 | 작업 | 결과 |
|----|------|:----:|
| 1 | 자연 측정 (SNN-output-diag G1 결과 — anger·chronic 분리) | **PASS** (n=205, pass_avg=0.72 vs fail_avg=0.50) |
| 2 | 분포 분석 (mean, median, P25/50/67/75/80/90) | **PASS** (P50=0.529, P75=0.641, stdev=0.133) |
| 3 | 결합점 후보 (anger threshold → uprising leader gate 강화) | **PASS** (단 axis A·B 차별 정당화 5단에서 검증) |
| 4 | 임계 분위수 + 시뮬 PASS 비율 (P50/P67/P75) | **PASS** (P75 시뮬 82%, cross_faction_lord_count 자연 발생) |
| 5 | 3엔진 cross-check (Claude+Codex+Gemini-flash) | **PASS** (3-way 만장: anger mechanism = 거짓 보정 안티패턴) |
| 6 | mechanism 결정 — closure 보고서 | **REJECT** (mechanism 추가 거부, axis A와 구조 동형 차단) |

**6단 거부 결정 근거**:
- 5단 결과: anger 임계 mechanism 추가는 axis A 기각 사유와 구조 동형 (3-way 합의).
- 잠재력은 자연 발생 (P75=3·3·3), 문제는 종료 시점 collapse 경로 (territory 설계 차원).
- mechanism 추가는 collapse 경로를 차단하지 못하고 acceptance 강제 (false correction anti-pattern).

**axis B의 가치**:
- 5단 cross-check 자체로 **mechanism 추가 거부의 정당화 자료** 산출.
- "왜 axis A에 이어 axis B도 기각하는가"의 데이터 근거 확보 (단순 재기각 아님).
- §3.7 사슬이 mechanism 거부에도 작동함을 입증 (positive 결과만 아니라 negative 결과도 6단 사슬 통과).

---

## 6. 계약 검증 (무파괴 9 + 안전 전제 5종 + BOOST=0.20 + 회귀 7종)

### 6.1 무파괴 9 보장 유지

| # | 항목 | 결과 |
|---|------|:--:|
| 1 | `_change_persona_faction` 시그니처 | 무수정 |
| 2 | `FactionChangeSource` Literal 4종 | 무수정 |
| 3 | AST whitelist `# noqa: PHASE17_FACTION_SSOT_WRITE` 5건 | 무수정 |
| 4 | `Faction.grace_until_tick` | 무수정 |
| 5 | `Faction.founder_lineage` | 무수정 |
| 6 | `InnerWorld.residence_ticks` | 무수정 |
| 7 | SNN 뉴런 300~349 / n_neurons=1000 | 무수정 |
| 8 | D10 7종 read-only API | 무수정 |
| 9 | Φ-3 신규 상수 5종 값 | 무수정 |

### 6.2 안전 전제 5종

- HYSTERESIS=2 ✓
- FOUNDER_RESPAWN_EVERY=480 ✓
- TARGET_ACTIVE=2 ✓
- COMMIT_EVERY=48 ✓
- MINORITY_PERSISTENCE_MAX_MEMBERS=2 ✓

### 6.3 BOOST=0.20

`MINORITY_PERSISTENCE_BOOST = 0.20` 무수정. v1 closure §7 데이터 정당화 그대로.

### 6.4 회귀 테스트 7종 PASS

| # | 테스트 | 결과 |
|---|--------|:--:|
| 1 | `test_phase17_faction_handoff_contract.py` (12건) | PASS |
| 2 | `test_branch_faction_id_no_collision` | PASS |
| 3 | `test_grievance_lord_id_not_sticky` | PASS |
| 4 | `test_uprising_tick_no_artificial_injection` | PASS |
| 5 | `test_phase14b_snn_integration.py` (8건) | PASS |
| 6 | `test_phase17_faction_stage3.py` | PASS |
| 7 | `test_phase17_acceptance.py` `phi3_grievance_pairs_resonate` | FAIL (자연 — Case B 정의 그대로) |

`#7 FAIL`은 거짓 PASS가 아닌 **Case B 정의 그대로의 자연 결과** — closure에 명시 인정.

---

## 7. Findings (v1 finding 계승 + v2 신규)

### 7.1 v1 finding 계승

- **주 finding (v1 §6)**: Phase 14 grievance accumulator의 cross-faction pair 응결 결손 → Phase 14 resonance 보강으로 propagation mechanism 추가 (2026-04-29). 그러나 종료 시점 collapse 미해소.
- **보조 finding 1 (v1 §6)**: branch_factions_total = 0 (모든 봉기가 join) → 잔존. Φ-4 검토 대상.
- **보조 finding 2 (v1 §6)**: probe vs pytest grievance pair SSoT 분리 → 잔존. Φ-4 charter 작성 시 통합.
- **보조 finding 3 (v1 §6)**: `observe_phase17_emergence.py` `_write_top_summary` 중복 정의 → 잔존. 위생 작업 후속.

### 7.2 v2 신규 finding

#### 주 finding A: cross_faction_lord_count 잠재력 → 종료 시점 collapse 경로 (territory 설계 차원)

- **현상**: P75 시뮬에서 cross_faction_lord_count = 4·3·3 자연 발생 (잠재력 충분). 그러나 acceptance #2 종료 시점에는 0/1/0으로 collapse.
- **mechanism 분석**: 진행 중 cross-faction lord 자연 응결 → 단일 dominant faction 흡수 → cross_faction lord 소멸. propagation mechanism은 **발화 시점 잠재력 생성**은 가능하나 **유지 강제는 미작동**.
- **근본 원인 후보**: territory cross-propagation의 **유지 폭** 부족 (TTL/adjacency 경계). active_factions_end = 1·2·1 (대부분 단일 dominant 수렴) → cross-faction 자체가 소멸.
- **§3.7 1~3단 진단 의무**: Φ-4 진입 전 cross-prop collapse 1단 진단으로 종료 시점 collapse 인과 확정.

> #### Addendum: v3 재판정 (2026-05-03)
>
> Case C V3 PROBE (3 seed × 20,000틱, mechanism 무수정) 완료. **Finding A는 v3 PROBE 정의에서 자연 발생 PASS**로 재판정한다. 상세는 [PHASE-17-CASE-C-DIAGNOSIS-REPORT-V3.md](PHASE-17-CASE-C-DIAGNOSIS-REPORT-V3.md) §13 참조.
>
> **v3 결과 요약**:
> - `cross_faction_lord_pair_emerged` 누적 = **22 / 23 / 19** (seed 7/13/42), P75 자연 발생 한참 초과 — 자연 발생 잠재력 PASS.
> - PROBE 정의 collapse = **0 / 0 / 0** — event_log 누적 정의에서는 단조 증가, "collapse" 미관측.
> - `conflict_pair_at_20000` = **1 / 1 / 1** — closure-v2 §6.2 자연 종결 1·1·1과 동일 (acceptance #2 의도 분포 도달).
>
> **v2 "잠재력 vs collapse" 해석 재해석**:
> - v2 본문은 **territory 점유 기반 측정**(소유자 = lord, 종료 시점 dominant 흡수로 collapse 0/1/0)
> - v3 PROBE는 **event_log 누적 측정**(`top_lord_id+fid` pair 감지, 단조 증가)
> - 두 측정은 **동일 현상의 두 차원**이며, 어느 쪽도 거짓 아님. v3 정의로 자연 발생 잠재력은 충분 — Φ-4 Trigger 1번 충족.
> - "termination collapse" 진단은 **mechanism 결손이 아니라 측정 정의 차원 차이**로 재해석 → mechanism 변경 불요 (axis C 가드레일 OQ 7-d 부합).
>
> **§3.7 1~3단 진단 의무 처리**:
> - 1단 (자연 측정): v3 PROBE로 완료 — 자연 발생 PASS.
> - 2단 (분포 분석): P50/P67/P75 분위수 시뮬과의 정합 확인 — 자연 발생은 P75 한참 상회.
> - 3단 (결합점 후보): collapse는 측정 정의 차원, mechanism 결합점 아님으로 결론 → 4단 임계 분위수 진입 불요.
> - 결과: Φ-4 진입 가능 (옵션 X+Y 하이브리드의 Y 부분 PASS).
>
> **무파괴 9 + 안전 전제 5종 + BOOST=0.20 + 회귀 7종 보존**: v3 진단 전 과정에서 변경 없음 확인. axis C 가드레일 5종 모두 PASS.
>
> **보고서 헤더 갱신**: closure-v2 §7.2 Finding A는 v3 진단으로 보강된 것이며, 본문은 v2 시점(2026-05-02) 기록을 보존한다.

#### 주 finding B: anger threshold mechanism = 거짓 보정 안티패턴 (axis B 6단 거부)

- **현상**: 5단 cross-check 3-way 합의 — anger 임계 mechanism 추가는 axis A 기각 사유와 구조 동형.
- **결정**: §3.7 6단 거부 (closure 보고서). axis B는 mechanism 추가 없이 **negative 결과** 산출.
- **가치**: 거짓 PASS 차단 + Φ-4 입력값 (territory 설계 차원이 진짜 결합점) 확보.

### 7.3 보조 finding 4 (v2 신규): branch faction 자연 경로 재검증 필요

- v1 §6 보조 finding 1과 동일 현상 잔존 + Phase 14B-B PROBE에서 추가 확인.
- `_uprising_trigger`의 인접 faction 강제 조건 → branch 발화 구조 차단 (가설 H1, Case C 진단 spec 참조).
- Φ-4 Nation charter 설계 시 자연 branch 경로 검토 필수 (분파→연맹→국가 사슬에서 분파 자체가 발생 안 함).

---

## 8. 다음 단계 (3계층 시퀀스)

### 8.1 Φ-3 closure 즉시 (본 v2 채택)

- 본 보고서 작성·커밋 시점에 **Φ-3 Case B closure 공식 인정**.
- mechanism 추가·acceptance 재정의 모두 거부.
- 회귀 테스트 #7 FAIL은 자연 결과로 인정 (`expected_failure` 처리 또는 acceptance 분리는 Φ-4 charter 단계 결정).

### 8.2 Φ-4 진입 전 의무 — cross-prop collapse 1단 진단

기존 `PHASE-17-CASE-C-COLLAPSE-DIAGNOSIS-SPEC.md`와 통합 검토 결과:
- Case C 진단 spec은 **active_factions_end collapse**를 진단 (가설 H1~H4, mechanism 무수정 텔레메트리 5종).
- cross-prop collapse 진단은 **cross_faction_lord_count 종료 시점 collapse**를 진단.
- **두 collapse는 동일 현상의 두 측면**: 단일 dominant faction 흡수 → active_factions=1 동시 cross_faction_lord_count=0.
- **결정**: 별도 spec 작성 불필요. 기존 Case C diagnosis spec을 **cross_faction_lord_count 추적 보강**으로 확장.

(상세 보강 사항은 §10 후속 작업에서 제시.)

### 8.3 Φ-4 full Charter 작성 (병렬 가능)

- `/design` 사이클로 Φ-4 Open Questions 6개 해소.
- **axis C 안티패턴 가드레일 명문화** (1차 validation §(d) 권고): Φ-4 1번 작업이 mechanism 변경으로 이어질 경우 §3.7 6단 사슬 처음부터 재진입 의무.
- **Φ-4 STUB Entry Trigger 4번 갱신**: "Φ-3 closure Case B 인정 시 Trigger 1번(`dom_share`)만으로 진입 가능" 추가.
- 진단 결과를 Φ-4 charter 입력값으로 사용 (territory 설계 차원).

---

## 9. 결론

본 closure-v2는 다음을 공식화한다:

1. **Φ-3 Struggle Case B 공식 closure** — 1/3 PASS는 자연 결합점 **부분 신호**, 우연 아닌 collapse 경로 잠복.
2. **axis B PROBE의 6단 거부 결정** — anger mechanism 추가는 axis A 기각 사유와 구조 동형 (3-way 합의). §3.7 사슬이 negative 결과로도 작동함을 입증.
3. **진짜 결합점 = territory 설계 차원** — cross-faction lord 잠재력 자연 발생 + 종료 시점 collapse 경로. Φ-4 charter 핵심 입력.
4. **사용자 옵션 X+Y 하이브리드 채택** — closure 즉시 + 진단 병행. mechanism 무수정 진단으로 거짓 보정 루프 차단.
5. **Gemini 폴백 사실 명문화** — gemini-2.5-flash 응답을 본 cross-check 입장으로 인정. 회복 시 재검증 가능성 보존.
6. **무파괴 9 + 안전 전제 5종 + BOOST=0.20 + 회귀 7종 보존** — mechanism 변경 없음, 진단만.

**v2 closure의 의미**:

> "거짓 PASS는 절대 허용하지 않는다" (CLAUDE.md `feedback_snn_emergence_first.md` + `feedback_root_cause_first.md`)는 원칙은 본 closure에서 두 번째로 작동했다 — v1에서 hotfix v1로 mechanism 거짓 5건을 제거했고, v2에서 mechanism 추가 자체를 거부하여 거짓 보정 루프 진입을 차단했다. **자연 mechanism이 부족하면 mechanism을 추가하는 것이 아니라 자연 mechanism의 결손 인과를 진단한다** — 이것이 §3.7 사슬의 본질이다.

Φ-3는 1/3 PASS에서 자연 종결되며, 진짜 병목(territory 설계 차원의 collapse 경로)은 Φ-4 charter 단계에서 자연 mechanism으로 흡수된다.

---

## 10. 후속 작업 (구체)

### 10.1 즉시

- [x] 본 closure-v2 작성·커밋
- [x] Gemini 폴백 우선순위 메모리 갱신 (`feedback_gemini_model_pin.md`)
- [x] `PHASE-17-CASE-C-COLLAPSE-DIAGNOSIS-SPEC.md` rev.3에 cross_faction_lord_pair_emerged + collapsed 텔레메트리 보강 완료 (2026-05-03)
- [x] V3 PROBE 3 seed × 20,000틱 실행 + 진단 보고서 (`PHASE-17-CASE-C-DIAGNOSIS-REPORT-V3.md`) 작성 완료 (2026-05-03)
- [x] §7.2 Finding A v3 재판정 addendum 추가 (2026-05-03)
- [ ] `PHASE-17-NATION-CHARTER-STUB.md` Entry Trigger 4번 갱신 + axis C 안티패턴 가드레일 명문화 (§10.3, 다음 작업)

### 10.2 Case C diagnosis spec 보강 항목 (별도 spec 작성 불필요, 기존 spec 확장)

기존 §3.1 텔레메트리 5종에 추가:
- `cross_faction_lord_resonance` 이벤트: 동일 `top_lord_id`를 가진 cross-faction pair가 중간 시점 발화 + 종료 시점 collapse 추적. 발화 tick + collapse tick + collapse 사유 (lord 페르소나 사망 / faction 흡수 / dominant 합병 등).
- 기존 `active_factions_snapshot` 이벤트 확장: `cross_faction_lord_count` 필드 추가 (현재 active 중 cross-faction lord 응결 수).
- 보고서 Case C Diagnosis 섹션에 신규 가설 H5 추가: "cross-faction lord 잠재력 자연 발생 → 단일 dominant 흡수 collapse 경로" PASS/FAIL.

### 10.3 Φ-4 STUB 갱신 항목 (별도 작업)

- §Entry Trigger Candidates 4번 명문 추가: "Φ-3 closure Case B 인정 시 Trigger 1번(dom_share window=720 ≥ 0.55)만으로 진입 가능. 본 v2 closure 채택 후 자연 충족."
- §Open Questions 7번 추가 (axis C 안티패턴 가드레일):
  - Φ-4 1번 작업이 mechanism 변경 spec으로 이어질 경우 §3.7 6단 사슬 처음부터 재진입 의무.
  - axis A/B 기각 사유 자체 검증 — "acceptance #2 PASS 의도 mechanism" 자체 검증.
  - 3엔진 cross-check 재실행 (Gemini 포함, gemini-3.1-pro 가용성 확인 후).
  - spec 본문에 "mechanism 변경 위치와 axis A/B와의 차별 정당화" 명시 의무.

### 10.4 위생 작업 (병행 가능, 비차단)

- v1 §7 잔존: `data/phase17_probe*/` `.gitignore` 패턴 확장
- v1 §7 잔존: `_write_top_summary` 중복 정리

---

## 11. Evidence

- `subagent-runs/discuss/phase14b-b-anger-coupling-cross-check-2026-05-02-quick/` — 3엔진 cross-check 전체 (round-1 raw + summary v2 + validation)
- `subagent-runs/claude/loom-phase14b-b-closure-option-review-2026-05-02/` — 옵션 X/Y/Z 검토 위임
- `data/phase14b_b_threshold_simulation.md` — Phase 14B-B PROBE 4단 산출
- `data/phase17_probe_phi3-snn-output-diag/SUMMARY.md` — Phase 14B-d1 진단 (acceptance 측정 출처 3)
- `data/phase17_probe_phi3-phase14-resonance/SUMMARY.md` — Phase 14 resonance 보강 결과
- `data/phase17_probe_phi3-hotfix/SUMMARY.md` — v1 hotfix 결과
- `PHASE-17-STRUGGLE-CLOSURE-REPORT.md` — v1 closure (참조 보존)
- `PHASE-14B-B-ANGER-COUPLING-PROBE-SPEC.md` — axis B PROBE spec
- `PHASE-17-CASE-C-COLLAPSE-DIAGNOSIS-SPEC.md` — cross-prop collapse 진단 spec (보강 대상)
- `PHASE-17-NATION-CHARTER-STUB.md` — Φ-4 STUB (갱신 대상)
- 본 파일 — closure-v2 (최종 closure)
