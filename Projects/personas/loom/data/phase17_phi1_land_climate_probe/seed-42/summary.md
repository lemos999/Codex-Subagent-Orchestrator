# DC-1 Land-Climate distribution - seed 42

> **Provenance**: synthetic smoke collector (random walk). NOT actual `ClimateEngine` output. Suitable as smoke evidence only. §7-2 evidence requires real-collector reproduction.

- current_window_measurements: 7680
- cumulative_measurements: 7680

## 분위수 후보 (8 metric × 2 window × 5 quantile)

| metric | window | P25 | P50 | P67 | P75 | P90 |
|---|---|---:|---:|---:|---:|---:|
| soil_moisture | current | 0.105721 | 0.193709 | 0.252254 | 0.281115 | 0.344296 |
| soil_moisture | cumulative | 0.105721 | 0.193709 | 0.252254 | 0.281115 | 0.344296 |
| fertility | current | 0.083482 | 0.178617 | 0.243450 | 0.271987 | 0.339972 |
| fertility | cumulative | 0.083482 | 0.178617 | 0.243450 | 0.271987 | 0.339972 |
| rainfall_30d | current | 2.667189 | 5.337976 | 7.112104 | 7.929601 | 9.925765 |
| rainfall_30d | cumulative | 2.667189 | 5.337976 | 7.112104 | 7.929601 | 9.925765 |
| temperature_30d | current | 19.808071 | 20.007574 | 20.127648 | 20.200164 | 20.420354 |
| temperature_30d | cumulative | 19.808071 | 20.007574 | 20.127648 | 20.200164 | 20.420354 |
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
