# DC-1 Land-Climate distribution - seed 7

> **Provenance**: synthetic smoke collector (random walk). NOT actual `ClimateEngine` output. Suitable as smoke evidence only. §7-2 evidence requires real-collector reproduction.

- current_window_measurements: 7680
- cumulative_measurements: 7680

## 분위수 후보 (8 metric × 2 window × 5 quantile)

| metric | window | P25 | P50 | P67 | P75 | P90 |
|---|---|---:|---:|---:|---:|---:|
| soil_moisture | current | 0.112385 | 0.202301 | 0.263224 | 0.291707 | 0.355573 |
| soil_moisture | cumulative | 0.112385 | 0.202301 | 0.263224 | 0.291707 | 0.355573 |
| fertility | current | 0.081654 | 0.182512 | 0.249001 | 0.280658 | 0.349538 |
| fertility | cumulative | 0.081654 | 0.182512 | 0.249001 | 0.280658 | 0.349538 |
| rainfall_30d | current | 2.791692 | 5.523445 | 7.360511 | 8.205393 | 10.175748 |
| rainfall_30d | cumulative | 2.791692 | 5.523445 | 7.360511 | 8.205393 | 10.175748 |
| temperature_30d | current | 19.751881 | 19.967379 | 20.115370 | 20.193727 | 20.401854 |
| temperature_30d | cumulative | 19.751881 | 19.967379 | 20.115370 | 20.193727 | 20.401854 |
| drought_days | current | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 |
| drought_days | cumulative | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 |
| depletion | current | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| depletion | cumulative | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| recovery_rate | current | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| recovery_rate | cumulative | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| hazard_damage | current | 0.066667 | 0.166667 | 0.233333 | 0.300000 | 0.433333 |
| hazard_damage | cumulative | 0.066667 | 0.166667 | 0.233333 | 0.300000 | 0.433333 |

## 주의

This extractor derives quantile candidates only. It does not freeze any analytic threshold and does not change mechanism code. The current vs cumulative split mirrors paper §8 separation and the spec §2.2 telemetry buckets.
