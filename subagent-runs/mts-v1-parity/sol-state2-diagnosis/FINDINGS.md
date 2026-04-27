# SOL STATE_2_ABORT Timing Diagnosis Findings

## Scope
- Task: `mts-v1-sol-state2-diagnosis`
- Scope kept diagnostic-only.
- No replay semantic files were changed:
  - `offline_replay.py`: unchanged
  - `strategy.py`: unchanged
  - `strategy.pine`: unchanged
- `samples/` and `runs/` artifacts were not overwritten.
- The worktree was already dirty before this task. This task applied patches only to diagnostic/report/test/evidence files, not to `offline_replay.py`, `strategy.py`, or `strategy.pine`.

## Verification Evidence
- `py_compile btc_parity_diff.py core5_parity_report.py`: passed via `uv run --no-project`.
- `py_compile btc_parity_diff.py btc_parity_trace.py core5_parity_report.py`: passed after trace common-window alignment.
- Import-level diagnostic assertion for `matched_exit_timing_bucket`: passed.
- `core5_parity_report.py --gate baseline`: passed.
- `parity_reports/sol_diff_entry15.md` now reports raw rows, common-window rows, before/tail rows outside Python artifact coverage, and common-window match rate directly in the detail report.
- `parity_reports/sol_trace_entry15.md` now reports raw rows, common-window rows, before/tail rows outside Python artifact coverage, and common-window match rate directly in the trace report.
- Dependency-free task self-check passed:
  - `uv run --no-project python ..\..\..\subagent-runs\mts-v1-parity\sol-state2-diagnosis\verify_task.py`
- Remaining external dependency condition resolved with local `uv` cache paths:
  - `run_cached_checks.ps1` wires cached `pytest` dependencies into `PYTHONPATH` and uses the cached `ruff.exe`.
  - Focused pytest passed: `26 passed in 0.18s`.
  - Targeted ruff passed: `All checks passed!`.
  - The same script also reruns `py_compile`, Core5 `--gate baseline`, and `verify_task.py`.

## BTC Baseline Confirmation
From regenerated `parity_reports/core5_parity.md`:

- Entry matches: `64/64`
- Exit timestamp matches: `64/64`
- Exit price <= `0.15`: `62/64`
- Exit price <= `1.0`: `64/64`
- SHA256: `BE6FDFE9CD6A853D7983B51DCDA4D61DA41EEFE546FF8FCEDB84114630AFB41D`
- Gate: `pass`

## SOL Current Common-Window Metrics
From regenerated `parity_reports/core5_parity.md`:

- TV rows: `71`
- Common TV rows: `69`
- TV tail outside Python artifact: `2`
- Entry matches: `40/69`
- Exit timestamp matches: `27/40`
- Exit price <= `0.15`: `33/40`
- Exit price <= `1.0`: `40/40`
- Gate: `pass`
- SOL diff and trace reports now both use common-window denominator for matched TV row summaries.

## SOL Matched Exit Timing Residuals
New diagnostics in `parity_reports/sol_diff_entry15.md` report:

- Timing buckets: `{'python_exit_early': 7, 'python_exit_late': 6}`
- Cause buckets: `{'entry_cycle_drift': 1, 'non_state2_abort': 6, 'same_bar_close_or_fill_ordering': 2, 'unknown_state2_abort': 4}`

The State 2 abort residual subset is entirely early on the Python side:

- `unknown_state2_abort`: 4 rows
  - trade `65`: `-1305.0m`
  - trade `64`: `-1305.0m`
  - trade `56`: `-390.0m`
  - trade `57`: `-390.0m`
- `same_bar_close_or_fill_ordering`: 2 rows
  - trade `30`: `-60.0m`
  - trade `69`: `-30.0m`
- `entry_cycle_drift`: 1 row
  - trade `29`: `-60.0m`

The non-State2 timing residuals are all `HARD_SL` late rows and are not the first SOL semantic target for this task.

## Data Limitation
The current Python JSONL events record `reason: STATE_2_ABORT`, but do not record whether the abort was caused by:

- HTF cross pulse
- reverse spike pulse
- both

Because of that, the diagnostic can separate `STATE_2_ABORT` early-vs-late behavior and same-bar/order candidates, but it cannot truthfully attribute the largest unknown rows to HTF cross or reverse spike without additional telemetry.

## Recommended Next Task
Exactly one next task:

**SOL STATE_2_ABORT trigger-source telemetry/reconstruction.**

Rationale:
- All SOL `STATE_2_ABORT` matched exit-timing residuals are Python-early.
- The largest residuals are not same-bar effects; they are long early exits (`-1305m`, `-390m`) with no trigger-source telemetry.
- Same-bar close/fill ordering explains only `2/7` State2 residual rows.
- Entry-cycle drift explains only `1/7` State2 residual rows.
- Therefore the next task should expose or reconstruct whether each SOL State2 abort came from HTF cross, reverse spike, or both. Only after that should one replay trigger pulse rule be changed.

Do not start with ETH/BNB, and do not change multiple replay rules in the next task.
