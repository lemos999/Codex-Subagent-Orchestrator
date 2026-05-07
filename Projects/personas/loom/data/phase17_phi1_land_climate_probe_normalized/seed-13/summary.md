# DC-1 Land-Climate distribution - seed 13

> **Provenance**: ClimateEngine normalized axis (precipitation_mm / 30.0). NOT raw or synthetic. paper §7-1 unit-normalized evidence base.

- current_window_measurements: 1920
- cumulative_measurements: 5760

## 분위수 후보 (8 metric × 2 window × 5 quantile)

| metric | window | P25 | P50 | P67 | P75 | P90 |
|---|---|---:|---:|---:|---:|---:|
| soil_moisture | current | 0.217708 | 0.288492 | 0.319697 | 0.326515 | 0.378943 |
| soil_moisture | cumulative | 0.193648 | 0.262500 | 0.306250 | 0.321212 | 0.370320 |
| fertility | current | 0.208333 | 0.267460 | 0.310317 | 0.326515 | 0.378621 |
| fertility | cumulative | 0.150000 | 0.247222 | 0.297917 | 0.317424 | 0.368950 |
| rainfall_30d | current | 0.348333 | 1.211667 | 1.396667 | 2.265000 | 5.497667 |
| rainfall_30d | cumulative | 0.383333 | 0.966667 | 1.346667 | 1.453333 | 5.406667 |
| temperature_30d | current | 12.320000 | 20.481667 | 21.333333 | 23.340000 | 30.373333 |
| temperature_30d | cumulative | 11.646843 | 20.109167 | 21.106667 | 22.572500 | 30.026667 |
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
