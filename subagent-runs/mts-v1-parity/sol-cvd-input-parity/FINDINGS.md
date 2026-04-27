# Findings

## Scope
- Added `cvd_input_parity_report.py`.
- Added focused coverage in `tests/test_cvd_input_parity_report.py`.
- Generated `Projects/Trading Value/MTS-V1/parity_reports/sol_cvd_input_parity.md`.
- No replay rule, accepted profile, or official artifact was changed.

## Diagnostic Result
- SOL reverse-spike exit-timing residuals inspected: `7`.
- `4` residuals also have a Python-formula reverse-spike pulse at the TradingView exit bar.
- `3` residuals are isolated Python pulses with no pulse at the TradingView exit bar.

## Interpretation
- CVD input mismatch alone does not explain all SOL reverse-spike timing drift.
- The `64/65` and `56/57` residual pairs still show Python-formula pulses at the later TradingView exits, so delaying or filtering early pulses by threshold/confirmation is insufficient.
- The next semantic candidate should inspect State2/order calculation pass timing around reverse-spike evaluation and fill recognition.

## External Evidence Gap
- TradingView Strategy Report CSV does not export `delta_bar`, `cvd_abs_sma_20`, or reverse-spike plot values.
- Direct TradingView CVD plot export remains external evidence if exact TV plot-value parity is required.

## Verification
- Focused tests: `61 passed`.
- Full MTS-V1 tests: `154 passed`.
- Ruff: passed.
- `py_compile`: passed.
- Core5 baseline gate: passed.
- BTC SHA remained `BE6FDFE9CD6A853D7983B51DCDA4D61DA41EEFE546FF8FCEDB84114630AFB41D`.
