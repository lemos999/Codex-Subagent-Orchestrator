# DC-1 SIS distribution - seed 42

- total_ticks: 20000
- windows: 28
- window_size: 720
- partial_windows: 1
- factions_observed: 24

## 분위수 후보

| metric | P25 | P50 | P67 | P75 | P90 |
|---|---:|---:|---:|---:|---:|
| dom_share | 0.600000 | 0.683333 | 0.809000 | 1.000000 | 1.000000 |
| member_share | 0.333333 | 0.500000 | 0.666667 | 0.725000 | 1.000000 |
| conflict_pair_count | 1.000000 | 2.000000 | 3.000000 | 3.000000 | 4.300000 |
| cross_faction_lord_count | 0.000000 | 1.000000 | 1.000000 | 1.000000 | 1.300000 |

## V3 일치 검증

- cfl_total: 19
- expected_cfl_total: 19
- last_contact_count_at_20000: 1
- expected_last_contact: 1
- passed: true

## 주의

This extractor derives distribution candidates only. It does not freeze a threshold, does not change mechanism code, and does not read mojibake summaries.
