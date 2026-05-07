# DC-1 Land-Climate distribution - seed 42

> **Provenance**: ClimateEngine multi-config axis (NovaPlanet alt instance: nova_cool). paper §7-1 planet-variation evidence base.

- current_window_measurements: 1920
- cumulative_measurements: 5760

## 분위수 후보 (8 metric × 2 window × 5 quantile)

| metric | window | P25 | P50 | P67 | P75 | P90 |
|---|---|---:|---:|---:|---:|---:|
| soil_moisture | current | 0.262500 | 0.282864 | 0.302083 | 0.306977 | 0.353756 |
| soil_moisture | cumulative | 0.186997 | 0.275000 | 0.299259 | 0.311187 | 0.366667 |
| fertility | current | 0.246512 | 0.276744 | 0.296899 | 0.303196 | 0.351667 |
| fertility | cumulative | 0.140000 | 0.264444 | 0.291111 | 0.304444 | 0.361416 |
| rainfall_30d | current | 12.700000 | 35.700000 | 42.700000 | 63.800000 | 135.580000 |
| rainfall_30d | cumulative | 11.900000 | 31.100000 | 41.100000 | 44.700000 | 146.440000 |
| temperature_30d | current | 6.327500 | 14.481667 | 15.333333 | 17.340000 | 24.373333 |
| temperature_30d | cumulative | 5.655051 | 14.109167 | 15.106667 | 16.572500 | 24.026667 |
| drought_days | current | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 2.000000 |
| drought_days | cumulative | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 3.000000 |
| depletion | current | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| depletion | cumulative | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| recovery_rate | current | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| recovery_rate | cumulative | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| hazard_damage | current | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 |
| hazard_damage | cumulative | 0.600000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 |

## 주의

This extractor derives quantile candidates only. It does not freeze any analytic threshold and does not change mechanism code. The current vs cumulative split mirrors paper §8 separation and the spec §2.2 telemetry buckets.
