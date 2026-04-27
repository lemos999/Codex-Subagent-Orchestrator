# Verification Log

## Commands

- Focused tests: `python -m pytest tests/test_offline_replay.py tests/test_btc_parity_diff.py tests/test_cvd_input_parity_report.py -q -p no:cacheprovider` -> `63 passed`.
- SOL probe 60m: `offline_replay.py ... --state2-reverse-min-minutes-since-l2 60` -> `241` events / `62` exits.
- SOL diff 60m: `btc_parity_diff.py --symbol SOL ... --report parity_reports/sol_diff_l2hold60.md` -> generated report with entry `40/71`, exit timestamp `26/40`.
- SOL probe 300m: `offline_replay.py ... --state2-reverse-min-minutes-since-l2 300` -> `223` events / `57` exits.
- SOL diff 300m: `btc_parity_diff.py --symbol SOL ... --report parity_reports/sol_diff_l2hold300.md` -> generated report with entry `39/71`, exit timestamp `27/39`.
- Full MTS-V1 tests: `python -m pytest tests -q -p no:cacheprovider` -> `162 passed`.
- Static check: `ruff check offline_replay.py tests/test_offline_replay.py` -> `All checks passed!`.
- Compile check: `python -m py_compile offline_replay.py btc_parity_diff.py cvd_input_parity_report.py` -> passed.
- Core5 gate: `python core5_parity_report.py --runs-dir runs --samples-dir samples --report parity_reports/core5_parity.md --bar-seconds 900 --examples 32 --gate baseline` -> passed.

## Locked BTC Baseline

- Entries: `64/64`.
- Exit timestamps: `64/64`.
- Exit price <=`0.15`: `62/64`.
- Exit price <=`1.0`: `64/64`.
- SHA256: `BE6FDFE9CD6A853D7983B51DCDA4D61DA41EEFE546FF8FCEDB84114630AFB41D`.
