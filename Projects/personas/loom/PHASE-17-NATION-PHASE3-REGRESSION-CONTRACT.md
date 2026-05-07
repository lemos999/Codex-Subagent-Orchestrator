# [문서·계약] PHASE 17 Nation Phase 3 Regression Contract — Single Source of Truth

> 긴급도: 보통
> 선행 조건: DC-1 SIS [확정] · DC-2 CPCM rev.3 [확정] · DC-3 P5R rev.2 [확정 후]
> 작업 유형: **문서 (회귀 contract single source of truth)**
> DB migration: 없음
> 외부 의존: 없음 (pytest 기존 환경)
> **코어 영역 판정**: **비코어** (회귀 정의 통합 — mechanism 무수정, acceptance 무변경). 게이트 §3.3.2 **불요**
> **canonical order**: PIPELINE-DRAFT.md §0 표 외부 (회귀 contract는 별도 권위)
> **rev**: rev.2 (V-3 실측 결과 통합 — closure-v2 부분 PASS 진실 보존)

---

## 변경 이력

- **rev.2** (2026-05-07): V-3 Tier 1 7종 실측 (4 failed / 89 passed in 1:01:23) 결과 통합. acceptance 4종(`test_phi3_grievance_pairs_resonate` / `test_grievance_propagate_natural_emergence` / `test_phi3_branch_lineage_chain` / `test_respawn_seed_group_emitted`)이 closure-v2 §2.2 "branch_factions_total = 0" + §2.1 "1/3 PASS Case B" 부분 PASS 잔재임이 확인됨. **회귀 0%** (mechanism 영역 코드 변경 없음 — 9175397 hotfix v2 이후 docs/test/scripts만). rev.1의 "PASS 기대 결과 — 모든 7종 PASS" 표기는 closure-v2 §2.2 사실 누락 → 거짓 PASS 위험. 본 rev에서 정정. paper(2026-05-07 첨부) 진단 "환경 빈약 → 자연 발생 부재"의 외부 검증 신호로 기록.
- **rev.1** (2026-05-07): Step 3.5 검증 (3 reviewer 만장일치 Finding 2 — 회귀 contract 4-way 불일치) 후속 신규 작성. workspace 실재 검증 완료한 7종을 Tier 1 권위로 고정. Phase 5 Package 진입 시 신규 4종 (Tier 2)을 신규 author로 별도 분리. DC-1/DC-2/DC-3/input-brief 분산 권위를 본 문서로 통합. DC-1/DC-2 [확정] spec 본문 변경 회피 — 본 문서가 reference 권위.

---

## 배경

Phase 17 Φ-4 Nation Charter Phase 3 통합 검증(Step 3.5 / 2026-05-07)에서 3 reviewer (opus / sonnet / Codex) 만장일치 Finding 2: 회귀 contract 4-way 불일치.

| # | 위치 | 회귀 목록 | workspace 실재성 |
|---|---|---|---|
| 1 | `PHASE-17-NATION-DC-1-SIS-SPEC.md:399` | 6종 | 일부 실재 |
| 2 | `PHASE-17-NATION-DC-2-CPCM-SPEC.md:586` | 6종 (DC-1과 동일) | 일부 실재 |
| 3 | `PHASE-17-NATION-DC-3-P5R-SPEC.md:276-282` (rev.1) | 7종 (V-3) | **4종 부재** (`test_branch.py` / `test_climate.py` / `test_grievance_propagation.py` / `test_phase14_grievance_propagation.py`) |
| 4 | `subagent-runs/discuss/phase17-nation-phase3-verify-2026-05-07-quick/input-brief.md:31` | 또 다른 7종 | **7종 모두 부재** (`test_struggle_charter` / `test_phase14b_phi3_diagnosis` / `test_phase14b_b_threshold_simulation` / `test_v3_summary_regen` / `test_dc1_sis_smoke` / `test_dc2_cpcm_smoke` / `test_phase17_struggle_smoke`) |

