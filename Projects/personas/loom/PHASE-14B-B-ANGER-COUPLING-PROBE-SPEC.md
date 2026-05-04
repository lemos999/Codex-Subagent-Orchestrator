# Phase 14B-B Anger Coupling — PROBE Spec (§3.7 4단·5단 진입)

> **본 spec은 PROBE spec이다.** mechanism 본문 변경 spec **아님**.
> §3.7 데이터 정당화 사슬 6단 중 **4단 (임계 분위수 결정) + 5단 (3엔진 cross-check 입력 자료)** 만 담당.
> mechanism 변경은 cross-check (5단) 통과 후 별도 spec에서 결정.

---

## 메타

| 항목 | 값 |
|------|-----|
| 긴급도 | 중간 (Φ-3 closure 의존) |
| 선행 조건 | Phase 14B-d1 진단 보고서 PASS (`PHASE-14B-SNN-OUTPUT-DIAGNOSIS-REPORT.md`) |
| 작업 유형 | PROBE (텔레메트리 보강 + 시뮬 측정) |
| DB migration | 없음 |
| 외부 의존 | 없음 |
| §3.7 위치 | **4단 (임계 분위수) + 5단 (3엔진 cross-check 입력)** |
| 본문 mechanism 변경 | **금지** (PROBE 단계) |

---

## 1. 배경

### 1.1 Phase 14B-d1 진단 결과 (선행)

`PHASE-14B-SNN-OUTPUT-DIAGNOSIS-REPORT.md` 결과:
- **G1 PASS** 3/3 — uprising leader anger 분리 0.21 (pass_avg 0.71 vs fail_avg 0.50, n=44+62+99=205)
- G4 PASS 3/3 — territory chronic CV 0.15 (분산 살아있음)
- G2/G3 INSUFFICIENT_N (자연 희소 + BOOST 과보호)

**결합점 1순위**: uprising leader **anger** ≥ 임계.

### 1.2 axis A (선행 기각) 차별 검토

axis A (`PHASE-14B-AFFILIATION-RESONANCE-SPEC.md`)는 2026-04-28 3엔진 cross-check에서 기각:
- magic threshold (`SNN_ANGER_AFFILIATION_GATE=0.5`) 창발 정당화 근거 부재
- mechanism 직접 변경 (`_compute_affiliation_tick` dampen 8줄)으로 acceptance #2 강제 PASS 위험
- 거짓 보정 5건과 구조 동형

**axis B (본 spec)의 차별점**:

| 항목 | axis A (기각) | axis B (PROBE spec) |
|------|--------------|---------------------|
| 임계 도출 | magic 0.5 | **자연 측정 분위수 (P50/P67/P75)** |
| mechanism 변경 | `_compute_affiliation_tick` 8줄 추가 | **변경 없음** — 텔레메트리 시뮬만 |
| 산출물 | 신규 상수 2개 + dampen 분기 | **임계 분위수 후보 + 시뮬 PASS 비율 데이터** |
| §3.7 사슬 단계 | 1·3단 건너뛰고 4단 magic | **1~3단 통과 후 4·5단 정상 진입** |
| 거짓 보정 위험 | 구조 동형 (인공 보정) | 구조 다름 (데이터 보강 + cross-check 입력) |
| Φ-3 acceptance 변경 | 강제 PASS 의도 | **PASS 비율 시뮬 데이터로 cross-check 의사결정 지원만** |

본 spec은 **mechanism을 박지 않는다**. 데이터·시뮬 결과만 산출하여 5단 cross-check에 입력 자료로 제공한다. mechanism 결정 권한은 사용자 + 3엔진 cross-check.

---

## 2. 작업 범위

### [필수]

1. **임계 분위수 후보 측정** — Phase 14B-d1 데이터 (`data/phase17_probe_phi3-snn-output-diag/seed-{7,13,42}/snn_output_events.json`)에서 `uprising_leader_snn_snapshot` 이벤트의 anger 분포 분위수 계산:
   - P25, P50, P67, P75, P80, P90 산출 (3 seed 통합 + seed별)
   - pass 그룹과 fail 그룹 분리 분위수
   - 출력: `Projects/personas/loom/data/phase14b_b_anger_quantiles.json`

