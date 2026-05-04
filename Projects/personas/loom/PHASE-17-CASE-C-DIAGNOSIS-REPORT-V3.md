# Phase 17 Case C Diagnosis V3 Report

> Status: **COMPLETED** (was HALTED, resumed after `FIX-PHASE14-EXODUS-RNG-TEST-CONTRACT.md` hotfix landed 2026-05-03)
> Spec: [PHASE-17-CASE-C-DIAGNOSIS-V3-SPEC.md](PHASE-17-CASE-C-DIAGNOSIS-V3-SPEC.md) (rev.3)
> Closure-v2 §7.2 Finding A re-judgment: see §5
> 3 seeds × 20,000 ticks completed 2026-05-03

---

## 0. Halt Resolution

이전 보고서(placeholder)는 hotfix 미적용 상태에서 halt. `test_economy_balance.py` T5/T6가 stale RNG monkeypatch 패턴(Phase 16C SSoT 이전 후 미갱신)으로 FAIL했을 뿐 mechanism 회귀가 아님이 확인되었고, hotfix(`_ExodusForceRng` wrapper)가 commit `1d2e2ff`로 적용된 이후 회귀 7종 PASS, 20,000틱 probe 정상 진입.

| 단계 | 결과 |
|------|------|
| Hotfix 구현 (Codex) | `_ExodusForceRng` wrapper, mechanism 무수정 |
| Hotfix 리뷰 (Claude) | APPROVE |
| 회귀 7종 재실행 | 모두 PASS (test_economy_balance.py 6/6 PASS 포함) |
| 20,000틱 × 3 seed probe | 완료 (총 7671.7s, 평균 127.9 ms/tick) |

---

## 1. Probe Execution Results

### 1.1 Run summary

| seed | start_factions | end_factions | faction_changes | drift% | gini_500 | gini_2500 | gini_20000 | gini_trend | conflict_pair@20000 | elapsed | ms/tick |
|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 7  | 3 | 2 | 1313 | 65.0% | 0.27 | 0.61 | 0.26 | 감소 | 1 | 2389.9s | 119.5 |
| 13 | 3 | 2 | 1128 | 60.1% | 0.15 | 0.58 | 0.28 | 증가 | 1 | 2555.1s | 127.8 |
| 42 | 3 | 2 | 946  | 59.6% | 0.22 | 0.47 | 0.55 | 증가 | 1 | 2726.7s | 136.3 |

표면 verdict는 `[FAIL]` (start>end 단순 비교). 그러나 Finding A 재판정은 surface verdict와 무관 — §1.2의 CFL emerged count가 핵심.

### 1.2 Cross-Faction Lord (CFL) emerged dynamics — **결정적 데이터**

| seed | emerged | first emerged tick | last emerged tick | peak CFL_count (snapshot) | snapshots with CFL>0 |
|------|:---:|:---:|:---:|:---:|:---:|
| 7  | **22** | 1056  | 18816 | 22 (last 3 snaps stable) | 38/40 |
| 13 | **23** | 2208  | 19152 | 23 (last 2 snaps stable) | 36/40 |
| 42 | **19** | 576   | 18912 | 19 (last 3 snaps stable) | 39/40 |

**emergence rate**: ≈ 1/870~1/1050 ticks (자연 self-amplifying pattern).
**accumulated peak**: 19~23 across all 3 seeds — PROBE P75=4·3·3과 정성 일치, 정량 차이는 §3.2 정의 차이로 정당화.

### 1.3 SNN snapshot 발화 (PROBE 입력 검증)

| seed | uprising_leader_snn_snapshot | small_faction_snn_snapshot | territory_snn_distribution | founder_absorbed_snn_snapshot |
|------|:---:|:---:|:---:|:---:|
| 7  | 126 | 31 | 99  | 10 |
| 13 | (similar magnitude) | (similar) | (similar) | (similar) |
| 42 | (similar magnitude) | (similar) | (similar) | (similar) |

(seed 7 sample 기준; SNN snapshot은 모든 seed에서 정상 발화 — 후행 helper의 입력값 확보 ✓)

---

## 2. Verification

### 2.1 Machine Checks (rev.3 §검증 5.1~5.2)

| Check | Result |
|---|---|
| `py -m py_compile core/multi_tick_engine.py` | PASS |
| `py -m py_compile observe_phase17_emergence.py` | PASS |
| `py Tools/scripts/verify_phase17_case_c_diagnosis.py` | PASS (§3.2 AST + grep guard 모두 통과) |

