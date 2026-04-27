# Plan

## Goal
Add a deterministic local diagnostic for the remaining SOL reverse-spike timing mismatch by reconstructing the Python OHLCV-derived CVD inputs around matched SOL `STATE_2_ABORT` reverse-spike residuals.

## Selected Backlog Item
`SOL CVD input parity around isolated reverse-spike pulse bars`.

## Constraints
- Do not change accepted replay semantics.
- Do not regenerate BTC artifacts.
- Keep BTC Core5 baseline locked.
- Treat TradingView Strategy Report CSV as trade-only; it does not expose `delta_bar` or `cvd_abs_sma_20`.
- No live-ready claim.

## Implementation
- Add a focused `cvd_input_parity_report.py` diagnostic script.
- Reuse existing TV/Python matching from `btc_parity_diff.py`.
- Reuse replay cache loading and indicator formulas from `offline_replay.py` / `strategy.py`.
- Generate `parity_reports/sol_cvd_input_parity.md`.
- Add focused tests for bar-level CVD metric reconstruction and residual selection.

## Verification
- Focused pytest for the new diagnostic and existing parity diff/replay tests.
- Full MTS-V1 pytest.
- Ruff and `py_compile` on touched files.
- Core5 baseline gate.
- Evidence self-check.

## Rollback
The change is additive. Remove the new diagnostic script, test file, generated report, and evidence files to restore the previous behavior.
