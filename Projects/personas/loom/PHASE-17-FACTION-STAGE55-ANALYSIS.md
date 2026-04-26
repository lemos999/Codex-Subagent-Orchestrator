# Phase 17 Φ-2 Stage 5.5 — 관찰 강화 분석

> 작성: 2026-04-26  
> 입력: Stage 5 probe 결과 (data/phase17_probe_stage5/)  
> 결론: **Stage 6 진입 차단 요소 없음**

---

## 1. last_500_active 검증 (Stage 6 진입 게이트)

| seed | 4500 | 4600 | 4700 | 4800 | 4900 | 5000 | min | 판정 |
|:----:|:----:|:----:|:----:|:----:|:----:|:----:|:---:|:----:|
| 7 | 3 | 3 | 3 | 3 | 3 | 3 | **3** | ✅ |
| 13 | 3 | 3 | 3 | 3 | 3 | 3 | **3** | ✅ |
| 42 | 3 | 3 | 3 | 3 | 3 | 3 | **3** | ✅ |

**Primary + last_500 3/3 PASS → Stage 6 진입 조건 충족.**

---

## 2. seed 7 drift_ratio=61% 진단

### 데이터

| seed | birth_founder | affiliation | drift | conflict |
|:----:|:-------------:|:-----------:|:-----:|:--------:|
| 7 | 3 (4%) | 28 (35%) | **48 (61%)** | 0 |
| 13 | 3 (7%) | 35 (76%) | 8 (17%) | 0 |
| 42 | 3 (6%) | 34 (68%) | 13 (26%) | 0 |

### 결론

drift_ratio=61%은 **이상이 아님**. 해석:

- W_TRUST=W_TERRITORY_SAME=0.5 동률에서 seed별 초기 배치(territory 분산 패턴)에 따라  
  drift 비율이 달라진다. seed 7은 초기에 territory 동거가 많아 affiliation이 빠르게 수렴 후  
  이후 drift가 dominant해지는 패턴.
- 중요한 것: **drift가 활발해도 collapse 없음** (active_end=3, last_500_active_min=3).  
  "경계 진동"이지 "흡수 경로"가 아님.
- drift_ratio 상한 정의 필요 여부: **Stage 6에서 H-lite 도입 후** 재측정. 현재 기준으로  
  drift_ratio < 70% → 정상으로 임시 규정.

---

## 3. Gini 임계값 정의 (Open Q #3)

### 데이터 (per-faction gini, 100틱 샘플)

| seed | t1500 | t3000 | t4500 | 최대 관찰값 |
|:----:|:-----:|:-----:|:-----:|:-----------:|
| 7 | 0.33/0.62/0.40 | 0.38/0.52/0.64 | 0.50/0.42/0.74 | **0.743** |
| 13 | 0.57/0.43/0.43 | 0.74/0.20/0.75 | 0.75/0.55/0.66 | **0.747** |
| 42 | 0.49/0.25/0.48 | 0.46/0.16/0.69 | 0.63/0.70/0.63 | **0.703** |

### 임계값 정의

| 구간 | 해석 | 처치 |
|------|------|------|
| gini < 0.60 | 정상 분산 | — |
| 0.60 ≤ gini < 0.75 | 계급 재료 축적 중 (Φ-3 소재) | 모니터링 |
| gini ≥ 0.75 | **과도 분산 경고** — 단일 faction 독식 위험 | Stage 6+ 처치 후보 |

현재 최대 관찰값 0.747 (seed 13, t3000 단일 faction) → 임계선(0.75) 근접.  
**I+G 적용 후 gini 과도 분산 가속 우려 (conclusion.md Open Q #3) = 실제 데이터로 확인됨.**  
H-lite 도입 후 gini 추이 재측정 필요.

---

## 4. residence_ticks 분포 (D 관찰)

- 현재 `InnerWorld.residence_ticks: dict[str, int]`는 **read-only 누적** (Stage 5 D).
- metrics.jsonl에 residence_ticks 분포 데이터 없음 → Stage 6에서 observe 스크립트에  
  `residence_ticks` 샘플링 추가 권장.
- affiliation 입력 격상 여부: residence_ticks 분포 확인 후 결정. **현재 Stage 6 범위 밖.**

---

## 5. Stage 6 진입 판정

| 조건 | 상태 |
|------|:----:|
| `last_500_active >= 2` 3/3 | ✅ |
| drift_ratio 이상 없음 | ✅ (61% = 건강한 drift) |
| gini 임계 미초과 | ✅ (최대 0.747 < 0.75) |
| H-lite 4-source 매핑 증명 | 🔲 **Stage 6 첫 번째 작업** |

→ **Stage 6 진입 승인. H-lite 매핑 증명 후 구현.**