2. **시뮬 PASS 비율 추정** — 각 임계 후보 (P50/P67/P75)에 대해, 만약 mechanism이 그 임계를 사용했을 때 acceptance #2 (`grievance_pairs_end ≥ 1`) PASS 비율을 **시뮬 추정** (실제 mechanism 변경 없이 텔레메트리 후처리로 추산):
   - 각 임계에서 anger ≥ 임계인 페르소나 비율
   - 그 페르소나의 grievance_lord 분포 → cross-faction pair 잠재 형성 가능성
   - 출력: `Projects/personas/loom/data/phase14b_b_threshold_simulation.md`

3. **3엔진 cross-check 입력 자료 정리** — `subagent-runs/discuss/phase14b-b-anger-coupling-cross-check-2026-05-XX-quick/` 폴더에 cross-check 입력으로 다음 정리:
   - axis A 기각 사유 + axis B 차별점 (본 spec §1.2)
   - Phase 14B-d1 G1 데이터 (선행 진단 보고서 발췌)
   - 임계 분위수 후보 + 시뮬 PASS 비율
   - cross-check 질문 4종 (§5)

4. **§3.7 4단·5단 위치 명시 evidence** — `subagent-runs/claude/loom-phase14b-b-anger-coupling-probe-2026-05-XX/`에 다음 기록:
   - run-manifest.md
   - run-summary.md
   - results/threshold-quantiles.result.md
   - results/simulation-pass-ratio.result.md

### [선택]

- 추가 seed (5+ 확장) 측정 — n_pass=20+14+16=50의 통계 신뢰도 보강. **단 mechanism 무수정 + 텔레메트리 무수정** 조건 유지.

### [금지]

- **mechanism 본문 변경** — `_compute_affiliation_tick`, `_uprising_trigger`, `_pick_uprising_target`, `_change_persona_faction` 등 본문 logic 수정 절대 금지.
- **신규 상수 추가** — `GRIEVANCE_LORD_FACTION_DAMPEN`, `SNN_ANGER_AFFILIATION_GATE` 등 axis A 잔재 상수 추가 금지.
- **acceptance 기준 변경** — Φ-3 acceptance 3종 (uprising_event ≥ 1, grievance_pairs_end ≥ 1, dom_share_end ≥ 0.50) 무수정.
- **신규 SNN 뉴런 / 신규 FactionChangeSource** — Charter v2 D10 freeze 유지.
- **acceptance #2 강제 PASS 의도 mechanism** — 본 spec은 데이터·시뮬만, mechanism 결정은 cross-check 후.
- **회귀 7종 우회** — test_economy/governance/class_promotion/nomos/phase17_faction_handoff_contract/phase14b_snn_integration/phase17_faction_stage3 PASS 유지.

---

## 3. 임계 분위수 후보

Phase 14B-d1 G1 데이터 (3 seed 통합):

| 그룹 | n | avg_anger | (예상) P50 | (예상) P67 | (예상) P75 |
|------|:-:|:---------:|:----------:|:----------:|:----------:|
| pass (uprising leader gate 통과) | 50 | 0.706~0.729 | ~0.71 | ~0.74 | ~0.78 |
| fail (gate 미통과) | 155 | 0.487~0.512 | ~0.50 | ~0.55 | ~0.60 |
| 통합 | 205 | ~0.55 | ~0.55 | ~0.65 | ~0.70 |

**임계 후보**:
- **P50 (~0.55)**: 약한 결합 — 통합 분포 중앙값. 자연 보수적.
- **P67 (~0.65)**: 중간 결합 — pass 평균과 fail 평균 중간 지점.
- **P75 (~0.70)**: 강한 결합 — pass 분포 P25 근처. 강한 변별.

본 spec은 **3 후보 모두 측정**. 정확한 분위수는 §2 [필수] #1에서 계산.

**임계 결정 권한**: 본 spec은 **결정 안 함**. 3엔진 cross-check (§5) + 사용자 결정.

---

