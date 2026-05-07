# DC-1 Land-Climate aggregate distribution

> **Provenance**: ClimateEngine normalized axis (precipitation_mm / 30.0). NOT raw or synthetic. paper §7-1 unit-normalized evidence base.

- seeds: 7, 13, 42
- tolerance: ±10 percent

## 분위수 후보 (3-seed flattened, 8 metric × 2 window × 5 quantile)

| metric | window | P25 | P50 | P67 | P75 | P90 |
|---|---|---:|---:|---:|---:|---:|
| soil_moisture | current | 0.254167 | 0.291473 | 0.312785 | 0.324828 | 0.373244 |
| soil_moisture | cumulative | 0.196212 | 0.264583 | 0.300758 | 0.317037 | 0.375342 |
| fertility | current | 0.225000 | 0.283333 | 0.308730 | 0.321970 | 0.369526 |
| fertility | cumulative | 0.150000 | 0.256250 | 0.293750 | 0.312593 | 0.370320 |
| rainfall_30d | current | 0.422500 | 1.156667 | 1.396667 | 2.126667 | 5.307667 |
| rainfall_30d | cumulative | 0.383333 | 0.973333 | 1.336667 | 1.460000 | 5.350000 |
| temperature_30d | current | 12.320000 | 20.481667 | 21.333333 | 23.340000 | 30.373333 |
| temperature_30d | cumulative | 11.646843 | 20.109167 | 21.106667 | 22.572500 | 30.026667 |
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
| rainfall_30d | current | P50 | false | 1.125556 | 0.975000 | 1.211667 | 1.190000 |
| rainfall_30d | current | P67 | true | 1.386667 | 1.340000 | 1.396667 | 1.423333 |
| rainfall_30d | current | P75 | true | 2.190833 | 2.180833 | 2.265000 | 2.126667 |
| rainfall_30d | cumulative | P50 | true | 0.968889 | 0.903333 | 0.966667 | 1.036667 |
| rainfall_30d | cumulative | P67 | true | 1.328889 | 1.270000 | 1.346667 | 1.370000 |
| rainfall_30d | cumulative | P75 | true | 1.445556 | 1.393333 | 1.453333 | 1.490000 |
| temperature_30d | current | P50 | true | 20.481667 | 20.481667 | 20.481667 | 20.481667 |
| temperature_30d | current | P67 | true | 21.333333 | 21.333333 | 21.333333 | 21.333333 |
| temperature_30d | current | P75 | true | 23.340000 | 23.340000 | 23.340000 | 23.340000 |
| temperature_30d | cumulative | P50 | true | 20.109167 | 20.109167 | 20.109167 | 20.109167 |
| temperature_30d | cumulative | P67 | true | 21.106667 | 21.106667 | 21.106667 | 21.106667 |
| temperature_30d | cumulative | P75 | true | 22.572500 | 22.572500 | 22.572500 | 22.572500 |
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
