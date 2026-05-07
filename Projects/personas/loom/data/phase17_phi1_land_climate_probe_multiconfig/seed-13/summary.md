# DC-1 Land-Climate distribution - seed 13

> **Provenance**: ClimateEngine multi-config axis (NovaPlanet alt instance: nova_cool). paper §7-1 planet-variation evidence base.

- current_window_measurements: 1920
- cumulative_measurements: 5760

## 분위수 후보 (8 metric × 2 window × 5 quantile)

| metric | window | P25 | P50 | P67 | P75 | P90 |
|---|---|---:|---:|---:|---:|---:|
| soil_moisture | current | 0.217708 | 0.288492 | 0.319697 | 0.326515 | 0.378943 |
| soil_moisture | cumulative | 0.193648 | 0.262500 | 0.306250 | 0.321212 | 0.370320 |
| fertility | current | 0.208333 | 0.267460 | 0.310317 | 0.326515 | 0.378621 |
| fertility | cumulative | 0.150000 | 0.247222 | 0.297917 | 0.317424 | 0.368950 |
| rainfall_30d | current | 10.450000 | 36.350000 | 41.900000 | 67.950000 | 164.930000 |
| rainfall_30d | cumulative | 11.500000 | 29.000000 | 40.400000 | 43.600000 | 162.200000 |
| temperature_30d | current | 6.327500 | 14.481667 | 15.333333 | 17.340000 | 24.373333 |
| temperature_30d | cumulative | 5.655051 | 14.109167 | 15.106667 | 16.572500 | 24.026667 |
| drought_days | current | 0.000000 | 1.000000 | 1.000000 | 2.000000 | 3.100000 |
| drought_days | cumulative | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 3.000000 |
| depletion | current | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| depletion | cumulative | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| recovery_rate | current | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| recovery_rate | cumulative | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| hazard_damage | current | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 |
| hazard_damage | cumulative | 0.633333 | 1.000000 | 1.000000 | 1.000000 | 1.000000 |

## 주의

This extractor derives quantile candidates only. It does not freeze any analytic threshold and does not change mechanism code. The current vs cumulative split mirrors paper §8 separation and the spec §2.2 telemetry buckets.
