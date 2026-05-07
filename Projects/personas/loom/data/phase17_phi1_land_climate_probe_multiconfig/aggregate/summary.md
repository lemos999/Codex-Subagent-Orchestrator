# DC-1 Land-Climate aggregate distribution

> **Provenance**: ClimateEngine multi-config axis (NovaPlanet alt instance: nova_cool). paper §7-1 planet-variation evidence base.

- seeds: 7, 13, 42
- tolerance: ±10 percent

## 분위수 후보 (3-seed flattened, 8 metric × 2 window × 5 quantile)

| metric | window | P25 | P50 | P67 | P75 | P90 |
|---|---|---:|---:|---:|---:|---:|
| soil_moisture | current | 0.254167 | 0.291473 | 0.312785 | 0.324828 | 0.373244 |
| soil_moisture | cumulative | 0.196212 | 0.264583 | 0.300758 | 0.317037 | 0.375342 |
| fertility | current | 0.225000 | 0.283333 | 0.308730 | 0.321970 | 0.369526 |
| fertility | cumulative | 0.150000 | 0.256250 | 0.293750 | 0.312593 | 0.370320 |
| rainfall_30d | current | 12.675000 | 34.700000 | 41.900000 | 63.800000 | 159.230000 |
| rainfall_30d | cumulative | 11.500000 | 29.200000 | 40.100000 | 43.800000 | 160.500000 |
| temperature_30d | current | 6.327500 | 14.481667 | 15.333333 | 17.340000 | 24.373333 |
| temperature_30d | cumulative | 5.655051 | 14.109167 | 15.106667 | 16.572500 | 24.026667 |
| drought_days | current | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 3.000000 |
| drought_days | cumulative | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 3.000000 |
| depletion | current | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| depletion | cumulative | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| recovery_rate | current | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| recovery_rate | cumulative | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| hazard_damage | current | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 |
| hazard_damage | cumulative | 0.600000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 |

## Seed consistency (3-seed P50/P67/P75 ±tolerance boolean)

| metric | window | quantile | within_tolerance | mean | seed_7 | seed_13 | seed_42 |
|---|---|---|---:|---:|---:|---:|---:|
| soil_moisture | current | P50 | true | 0.290452 | 0.300000 | 0.288492 | 0.282864 |
| soil_moisture | current | P67 | true | 0.313609 | 0.319048 | 0.319697 | 0.302083 |
| soil_moisture | current | P75 | true | 0.323664 | 0.337500 | 0.326515 | 0.306977 |
| soil_moisture | cumulative | P50 | true | 0.266667 | 0.262500 | 0.262500 | 0.275000 |
| soil_moisture | cumulative | P67 | true | 0.301096 | 0.297778 | 0.306250 | 0.299259 |
| soil_moisture | cumulative | P75 | true | 0.316091 | 0.315873 | 0.321212 | 0.311187 |
| fertility | current | P50 | true | 0.281245 | 0.299531 | 0.267460 | 0.276744 |
| fertility | current | P67 | true | 0.308755 | 0.319048 | 0.310317 | 0.296899 |
| fertility | current | P75 | true | 0.321544 | 0.334921 | 0.326515 | 0.303196 |
| fertility | cumulative | P50 | true | 0.255741 | 0.255556 | 0.247222 | 0.264444 |
| fertility | cumulative | P67 | true | 0.294259 | 0.293750 | 0.297917 | 0.291111 |
| fertility | cumulative | P75 | true | 0.310464 | 0.309524 | 0.317424 | 0.304444 |
| rainfall_30d | current | P50 | false | 33.766667 | 29.250000 | 36.350000 | 35.700000 |
| rainfall_30d | current | P67 | true | 41.600000 | 40.200000 | 41.900000 | 42.700000 |
| rainfall_30d | current | P75 | true | 65.725000 | 65.425000 | 67.950000 | 63.800000 |
| rainfall_30d | cumulative | P50 | true | 29.066667 | 27.100000 | 29.000000 | 31.100000 |
| rainfall_30d | cumulative | P67 | true | 39.866667 | 38.100000 | 40.400000 | 41.100000 |
| rainfall_30d | cumulative | P75 | true | 43.366667 | 41.800000 | 43.600000 | 44.700000 |
| temperature_30d | current | P50 | true | 14.481667 | 14.481667 | 14.481667 | 14.481667 |
| temperature_30d | current | P67 | true | 15.333333 | 15.333333 | 15.333333 | 15.333333 |
| temperature_30d | current | P75 | true | 17.340000 | 17.340000 | 17.340000 | 17.340000 |
| temperature_30d | cumulative | P50 | true | 14.109167 | 14.109167 | 14.109167 | 14.109167 |
| temperature_30d | cumulative | P67 | true | 15.106667 | 15.106667 | 15.106667 | 15.106667 |
| temperature_30d | cumulative | P75 | true | 16.572500 | 16.572500 | 16.572500 | 16.572500 |
| drought_days | current | P50 | false | 0.333333 | 0.000000 | 1.000000 | 0.000000 |
| drought_days | current | P67 | true | 1.000000 | 1.000000 | 1.000000 | 1.000000 |
| drought_days | current | P75 | false | 1.333333 | 1.000000 | 2.000000 | 1.000000 |
| drought_days | cumulative | P50 | true | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| drought_days | cumulative | P67 | true | 1.000000 | 1.000000 | 1.000000 | 1.000000 |
| drought_days | cumulative | P75 | true | 1.000000 | 1.000000 | 1.000000 | 1.000000 |
| depletion | current | P50 | true | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| depletion | current | P67 | true | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| depletion | current | P75 | true | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| depletion | cumulative | P50 | true | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| depletion | cumulative | P67 | true | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| depletion | cumulative | P75 | true | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| recovery_rate | current | P50 | true | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| recovery_rate | current | P67 | true | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| recovery_rate | current | P75 | true | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| recovery_rate | cumulative | P50 | true | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| recovery_rate | cumulative | P67 | true | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| recovery_rate | cumulative | P75 | true | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| hazard_damage | current | P50 | true | 1.000000 | 1.000000 | 1.000000 | 1.000000 |
| hazard_damage | current | P67 | true | 1.000000 | 1.000000 | 1.000000 | 1.000000 |
| hazard_damage | current | P75 | true | 1.000000 | 1.000000 | 1.000000 | 1.000000 |
| hazard_damage | cumulative | P50 | true | 0.988889 | 0.966667 | 1.000000 | 1.000000 |
| hazard_damage | cumulative | P67 | true | 1.000000 | 1.000000 | 1.000000 | 1.000000 |
| hazard_damage | cumulative | P75 | true | 1.000000 | 1.000000 | 1.000000 | 1.000000 |

## 주의

This extractor only derives quantile candidates. It does not freeze any analytic threshold and does not change mechanism code. Threshold freeze is reserved for §7-2 after this raw analysis is complete.
