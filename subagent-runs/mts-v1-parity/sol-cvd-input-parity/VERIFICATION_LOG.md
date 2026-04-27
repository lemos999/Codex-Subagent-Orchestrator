# Verification Log

## Parent Local Verification

- Focused tests:
  - Command: `python -m pytest tests/test_cvd_input_parity_report.py tests/test_btc_parity_diff.py tests/test_offline_replay.py -q -p no:cacheprovider`
  - Result: `61 passed`
- Full MTS-V1 tests:
  - Command: `python -m pytest tests -q -p no:cacheprovider`
  - Result: `154 passed`
- Ruff:
  - Command: `ruff check offline_replay.py strategy.py btc_parity_diff.py btc_parity_trace.py parity_check.py core5_parity_report.py cvd_input_parity_report.py tests/test_btc_parity_diff.py tests/test_btc_parity_trace.py tests/test_core5_parity_report.py tests/test_offline_replay.py tests/test_cvd_input_parity_report.py`
  - Result: `All checks passed!`
- Python compile:
  - Command: `python -m py_compile offline_replay.py strategy.py btc_parity_diff.py btc_parity_trace.py parity_check.py core5_parity_report.py cvd_input_parity_report.py`
  - Result: passed
- Core5 baseline gate:
  - Command: `python core5_parity_report.py --runs-dir runs --samples-dir samples --report parity_reports/core5_parity.md --bar-seconds 900 --examples 32 --gate baseline`
  - Result: passed
- Evidence self-check:
  - Command: `python subagent-runs/mts-v1-parity/sol-cvd-input-parity/verify_task.py`
  - Result: `sol-cvd-input-parity self-check passed`

## BTC Baseline

- SHA256: `BE6FDFE9CD6A853D7983B51DCDA4D61DA41EEFE546FF8FCEDB84114630AFB41D`
- Entry matches: `64 / 64`
- Exit timestamp matches: `64 / 64`
- Exit price `<=0.15`: `62 / 64`
- Exit price `<=1.0`: `64 / 64`
- Average exit delta: `0.0420`
- Max exit delta: `0.1794`

## Parallel Agent Cross-Check

- Goal/scope reviewer: PASS for Core5 gate foundation, SOL reverse-spike diagnostics/experiments, and latest SOL CVD input diagnostic. Noted no live-ready overclaim.
- Test/gate reviewer: independently reproduced focused tests, full tests, Ruff, `py_compile`, Core5 baseline gate, and BTC baseline metrics.
- Evidence/artifact reviewer: confirmed the CVD report counts are internally consistent: `7` residuals split into `4` `python_formula_pulses_at_tv_exit` and `3` `isolated_python_pulse_no_tv_exit_pulse`.

## Follow-Up Fixes From Review

- Added stale notices to historical `parity_report.md` and `parity_summary.md` so they cannot be mistaken for the current Core5 release gate.
- Added this verification log to preserve the latest test/gate outputs in the evidence bundle.
- Added `subagent-runs/mts-v1-parity/core5-gate-foundation-validation/` to close the dedicated Core5 evidence-bundle gap found by the scope reviewer.
