# /plan: MTS-V1 SOL STATE_2_ABORT Timing Diagnosis

## Task
Diagnose SOL `STATE_2_ABORT` timing residuals without changing replay semantics. The output must identify the most likely first semantic fix candidate for the next task.

## Current Baseline
- Core5 baseline gate passes.
- BTC locked baseline:
  - Entry matches: `64/64`
  - Exit timestamp matches: `64/64`
  - Exit price <= `0.15`: `62/64`
  - Exit price <= `1.0`: `64/64`
  - SHA256: `BE6FDFE9CD6A853D7983B51DCDA4D61DA41EEFE546FF8FCEDB84114630AFB41D`
- SOL common-window state from the latest report:
  - Entry matches: `40/69`
  - Exit timestamp matches: `27/40`
  - Exit price <= `1.0`: `40/40`
  - TV tail outside Python artifact: `2`

## Proposed Work
1. Add matched-exit timing diagnostics to the existing diff report.
   - Keep existing sections intact.
   - Add a `Matched Exit Timing Residuals` section focused on matched rows whose Python exit timestamp differs from TV beyond tolerance.
   - Row selection is `symbol == SOL`, common TV/Python coverage, matched rows only. Outside-artifact tail rows stay in unmatched/coverage reporting and are not semantic timing residuals.
   - Include trade number, entry event, side, TV entry/exit, Python entry/exit, signed exit delta minutes, Python exit reason, Python entry reason, a coarse timing bucket, and a candidate cause bucket.

2. Add a small classifier for matched exit timing buckets.
   - `python_exit_early_state2_abort`
   - `python_exit_late_state2_abort`
   - `python_exit_early_other`
   - `python_exit_late_other`
   - `missing_python_exit`
   - `missing_tv_exit`
   - `matched_within_tolerance`

3. Add candidate cause buckets for `STATE_2_ABORT`.
   - `htf_cross_pulse`
   - `reverse_spike_pulse`
   - `same_bar_close_or_fill_ordering`
   - `entry_cycle_drift`
   - `unknown_state2_abort`
   - The classifier must stay evidence-based. If existing JSONL fields do not expose the exact abort trigger, use conservative buckets and record the data limitation in `FINDINGS.md`.

4. Add tests for the classifier and report section.
   - Use synthetic `STATE_2_ABORT` early/late examples.
   - Avoid modifying replay or strategy behavior.

5. Regenerate Core5 reports with the baseline gate.
   - Use generated SOL report to identify the first fix candidate.
   - Record findings in `FINDINGS.md` under this task evidence directory.
   - Candidate selection must include residual count, representative trade numbers, signed delta distribution, cause bucket share, and BTC metric/SHA confirmation.

## Validation
Run:

```powershell
# cwd: Projects/Trading Value/MTS-V1
uv run --no-project --with pytest --with pandas --with pyyaml python -m pytest tests/test_core5_parity_report.py tests/test_btc_parity_diff.py tests/test_btc_parity_trace.py -q -p no:cacheprovider
uv run --no-project python core5_parity_report.py --runs-dir runs --samples-dir samples --report parity_reports/core5_parity.md --bar-seconds 900 --examples 32 --gate baseline
uv run --no-project --with ruff ruff check btc_parity_diff.py core5_parity_report.py tests/test_btc_parity_diff.py tests/test_core5_parity_report.py
uv run --no-project python -m py_compile btc_parity_diff.py core5_parity_report.py
```

If `uv` cannot use its default cache under sandbox constraints, rerun with a workspace-local cache:

```powershell
$env:UV_CACHE_DIR = ".uv-cache"; uv run --no-project ...
```

## Acceptance
- BTC metrics and SHA remain unchanged.
- Baseline gate passes.
- SOL report contains timing residual buckets that isolate `STATE_2_ABORT` early/late behavior.
- `FINDINGS.md` names exactly one recommended replay-rule candidate for the next task with quantitative evidence.

## Non-Goals
- No semantic replay fix in this task.
- No ETH/BNB expansion.
- No live-ready claim.
