# Phase 17 Φ-3 Case-C P1+P2 SPEC v2 — 자연 빈도 강화

> 긴급도: 중간
> 선행 조건: PHASE-17-CASE-C-P1-P2-SPEC.md (v1) 구현 완료 + 자연 측정 1차 결과 (1/3 PASS)
> 작업 유형: 기능 (백엔드) — 단일 임계 상수 조정
> DB migration: 없음
> 외부 의존: 없음

---

## 배경

Phase 17 Φ-3 Case-C P1+P2 spec v1 구현(2026-04-30)은 자연 측정 acceptance #2 (`grievance_pairs_end >= 1`) 에서 **1/3 PASS, 2/3 FAIL** (3 seed × 5000틱 결과: seed-7 FAIL, seed-13 FAIL, **seed-42 PASS**). spec 요구 "3 seed 전부 PASS" 미달.

**근본 원인 분석 (chain.json 비교)**:

| 이벤트 | seed-7 | seed-13 | seed-42 | 의미 |
|--------|:------:|:-------:|:-------:|------|
| `respawn_seed_group` (P1) | 5 | 1 | **2** | seed-42는 P1이 적게 작동했음에도 PASS |
| `drift_recovery_to_minority` | 119 | 69 | **151** | seed-42 압도적 (1.27× / 2.19×) |
| `minority_boost_applied` | 828 | 373 | 458 | seed-42 중간 |
| `faction_change` total | 202 | 137 | 221 | seed-42 다수, minority 비율도 高 (151/221=68%) |
| `uprising` | 15 | 11 | 16 | seed-42 다수 |

**가르침 (Rule 14 "This tells us:")**:

1. **P1 (`respawn_seed_group`) 빈도는 PASS 결정 변수가 아님** — seed-7 (P1=5) 흡수, seed-42 (P1=2) PASS. 즉 P1 max_size 강화는 헛수고.
2. **`drift_recovery_to_minority` 빈도가 PASS 결정 변수** — seed-42에서 151회 (다른 seed의 1.27~2.19배). 이는 P2 (GRACE_AFFILIATION_BOOST) + 기존 minority boost (Phase 14B 안티콜랩스) 가 자연 균형을 만들 때 active=2 5000틱 끝까지 유지 가능.
3. **`minority_boost_applied` 양과 PASS는 비례 안 함** — seed-7=828 (가장 많음) 이지만 흡수 발생. 즉 boost 양만으로 부족, **drift 시점에 minority faction이 선택되는 빈도** 가 결정적.
4. **자연 변동성**: seed별 minority 합류 비율은 분포(자연 변동성). 이 분포의 중간값을 끌어올리면 PASS 빈도 ↑ 가능성.

**근본 lever 식별**:

`MINORITY_PERSISTENCE_BOOST = 0.15` (layers.py:230) — minority faction (members ≤ 2) 에 score 가산. drift 시 이 boost가 minority 선택을 유도. **0.15→0.20 (33% 강화) 가 가장 직접적 lever**.

다른 후보 (기각 사유):
- `seed_group max_size 2→4`: P1 빈도 lever, PASS 결정 변수 아님 (위 분석)
- `RESPAWN_GRACE_TICKS 200→400`: P2 grace 윈도우 연장. 단 GRACE_AFFILIATION_BOOST=0.12 보다 MINORITY_PERSISTENCE_BOOST=0.15 가 더 큰 score weight + drift_recovery 빈도에 직접 작용 → **2순위 후보**
- `MINORITY_PERSISTENCE_MAX_MEMBERS 2→3`: 보호 대상 범위 확장. 임계 자체 변경으로 안티패턴 #2 위험 더 큼 (자연 측정 정당화 요구) → 보류

---

## 작업 범위

### [필수]

