# Phase 17 Emergence Probe — Stage 6 H-lite 결과 요약

## Stage 6 Primary Acceptance ✅

| seed | active_factions_end | min_active_1000to5000 | drift_ratio | gini_mean_end | Stage6_Primary |
|:----:|:-------------------:|:---------------------:|:-----------:|:-------------:|:--------------:|
| 7 | 3 | 3 | 8% | 0.60 | **PASS** |
| 13 | 3 | 3 | 3% | 0.53 | **PASS** |
| 42 | 3 | 3 | 14% | 0.39 | **PASS** |

**Primary 기준** (Charter v2 acceptance):
- `active_factions_end >= 2` AND `min_active_1000to5000 >= 2` — 3/3 PASS
- `drift_ratio <= 70%` — 3/3 PASS (Stage 5 대비 큰 폭 감소)
- `gini_mean_end < 0.75` — 3/3 PASS

→ **Φ-3 Struggle 진입 조건 충족.**

> 샘플링 차이 주의: Stage 5는 100틱 간격 샘플(last_500_active_min 산출 가능), Stage 6는 1000틱 간격 샘플 → `min_active_1000to5000`로 보수 측정. 1000~5000 모든 샘플에서 활성 ≥ 3 유지.

---

## H-lite 효과: drift_ratio 안정화

| seed | Stage 5 drift_ratio | Stage 6 drift_ratio | 변화 |
|:----:|:------------------:|:-------------------:|:----:|
| 7 | 61% | 8% | **−53%p** |
| 13 | 17% | 3% | **−14%p** |
| 42 | 26% | 14% | **−12%p** |

founder_lineage identity affinity (W_LINEAGE=0.2)가 같은 계보 faction과의 결속을 강화 → 무분별한 drift 억제. seed 7에서 가장 큰 안정화 효과.

---

## Probe 4종 판정 (참고용)

> ⚠️ probe verdict는 `final_active > initial_active`(분화 발생) 등 별도 기준. Stage 6 Primary와 무관.

| seed | active_factions_end | contact_pairs_end | drift_ratio | gini_mean_end | probe_verdict |
|:----:|:-------------------:|:-----------------:|:-----------:|:-------------:|:-------------:|
| 7 | 3 | 3 | 8% | 0.60 | FAIL |
| 13 | 3 | 3 | 3% | 0.53 | FAIL |
| 42 | 3 | 3 | 14% | 0.39 | FAIL |

probe FAIL 원인: `final_active(3) == initial_active(3)` → "분화 미발생" 판정.
Stage 6 목표(collapse 방지 + 계보 결속)와는 다른 기준.

---

## Charter v2 무파괴 9 보장 (검증 완료)

| 보장 항목 | Stage 6 변화 | 상태 |
|-----------|------------|:----:|
| FactionChangeSource 4종 | 추가 없음 | ✅ |
| AST whitelist `PHASE17_FACTION_SSOT_WRITE` 5건 | persona.faction 쓰기 경로 불변 | ✅ |
| D10 5채널 (birth_founder/affiliation/drift/conflict/territory) | 신규 채널 없음 | ✅ |
| SNN 뉴런 300~349 동결 | affiliation_score 계산 변경은 SNN 미침 | ✅ |
| Faction.grace_until_tick (Stage 5) | 무수정 | ✅ |
| InnerWorld.residence_ticks (Stage 5 D) | 무수정 | ✅ |
| five_channel_determinism | 통과 | ✅ |
| seed 42 tick perf (median ≤ 250ms, p95 ≤ 350ms) | 통과 | ✅ |
| faction_kernel ≤ 5ms/tick | 통과 | ✅ |

---

## 다음 단계

- ✅ Stage 6 H-lite 완료 → Stage 6 closure
- → Φ-3 Struggle Charter (`PHASE-17-STRUGGLE-CHARTER-STUB.md` 기반 본 Charter 작성)
- (보류) 체인 lineage 승계 — Stage 6.5 후보. 단일 founder.id 형태로도 acceptance 충족했으므로 실제 효과 데이터 모인 후 도입 결정.