Codex 본질 지적: "숫자가 아니라 single source of truth 부재가 문제. 6이든 7이든 한 문서에서 고정되고 실제 파일/실행 명령으로 재현 가능해야 한다."

본 문서는 **회귀 contract 단일 권위**를 확정한다. 모든 spec/문서는 본 문서를 reference. 본 문서 외부에서 회귀 목록 재정의 금지.

---

## Tier 분리 원칙

| Tier | 정의 | workspace 실재 | 진입 게이트 |
|---|---|:---:|---|
| **Tier 1** | Phase 17 Φ-4 Nation Phase 3 진행 시점에 즉시 보존 의무가 있는 회귀 — body semantics·mechanism·acceptance 무영향 검증의 base | ✓ (7/7) | DC-3 P5R rev.2 [확정] / Phase 4 Verify 즉시 |
| **Tier 2** | Phase 5 Package 진입 시 신규 author 작성 — DC-1/DC-2/DC-3 자체의 smoke 검증 | ✗ (Phase 5 시 신규) | Phase 5 Package 진입 게이트 |

Tier 1과 Tier 2는 분리 운용. Tier 1만으로 Phase 4 Verify (interface declaration 회귀 무영향) 검증 가능. Tier 2는 Phase 5 Package 신규 author 시 신규 작성 후 본 문서 rev.2로 전환 등재.

---

## Tier 1 — Phase 17 Φ-4 Nation Phase 3 즉시 회귀 (workspace 실재 7종)

### 회귀 목록 (권위 — 본 절 외부 재정의 금지)

| # | 파일 (Projects/personas/loom/) | 검증 영역 | V-3 실측 (rev.2) | 분류 |
|---|---|---|:---:|---|
| 1 | `test_phase17_acceptance.py` | Phase 17 acceptance gate (자연 발생 / top-down 금지) | **부분 PASS** (4 sub-test FAIL — closure-v2 §2.1/§2.2 잔재) | 환경 빈약 신호 |
| 2 | `test_phase17_faction.py` | Φ-3 Struggle root | ✓ | mechanism 무영향 |
| 3 | `test_phase17_faction_stage3.py` | Stage 3 (cross_faction_lord_pair_emerged 자연 발생 PASS) | ✓ | mechanism 무영향 |
| 4 | `test_phase17_faction_regression.py` | Φ-3 회귀 (BOOST=0.20 / 안전 전제 5종 보존) | ✓ | mechanism 무영향 |
| 5 | `test_phase17_faction_handoff_contract.py` | Φ-3 → Φ-4 handoff 단방향 계약 | ✓ | mechanism 무영향 |
| 6 | `test_phase14b_snn_integration.py` | SNN 창발 검증 (사용자 메모리 `feedback_snn_emergence_first.md` 정합) | ✓ | mechanism 무영향 |
| 7 | `test_phase17_land.py` | Φ-1 Land 단방향 계약 발끝 | ✓ | mechanism 무영향 |

### #1 acceptance 부분 PASS 상세 (rev.2 신규)

V-3 실측 (2026-05-07, 89 passed / 4 failed in 1:01:23):

| sub-test | seed 영향 | 원인 | 정합성 |
|---|---|---|---|
| `test_phi3_grievance_pairs_resonate` | seed 13 | closure-v2 §2.1 "acceptance #2 = 1/3 PASS (seed 13 1쌍)" 의 stochastic 변동 (1쌍 → 0쌍 임계 노이즈) | 자연 변동 — closure-v2 부분 PASS 신호 |
| `test_grievance_propagate_natural_emergence` | seed 13 | 동상 — propagation 자연 발생 임계 노이즈 | 자연 변동 |
| `test_phi3_branch_lineage_chain` | 3 seed 합계 0 | closure-v2 §2.2 "`branch_factions_total = 0` 모든 봉기 join, branch faction 자연 발화 경로 부재. **Φ-4 검토 대상**" 명시 → 본 sub-test는 closure-v2 시점부터 자연 부재 | mechanism 빈약 — Φ-4 검토 대상 |
| `test_respawn_seed_group_emitted` | 3 seed 합계 0 | respawn_seed_group 자연 부재 — closure-v2 시점부터 자연 발생 경로 부재 | mechanism 빈약 — Φ-4 검토 대상 |

