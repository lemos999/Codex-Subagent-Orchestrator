# DC-1 SIS distribution - seed 7

- total_ticks: 20000
- windows: 28
- window_size: 720
- partial_windows: 1
- factions_observed: 23

## 분위수 후보

| metric | P25 | P50 | P67 | P75 | P90 |
|---|---:|---:|---:|---:|---:|
| dom_share | 0.600000 | 0.900000 | 1.000000 | 1.000000 | 1.000000 |
| member_share | 0.400000 | 0.577778 | 0.900000 | 0.975000 | 1.000000 |
| conflict_pair_count | 1.750000 | 3.000000 | 3.000000 | 4.000000 | 6.000000 |
| cross_faction_lord_count | 0.000000 | 0.500000 | 1.000000 | 1.250000 | 2.000000 |

## V3 일치 검증

- cfl_total: 22
- expected_cfl_total: 22
- last_contact_count_at_20000: 1
- expected_last_contact: 1
- passed: true

## 주의

This extractor derives distribution candidates only. It does not freeze a threshold, does not change mechanism code, and does not read mojibake summaries.
