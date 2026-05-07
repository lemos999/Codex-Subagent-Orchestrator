# DC-1 Land-Climate distribution - seed 7

> **Provenance**: ClimateEngine real evolution (90 tick, 3 seed × 64 cell). NOT synthetic random walk. paper §7-1 raw evidence base.

- current_window_measurements: 1920
- cumulative_measurements: 5760

## 분위수 후보 (8 metric × 2 window × 5 quantile)

| metric | window | P25 | P50 | P67 | P75 | P90 |
|---|---|---:|---:|---:|---:|---:|
| soil_moisture | current | 0.264583 | 0.300000 | 0.319048 | 0.337500 | 0.376549 |
| soil_moisture | cumulative | 0.206013 | 0.262500 | 0.297778 | 0.315873 | 0.387559 |
| fertility | current | 0.256250 | 0.299531 | 0.319048 | 0.334921 | 0.376526 |
| fertility | cumulative | 0.173333 | 0.255556 | 0.293750 | 0.309524 | 0.386150 |
| rainfall_30d | current | 13.675000 | 29.250000 | 40.200000 | 65.425000 | 160.410000 |
| rainfall_30d | cumulative | 11.400000 | 27.100000 | 38.100000 | 41.800000 | 164.220000 |
| temperature_30d | current | 12.320000 | 20.481667 | 21.333333 | 23.340000 | 30.373333 |
| temperature_30d | cumulative | 11.646843 | 20.109167 | 21.106667 | 22.572500 | 30.026667 |
| drought_days | current | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 3.000000 |
| drought_days | cumulative | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 2.000000 |
| depletion | current | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| depletion | cumulative | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| recovery_rate | current | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| recovery_rate | cumulative | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| hazard_damage | current | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 |
| hazard_damage | cumulative | 0.533333 | 0.966667 | 1.000000 | 1.000000 | 1.000000 |

## 주의

This extractor derives quantile candidates only. It does not freeze any analytic threshold and does not change mechanism code. The current vs cumulative split mirrors paper §8 separation and the spec §2.2 telemetry buckets.
