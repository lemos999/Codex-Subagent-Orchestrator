# Findings

## Scope
- Added State2 trigger-source telemetry to Python replay JSONL.
- Updated diff and trace reports to display State2 trigger source.
- Regenerated the SOL exact artifact and Core5 reports.
- Did not change replay semantics, `strategy.py`, or BTC artifact.

## SOL Result
- SOL matched Python `STATE_2_ABORT` exits: `24`.
- Trigger-source split:
  - `reverse_spike`: `20`, with `13` exit timestamp matches and `7` Python-early residuals.
  - `htf_cross`: `4`, with `4` exit timestamp matches and `0` early/late residuals.
- All SOL State2 matched exit-timing residuals are therefore `reverse_spike`, not HTF cross.
- The four formerly `unknown_state2_abort` long residual rows are now `state2_reverse_spike`.
- Same-bar/order candidates remain separate: `2` reverse-spike rows.
- Entry-cycle drift remains separate: `1` reverse-spike row.

## Semantic Equivalence
- Probe SOL artifact and previous SOL artifact were compared after removing all `state2_*` telemetry fields.
- Result: `old_rows=254 new_rows=254 stripped_equal=True`.

## Gate Evidence
- Core5 baseline gate passed.
- Focused tests passed: `72 passed`.
- Full MTS-V1 tests passed: `147 passed`.
- Targeted ruff and `py_compile` passed.
- BTC baseline remains unchanged:
  - entries `64/64`
  - exit timestamps `64/64`
  - exit price <= `0.15`: `62/64`
  - exit price <= `1.0`: `64/64`
  - SHA256 `BE6FDFE9CD6A853D7983B51DCDA4D61DA41EEFE546FF8FCEDB84114630AFB41D`
- SOL artifact SHA changed to `29477E417024C8D115C77FF80EBCC3B74180763687F17AC770BF642E263B198F` because telemetry fields were added.

## Recommended Next Task
SOL reverse-spike pulse parity inspection.

Rationale:
- The State2 timing residuals are all reverse-spike sourced.
- HTF cross State2 rows are already matched on exit timestamp in the matched subset.
- The next semantic fix candidate should compare Python vs TradingView reverse-spike pulse timing and same-bar close ordering for the seven reverse-spike residual rows only.

No ETH/BNB expansion and no live-ready claim.
