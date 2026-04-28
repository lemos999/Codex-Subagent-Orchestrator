# Phase 17 Φ-3 Struggle Closure Report (1차)

> Measured: 2026-04-28
> Baseline: a8d61e7 (Charter/Decisions/CODEX-INSTRUCTIONS) + 8a00768 (1차 구현) + 6a29d2e (hotfix v1 지시서)
> Verdict: **Case B — 조건부 closure. hotfix 의도(거짓 PASS 제거)는 달성. Φ-3 자연 acceptance는 미완.**
> User decision: pending — Phase 14 grievance resonance 보강 spec 진입 권고.

---

## 1. 배경 및 hotfix 의도

a8d61e7 트릴로지 기반 1차 구현은 acceptance 3종을 PASS시켰으나(13/13/14, 1/1/1, 80/78/56%), Claude 리뷰가 mechanism 거짓 5건을 식별했다. 1차 PASS 수치는 자연 mechanism 산물이 아닌 **인공 보정의 산물**이었다 (collapse_branch_pressure / follower reserve / resonance carrier sticky / artificial grievance pair injection / sticky lord_id guard).

hotfix v1은 모든 인공 보정을 제거하고 자연 mechanism만 측정한다는 명시적 목표로 수행되었다. 결과:
- **PASS**: Φ-3 mechanism 자연 확정
- **FAIL**: Phase 14 결손 finding (Phase 14 보강 또는 acceptance 완화로 분기)

거짓 PASS는 절대 허용하지 않는다 (CLAUDE.md `feedback_snn_emergence_first.md` + `feedback_root_cause_first.md`).

---

## 2. Probe Summary

Command:

```bash
py observe_phase17_emergence.py --label phi3-hotfix --seeds 7,13,42 --ticks 5000
```

### Primary Acceptance (3종)

| # | 기준 | seed 7 | seed 13 | seed 42 | 결과 |
|---|------|:------:|:-------:|:-------:|:----:|
| 1 | uprising_event ≥ 1 | 8 | 12 | 9 | **PASS** |
| 2 | grievance_pairs_end ≥ 1 | 0 | 0 | 0 | **FAIL** |
| 3 | dom_share_end ≥ 0.50 | 80% | 100% | 50% | **PASS** |

### Secondary Metrics

| seed | active_factions_end | contact_pairs_end | drift_ratio | gini_mean_end | branch_factions_total | uprising_branch_share | uprising_join_share |
|------|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| 7 | 2 | 0 | 58% | 0.62 | 0 | 0% | 100% |
| 13 | 1 | 0 | 44% | 0.78 | 0 | 0% | 100% |
| 42 | 3 | 1 | 17% | 0.51 | 0 | 0% | 100% |

산출 파일: [data/phase17_probe_phi3-hotfix/](data/phase17_probe_phi3-hotfix/SUMMARY.md)

---

## 3. a8d61e7 1차 vs hotfix 비교 — 거짓 PASS 정체

| metric | a8d61e7 (1차) | hotfix (자연) | 변화 | 해석 |
|--------|:--:|:--:|:--:|------|
| uprising_count | 13 / 13 / 14 | 8 / 12 / 9 | -3.2 평균 | collapse_branch_pressure 우회 제거로 자연 빈도 노출 |
| shared_pairs_end | 1 / 1 / 1 | **0 / 0 / 0** | 1.0 → 0.0 | **artificial injection이 1쌍을 강제 유지하던 정체 노출** |
| dom_share_end | 80 / 78 / 56% | 80 / 100 / 50% | 대체 유지 | 봉기 자체는 자연 발화하여 dominance 변화 발생 |
| branch_factions_total | (미측정) | 0 / 0 / 0 | — | 모든 봉기가 join (인접 faction 흡수), 분파 0건 |

**핵심 통찰**: 1차의 shared_pairs_end=1/1/1은 `_uprising_tick`의 후반부 artificial injection이 매 틱 강제 유지한 산물. hotfix 제거 후 자연 측정에서는 0/0/0으로 노출됨. **Phase 14 grievance accumulator는 lord-level cross-faction pair를 자연 응결/유지 못함**.

---

## 4. 계약 검증 (무파괴 9 보장 + Mechanism 거짓 제거)

### 거짓 5건 제거 확인

