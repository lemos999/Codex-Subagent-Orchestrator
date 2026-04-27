# MTS-V1 Parity Report

> Historical Phase7 sample report. This is not the current Core5 release gate.
> Use `parity_reports/core5_parity.md` and `core5_parity_report.py --gate baseline`
> for the active TradingView/Python/Paper parity baseline.

- Status: PASS
- Pine CSV: `samples\phase7_pine_export.csv`
- Python JSONL: `samples\phase7_trades.jsonl`

| Metric | Value | Comparable | Threshold | Pass | Detail |
|---|---:|---:|---|:---:|---|
| entry_timing_match | 1.000000 | 2 | >= 0.85 | yes | +/-1 bar |
| winrate_delta_24h | 0.000000 | 2 | <= 0.05 | yes | absolute |
| avg_rr_delta | 0.000000 | 2 | <= 0.15 | yes | relative |
| cvd_sign_match | 1.000000 | 2 | >= 0.90 | yes | bar timestamp |
