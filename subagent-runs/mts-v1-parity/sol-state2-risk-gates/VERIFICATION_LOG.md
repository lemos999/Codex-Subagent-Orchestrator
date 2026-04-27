# Verification Log

## Commands

- Focused tests: `python -m pytest tests/test_risk_gate.py tests/test_mts_paper_runner.py tests/test_pine_static.py tests/test_cvd_input_parity_report.py tests/test_btc_parity_diff.py tests/test_offline_replay.py -q -p no:cacheprovider` -> `78 passed`.
- Full MTS-V1 tests: `python -m pytest tests -q -p no:cacheprovider` -> `160 passed`.
- Static check: targeted `ruff check` over replay, parity, risk gate, paper runner, and touched tests -> `All checks passed!`.
- Compile check: `python -m py_compile offline_replay.py strategy.py btc_parity_diff.py btc_parity_trace.py parity_check.py core5_parity_report.py cvd_input_parity_report.py risk_gate.py mts_paper_runner.py` -> passed.
- Core5 gate: `python core5_parity_report.py --runs-dir runs --samples-dir samples --report parity_reports/core5_parity.md --bar-seconds 900 --examples 32 --gate baseline` -> passed.
- Evidence self-check: `python subagent-runs/mts-v1-parity/sol-state2-risk-gates/verify_task.py` -> passed.

## Locked Baseline

- BTC entries: `64/64`.
- BTC exit timestamps: `64/64`.
- BTC exit price <=`0.15`: `62/64`.
- BTC exit price <=`1.0`: `64/64`.
- BTC SHA256: `BE6FDFE9CD6A853D7983B51DCDA4D61DA41EEFE546FF8FCEDB84114630AFB41D`.

## Review Decision

- `reverse_spike_min_ratio=1.5` is rejected and not promoted.
- Local risk gates are accepted as a paper/live safety prerequisite.
- Real live readiness remains blocked on exchange MMR sourcing and live daily PnL accounting.