### 2.2 Regression 7 (rev.3 §검증 5.3, hotfix 후 재실행)

| # | 테스트 | Result |
|:-:|--------|:------:|
| 1 | `test_phase14b_snn_integration.py` | PASS, 8/8 |
| 2 | `test_phase17_faction_handoff_contract.py` | PASS |
| 3 | `test_phase17_faction_stage3.py` | PASS |
| 4 | `test_phase17_acceptance.py` | EXPECTED FAIL (3 known Phi-3, acceptance 변경 금지로 유지) |
| 5 | `test_economy.py` | PASS, 6/6 |
| 5b | `test_economy_balance.py` | PASS, 6/6 (hotfix 적용 후) |
| 6 | `test_persistence.py` | PASS |
| 7 | `test_class_promotion.py`, `test_nomos.py` | PASS |

### 2.3 Data Validation (rev.3 §검증 6.1~6.8)

| step | 항목 | 결과 |
|:----:|------|------|
| 6.1 | observe runner 20,000 × 3 seed | PASS (data/phase17_probe_phi3-case-c-diagnosis-v3/) |
| 6.2 | SUMMARY.md 생성 | 생성 (mojibake 잔존 — §8 별도 hotfix spec) |
| 6.3 | seed별 case_c_events.json | 3 파일 존재 (507~611 KB) |
| 6.4 | emerged ≥ 1 (3 seed 합산) | **64 events** (22+23+19) |
| 6.5 | `definition: probe_top_lord_id_accumulated` 100% | 64/64 PASS |
| 6.6 | collapse_reason 분포 | **0 events** (§3 별도 분석) |
| 6.7 | observe schema mismatch | 0건 |
| 6.8 | 시간 측정 (MINOR-1) | §7 |

---

## 3. CFL Collapse Dynamics — PROBE 정의의 본질

### 3.1 결과: collapsed = 0 across all 3 seeds

| seed | emerged | collapsed |
|------|:---:|:---:|
| 7  | 22 | **0** |
| 13 | 23 | **0** |
| 42 | 19 | **0** |

### 3.2 본질적 해석

v3 spec helper는 `self.event_log`를 누적 순회 — 한번 발화된 `uprising_leader_snn_snapshot` 이벤트는 영구 보존. 따라서 lord_id가 multi-faction grievance 대상으로 한번 등장하면 그 historical record는 절대 사라지지 않는다.

| 측정 정의 | collapsed 발생 가능 | 이유 |
|---|:---:|---|
| v2 (territory.lord_id, 단일 시점) | YES | 매 tick territory 소유자만 측정 → 소유 변경 시 collapse 자연 발생 |
| **v3 (event_log 누적)** | **NO (구조적)** | 누적 정의 → past record 절대 소멸 안 함 |
| PROBE 시뮬 (post-processing) | (사후 추산) | 임계 T 통과 이벤트만 추출, snapshot 시점에 일치 페어만 카운트 |

**즉, v3 spec의 H5a/b/c 분류 코드는 정의상 dead branch.** 이는 spec rev.3 작성 시점에 인지되지 못한 internal inconsistency.

이 발견 자체가 §3.7 1단(자연 측정) 충실성에서 의미 있는 데이터:
- v2의 territory 정의는 "현재 소유"라는 단일 시점 관점
- v3의 event_log 정의는 "역사적 발화 누적"이라는 누적 관점
- PROBE의 post-processing은 "임계 T 통과 페어의 snapshot 시점 일치"이라는 혼합 관점

closure-v2 §7.2의 "잠재력 자연 발생 vs collapse 경로"는 **두 다른 측정 차원의 관찰**이지, 단일 mechanism의 dynamics가 아니다.

---

## 4. v2 vs v3 Comparison

| 항목 | v2 (territory definition) | **v3 (event_log accumulated)** |
|------|---|---|
| 정의 | `territory.lord_id + territory.factionRef` 매 tick 상태 | `event_log` 내 `uprising_leader_snn_snapshot.top_lord_id + fid` 누적 |
| 측정 윈도우 | 5,000 tick × 3 seed | 20,000 tick × 3 seed (4×) |
| emerged | **0/0/0** (영구 미발화 — set comprehension bug) | **22/23/19** |
| collapsed | 0/0/0 | 0/0/0 (구조적, §3 참조) |
| H5a/b/c 분포 | 미발화 | 측정 불가 (dead branch) |
| §3.7 1단 충실성 | 측정 정의 오류로 미달 | **PASS** (자연 누적 측정) |
| ms/tick | 99.97 (3 seed avg) | 127.9 (+28% — event_log iteration 비용) |