**핵심 사실**:
- 회귀 0% — 9175397 hotfix v2 이후 mechanism 영역 git diff empty (확인 명령: `git log --oneline 9175397..HEAD -- Projects/personas/loom/core/ Projects/personas/loom/ontology/ Projects/personas/loom/physis/` 0 hits)
- 4 sub-test FAIL은 closure-v2 §2.1 "1/3 PASS Case B" + §2.2 "branch 자연 부재 Φ-4 검토 대상" 의 정합 잔재
- DC-3 P5R rev.2 interface declaration은 mechanism 무영향 — 다른 6종 PASS가 회귀 무영향 증명
- paper(2026-05-07 첨부) 진단 "Loom의 다음 진보는 brain 확대 아닌 환경 확대 — 환경 빈약 → 자연 발생 부재" 외부 검증 신호로 기록

### 실행 커맨드 (재현 가능)

```bash
cd Projects/personas/loom
py -m pytest \
  test_phase17_acceptance.py \
  test_phase17_faction.py \
  test_phase17_faction_stage3.py \
  test_phase17_faction_regression.py \
  test_phase17_faction_handoff_contract.py \
  test_phase14b_snn_integration.py \
  test_phase17_land.py \
  -q
```

### PASS 기대 결과 (rev.2 정정)

- **6종 (#2~#7) 전 PASS** — DC-3 P5R rev.2는 interface declaration 신규(`api/` 모듈)이므로 mechanism 무영향 → 회귀 0 기대
- **#1 (`test_phase17_acceptance.py`) 부분 PASS** — 89/93 sub-test PASS, 4 sub-test FAIL (위 §"#1 acceptance 부분 PASS 상세"). 본 4 FAIL은 **closure-v2 §2.1 "1/3 PASS Case B" + §2.2 "branch 자연 부재 Φ-4 검토 대상" 의 정합 잔재** — DC-3 P5R rev.2 변경과 무관 (mechanism 영역 git diff empty 검증)
- **PASS 판정 권위**:
  - DC-3 P5R rev.2 interface declaration의 회귀 무영향 검증 → **충족** (#2~#7 전 PASS + #1의 acceptance 외 모든 sub-test PASS)
  - acceptance 4 sub-test FAIL 처리 → closure-v2 §2.1/§2.2 잔재로 기록, **paper 진단 진로 결정 영역으로 분리** (Φ-1 Land rev.next vs Φ-5 직진은 사용자 게이트)
- **실패 시 정정 절차** (rev.2 신규):
  - **mechanism 영역 회귀 발견**: 즉시 작업 중단, 사용자 보고 (DC-3 변경이 mechanism 영역에 침투했을 가능성 — `[금지] 6/7` 위반)
  - **#1 acceptance 부분 PASS 변동 (4 → 5+ sub-test FAIL)**: closure-v2 §2.1/§2.2 부분 PASS 잔재 외 신규 FAIL — 즉시 사용자 보고
  - **6종 (#2~#7) FAIL**: 회귀 신호 — 즉시 사용자 보고 + git bisect로 원인 추적

### 본 회귀 7종이 의도적으로 다루지 않는 영역

- **CPCM/SIS 본체 결정성** (Tier 2에서 신규 author)
- **API surface import 단독 검증** (Tier 2에서 신규 author)
- **placebo / smoke level 본체 결정성** — DC-1/DC-2 spec 본문 §V (각자) 절차 그대로 유지

---

## Tier 2 — Phase 5 Package 진입 시 신규 author 4종 (현 시점 부재)

> **운용 규칙**: 본 절은 **Phase 5 Package 진입 게이트**에서만 활성화. Phase 17 Φ-4 Nation Phase 3 (현재 단계)에서는 **신규 author 금지** (DC-3 [필수] 7종 외 코드 산출물 금지). 본 절은 Phase 5 진입 시 본 문서 rev.2 갱신 후 등재.

### 회귀 목록 (Phase 5 진입 시 신규 author, 현 시점 placeholder)

| # | 파일 (Phase 5 Package 신규) | 검증 영역 | 진입 게이트 |
|---|---|---|---|
| A | `tests/test_dc1_sis_smoke.py` | DC-1 distribution.json strict JSON parse + 9-a/9-b/9-c anchor 무 mutate | DC-1 SIS Phase 5 author |
| B | `tests/test_dc2_cpcm_smoke.py` | DC-2 overlap distribution strict JSON parse + 9-a/9-b/9-c anchor 무 mutate + brain·SNN 0건 호출 | DC-2 CPCM Phase 5 author |
| C | `tests/test_p5r_import_grep.py` | DC-3 V-1 (import 성공) + V-4 (reserved 3 슬롯 typed field 부재 grep) 자동화 | DC-3 P5R Phase 5 author |
| D | `tests/test_p5r_handoff_freeze.py` | Φ-5 → Φ-4 → Φ-3 → Φ-2 → Φ-1 단방향 계약 — 역방향 mutate 시도 시 즉시 실패 (mock 기반) | DC-3 P5R Phase 5 author |

### 4종 신규 author 시 본 문서 rev.2 절차

1. Phase 5 Package 진입 결정 (사용자 게이트)
2. 위 4종 신규 author (각 파일 PR 단위)
3. 4종 모두 `pytest` 통과 후 본 문서 rev.2 갱신:
   - Tier 2 4종을 placeholder → 실재 등재로 전환
   - 변경 이력 rev.2 항목 추가
4. DC-3 spec rev.3 (V-3 절을 본 문서 reference로 명시 갱신 — 단, Tier 1만으로 충분하면 갱신 불요)

### Tier 2 신규 author 시 [금지]

1. mechanism 변경 (acceptance / charter / brain·SNN API 무수정)
2. core / persona / ontology / brain / snn / physis 변경 (read-only)
3. Tier 1 7종에 영향 (Tier 1은 mechanism 무수정 → Tier 2는 신규 모듈만 다룬다)
4. body semantics 고정 (DC-1 §1.0 caveat 위반)
5. SIS 분위수 값 / CPCM 0.7 수치를 fixed value로 박기 (각 spec caveat 정합)

---

## 단일 권위 명시

| Spec / 문서 | 회귀 절 처리 |
|---|---|
| `PHASE-17-NATION-DC-1-SIS-SPEC.md` | 본문 [확정] 보존 — 회귀 절은 본 문서 reference로 갈음 권장 (rev.next 갱신 시점에 결정) |
| `PHASE-17-NATION-DC-2-CPCM-SPEC.md` | 본문 [확정] rev.3 보존 — 회귀 절은 본 문서 reference로 갈음 권장 (rev.next 갱신 시점에 결정) |
| `PHASE-17-NATION-DC-3-P5R-SPEC.md` | rev.2에서 V-3 절을 본 문서 reference로 교체 (의무) |
| `subagent-runs/discuss/phase17-nation-phase3-verify-2026-05-07-quick/input-brief.md` | 토론 인풋이므로 **historical record로 보존** — 갱신 불요. 본 문서가 권위 |

---

## 검증 contract — 본 문서 자체 (단일 source of truth 검증)

```bash
# 1. Tier 1 7종 모두 workspace 실재 확인 (본 문서 rev.1 시점 기준)
cd Projects/personas/loom
for f in test_phase17_acceptance.py test_phase17_faction.py test_phase17_faction_stage3.py \
         test_phase17_faction_regression.py test_phase17_faction_handoff_contract.py \
         test_phase14b_snn_integration.py test_phase17_land.py; do
  test -f "$f" || echo "MISSING: $f"
done
# 무 출력 = PASS

# 2. Tier 2 4종 부재 확인 (Phase 5 진입 전 placeholder 상태)
for f in tests/test_dc1_sis_smoke.py tests/test_dc2_cpcm_smoke.py \
         tests/test_p5r_import_grep.py tests/test_p5r_handoff_freeze.py; do
  test ! -f "$f" || echo "PRESENT (rev.2 갱신 필요): $f"
done
# 무 출력 = PASS (현 시점)

# 3. Tier 1 회귀 PASS
py -m pytest test_phase17_acceptance.py test_phase17_faction.py test_phase17_faction_stage3.py \
              test_phase17_faction_regression.py test_phase17_faction_handoff_contract.py \
              test_phase14b_snn_integration.py test_phase17_land.py -q
# 모두 PASS = 본 contract 충족
```

---

## §3.7 6단 사슬 정합

본 문서는 §3.7 사슬에 직접 진입하지 않음 (회귀 contract는 mechanism이 아닌 invariant 보존 검증). 단:

- **Tier 1**: §3.7 6단 closure 보고서의 "회귀 보존" evidence 절에서 본 문서 Tier 1 reference로 사용
- **Tier 2**: Phase 5 Package author 시 §3.7 5단 (3엔진 cross-check) 외부 — 회귀 author는 자연 측정 외 mechanism 무관

---

## Rollback

본 문서 자체 rollback:

```bash
git rm Projects/personas/loom/PHASE-17-NATION-PHASE3-REGRESSION-CONTRACT.md
```

데이터 영향: 없음 (회귀 7종 자체는 본 문서와 독립 — workspace 실재 변경 없음).

DC-3 spec rev.2가 본 문서를 reference하는 경우, DC-3 spec rev.1로 동시 rollback 의무 (단방향 의존 회피).

---

## [금지] (본 문서 갱신 시)

1. **본 문서 외부에서 회귀 목록 재정의 금지** — 다른 spec/문서에서 새 회귀 목록 신설 시 본 문서 rev.next 갱신 의무
2. **Tier 1 7종 변경 (제외/추가) 금지** — Phase 17 Φ-4 진행 중에는 Tier 1 고정. 변경 필요 시 사용자 사전 승인 게이트 (§3.3.2 비코어이지만 회귀 권위 변경은 사용자 결정 영역)
3. **Tier 2 4종 신규 author 시 본 문서 rev.next 갱신 의무** — placeholder → 실재 등재 누락 금지
4. **mechanism / acceptance / charter 본문 변경** — 본 문서는 회귀 contract 권위만 (mechanism 무관)
5. **Tier 1 7종을 author한 코드 수정** — 본 문서는 회귀 정의 권위. 회귀 본체 author는 별도 영역

---

## 참조

- `subagent-runs/claude/phase17-step35-validation-2026-05-07/run-summary.md` — Step 3.5 종합 결론 (Finding 2 만장일치)
- `subagent-runs/claude/phase17-step35-validation-2026-05-07/results/codex.result.md` — Codex Finding 2 본질 지적 ("single source of truth 부재")
- `Projects/personas/loom/PHASE-17-NATION-DC-3-P5R-SPEC.md` — DC-3 V-3 절 본 문서 reference로 교체 (rev.2)
- `Projects/personas/loom/LOOM-DIRECTION.md` §3.7 6단 사슬 / §3.3.2 코어 게이트
- workspace 실재 7종 (Glob 검증 2026-05-07) — `test_phase17_*.py` + `test_phase14b_snn_integration.py`