| # | 항목 | grep 결과 |
|---|------|:--:|
| 1 | `_uprising_trigger`의 `collapse_branch_pressure`, `active_count` | 0건 |
| 2 | `_emit_uprising`의 `resonance_carriers`, `reserve_limited_followers` | 0건 |
| 3 | `_uprising_tick` 본문 ≤ 5줄 | 충족 (trigger→emit 단순 호출) |
| 4 | `_update_grievances` sticky 가드 | 0건 |
| 5 | `_spawn_branch_faction`의 `founder_pid[:` | 0건 |

### 무파괴 9 보장 유지

| # | 항목 | 결과 |
|---|------|:--:|
| 1 | `_change_persona_faction` 시그니처 | 무수정 |
| 2 | `FactionChangeSource` Literal 4종 | 무수정 |
| 3 | AST whitelist `# noqa: PHASE17_FACTION_SSOT_WRITE` 5건 | 무수정 (5건 유지) |
| 4 | `Faction.grace_until_tick` | 무수정 |
| 5 | `Faction.founder_lineage` | 무수정 |
| 6 | `InnerWorld.residence_ticks` | 무수정 |
| 7 | SNN 뉴런 300~349 / n_neurons | 무수정 |
| 8 | D10 7종 read-only API | 무수정 |
| 9 | Φ-3 신규 상수 5종 값 | 무수정 |

### 회귀 검증 3건

| # | 테스트 | 결과 |
|---|--------|:--:|
| 1 | `test_branch_faction_id_no_collision` | PASS |
| 2 | `test_grievance_lord_id_not_sticky` | PASS |
| 3 | `test_uprising_tick_no_artificial_injection` | PASS |

### 기타 회귀

| # | 테스트 | 결과 |
|---|--------|:--:|
| 1 | `test_phase17_faction_handoff_contract.py` (12건) | PASS |
| 2 | `py -m py_compile core/multi_tick_engine.py` | PASS |
| 3 | `py -m py_compile observe_phase17_emergence.py` | PASS |
| 4 | `py -m py_compile test_phase17_acceptance.py` | PASS |

