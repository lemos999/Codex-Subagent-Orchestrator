# Phase 17 Emergence Probe — seed 7

## 실행 요약
- 틱: 5000
- 시작 faction 수: 3
- 종료 faction 수: 3
- 총 faction_change 이벤트: 79
- 경과: 667.6s (133.5ms/tick)

## 분포 진화 (1000틱 간격 샘플)
| tick | 활성 faction 수 | 최대 소속 인원 | 균등도 (H/Hmax) |
|------|----------------|----------------|------------------|
| 0 | 3 | 1 | 1.00 |
| 1000 | 3 | 4 | 0.99 |
| 2000 | 3 | 4 | 0.97 |
| 3000 | 3 | 4 | 0.99 |
| 4000 | 3 | 5 | 0.94 |
| 5000 | 3 | 4 | 0.99 |

## Φ-3 재료: 접촉 쌍 추이
- tick 0: 0쌍
- tick 1000: 1쌍
- tick 5000: 3쌍
- **판정**: [PASS] if ≥1쌍 at tick 5000 else [FAIL]

## Source 비율 (누적)
| source | count | pct |
|--------|-------|-----|
| birth_founder | 3 | 4% |
| affiliation | 28 | 35% |
| drift | 48 | 61% |
| conflict | 0 | 0% |

**판정**: drift ≥ 5% → [PASS]

## Wealth gini 추이
- tick 500: avg gini 0.24
- tick 2500: avg gini 0.53
- tick 5000: avg gini 0.54
- **경향**: [증가]

## Grievance 공유 (봉기 재료)
- tick 5000 기준: 0 쌍의 faction이 같은 lord를 grievance 대상으로 공유
- **판정**: [N/A] if ≥1쌍 else [N/A]

## 종합 판정
- [FAIL] 분화 발생 (최종 active faction 수 > 초기)
- [PASS] 접촉 쌍 ≥ 1 (Φ-3 진입 가능)
- [PASS] drift source ≥ 5% (bottom-up 재배치 실제 발생)
- [PASS] wealth gini 증가 경향 (계급 재료 축적)

## 이상 징후 (있을 경우)
- 없음
