# Phase 14B-B Anger Coupling — Threshold Simulation

> Source: `data/phase17_probe_phi3-snn-output-diag/seed-{7,13,42}/snn_output_events.json`
> Spec: `PHASE-14B-B-ANGER-COUPLING-PROBE-SPEC.md`
> §3.7 위치: 4단 (임계 분위수) + 5단 cross-check 입력
> mechanism 본문 변경 **없음** — 텔레메트리 후처리만

## 1. 전체 통합 분포

| 항목 | n | min | P25 | P50 | P67 | P75 | P80 | P90 | max | mean | stdev |
|------|:-:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:----:|:-----:|
| 전체 (pass+fail) | 205 | 0.311 | 0.452 | 0.529 | 0.594 | 0.641 | 0.664 | 0.749 | 0.895 | 0.550 | 0.133 |
| pass (gate 통과) | 50 | 0.600 | 0.649 | 0.702 | 0.763 | 0.778 | 0.792 | 0.851 | 0.895 | 0.720 | 0.082 |
| fail (gate 미통과) | 155 | 0.311 | 0.427 | 0.487 | 0.532 | 0.544 | 0.561 | 0.597 | 0.894 | 0.496 | 0.095 |

## 2. 임계 후보 (3 seed 통합 분위수에서 도출)

| 후보명 | 임계 | 위치 정당화 |
|--------|:----:|-------------|
| **P50** | 0.5293 | 통합 분포 중앙값 — 약한 결합, 자연 보수적 |
| **P67** | 0.5942 | pass 평균과 fail 평균 사이 — 중간 결합 |
| **P75** | 0.6406 | pass 분포 P25 근처 — 강한 변별 |
| (참고) fail_P50 | 0.4873 | fail 그룹 중앙값 — 너무 낮음 |
| (참고) pass_P25 | 0.6489 | pass 그룹 P25 — pass 그룹의 75% 통과 지점 |

## 3. 임계 후보 시뮬 — seed별 PASS 비율 추정

**시뮬 방법**: 각 임계 T에 대해, anger ≥ T인 leader 이벤트만 세서 (1) 실제 gate_passed 비율, (2) cross-faction lord 공유 카운트 (top_lord_id가 동일한 다른 fid 페어 카운트). 이는 mechanism 변경 없는 **후처리 추산** — 실제 mechanism이 임계를 사용한 결과 측정 아님.

### seed-7

| 후보 | 임계 | meet_count | meet_pass | meet_fail | meet_pass_ratio | unique_top_lords | cross_faction_lord_count |
|------|:----:|:----------:|:---------:|:---------:|:---------------:|:----------------:|:------------------------:|
| P50 | 0.5293 | 27 | 20 | 7 | 0.741 | 10 | 4 |
| P67 | 0.5942 | 24 | 20 | 4 | 0.833 | 10 | 4 |
| P75 | 0.6406 | 20 | 18 | 2 | 0.900 | 9 | 4 |
| fail_P50 | 0.4873 | 31 | 20 | 11 | 0.645 | 10 | 4 |
| pass_P25 | 0.6489 | 17 | 15 | 2 | 0.882 | 9 | 4 |

### seed-13

| 후보 | 임계 | meet_count | meet_pass | meet_fail | meet_pass_ratio | unique_top_lords | cross_faction_lord_count |
|------|:----:|:----------:|:---------:|:---------:|:---------------:|:----------------:|:------------------------:|
| P50 | 0.5293 | 35 | 14 | 21 | 0.400 | 9 | 5 |
| P67 | 0.5942 | 20 | 14 | 6 | 0.700 | 8 | 4 |
| P75 | 0.6406 | 15 | 11 | 4 | 0.733 | 7 | 3 |
| fail_P50 | 0.4873 | 44 | 14 | 30 | 0.318 | 9 | 5 |
| pass_P25 | 0.6489 | 13 | 9 | 4 | 0.692 | 6 | 2 |

### seed-42

| 후보 | 임계 | meet_count | meet_pass | meet_fail | meet_pass_ratio | unique_top_lords | cross_faction_lord_count |
|------|:----:|:----------:|:---------:|:---------:|:---------------:|:----------------:|:------------------------:|
| P50 | 0.5293 | 41 | 16 | 25 | 0.390 | 9 | 6 |
| P67 | 0.5942 | 24 | 16 | 8 | 0.667 | 8 | 3 |
| P75 | 0.6406 | 17 | 14 | 3 | 0.824 | 6 | 3 |
| fail_P50 | 0.4873 | 53 | 16 | 37 | 0.302 | 9 | 6 |
| pass_P25 | 0.6489 | 17 | 14 | 3 | 0.824 | 6 | 3 |

## 4. 해석 (cross-check 입력 자료)

- **meet_pass_ratio**: 임계 T 통과 leader 중 실제 gate_passed 비율. 1.0에 가까울수록 임계가 pass 그룹 변별력 높음.
- **cross_faction_lord_count**: 동일 `top_lord_id`를 가진 다른 fid 페어 수. ≥ 1이면 cross-faction grievance pair 잠재력 존재 — acceptance #2 (`grievance_pairs_end ≥ 1`) 자연 발생 가능성 시뮬 지표.
- **주의**: 본 시뮬은 **현재 텔레메트리 후처리** — 실제 mechanism 변경 시 leader 풀이 바뀔 수 있음. 시뮬 결과는 잠재력 비교 자료 (cross-check 의사결정 입력).

## 5. 다음 단계

3엔진 cross-check (`/discuss --quick`) 입력으로 본 데이터 + axis A vs B 차별 검토 + Spec §5의 4 질문 사용. cross-check 후 mechanism 결정.
