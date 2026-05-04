# DC-1 SIS aggregate distribution

- seeds: 7, 13, 42
- total_ticks: 20000
- window_size: 720

## 분위수 후보

| metric | P25 | P50 | P67 | P75 | P90 |
|---|---:|---:|---:|---:|---:|
| dom_share | 0.600000 | 0.777778 | 1.000000 | 1.000000 | 1.000000 |
| member_share | 0.343750 | 0.555556 | 0.666667 | 0.900000 | 1.000000 |
| conflict_pair_count | 1.000000 | 2.000000 | 3.000000 | 4.000000 | 5.700000 |
| cross_faction_lord_count | 0.000000 | 1.000000 | 1.000000 | 1.000000 | 2.000000 |

## Seed consistency within 10 percent

| metric | quantile | within_10pct | mean | seed_7 | seed_13 | seed_42 |
|---|---|---:|---:|---:|---:|---:|
| dom_share | P50 | false | 0.774074 | 0.900000 | 0.738889 | 0.683333 |
| dom_share | P67 | false | 0.936333 | 1.000000 | 1.000000 | 0.809000 |
| dom_share | P75 | true | 1.000000 | 1.000000 | 1.000000 | 1.000000 |
| member_share | P50 | false | 0.507407 | 0.577778 | 0.444444 | 0.500000 |
| member_share | P67 | false | 0.723556 | 0.900000 | 0.604000 | 0.666667 |
| member_share | P75 | false | 0.862963 | 0.975000 | 0.888889 | 0.725000 |
| conflict_pair_count | P50 | false | 2.500000 | 3.000000 | 2.500000 | 2.000000 |
| conflict_pair_count | P67 | false | 3.333333 | 3.000000 | 4.000000 | 3.000000 |
| conflict_pair_count | P75 | false | 3.666667 | 4.000000 | 4.000000 | 3.000000 |
| cross_faction_lord_count | P50 | false | 0.833333 | 0.500000 | 1.000000 | 1.000000 |
| cross_faction_lord_count | P67 | true | 1.000000 | 1.000000 | 1.000000 | 1.000000 |
| cross_faction_lord_count | P75 | false | 1.166667 | 1.250000 | 1.250000 | 1.000000 |

## V3 일치 검증

| seed | cfl_total | last_contact_count_at_20000 |
|---:|---:|---:|
| 7 | 22 | 1 |
| 13 | 23 | 1 |
| 42 | 19 | 1 |

## 주의

This extractor only derives quantile candidates. It does not freeze a threshold and does not change mechanism code.
