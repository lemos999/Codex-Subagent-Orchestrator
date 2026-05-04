# DC-1 SIS distribution - seed 13

- total_ticks: 20000
- windows: 28
- window_size: 720
- partial_windows: 1
- factions_observed: 23

## 분위수 후보

| metric | P25 | P50 | P67 | P75 | P90 |
|---|---:|---:|---:|---:|---:|
| dom_share | 0.588889 | 0.738889 | 1.000000 | 1.000000 | 1.000000 |
| member_share | 0.375000 | 0.444444 | 0.604000 | 0.888889 | 1.000000 |
| conflict_pair_count | 1.000000 | 2.500000 | 4.000000 | 4.000000 | 5.300000 |
| cross_faction_lord_count | 0.000000 | 1.000000 | 1.000000 | 1.250000 | 2.000000 |

## V3 일치 검증

- cfl_total: 23
- expected_cfl_total: 23
- last_contact_count_at_20000: 1
- expected_last_contact: 1
- passed: true

## 주의

This extractor derives distribution candidates only. It does not freeze a threshold, does not change mechanism code, and does not read mojibake summaries.