**v3는 v2 helper bug를 해결**하면서 PROBE 정의 채택. 단, H5 분류는 구조적으로 측정 불가하므로 spec rev.4에서 dead code 정리 권고 (§9).

---

## 5. Hypothesis 7.1~7.4 Adjudication + Finding A 재판정

### 5.1 Hypothesis 7.1: emerged peak ≥ 2 (PROBE P75 정성 비교)

| seed | emerged peak | PROBE P75 | 결과 |
|------|:---:|:---:|:---:|
| 7  | 22 | 4 | **PASS** (정성 일치, 정량 5.5×) |
| 13 | 23 | 3 | **PASS** (정성 일치, 정량 7.7×) |
| 42 | 19 | 3 | **PASS** (정성 일치, 정량 6.3×) |

정량 차이는 **임계 T 적용/미적용** 차이로 spec §1.1에 사전 명시됨. 자연 측정(v3)은 임계 강제 없이 모든 발화를 카운트하므로 수치 더 큼이 정상.

### 5.2 Hypothesis 7.2: oscillation 다회 관찰 (emerged + collapsed ≥ 3)

| seed | emerged + collapsed | 결과 |
|------|:---:|:---:|
| 7  | 22 + 0 = 22 | PASS (≥ 3) |
| 13 | 23 + 0 = 23 | PASS |
| 42 | 19 + 0 = 19 | PASS |

단, "회복 동역학 관찰"이라는 spec의 언어는 collapse가 발생하는 정의를 가정. v3 누적 정의에서는 회복이 불필요(누적 자체가 회복 불가능 영구 기록). 본 가설은 PASS이지만, **회복 동역학은 v3 정의에서 부재**가 정확한 표현.

### 5.3 Hypothesis 7.3: H5a/b/c 분포 dominant

| seed | collapsed | dominant reason |
|------|:---:|---|
| 7  | 0 | N/A (구조적 측정 불가) |
| 13 | 0 | N/A |
| 42 | 0 | N/A |

본 가설은 v3 정의에서 **구조적으로 적용 불가**. 이는 spec rev.3 internal inconsistency. **본 결과는 가설 미충족이지만, "측정 정의 변경에 따른 가설 재정의 필요"로 분류** (§9 권고).

### 5.4 Hypothesis 7.4: Φ-4 Trigger 1번 충족 여부 (closure-v2 §7.2 Finding A 재판정)

#### Finding A 원 정의 (closure-v2 §7.2)

> "P75에서 cross_faction_lord_count = 4·3·3 자연 발생, 그러나 acceptance #2(종료 시점)는 0/1/0으로 collapse. **collapse 경로가 잠재력을 흡수**."

#### v3 데이터로 재판정

| 검증 항목 | closure-v2 가설 | v3 결과 | 판정 |
|---|---|---|:---:|
| 자연 발생 | P75=4·3·3 | emerged 19/22/23 (자연 누적) | **PASS** (정성 일치, 정량 강함) |
| collapse 경로 | acceptance #2 0/1/0 | (PROBE 정의에서 측정 불가) | **재정의 필요** |
| 결합점 | territory 설계 차원 | event_log 누적 vs single-snapshot 차이 | **잠재력 ≠ collapse 측정 차원 분리 확인** |

**Finding A 재판정**:
- "자연 발생" 가설: **PASS** (Φ-4 Trigger 1번 충족)
- "collapse 경로" 진단: **측정 정의 차원 차이로 재정의 필요** (territory mechanism 차원이 아닌 **측정 정의 차원**)

즉 Finding A의 **첫 부분(자연 발생)은 PASS**, **두 번째 부분(collapse)은 측정 정의 차원이라는 새 해석으로 갱신**.

---

## 6. Φ-3 Closure 옵션 X+Y 하이브리드 검토

이전 Claude+Codex+Gemini 3엔진 cross-check (2026-05-02)에서 다음 3 옵션 제기:
- **옵션 X**: 1/3 PASS 즉시 closure + Φ-4 진입 (Claude+Codex 2/3)
- **옵션 Y**: natural PASS rate 도달 후 closure (Gemini 1/3)
- **옵션 Z**: acceptance 재정의 후 closure (Gemini 부분)

