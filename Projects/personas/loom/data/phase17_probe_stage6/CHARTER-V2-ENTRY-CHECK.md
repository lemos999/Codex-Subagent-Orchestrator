# Phase 17 Charter v2 — Φ-3 진입 OR 조건 정량 측정

> 측정 스크립트: `scripts/phase17_charter_v2_entry_check.py`
> 측정 시각: 2026-04-27
> 데이터셋: v6 (Stage 4 이전 collapse) / stage5 (drift mitigation 후) / stage6 (H-lite founder_lineage W=0.2)
> 목적: Stage 6 SUMMARY 정성 보고를 1차 자료(metrics.jsonl)에서 정량 확인 + 로드맵 v2 finding #2 데이터 정합성 게이트.

---

## 1. Charter v2 Φ-3 진입 OR 조건 3종 (Charter §"Phi-3 Entry Trigger Candidates")

OR 결합: 1개 이상 충족 시 Φ-3 진입 가능.

| seed | OR-1 Geographic (contact_pairs ≥ 1) | OR-2 Imbalance (dom_share ≥ 55%) | OR-3 Grievance (shared_pairs ≥ 1) | 충족 | Φ-3 진입 |
|:----:|:----:|:----:|:----:|:----:|:----:|
| 7 | **PASS** (3쌍) | FAIL (40.0%) | FAIL (0쌍) | 1/3 | **YES** |
| 13 | **PASS** (3쌍) | FAIL (40.0%) | FAIL (0쌍) | 1/3 | **YES** |
| 42 | **PASS** (3쌍) | FAIL (40.0%) | FAIL (0쌍) | 1/3 | **YES** |

**결론**: 3 seed 전부 OR-1 단독 충족으로 Φ-3 진입 자격 확인. 그러나 OR-2/OR-3 미충족 → **이것이 Φ-3가 해결해야 할 핵심 결손**.

---

## 2. dataset 간 비교 (seed별)

### seed 7

|  set    | min_act | pop@end | top | dom%  | contact | grievance | gini@2500 | gini@5000 | drift% |
|:-------:|:------:|:-------:|:---:|:-----:|:-------:|:---------:|:---------:|:---------:|:------:|
| v6      | 1      | 10      | 10  | 100.0 | 0       | 0         | 0.234     | 0.204     | 54.9   |
| stage5  | 3      | 10      | 4   | 40.0  | 3       | 0         | 0.535     | 0.541     | 60.8   |
| stage6  | 3      | 10      | 4   | 40.0  | 3       | 0         | 0.483     | **0.600** | **7.9** |

### seed 13

|  set    | min_act | pop@end | top | dom%  | contact | grievance | gini@2500 | gini@5000 | drift% |
|:-------:|:------:|:-------:|:---:|:-----:|:-------:|:---------:|:---------:|:---------:|:------:|
| v6      | 1      | 10      | 10  | 100.0 | 0       | 0         | 0.240     | 0.219     | 51.4   |
| stage5  | 3      | 10      | 4   | 40.0  | 3       | 0         | 0.614     | 0.532     | 17.4   |
| stage6  | 3      | 10      | 4   | 40.0  | 3       | 0         | 0.614     | 0.532     | **2.6** |

### seed 42

|  set    | min_act | pop@end | top | dom%  | contact | grievance | gini@2500 | gini@5000 | drift% |
|:-------:|:------:|:-------:|:---:|:-----:|:-------:|:---------:|:---------:|:---------:|:------:|
| v6      | 1      | 10      | 10  | 100.0 | 0       | 0         | 0.183     | 0.283     | 41.7   |
| stage5  | 3      | 10      | 4   | 40.0  | 2       | 0         | 0.503     | 0.462     | 26.0   |
| stage6  | 3      | 10      | 4   | 40.0  | 3       | 0         | 0.540     | **0.390** | **13.6** |

---

## 3. 핵심 finding

### 3-1. v6 → stage5/6 Phase 회복 (collapse → multi-faction)

- v6: active=1, dom_share=100%, contact=0 — 전 seed에서 단일 faction collapse
- stage5/6: active=3, dom_share=40%, contact=3 — 1000~5000 tick 모든 sample에서 3 faction 활성 유지
- **Stage 2 mitigation(size tax + homeostasis) + Stage 3 anti-collapse + Stage 5 drift + Stage 6 founder_lineage가 누적되어 collapse 회피**

### 3-2. drift_ratio 큰 폭 안정화 (Stage 6 H-lite의 핵심 효과)

| seed | Stage 5 | Stage 6 | 차이 | SUMMARY 보고 |
|:----:|:-------:|:-------:|:----:|:------------:|
| 7    | 60.8%   | 7.9%    | **-52.9%p** | -53%p ✓ |
| 13   | 17.4%   | 2.6%    | **-14.8%p** | -14%p ✓ |
| 42   | 26.0%   | 13.6%   | **-12.4%p** | -12%p ✓ |

