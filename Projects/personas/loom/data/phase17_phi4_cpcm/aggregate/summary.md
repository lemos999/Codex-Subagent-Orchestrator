# DC-2 CPCM aggregate overlap distribution

- seed: 7, 13, 42
- total_ticks: 20000
- snapshot_count_per_seed: 40
- algorithm: Jaccard

## 분위수 후보

| 분위수 | 값 |
|---|---:|
| P25 | 0.285714 |
| P50 | 0.500000 |
| P67 | 1.000000 |
| P75 | 1.000000 |
| P90 | 1.000000 |

## Seed consistency within 10 percent

| 분위수 | within_10pct | mean | seed_7 | seed_13 | seed_42 |
|---|---:|---:|---:|---:|---:|
| P50 | false | 0.611111 | 1.000000 | 0.500000 | 0.333333 |
| P67 | true | 1.000000 | 1.000000 | 1.000000 | 1.000000 |
| P75 | true | 1.000000 | 1.000000 | 1.000000 | 1.000000 |

## V3 anchor 검증

| seed | snapshot_count | fid set match | active_count self-consistency |
|---:|---:|---:|---:|
| 7 | True | True | True |
| 13 | True | True | True |
| 42 | True | True | True |

## 주의

이 결과는 exploratory telemetry다. 분위수 후보만 산출하며 의사결정 조건을 고정하지 않는다.
SIS와 CPCM 결합, P5R body, branch rule 승격은 별도 spec에서 다룬다.
