# DC-1 Land-Climate distribution - seed 13

> **Provenance**: synthetic smoke collector (random walk). NOT actual `ClimateEngine` output. Suitable as smoke evidence only. §7-2 evidence requires real-collector reproduction.

- current_window_measurements: 7680
- cumulative_measurements: 7680

## 분위수 후보 (8 metric × 2 window × 5 quantile)

| metric | window | P25 | P50 | P67 | P75 | P90 |
|---|---|---:|---:|---:|---:|---:|
| soil_moisture | current | 0.103688 | 0.195021 | 0.250910 | 0.280415 | 0.348296 |
| soil_moisture | cumulative | 0.103688 | 0.195021 | 0.250910 | 0.280415 | 0.348296 |
| fertility | current | 0.074956 | 0.173547 | 0.237648 | 0.268232 | 0.340818 |
| fertility | cumulative | 0.074956 | 0.173547 | 0.237648 | 0.268232 | 0.340818 |
| rainfall_30d | current | 2.601647 | 5.331056 | 7.060618 | 7.913962 | 9.941888 |
| rainfall_30d | cumulative | 2.601647 | 5.331056 | 7.060618 | 7.913962 | 9.941888 |
| temperature_30d | current | 19.780232 | 19.976401 | 20.118770 | 20.206466 | 20.436171 |
| temperature_30d | cumulative | 19.780232 | 19.976401 | 20.118770 | 20.206466 | 20.436171 |
| drought_days | current | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 |
| drought_days | cumulative | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 |
| depletion | current | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| depletion | cumulative | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| recovery_rate | current | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| recovery_rate | cumulative | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| hazard_damage | current | 0.066667 | 0.200000 | 0.266667 | 0.300000 | 0.466667 |
| hazard_damage | cumulative | 0.066667 | 0.200000 | 0.266667 | 0.300000 | 0.466667 |

## 주의

This extractor derives quantile candidates only. It does not freeze any analytic threshold and does not change mechanism code. The current vs cumulative split mirrors paper §8 separation and the spec §2.2 telemetry buckets.