## 4. 시뮬 PASS 비율 추정 방법

각 임계 후보 T (P50/P67/P75)에 대해:

```
1. uprising_leader_snn_snapshot 이벤트 중 anger ≥ T 인 leader 식별
2. 각 leader의 grievance_lord_id 분포 분석
3. 동일 lord_id를 공유하는 leader 페어 카운트 (cross-faction 가능성)
4. 추정 grievance_pairs_end_simulated = (cross-faction pair 카운트가 acceptance #2 임계 ≥ 1 통과하는 시나리오 비율)
```

**중요**: 본 시뮬은 **텔레메트리 후처리**다. 실제 mechanism이 임계 T를 사용한 결과 측정이 **아니다**. 실제 mechanism은 cross-check 후 결정.

따라서 본 시뮬 결과는 **임계 후보의 잠재력 비교** 자료 — cross-check 의사결정에 입력만.

---

## 5. 3엔진 cross-check 질문 4종

`/discuss --quick` 입력으로 사용:

1. **§3.7 사슬 정합성**: Phase 14B-d1 진단 (1~3단) → 본 spec (4단) → 본 cross-check (5단)이 §3.7 표준에 정합하는가? 한 단이 비어있는가?

2. **axis A vs axis B 차별 정당화**: axis A 기각 사유 (magic threshold + mechanism 직접 변경 + 거짓 보정 구조 동형)와 axis B (분위수 도출 + PROBE 단계)는 본질적으로 다른가? 같다면 axis B도 거부?

3. **임계 분위수 선택**: P50/P67/P75 중 어느 것이 자연 결합 정신에 가장 정합한가? 또는 분위수 자체가 magic threshold의 정교화일 뿐인가?

4. **다음 단계 mechanism 후보**: cross-check가 임계를 승인한다면, 다음 mechanism spec은 어떤 형태가 자연인가? (옵션: a) anger를 affiliation 가중치에 가산, b) anger 분리를 grievance 응결 가속에만 결합, c) territory cross-propagation 강화 우선, d) 모든 mechanism 변경 보류 — Φ-4 진입)

---

## 6. 변경 파일

| 파일 | 작업 | 유형 |
|------|------|:---:|
| `Projects/personas/loom/data/phase14b_b_anger_quantiles.json` | 신규 (분위수 산출) | 추가 |
| `Projects/personas/loom/data/phase14b_b_threshold_simulation.md` | 신규 (시뮬 추정) | 추가 |
| `subagent-runs/claude/loom-phase14b-b-anger-coupling-probe-2026-05-XX/run-manifest.md` | 신규 | 추가 |
| `subagent-runs/claude/loom-phase14b-b-anger-coupling-probe-2026-05-XX/run-summary.md` | 신규 | 추가 |
| `subagent-runs/claude/loom-phase14b-b-anger-coupling-probe-2026-05-XX/results/threshold-quantiles.result.md` | 신규 | 추가 |
| `subagent-runs/claude/loom-phase14b-b-anger-coupling-probe-2026-05-XX/results/simulation-pass-ratio.result.md` | 신규 | 추가 |
| `subagent-runs/discuss/phase14b-b-anger-coupling-cross-check-2026-05-XX-quick/discussion-summary.md` | 신규 (cross-check 결과) | 추가 |

**변경 없음 (절대 금지)**:
- `Projects/personas/loom/core/multi_tick_engine.py` — mechanism 본문 + 텔레메트리 (Phase 14B-d1에서 이미 추가, 본 spec은 추가 변경 X)
- `Projects/personas/loom/ontology/layers.py` — 상수 무수정
- `Projects/personas/loom/observe_phase17_emergence.py` — 무수정 (필요 시 별도 spec)
- 회귀 테스트 7종

---

## 7. 검증

### 기계 검증
1. JSON 파일 valid (`python -m json.tool phase14b_b_anger_quantiles.json`)
2. simulation 산출 텍스트가 분위수 후보 3종 모두 표 형식 포함
3. cross-check 질문 4종이 §5와 일치

