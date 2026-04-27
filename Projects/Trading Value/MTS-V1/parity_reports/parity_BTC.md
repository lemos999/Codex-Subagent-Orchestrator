# MTS-V1 Parity Report

- Status: FAIL
- Symbol: `BTC`
- Pine CSV: `Projects\Trading Value\MTS-V1\samples\tradingview_mtsv1_BTC.csv`
- Python JSONL: `Projects\Trading Value\MTS-V1\runs\mtsv1_improve_core5_symbol_rsm_best5_nol3cap\trades.jsonl`

| Metric | Value | Comparable | Threshold | Pass | Detail |
|---|---:|---:|---|:---:|---|
| entry_timing_match | 0.032967 | 273 | >= 0.85 | no | +/-1 bar |
| winrate_delta_24h | 1.000000 | 16 | <= 0.05 | no | absolute |
| avg_rr_delta | 1007.141266 | 31 | <= 0.15 | no | relative |
| cvd_sign_match | 0.000000 | 0 | >= 0.90 | no | bar timestamp |

## Failure Candidates
- Entry timing: Pine bar-close vs Python execution timestamp alignment.
- Win/RR delta: fee, funding, partial-fill, or rounding differences.
- CVD sign: Pine proxy vs Python tick-stream source mismatch.