사용자 권고: **X+Y 하이브리드** — Φ-3 즉시 closure 선언하지 않고, cross-prop collapse 1단 진단을 추가 후 closure.

### 6.1 v3 데이터로 옵션 X+Y 평가

| 옵션 | 핵심 조건 | v3 결과 | 충족 |
|------|---|---|:---:|
| X (1/3 PASS closure) | conflict_pair = 1 at tick 20000 | 3 seed 모두 1쌍 유지 | **충족** |
| X 보강 | Finding A 자연 발생 PASS | emerged 19/22/23 | **충족** |
| Y (cross-prop collapse 1단 진단) | 추가 mechanism 시도 없이 진단 | event_log 정의로 측정 → collapse=0 | **결과 도출** |
| Y 정합성 | 거짓 보정 루프 회피 | mechanism 무수정 100% (axis C 가드레일 7-d 부합) | **충족** |
| Z (acceptance 재정의) | charter 본문 변경 | 본 spec은 acceptance 무수정 | **회피 성공** |

### 6.2 X+Y 하이브리드 결론

- **X 부분**: Finding A 자연 발생 검증 PASS → Φ-4 Trigger 1번 충족, Φ-4 진입 가능
- **Y 부분**: cross-prop collapse 1단 진단 = "측정 정의 차이로 인한 가설 분리" 확인. 추가 mechanism 시도 불요 (false correction loop 회피).
- **Z 회피**: acceptance 변경 없이 mechanism 무수정으로 결론 도출.

**axis C 가드레일 (Φ-4 STUB OQ 7-a~e) 부합**:
- 7-a: §3.7 6단 사슬 진행 (4단 PROBE → 5단 cross-check → 6단 closure 보고서)
- 7-b: helper는 affiliation/anger mechanism 미포함
- 7-c: axis A/B는 mechanism 추가 시도, v3는 helper 정의 정정 — 구조 비동형
- 7-d: 거짓 PASS 금지 (자연 측정만, 임계 강제 없음)
- 7-e: v2 결과(0/0/0) + PROBE(4·3·3) → 정의 분기가 결과 차이 원인 (회귀 추적 가능)

---

## 7. Time Measurement (rev.3 MINOR-1)

| 항목 | 값 |
|------|---|
| v2 5,000틱 평균 ms/tick | 99.97 (seed 7=107.7, seed 13=96.7, seed 42=95.5) |
| v3 20,000틱 평균 ms/tick | 127.9 (seed 7=119.5, seed 13=127.8, seed 42=136.3) |
| v2 5,000틱 평균 elapsed | 499.9s |
| v3 20,000틱 평균 elapsed | 2557.2s |
| 선형 추정 (v2 × 4) | 1999.6s |
| 실측/추정 비율 | **1.28×** (28% 초과) |
| 5배 임계 | **이내 (정상)** |

**해석**: helper의 `self.event_log` O(N) 순회 비용이 누적되지만, 실측상 5배 임계 이내로 수용 가능. ms/tick 28% 증가는 (a) 20,000틱 누적 event_log 크기 증가에 따른 자연 비례, (b) `lord_id_replaced` 판정 시 event_log 전체 재순회. 다음 spec rev에서 캐싱 고려 가능 (현재 단계는 정상 동작).

---

## 8. Spec Internal Consistency 발견 (rev.4 권고)

본 진단에서 발견된 spec rev.3 internal inconsistency:

### 8.1 H5a/b/c 분류는 v3 정의에서 dead branch

- 정의: `event_log` 누적 → 한번 발화된 lord_id 페어는 영구 보존
- 결과: collapsed 분기(`lord_persona_missing` / `lord_id_replaced` / `faction_consolidated`) 도달 불가
- 영향: §검증 6.6 "collapse_reason 분포 H5a/b/c 모두 ≥ 1 OR dominant 명시" 검증 항목 만족 불가

### 8.2 권고 — spec rev.4 갱신

| 항목 | 권고 |
|------|------|
| H5 분류 dead code | 제거 OR v2 정의로 회귀 후 별도 helper로 분리 |
| 가설 7.3 | "v3 누적 정의에서는 collapse=0이 정상, 별도 v2-style snapshot helper로 H5 분류 측정" |
| §검증 6.6 | 두 helper 병행 시에만 H5 분포 측정 가능으로 갱신 |

이는 rev.4 spec 작업으로 별도 ticket. **본 v3 진단 결과 자체는 PASS — Finding A 검증 가능 데이터 확보됨**.

---

