# DC-2 CPCM overlap distribution - seed 42

- seed: 42
- total_ticks: 20000
- snapshot_count: 40
- snapshot_interval: 500
- algorithm: Jaccard
- 활성 faction pair 관측치: 36
- 빈 charter pair (nan): 0

## 분위수 후보

| 분위수 | 값 |
|---|---:|
| P25 | 0.125000 |
| P50 | 0.333333 |
| P67 | 1.000000 |
| P75 | 1.000000 |
| P90 | 1.000000 |

## V3 anchor 검증

- snapshot count: True
- active fid set match: True
- active_count self-consistency: True
- passed: True

## 주의

이 결과는 exploratory telemetry다. 분위수 후보만 산출하며 의사결정 조건을 고정하지 않는다.
P5R body semantics나 branch rule로 승격하지 않는다.
