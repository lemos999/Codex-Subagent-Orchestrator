# DC-1 Land-Climate aggregate distribution

> **Provenance**: synthetic smoke collector (random walk). NOT actual `ClimateEngine` output. Suitable as smoke evidence only. §7-2 evidence requires real-collector reproduction.

- seeds: 7, 13, 42
- tolerance: ±10 percent

## 분위수 후보 (3-seed flattened, 8 metric × 2 window × 5 quantile)

| metric | window | P25 | P50 | P67 | P75 | P90 |
|---|---|---:|---:|---:|---:|---:|
| soil_moisture | current | 0.107387 | 0.197051 | 0.255536 | 0.284374 | 0.349893 |
| soil_moisture | cumulative | 0.107387 | 0.197051 | 0.255536 | 0.284374 | 0.349893 |
| fertility | current | 0.079885 | 0.178680 | 0.243464 | 0.274183 | 0.343859 |
| fertility | cumulative | 0.079885 | 0.178680 | 0.243464 | 0.274183 | 0.343859 |
| rainfall_30d | current | 2.691725 | 5.400435 | 7.170748 | 8.030985 | 10.013221 |
| rainfall_30d | cumulative | 2.691725 | 5.400435 | 7.170748 | 8.030985 | 10.013221 |
| temperature_30d | current | 19.778574 | 19.984630 | 20.121202 | 20.200620 | 20.417636 |
| temperature_30d | cumulative | 19.778574 | 19.984630 | 20.121202 | 20.200620 | 20.417636 |
| drought_days | current | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 |
| drought_days | cumulative | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 |
| depletion | current | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| depletion | cumulative | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| recovery_rate | current | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| recovery_rate | cumulative | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| hazard_damage | current | 0.066667 | 0.166667 | 0.266667 | 0.300000 | 0.433333 |
| hazard_damage | cumulative | 0.066667 | 0.166667 | 0.266667 | 0.300000 | 0.433333 |

## Seed consistency (3-seed P50/P67/P75 ±tolerance boolean)

| metric | window | quantile | within_tolerance | mean | seed_7 | seed_13 | seed_42 |
|---|---|---|---:|---:|---:|---:|---:|
| soil_moisture | current | P50 | true | 0.197010 | 0.202301 | 0.195021 | 0.193709 |
| soil_moisture | current | P67 | true | 0.255462 | 0.263224 | 0.250910 | 0.252254 |
| soil_moisture | current | P75 | true | 0.284413 | 0.291707 | 0.280415 | 0.281115 |
| soil_moisture | cumulative | P50 | true | 0.197010 | 0.202301 | 0.195021 | 0.193709 |
| soil_moisture | cumulative | P67 | true | 0.255462 | 0.263224 | 0.250910 | 0.252254 |
| soil_moisture | cumulative | P75 | true | 0.284413 | 0.291707 | 0.280415 | 0.281115 |
| fertility | current | P50 | true | 0.178225 | 0.182512 | 0.173547 | 0.178617 |
| fertility | current | P67 | true | 0.243367 | 0.249001 | 0.237648 | 0.243450 |
| fertility | current | P75 | true | 0.273626 | 0.280658 | 0.268232 | 0.271987 |
| fertility | cumulative | P50 | true | 0.178225 | 0.182512 | 0.173547 | 0.178617 |
| fertility | cumulative | P67 | true | 0.243367 | 0.249001 | 0.237648 | 0.243450 |
| fertility | cumulative | P75 | true | 0.273626 | 0.280658 | 0.268232 | 0.271987 |
| rainfall_30d | current | P50 | true | 5.397492 | 5.523445 | 5.331056 | 5.337976 |
| rainfall_30d | current | P67 | true | 7.177744 | 7.360511 | 7.060618 | 7.112104 |
| rainfall_30d | current | P75 | true | 8.016319 | 8.205393 | 7.913962 | 7.929601 |
| rainfall_30d | cumulative | P50 | true | 5.397492 | 5.523445 | 5.331056 | 5.337976 |
| rainfall_30d | cumulative | P67 | true | 7.177744 | 7.360511 | 7.060618 | 7.112104 |
| rainfall_30d | cumulative | P75 | true | 8.016319 | 8.205393 | 7.913962 | 7.929601 |
| temperature_30d | current | P50 | true | 19.983785 | 19.967379 | 19.976401 | 20.007574 |
| temperature_30d | current | P67 | true | 20.120596 | 20.115370 | 20.118770 | 20.127648 |
| temperature_30d | current | P75 | true | 20.200119 | 20.193727 | 20.206466 | 20.200164 |
| temperature_30d | cumulative | P50 | true | 19.983785 | 19.967379 | 19.976401 | 20.007574 |
| temperature_30d | cumulative | P67 | true | 20.120596 | 20.115370 | 20.118770 | 20.127648 |
| temperature_30d | cumulative | P75 | true | 20.200119 | 20.193727 | 20.206466 | 20.200164 |
| drought_days | current | P50 | true | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| drought_days | current | P67 | true | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| drought_days | current | P75 | true | 1.000000 | 1.000000 | 1.000000 | 1.000000 |
| drought_days | cumulative | P50 | true | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| drought_days | cumulative | P67 | true | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
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
| hazard_damage | current | P50 | false | 0.177778 | 0.166667 | 0.200000 | 0.166667 |
| hazard_damage | current | P67 | true | 0.244444 | 0.233333 | 0.266667 | 0.233333 |
| hazard_damage | current | P75 | true | 0.300000 | 0.300000 | 0.300000 | 0.300000 |
| hazard_damage | cumulative | P50 | false | 0.177778 | 0.166667 | 0.200000 | 0.166667 |
| hazard_damage | cumulative | P67 | true | 0.244444 | 0.233333 | 0.266667 | 0.233333 |
| hazard_damage | cumulative | P75 | true | 0.300000 | 0.300000 | 0.300000 | 0.300000 |

## 주의

This extractor only derives quantile candidates. It does not freeze any analytic threshold and does not change mechanism code. Threshold freeze is reserved for §7-2 after this raw analysis is complete.
