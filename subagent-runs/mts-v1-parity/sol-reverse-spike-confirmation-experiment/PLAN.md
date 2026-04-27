# Plan

## Backlog
- Current item: SOL reverse-spike confirmation/order-timing experiment.
- Later items: promote or reject the confirmation rule, then repeat the narrowed process on XRP.

## Selected Task
Add one replay-only confirmation control for reverse-spike State2 exits and test `2` consecutive LTF pulses on SOL.

## Rationale
- The `1.005` threshold-edge guard delayed the 4/20 early exit but did not align timing.
- The official Python artifact shows extra SOL cycles between the TV entry at `2026-04-20T10:45:00Z` and TV exit at `2026-04-21T12:30:00Z`.
- A one-bar confirmation probe can answer whether Python is reacting to isolated reverse-spike pulses too early without changing the accepted default.

## Implementation Intent
- Add `reverse_spike_confirm_bars` with default `1`.
- Support only `1` or `2` for now to keep the experiment narrow.
- Add previous-bar reverse-spike telemetry and residual report columns.
- Run SOL probe with `--reverse-spike-confirm-bars 2`.
- Do not promote unless SOL timing improves and BTC baseline remains protected.

## Verification
- Focused unit tests.
- SOL probe diff report.
- Default equivalence check for SOL.
- Core5 baseline gate.
- Full MTS-V1 tests plus ruff/py_compile.

## Rollback
- Revert the option and generated probe artifacts if default behavior changes or tests/gates fail.
