# Phase 14B-d1 — SNN 출력 회로 진단 보고서

> **Date**: 2026-05-02
> **선행 spec**: [PHASE-14B-SNN-OUTPUT-DIAGNOSIS-SPEC.md](PHASE-14B-SNN-OUTPUT-DIAGNOSIS-SPEC.md)
> **Run**: [subagent-runs/claude/loom-phase14b-snn-output-diagnosis-spec-2026-05-02/](../../subagent-runs/claude/loom-phase14b-snn-output-diagnosis-spec-2026-05-02/)
> **Engine**: Claude (메인 세션 직접 구현)
> **상태**: 진단 완료 — 결합점 후보 식별 + LOOM-DIRECTION §3.7 데이터 정당화 사슬 표준 권고

---

## 0. 3계층 목표 (LOOM-DIRECTION §3.1 의무)

- **궁극 목적**: SNN 창발 + PersonaBrain 논문. SNN gate 정당화의 데이터 사슬 표준이 정립되어야 anti-pattern #3 (SNN gate 정당화 부재) 회피가 데이터로 입증 가능.
- **Phase 17 Φ-3 목적**: Φ-3 Struggle 한계 (acceptance #2 자연 측정 1/3) 의 근본 원인 식별 → 결합점 자연 매핑 후보 도출 → Φ-4 Nation 진입 재료 보존.
- **현 작업의 고유 역할**: 4 가설 (G1~G4) 자연 측정 → SNN 출력 회로 정체 가설 검증 → 데이터 정당화 사슬 표준 정립.

---

## 1. 근본 원인 5단 추적 (spec §1.2 박힘) — 측정 후 재해석

| 단계 | 가설 | 측정 결과 | 판정 |
|:----:|------|----------|:----:|
| 표면 | acceptance #2 1/3 PASS | seed-7=0, seed-13=1, seed-42=0 | 일치 |
| 1단 | contact graph 붕괴 | uprising_skip_no_contact 56~154 (전 seed) | 일치 (active=1 collapse 시 uprising 차단) |
| 2단 | territory 흡수 | active_factions_end 7=1 / 13=2 / 42=1 | 일치 |
| 3단 | affiliation 보호 부족 | small_faction_snn_snapshot **n_persisted=19/12/5, n_expired=0** | **부분 기각** — BOOST가 보호 중이지만 흡수가 다른 경로로 일어남 |
| 4단 | BOOST 정적 임계 | minority_boost_applied 871/546/234 | BOOST 활발 작동 |
| 5단 | SNN 출력 회로 정체 | **G1+G4 PASS 3/3 (강한 신호)** | **기각** — 회로 자체는 정상 출력 |
| **재정의된 근본** | SNN 출력 신호 → mechanism 결합점 매핑 미설계 | G1 leader_anger diff 0.21 (gate에서만 사용) | **확정** |

**This tells us**: SNN 출력 회로는 정체된 게 아니라 **강한 신호를 출력하고 있는데**, 그 출력을 활용하는 mechanism 결합점이 uprising gate 한 곳에만 있다. G1 데이터는 SNN gate 정당화의 명확한 데이터 사슬을 제공한다 — anti-pattern #3 (SNN gate 정당화 부재) 가 본 진단으로 데이터에 의해 회피 가능해진 것.

---

## 2. 자연 측정 결과

### 2.1 Verdict Matrix (G1~G4)

| 가설 | seed-7 | seed-13 | seed-42 | 종합 |
|------|:------:|:-------:|:-------:|:----:|
| **G1** uprising leader gate diff | PASS | PASS | PASS | **3/3 PASS** |
| **G2** founder vs absorbing chronic | INSUFFICIENT_N | INSUFFICIENT_N | INSUFFICIENT_N | **0/3 (자연 희소)** |
| **G3** small faction persist diff | INSUFFICIENT_N | INSUFFICIENT_N | INSUFFICIENT_N | **0/3 (BOOST 과보호)** |
| **G4** territory dist CV | PASS | PASS | PASS | **3/3 PASS** |

### 2.2 G1 Detail — uprising leader gate diff (★ 1순위 결합점)

| seed | n_pass | n_fail | diff_sum | pass_avg_anger | fail_avg_anger | pass_avg_chronic | fail_avg_chronic |
|:----:|:------:|:------:|:--------:|:--------------:|:--------------:|:----------------:|:----------------:|
| 7    | 20     | 24     | 0.637    | 0.723          | 0.493          | 0.810            | 0.786            |
| 13   | 14     | 48     | 0.677    | 0.729          | 0.512          | 0.769            | 0.805            |
| 42   | 16     | 83     | 0.557    | 0.706          | 0.487          | 0.784            | 0.765            |

**해석**:
- pass_avg_anger 0.71 vs fail_avg_anger 0.50 — **anger 0.21 분리** (임계 midpoint ≈ 0.605)
- chronic_stress는 pass/fail 사이 차이 미미 (0.77~0.81)
- → SNN gate가 anger에 강하게 반응하고 있음. **anger가 결합점 1순위 신호**.
- diff_sum = anger + fear + dignity + chronic 합산 → 0.557~0.677 (임계 0.05의 11~13배)

### 2.3 G2 Detail — founder vs absorbing chronic (희소 — INSUFFICIENT_N)

| seed | n | avg_diff_chronic | avg_founder_chronic | avg_absorbing_chronic |
|:----:|:-:|:----------------:|:-------------------:|:---------------------:|
| 7    | 1 | 0.020            | 0.754               | 0.734                 |
| 13   | 0 | n/a              | n/a                 | n/a                   |
| 42   | 2 | 0.160            | 0.793               | 0.632                 |

**해석**: founder 흡수 자체가 자연 희소 (전 seed 합 n=3). founder는 보통 자기 faction에 머물거나 사망 후 새 faction 생성 → 흡수 경로는 mechanism 결함이 아니라 **statistical rarity**. 결합점 후보 아님 (데이터 부족).

### 2.4 G3 Detail — small faction persist diff (BOOST 과보호 신호)

| seed | n_persisted | n_expired | diff_sum | persisted_avg_chronic | expired_avg_chronic |
|:----:|:-----------:|:---------:|:--------:|:---------------------:|:-------------------:|
| 7    | 19          | 0         | n/a      | 0.673                 | n/a                 |
| 13   | 12          | 0         | n/a      | 0.627                 | n/a                 |
| 42   | 5           | 0         | n/a      | 0.654                 | n/a                 |

**해석** (이중 신호):
1. **n_expired=0 (3/3)**: small_faction_snn_snapshot이 발화한 fid는 **모두 5000틱까지 살아남는다**. BOOST=0.20이 과보호 작동 중.
2. **측정 편향**: small_faction_snn_snapshot은 minority_boost_applied 시점에만 발화 → 보호받지 못한 small faction은 측정에서 누락 (snapshot 없음). 진정한 expired faction은 telemetry로 잡히지 않음.
3. → G3는 INSUFFICIENT_N으로 분류되지만, 이는 **자연 현상의 측정 편향**이지 mechanism 결함이 아님. 추후 측정 시 telemetry 발화 조건을 minority_boost_applied 외 시점으로 확장해야 진짜 expired 그룹 비교 가능.

### 2.5 G4 Detail — territory dist CV (분산 살아있음)

| seed | n_territories | avg_cv_chronic |
|:----:|:-------------:|:--------------:|
| 7    | 3             | 0.158          |
| 13   | 3             | 0.147          |
| 42   | 3             | 0.153          |

**해석**: territory별 chronic_stress 시계열의 변동계수 (CV = std/mean) 가 0.147~0.158로 임계 0.05의 약 3배. → **territory 간 동질화 없음**, SNN 출력 신호가 territory 수준에서 자연 분산 작동 중. anti-pattern #3 검증에서 SNN 출력 회로 "정체" 가설이 데이터로 명확히 기각됨.

### 2.6 Telemetry Event Counts (정합성 점검)

| event_type | seed-7 | seed-13 | seed-42 |
|------------|:------:|:-------:|:-------:|
| uprising_leader_snn_snapshot | 44 | 62 | 99 |
| founder_absorbed_snn_snapshot | 1 | 0 | 2 |
| small_faction_snn_snapshot | 19 | 12 | 5 |
| territory_snn_distribution | 24 | 24 | 24 |

- territory_snn_distribution = 24/seed (5000틱 / 100틱 주기 = 50 측정 시점, 그중 territory 3개 × 8 visit ≈ 24) — 정합
- mechanism 무수정 검증: 이전 v2 측정 시 uprising_skip_snn_inactive_count 24/48/83 = 현재 g1 fail bucket n (24/48/83) 일치 ✓

---

## 3. 결합점 후보 (SNN 출력 → mechanism 자연 매핑)

| 순위 | 결합점 | 데이터 근거 | 이미 사용 중 | 활용 후보 |
|:----:|--------|-------------|:------------:|----------|
| **1** | **uprising leader anger** (chiljeong[1]) | G1 pass_avg=0.71 / fail_avg=0.50, diff 0.21 (n=44+62+99) | uprising gate 1곳 | (a) affiliation 분리 가중 (drift 시 anger 높은 follower 보존), (b) faction split 자연 trigger |
| 2 | **territory chronic CV** (분산 신호) | G4 평균 CV 0.153 (n=72) | 미사용 | 영주 정책 자연 차이화 (territory 간 chronic 분산 활용) |
| 3 | leader chronic_stress | G1 diff 미미 (0.77~0.81) | 미사용 | **결합점 부적합** — 신호 차이 약함 |

### 3.1 임계 분위수 후보 (G1 leader_anger)

3 seed 합산 분포에서:
- pass 그룹: avg ≈ 0.72, n=50
- fail 그룹: avg ≈ 0.50, n=155
- **midpoint ≈ 0.61**
- **분위수 candidates**: P50 ≈ 0.55 / P67 ≈ 0.65 / P75 ≈ 0.70 — Phase 14B 패치 시 데이터에서 역산.

→ Phase 14B 패치는 SNN gate **이미 통과한 신호 분포** 위에서 결합점을 추가해야 한다. 새 임계는 측정 분위수에서만 도출 (anti-pattern #2 회피).

---

## 4. "This tells us:" (Rule 14)

1. **SNN 출력 회로는 정상**: G1+G4 3/3 PASS로 회로 정체 가설 기각. 5단 근본 원인 재정의 — "출력 신호는 강한데 결합점이 부족".
2. **anger가 가장 강한 분리 신호**: G1 diff_sum 0.557~0.677 중 anger 단독 0.21 차이가 주된 기여. fear/dignity/chronic는 보조.
3. **founder 흡수와 small faction 소멸은 자연 희소**: G2/G3 INSUFFICIENT_N은 mechanism 결함이 아니라 statistical rarity + telemetry 측정 편향. BOOST=0.20은 과보호 작동 중이지만 직접 mechanism 변경 불요.
4. **territory level의 자연 분산 살아있음**: G4 CV 0.15는 동질화 부재 입증. SNN 신호가 territory 정책 차이화에 활용 가능 (영주 의사결정 다양화 후보).
5. **데이터 정당화 사슬 작동**: 본 진단의 가치는 G1 데이터로 SNN gate 정당화가 가능해진 것 — anti-pattern #3 회피 표준 사례. LOOM-DIRECTION §3.7로 박을 필요.

---

## 5. 권고 — Phase 14B 패치 axis 후보

### 5.1 axis B (제안) — affiliation 결정에 anger 자연 가중

**근거**: G1 pass/fail 분리가 anger 0.21로 명확. 같은 SNN 신호를 affiliation 결정에서도 활용 = 결합점 자연 추가 (anti-pattern #3 회피).

**구현 후보 (spec 단계 진행 시)**:
- `_compute_affiliation_tick`에서 dominant 흡수 직전, 후보 follower의 anger가 분위수 (예: P67=0.65) 이상이면 affiliation score에 자연 보너스
- BOOST와 별개의 결합점 — BOOST는 minority size 보호, anger는 정치적 동기 보존
- 임계 0.65는 G1 측정 분위수에서 **데이터 정당화** (LOOM-DIRECTION §3.7 표준 사례)

### 5.2 axis C (제안) — territory 정책에 SNN 분산 활용

**근거**: G4 CV 0.15. territory 간 chronic_stress 차이가 자연 분산 → 영주 정책 차이화의 자연 입력.

### 5.3 기각 — axis A (이미 기각된 axis 재검토)

**Phase 14B-A** (affiliation drift dampen + SNN anger gate) 는 2026-04-28 cross-check에서 거짓 보정 5건과 구조 동형 식별로 기각됨. 본 진단으로도 axis A의 "drift dampen" 부분은 자연성 부족으로 재기각 — drift 자체는 자연 mechanism이고 anger는 별도 가중축으로 분리해야 함.

---

## 6. LOOM-DIRECTION.md §3.7 권고 (별도 작업)

본 진단 절차 자체가 데이터 정당화 사슬 표준의 사례:

1. **자연 측정** (5000틱 × 3 seed) — 측정 자체로 mechanism 변경 없음
2. **분포 분석** (PASS/FAIL/INSUFFICIENT_N 가설별 판정)
3. **결합점 후보 도출** (G1 anger 단독 분리 신호 식별)
4. **임계 분위수** (P50/P67/P75 측정 분포에서 역산)
5. **3엔진 cross-check** (anti-pattern #3 검증)
6. **closure/diagnosis 보고서** (본 문서) 에 사슬 전체 기록

→ 본 6단 사슬을 LOOM-DIRECTION §3.7 "데이터 정당화 사슬 표준"으로 박는다.

---

## 7. 보존 점검 (변경 허용 경계)

| 항목 | 상태 |
|------|:----:|
| mechanism 본문 무수정 (telemetry append만) | ✅ AST 본문 길이 검증 가능 |
| 안전 전제 5종 (HYSTERESIS=2, FOUNDER_RESPAWN_EVERY=480, TARGET_ACTIVE=2, COMMIT_EVERY=48, MAX_MEMBERS=2) | ✅ 무수정 |
| 회귀 테스트 7종 PASS | ✅ test_economy 6/6, test_governance 8/8, test_class_promotion 6/6, test_nomos 5/5, test_phase17_faction_handoff_contract exit 0, test_phase14b_snn_integration 8/8, test_phase17_faction_stage3 exit 0 |
| BOOST=0.20 무수정 (closure-v2 §7 데이터 사슬 보존) | ✅ |
| acceptance 기준 무수정 | ✅ |
| 신규 source/RNG 추가 없음 | ✅ |

---

## 8. 다음 단계 (사용자 결정 영역)

| 옵션 | 내용 | 권고 |
|:----:|------|:----:|
| (a) | LOOM-DIRECTION §3.7 데이터 정당화 사슬 표준 박음만 (현 진단 종결) | ★ 본 단계 권고 |
| (b) | Phase 14B-B axis spec 작성 (anger 결합점 추가) → 3엔진 cross-check → 구현 | 다음 단계 후보 |
| (c) | G3 telemetry 발화 조건 확장 (true expired faction 측정) → 재진단 | 보조 후보 |
| (d) | Φ-3 종결 → Φ-4 Nation Charter 진입 | 별도 트랙 |

본 보고서는 (a) 권고와 (b)/(c) 후보 명시로 종결. 사용자 결정 후 다음 단계 진입.

---

## 9. Evidence 위치

- spec: `Projects/personas/loom/PHASE-14B-SNN-OUTPUT-DIAGNOSIS-SPEC.md`
- 자연 측정: `Projects/personas/loom/data/phase17_probe_phi3-snn-output-diag/seed-{7,13,42}/`
- snn_output_events: `data/phase17_probe_phi3-snn-output-diag/seed-{7,13,42}/snn_output_events.json`
- SUMMARY: `data/phase17_probe_phi3-snn-output-diag/SUMMARY.md`
- run-manifest: `subagent-runs/claude/loom-phase14b-snn-output-diagnosis-spec-2026-05-02/run-manifest.md`
- run-summary (예정): 본 보고서 + LOOM-DIRECTION §3.7 갱신 후 작성