### 정합성 검증 (§3.4 SSoT 4중 체크 적용)
- spec 본문 mechanism 변경 없음 — 1번 항목 N/A (mechanism 박지 않음)
- `ontology/layers.py` 상수 변경 없음 — 2번 항목 N/A
- acceptance 테스트 변경 없음 — 3번 항목 N/A
- closure 보고서 변경 없음 — 4번 항목 N/A
- **본 spec은 mechanism을 박지 않으므로 SSoT 4중 체크 적용 면제** — 단 5단 cross-check 후 mechanism spec에서 4중 체크 의무 발생

### 거짓 보정 안티패턴 자체 검증
- [ ] mechanism 본문에 분기 추가? → 없음
- [ ] acceptance 미달 상태를 막는 조건 삽입? → 없음 (PROBE 단계)
- [ ] magic threshold? → 분위수 후보 3종 (P50/P67/P75)은 자연 측정 분포에서 도출 — magic 아님
- [ ] 자연 현상으로 포장? → 본 spec은 cross-check 입력 자료, 자연 mechanism 주장 안 함

### §3.7 6단 사슬 자체 검증
| 단 | 본 spec 위치 | 산출물 |
|----|--------------|--------|
| 1. 자연 측정 | 선행 (Phase 14B-d1 진단 보고서) | `data/phase17_probe_phi3-snn-output-diag/SUMMARY.md` |
| 2. 분포 분석 | 선행 (Phase 14B-d1 진단 보고서) | G1~G4 verdict matrix |
| 3. 결합점 후보 | 선행 (Phase 14B-d1 진단 보고서) | anger 1순위 |
| 4. **임계 분위수** | **본 spec** | `phase14b_b_anger_quantiles.json` |
| 5. **3엔진 cross-check** | **본 spec** | `discussion-summary.md` |
| 6. closure 보고서 | 후속 (mechanism spec 후) | TBD |

---

## 8. Rollback

본 spec은 데이터 파일 + cross-check 보고서 + evidence만 추가. 코드 변경 없음. Rollback:
```bash
rm Projects/personas/loom/data/phase14b_b_anger_quantiles.json
rm Projects/personas/loom/data/phase14b_b_threshold_simulation.md
rm -rf subagent-runs/claude/loom-phase14b-b-anger-coupling-probe-2026-05-XX/
rm -rf subagent-runs/discuss/phase14b-b-anger-coupling-cross-check-2026-05-XX-quick/
```

데이터 영향 없음. 회귀 테스트 영향 없음.

---

## 9. 다음 단계 (cross-check 후)

| cross-check 결과 | 다음 spec |
|------------------|-----------|
| 임계 P50 승인 + mechanism (a) 권고 | `PHASE-14B-B-ANGER-AFFILIATION-WEIGHT-SPEC.md` (mechanism 변경) |
| 임계 P67/P75 승인 + mechanism (b) 권고 | `PHASE-14B-B-GRIEVANCE-RESONANCE-ACCELERATE-SPEC.md` |
| 임계 기각 + territory 차원 권고 | `PHASE-14B-C-TERRITORY-CROSS-PROP-SPEC.md` |
| 모든 mechanism 보류 + Φ-4 권고 | Φ-4 full Charter 작성 (현 STUB → full) |

본 spec은 **다음 spec의 사전 조건**이지 mechanism 변경 spec이 아니다.

---

## 10. open questions (cross-check 5단에서 해소)

1. 임계 분위수 도출이 magic threshold의 정교화 vs 자연 결합의 진정한 차별 — cross-check 의사결정 사항
2. acceptance #2 (`grievance_pairs_end ≥ 1`) 자연 PASS의 진짜 자연 경로 — anger 결합 vs territory 차원 vs 다른 차원
3. Φ-3 closure 시점 정의 — acceptance 1/3 PASS 그대로 closure vs 임계 추가 시도 후 closure
4. Φ-4 진입을 본 spec과 병행 (§3.6 넓이 우선) vs Φ-3 closure 우선

---

**핵심 한 줄**: 본 spec은 데이터·시뮬·cross-check 입력만. mechanism은 박지 않는다. axis A 기각 패턴 회피 + §3.7 4단·5단 정상 진입.