1. **MINORITY_PERSISTENCE_BOOST**: `0.15` → `0.20` 변경 (layers.py:230 단일 줄 1개 상수).
2. 코드 수정 후 자연 측정 5000틱 × 3 seed 재현 + acceptance #2 (`grievance_pairs_end >= 1`) PASS 빈도 측정.
3. closure 보고서 작성 — 본 spec v2 작업 결과 및 PASS 빈도 변화 명시 (LOOM-DIRECTION.md 안티패턴 #2 정당화 요구).

### [선택]

- **2순위 lever 시도** (1순위 효과 부족 시): `RESPAWN_GRACE_TICKS 200 → 300` (50% 연장). 1순위 단독으로 2/3 PASS 미달 시에만 시도. 본 spec v2 단계에서는 보류.

### [금지]

- **안전 전제 4종 무수정** (Rule 13 반전 금지):
  - `FACTION_HYSTERESIS = 2`
  - `FOUNDER_RESPAWN_EVERY = 480`
  - `FOUNDER_RESPAWN_TARGET_ACTIVE = 2`
  - `FACTION_COMMIT_EVERY = 48`
- **P1 코드 (`_pick_seed_group`, `_respawn_faction_tick`) 무수정** — spec v1 구현 검증 완료, P1 빈도 강화는 PASS 결정 변수 아님 입증.
- **P2 코드 (`GRACE_AFFILIATION_BOOST`, `_compute_affiliation_tick` grace 분기) 무수정** — spec v1 효과는 입증되었으며 임계 조정 외 변경 불필요.
- **`MINORITY_PERSISTENCE_MAX_MEMBERS = 2` 무수정** (보호 대상 범위 변경 보류, 자연 측정 정당화 미확보).
- **회귀 테스트 7종 무수정** (handoff_contract, snn_integration, faction_stage3, economy, governance, class_promotion, nomos).
- **brain/** , charters, spec v1, physis/world.py 전부 무수정.

---

## 구체 사양

### A. 단일 상수 변경

**파일**: `Projects/personas/loom/ontology/layers.py`
**위치**: line 230
**변경**:

```python
# Before (line 229~230)
MINORITY_PERSISTENCE_MAX_MEMBERS = 2      # members <= 2일 때 boost 적용
MINORITY_PERSISTENCE_BOOST = 0.15         # score 가산값 (= DRIFT_MARGIN_MIN * HOMEOSTASIS_DRIFT_MARGIN_SCALE 와 동일 규모)
```

```python
# After
MINORITY_PERSISTENCE_MAX_MEMBERS = 2      # members <= 2일 때 boost 적용
MINORITY_PERSISTENCE_BOOST = 0.20         # score 가산값 (Phase 17 Case-C v2: 0.15→0.20 강화 — drift_recovery 빈도 ↑ 목적, closure v2 데이터 근거)
```

**1줄 수정**. 주석 갱신은 정당화 데이터 출처 명시 (LOOM-DIRECTION.md 요구).

### B. 자연 측정 acceptance 재현

**명령**:
```bash
cd Projects/personas/loom
py observe_phase17_emergence.py --label "phi3-case-c-p1p2-natural-v2" --seeds 7 13 42 --ticks 5000
```

**기대 결과**:
- 1순위 가설: **2/3 또는 3/3 seed PASS** (`grievance_pairs_end >= 1`)
- 보수적 가설: **1/3 PASS 빈도 유지** (즉 효과 미달) → 2순위 lever (`RESPAWN_GRACE_TICKS 200→300`) 별도 spec v2.1 검토

**측정 지표**:
- 각 seed의 `drift_recovery_to_minority` 카운트 변화 (현재: 119, 69, 151 → 기대: 1.2~1.5배 ↑)
- `grievance_pairs_end` (acceptance #2 본체)
- `active_factions_end` (보조 지표)
- `faction_change` total + minority 비율

### C. 안전 전제 보존 검증 (자기 점검)

| 항목 | 변경 여부 |
|------|:---------:|
| `FACTION_HYSTERESIS = 2` | 무수정 |
| `FOUNDER_RESPAWN_EVERY = 480` | 무수정 |
| `FOUNDER_RESPAWN_TARGET_ACTIVE = 2` | 무수정 |
| `FACTION_COMMIT_EVERY = 48` | 무수정 |
| `MINORITY_PERSISTENCE_MAX_MEMBERS = 2` | 무수정 |
| `RESPAWN_GRACE_TICKS = 200` | 무수정 |
| `THETA_UPRISING = 0.40` | 무수정 |
| `SNN_ANGER_FIRE_THRESHOLD = 0.6` | 무수정 |
| `GRIEVANCE_PROPAGATE_TRUST_MIN = 0.6` | 무수정 |
| `GRIEVANCE_DONOR_MIN = 0.5` | 무수정 |
| `GRACE_AFFILIATION_BOOST = 0.12` | 무수정 |

`MINORITY_PERSISTENCE_BOOST` **단일 상수만** 0.15→0.20 변경.

---

## 변경 파일

| 파일 | 작업 | 라인 변동 |
|------|------|:---:|
| `Projects/personas/loom/ontology/layers.py` | 1줄 수정 (line 230) + 주석 1줄 갱신 | 수정 |
| `Projects/personas/loom/PHASE-17-CASE-C-P1-P2-CLOSURE-V2.md` | 신규 (closure 보고) | 추가 |

**변경 없음 (금지)**:
- `Projects/personas/loom/core/multi_tick_engine.py`
- `Projects/personas/loom/observe_phase17_emergence.py`
- `Projects/personas/loom/test_phase17_acceptance.py`
- `Projects/personas/loom/brain/**`
- `Projects/personas/loom/PHASE-17-FACTION-CHARTER.md`
- `Projects/personas/loom/PHASE-17-STRUGGLE-CHARTER.md`
- `Projects/personas/loom/PHASE-17-CASE-C-DIAGNOSIS-REPORT.md`
- `Projects/personas/loom/PHASE-17-CASE-C-P1-P2-SPEC.md` (v1 무수정)
- `Projects/personas/loom/physis/world.py`
- 회귀 테스트 7종

---

## 안티패턴 #2 정당화 (LOOM-DIRECTION.md §자연 측정 회귀·실험 정당화 요구)

### 데이터 근거 (3 seed × 5000틱 자연 측정 결과)

본 spec v2 임계 조정 (`MINORITY_PERSISTENCE_BOOST 0.15→0.20`) 의 정당화:

1. **drift_recovery 빈도와 PASS 상관성 입증**: seed-42 (151회) PASS, seed-7 (119회)/seed-13 (69회) FAIL. 즉 자연 측정에서 drift_recovery 빈도가 PASS 결정 변수임이 데이터로 확인됨.

2. **boost 양과 PASS 비례 아님**: seed-7 (boost 828회) FAIL → 단순 boost 횟수 강화는 비효과. **boost 강도 (gain 0.15→0.20)** 가 drift 결정 시 minority 선택 빈도에 직접 영향 가능.

3. **상수 규모의 정합성**: `MINORITY_PERSISTENCE_BOOST` 는 layers.py 주석에 명시된 대로 `DRIFT_MARGIN_MIN * HOMEOSTASIS_DRIFT_MARGIN_SCALE` 동일 규모. 0.15→0.20 변경은 33% 증가로, drift_recovery 빈도가 1.27배 (seed-7→seed-42 비) 또는 2.19배 (seed-13→seed-42 비) 증가하는 자연 변동성 폭과 동일 차수.

4. **안전 전제 침범 없음**: HYSTERESIS=2 + FOUNDER_RESPAWN_* + FACTION_COMMIT_EVERY=48 무수정. minority faction 선택 가산만 강화하며, faction 라이프사이클 자체는 무변경.

5. **closure 보고서 작성 의무**: `PHASE-17-CASE-C-P1-P2-CLOSURE-V2.md` 신규 작성으로 변경 효과 데이터 명시 — 임계 조정의 자연 측정 정당화 사슬 닫음.

### 기각 후보 (정당화 부족)

- `seed_group max_size 2→4`: 데이터 분석 결과 P1 빈도는 PASS 결정 변수 아님. 정당화 데이터 부재.
- `MINORITY_PERSISTENCE_MAX_MEMBERS 2→3`: 보호 대상 범위 확장. 자연 측정 정당화 데이터 부재 (현재 2 임계가 적정인지 측정 미실행).
- `RESPAWN_GRACE_TICKS 200→400`: 2순위 lever, 1순위 단독 효과 부족 시에만 검토.

---

## 검증

### 1. 기계 검증
1. `py -m py_compile ontology/layers.py` (변경 1줄, syntax 확인)
2. import 영향 없음 — 상수만 변경, signature 무변경.

### 2. 회귀 검증 (Phase 11~16 무파괴)
- `py test_economy.py` (6/6 PASS 기대)
- `py test_governance.py` (8/8 PASS 기대)
- `py test_class_promotion.py` (PASS 기대)
- `py test_nomos.py` (PASS 기대)
- `py test_phase17_faction_handoff_contract.py` (D10 12/12 PASS 기대)
- `py test_phase14b_snn_integration.py` (8/8 PASS 기대)
- `py test_phase17_faction_stage3.py` (PASS 기대)

### 3. 자연 측정 acceptance #2 (필수)
```bash
py observe_phase17_emergence.py --label "phi3-case-c-p1p2-natural-v2" --seeds 7 13 42 --ticks 5000
```

**판정 기준 (acceptance #2 — `grievance_pairs_end >= 1`)**:

| 결과 | 판정 | 다음 단계 |
|------|------|----------|
| 3/3 PASS | **COMPLETE** | spec v2 closure |
| 2/3 PASS | **PARTIAL_PROGRESS** | spec v2 closure (개선 입증) + 사용자 결정 (v2.1 진행 여부) |
| 1/3 PASS (현재 유지) | **NO_PROGRESS** | spec v2.1 (RESPAWN_GRACE_TICKS 200→300) 검토 |
| 0/3 PASS | **REGRESSION** | rollback + 한계 대응 전제 D 발동 |

**다른 acceptance 영향 검토** (참고 — 본 spec v2 직접 목표 아님):
- acceptance #1 (`uprising_event_count >= 1`): v1 결과 모든 seed 충족 (15/11/16). 본 spec v2 변경은 uprising 트리거 영향 없음 → 무영향 예상.
- acceptance #3 (`dom_share_end >= 0.50`): v1 결과 모든 seed 충족. minority 강화 시 dominant share ↓ 가능 — 단 active=2 유지가 목표라면 0.50 이상 유지 가능 (자연 균형). seed-42 결과 (active=2, dom_share≈0.5~0.7) 참조.
- acceptance #4 (`factions_in_contact_end >= 1`): v1 결과 모든 seed 0 (FAIL). 본 spec v2 직접 목표 아님 — Φ-3 Stage 4 trigger 별도 차원. spec v2 효과로 active=2 유지 시 contact 기회 발생 가능 (간접 효과).

### 4. 안티패턴 12종 자기 점검 (spec v1 동일)
- 특히 #11 (`factionRef_changed_by_respawn_count >= 1`) — 1순위 lever 효과 검증 핵심.

### 5. 결정성 (선택)
- 동일 seed 2회 시뮬 chain.json snapshot diff empty 확인 (spec v2는 RNG 영향 없음).

---

## Rollback

```bash
cd Projects/personas/loom
git checkout ontology/layers.py
```

데이터 영향: 없음 (자연 측정 결과는 별도 디렉토리 `data/phase17_probe_phi3-case-c-p1p2-natural-v2/`).

---

## closure 보고서 (별도 작성)

`PHASE-17-CASE-C-P1-P2-CLOSURE-V2.md` 작성 항목:
1. 적용 변경: `MINORITY_PERSISTENCE_BOOST 0.15→0.20`
2. 자연 측정 acceptance #2 결과 (v1 vs v2 비교 표)
3. drift_recovery_to_minority 빈도 변화 (3 seed)
4. faction_change minority 비율 변화
5. 회귀 테스트 7종 결과
6. 종합 판정 (3/3 PASS / 2/3 PASS / 1/3 PASS / 0/3 PASS)
7. 안티패턴 #2 정당화 데이터 사슬 닫음

---

## 종합 권고 (sub-implementer)

이 spec v2 는 **단일 상수 조정 + 자연 측정 재현 + closure 보고** 의 단순 구조. v1과 달리:
- 코드 변경 1줄 (vs v1 +740줄)
- 안전 전제 무수정 (v1 동일)
- 핵심 결정 단순 (v1 = 메커니즘 도입 / v2 = 임계 조정)

implementer 워크플로우:
1. layers.py 1줄 변경 + 주석 1줄 갱신
2. py_compile 검증 (~1초)
3. 회귀 7종 실행 (~3~5분)
4. 자연 측정 5000틱 × 3 seed 실행 (sequential 약 31분 — v1 측정값 합: seed-7=820s, seed-13=465s, seed-42=570s; 병렬화 시 ~14분, 단 RNG 결정성 영향 검증 필요)
5. chain.json 분석 + closure-v2 작성 (~10~15분)
6. 결과 보고 + 판정

총 예상 시간: sequential 약 45~50분, 병렬 약 30분 (v1 대비 1/3~1/4 수준).