`test_phase17_acceptance.py`의 `phi3_grievance_pairs_resonate`는 자연 측정 결과 그대로 FAIL (acceptance #2 미충족 — Case B의 정의 그대로).

---

## 5. 결과 분기 — Case B 공식 인정

hotfix 지시서 §결과 분기 정책 그대로:

> **Case B — uprising은 PASS이나 grievance_pairs FAIL (Phase 14 결손 finding)**
> - `uprising_count ≥ 1` 모두 충족이나 `shared_pairs_end == 0`
> - 봉기 자체는 일어나지만 5000틱 내 grievance pair 자연 응결이 안 됨
> - **finding**: Phase 14 grievance accumulator가 lord-level 응결을 자연 생성 못함 (Charter v2 entry check OR-3=0쌍 결손이 Φ-3 후에도 잔존)
> - 후속: Phase 14 grievance 보강 spec **또는** acceptance 완화

본 closure는 **Case B를 공식 finding으로 등록**. 거짓 PASS 차단 목적을 달성했으며, 진짜 병목이 정확히 노출되었다.

---

## 6. Findings — Phase 14 결손 + 보조 finding 3건

### 주 finding: Phase 14 grievance accumulator의 cross-faction pair 응결 결손

- **현상**: 5000틱 진행 후 모든 seed에서 `shared_pairs_end == 0`
- **mechanism 분석**: `_update_grievances`는 territory lord_id를 매개로 개별 페르소나의 grievance를 누적하지만, **다른 territory에 거주하는 페르소나가 같은 lord_id를 grievance 대상으로 공유**하는 자연 경로가 부재. 즉 lord-level pair 응결은 territory boundary를 넘지 못함
- **Charter v2 entry check 일관성**: OR-3=0쌍 결손이 이미 측정되었으며 Φ-3 후에도 잔존. **Φ-3가 해결할 수 있는 결손이 아니라 Phase 14 자체 결손**
- **근본 원인**: territory cross propagation mechanism 부재 — 페르소나가 다른 territory의 lord를 grievance 대상으로 인식하는 자연 경로 미설계

### 보조 finding 1: branch_factions_total = 0 (모든 봉기가 join)

- **현상**: 봉기 9건 평균 발화하나 분파 신생은 0건. uprising_join_share = 100%
- **mechanism 분석**: `_uprising_trigger`가 인접 faction 조건을 강제 → target_fid 추출 가능 → 모두 흡수 봉기. branch는 인접 faction이 없을 때만 발화하나, 인접 조건 자체가 봉기 trigger 조건이므로 branch 발화는 구조적으로 닫힘
- **acceptance 영향**: Φ-3 acceptance 3종에 branch 비율이 명시되지 않으므로 strict하게 FAIL은 아님. 단 Charter §Operating Loop가 분파 신생을 자연 결과로 기대하므로 mechanism 의도와 불일치
- **후속**: Φ-4 Nation 설계 시 branch faction 자연 경로 별도 검토 필요

### 보조 finding 2: probe vs pytest grievance pair SSoT 분리

- **현상**: probe (`observe_phase17_emergence.py`)와 pytest (`test_phase17_acceptance.py`)의 grievance pair 판정이 미묘하게 다름
- **영향**: 같은 acceptance 기준이 두 위치에서 별개 helper로 계산되므로 향후 수식 변경 시 양쪽 동기화 누락 위험
- **후속**: Phase 14 보강 spec에 grievance pair 판정 helper SSoT 통합 포함

### 보조 finding 3: `observe_phase17_emergence.py`의 `_write_top_summary` 중복 정의

- **현상**: a8d61e7 1차 구현 시 추가된 `_write_top_summary` 함수가 2개 정의됨 (후자가 override). hotfix는 observe 변경 없음 지시이므로 미수정
- **영향**: 동작상 문제 없으나 "완전 교체" 계약 관점에서 위생 정리 필요
- **후속**: 별도 위생 commit 또는 Phase 14 보강 spec에 포함

---

## 7. 다음 단계 권고

### 4-2단계: Phase 14 grievance resonance 보강 spec (권장 우선)

**근본 해결 경로** — `feedback_root_cause_first.md`("표면 해결 금지. 꼬리에 꼬리를") 직접 적용.

지시서 작성 대상: `PHASE-14-GRIEVANCE-RESONANCE-SPEC.md`

핵심 작업:
1. **lord_id cross-territory propagation**: 페르소나가 인접 territory의 lord를 grievance 대상으로 자연 인식하는 mechanism (relationship trust < 임계 + 인접 territory 거주자가 같은 lord 보유 시 영향 전파)
2. **grievance pair SSoT helper 통합**: probe + pytest 양쪽이 같은 helper 호출
3. **Φ-3 acceptance 자연 PASS 검증**: 3 seed × 5000 tick 재측정 (phi3-hotfix와 동일 조건)
4. **무파괴 9 보장 계승**: hotfix와 동일 제약

### 4-3단계: Φ-3 closure 2차 (자연 PASS 확정)

Phase 14 보강 후 재측정. Case A 충족 시 Φ-3 closure 확정. Case B 잔존 시 acceptance 완화 분기 결정 (10000틱 확장 또는 acceptance #2를 Φ-4로 이연).

### 5단계: Φ-4 Nation Charter

Φ-3 acceptance 자연 충족 후에만 진입 (Charter 무결성 — Land→Faction→Struggle→Nation 인과 사슬 보장).

### 위생 작업 (병행 가능)

- `data/phase17_probe*/` `.gitignore` 패턴 확장 (현재 `data/phase17_probe/`만 매칭)
- `observe_phase17_emergence.py`의 `_write_top_summary` 중복 정리

---

## 8. 결론

본 hotfix는 Φ-3 mechanism 거짓 5건을 제거하여 **자연 측정의 진실성**을 회복했다. acceptance 3종 중 #1·#3은 자연 PASS, #2는 Phase 14 결손에 의해 FAIL — 이는 **거짓 PASS보다 우월한 결과**다.

진짜 병목은 Φ-3가 아니라 Phase 14에 있다. 다음 단계는 Phase 14 grievance resonance 보강 spec으로 진입하여 cross-territory lord_id propagation을 자연 mechanism으로 추가한다. 보강 후 재측정으로 Case A 충족 시 Φ-3 closure 확정, Φ-4 진입 가능.

**hotfix 의도(거짓 PASS 제거 + 진짜 병목 노출)는 100% 달성. Φ-3 acceptance 자연 충족은 Phase 14 보강 후속 작업으로 이연.**