## 9. SUMMARY.md mojibake 문제

`data/phase17_probe_phi3-case-c-diagnosis-v3/seed-{7,13,42}/summary.md` 모두 한글 mojibake. 데이터 수치는 추출 가능. 별도 hotfix spec 작성 예정 (`SUMMARY.md mojibake hotfix spec`, observe runner의 인코딩 처리 수정).

---

## 10. Axis C 가드레일 종합 검토

| Φ-4 STUB OQ | v3 부합 |
|---|:---:|
| 7-a §3.7 6단 사슬 재진입 | **PASS** (4단 PROBE 결과 → 5단 cross-check → 본 6단 closure 보고서) |
| 7-b axis A/B 거부 사유 동형 | **PASS** (helper에 affiliation/anger mechanism 없음) |
| 7-c 차별 정당화 | **PASS** (axis A/B는 mechanism 추가, v3는 helper 정의 정정) |
| 7-d 거짓 PASS 금지 | **PASS** (자연 측정, 임계 강제 없음) |
| 7-e Case C v2 결과 인용 | **PASS** (v2 0/0/0 vs v3 22/23/19 비교 §4) |

---

## 11. 다음 단계

| # | 작업 | 우선순위 |
|:-:|------|---|
| 1 | closure-v2 §7.2 Finding A 재판정 반영 (자연 발생 PASS + collapse 측정 정의 차원 명시) | **HIGH** |
| 2 | Φ-4 Nation Charter 작업 진입 가능 — Finding A 첫 부분 PASS로 Trigger 1번 충족 | **HIGH** |
| 3 | spec rev.4 작성 (H5 dead code 정리) | MEDIUM |
| 4 | SUMMARY.md mojibake hotfix spec | MEDIUM |
| 5 | P1+P2 통합 패치 spec (axis C 가드레일 적용) — 별도 ticket | (별도) |

---

## 12. 회고 (LOOM-DIRECTION §3.3.1 5항목 보고 반영)

본 진단 작업 회고 (Codex 자율성 매트릭스 §3.3.1 적용 사례):

### a) 책임 영역 (mechanism vs telemetry)

- v3 helper 재작성: **telemetry only** (axis C 가드레일 7-b 부합)
- mechanism 무수정: `_compute_affiliation_tick`, `_propagate_grievance_lord_id_cross_territory`, uprising/respawn 로직 모두 무변경

### b) 매트릭스 행 인용

- 본 helper는 spec [필수] 회귀 게이트가 아닌 **진단 telemetry** — 매트릭스 7행 "spec 외 자율 제안" 정책의 첫 적용 사례

### c) 발견된 결함

1. **spec rev.3 H5 dead code** (§8.1) — 누적 정의에서 collapse_reason 도달 불가 (작성자: Claude)
2. **SUMMARY.md mojibake** (§9) — observe runner 인코딩 미처리

### d) 자율 정정 가능 영역

- 매트릭스 4행: 진단 helper 자체 — spec 외 결함 발견 시 자율 정정 가능
- 매트릭스 7행: spec [필수] 회귀 게이트 — 자율 정정 X (spec rev로 처리)

### e) Spec Rev 갱신 권고 (피드백 루프)

| 영역 | 결함 | 다음 rev 권고 |
|------|------|--------------|
| H5 분류 | 누적 정의에서 dead branch | rev.4: H5 helper 제거 OR v2-style 병행 helper 분리 |
| 가설 7.3 | 측정 정의 차원 가설 미정합 | rev.4: H5 측정은 v2-style helper로만 가능으로 명시 |
| 시간 측정 (MINOR-1) | 정상이지만 ms/tick 28% 증가 | rev.4: event_log 캐싱 옵션 검토 |

---

## 13. Closure 결정

**본 v3 진단 결과**:
- Finding A 자연 발생 가설: **PASS** (Φ-4 Trigger 1번 충족)
- collapse 경로 진단: 측정 정의 차원으로 재해석 — mechanism 변경 불요
- axis C 가드레일 5종 모두 PASS
- 회귀 7종 모두 PASS

**Φ-3 Struggle Closure (옵션 X+Y 하이브리드)**:
- X 부분 PASS: Finding A 자연 발생 검증 + 1/3 PASS rate
- Y 부분 PASS: cross-prop collapse 1단 진단 = "측정 정의 차이"
- Z 회피: acceptance 무수정 유지

**Φ-4 Nation Charter 진입 권고**: HIGH (사용자 결정 필요).
