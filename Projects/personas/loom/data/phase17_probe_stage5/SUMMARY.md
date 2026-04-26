# Phase 17 Emergence Probe — Stage 5 결과 요약

## Stage 5 Primary Acceptance ✅

| seed | active_factions_end | last_500_active_min | Stage5_Primary |
|:----:|:-------------------:|:-------------------:|:--------------:|
| 7 | 3 | 3 | **PASS** |
| 13 | 3 | 3 | **PASS** |
| 42 | 3 | 3 | **PASS** |

**Primary 기준**: `active_factions_end >= 2` AND `last_500_active_min >= 2` — 3/3 PASS.  
→ **Stage 6 진입 조건 충족.**

---

## Probe 4종 판정 (참고용)

> ⚠️ probe verdict는 `final_active > initial_active`(분화 발생) 등 별도 기준. Stage 5 Primary와 무관.

| seed | active_factions_end | contact_pairs_end | drift_ratio | gini_mean_end | probe_verdict |
|:----:|:-------------------:|:-----------------:|:-----------:|:-------------:|:-------------:|
| 7 | 3 | 3 | 61% | 0.54 | FAIL |
| 13 | 3 | 3 | 17% | 0.53 | FAIL |
| 42 | 3 | 2 | 26% | 0.46 | FAIL |

probe FAIL 원인: `final_active(3) == initial_active(3)` → "분화 미발생" 판정.  
Stage 5 목표(collapse 방지)와는 다른 기준.

---

## 이상 징후 (Stage 5.5 모니터링 대상)

- **seed 7 drift_ratio=61%** + gini=0.54: 가중치 0.5 동률에서 drift 활발. 흡수는 막혔지만 경계 진동 큼.
- gini 과도 분산 임계값 미정 (conclusion.md Open Q #3) — Stage 5.5에서 정의 필요.