**측정 ↔ Stage 6 SUMMARY 정합성: PASS** (반올림 차 1%p 이내). founder_lineage 동일 계보 affinity (W_LINEAGE=0.2)가 무분별한 drift를 억제.

### 3-3. gini 추세 — 단조 증가 아님 (Stage 6 SUMMARY 정성 표현 정정)

Stage 6 SUMMARY는 "wealth gini 증가 경향 → 계급 재료 축적"이라고 보고했으나, 실제 측정은 seed별 mixed:

| seed | gini@2500 | gini@5000 | 추세 |
|:----:|:---------:|:---------:|:----:|
| 7    | 0.483     | 0.600     | 증가 |
| 13   | 0.614     | 0.532     | **감소** |
| 42   | 0.540     | 0.390     | **감소** |

**판정**: gini는 5000 tick 시점에서 "증가 경향"을 일반화하기엔 노이즈가 크다. seed 평균: 0.546→0.507 (소폭 감소). Φ-3 시점에서 다시 측정 필요. **로드맵 v2 finding #2 정정 반영**: Stage 6 SUMMARY의 "증가 경향" 문구는 seed 7만 해당, 일반화 표현은 보수적으로 수정 권장.

### 3-4. OR-3 Grievance 0쌍 — Φ-3가 해결할 핵심 결손

3 seed 모두 grievance_targets `raw = {fid: {} for fid in factions}` — 모든 faction이 어떤 lord_id도 grievance 대상으로 누적하지 않음.

- 원인: 현 시점 grievance accumulator가 lord-specific 사건을 충분히 발생시키지 않거나, 5000 tick이 grievance 응결에 부족
- Φ-3 핵심 입력 부재: "공유 분노 대상" 없이는 "왜 싸우는가" 동역학이 시작되지 않음
- **Φ-3 Charter 작성 시**: grievance 채널을 1차 입력으로 강제하거나, 별도 mechanism으로 lord-faction 그리바이언스 생성 필요

### 3-5. OR-2 Imbalance 40% — 균등 분포 한계

3 faction × 평균 3.33명, top=4. 이는 H-lite founder_lineage가 Stage 5의 drift fluctuation을 지나치게 평탄화했을 가능성. Φ-3가 conflict-driven asymmetry를 도입하지 않으면 자연스러운 imbalance가 생기지 않을 수 있다.

---

## 4. SUMMARY 비교 — 자체 정합성

Stage 6 SUMMARY의 정성 보고가 metrics.jsonl 1차 자료와 어디서 일치/불일치하는지 명시.

| 항목 | SUMMARY 보고 | 측정 | 정합성 |
|------|-------------|------|:------:|
| active_factions_end | 3/3/3 | 3/3/3 | ✓ |
| min_active_1000to5000 | 3/3/3 | 3/3/3 | ✓ |
| drift_ratio | 8/3/14% | 7.9/2.6/13.6% | ✓ (반올림) |
| contact_pairs_end | 3/3/3 (seed 42 명시) | 3/3/3 | ✓ |
| grievance_pairs | 0쌍 (seed 42 명시) | 0/0/0 | ✓ |
| gini_mean_end | 0.60/0.53/0.39 | 0.600/0.532/0.390 | ✓ |
| **wealth gini 증가 경향** | "증가 경향" | seed별 mixed (7 증가, 13/42 감소) | **부분 불일치** |

→ 6/7 정합. 1건(gini 추세) 정성 표현 보수화 권장. 그 외 SUMMARY 수치는 모두 1차 자료와 일치.

---

## 5. 다음 단계 권고

1. **Φ-3 Charter는 OR-1 단독 진입 자격으로 작성 가능** — OR-1 조건 확인 PASS
2. **Φ-3 Charter 핵심 설계 항목**:
   - OR-3 grievance 채널 활성화 (lord_id 기반 누적 mechanism 보강 또는 충돌-grievance 연결)
   - OR-2 imbalance 자연 형성 (conflict source 도입, 또는 territory 분포 비대칭 유도)
3. **Stage 6 SUMMARY 미세 정정**: "wealth gini 증가 경향" → "wealth gini 변동 (seed별 mixed)" 또는 단조성 단정 제거
4. **measurement 스크립트 보존**: `phase17_charter_v2_entry_check.py`는 Φ-3 closure 시 동일 OR 조건 재측정에 재사용

---

## 6. 무파괴 9 보장 영향

이번 측정은 **read-only 스크립트** (D10 7 API 외부 — metrics.jsonl 직접 파싱). 신규 mutation 0건, Charter v2 무파괴 9 보장 무영향.
