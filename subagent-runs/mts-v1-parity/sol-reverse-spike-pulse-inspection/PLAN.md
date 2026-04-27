# Plan

## Remaining Task
SOL reverse-spike pulse parity inspection.

## Success Criteria
- Add diagnostic-only reverse-spike pulse telemetry to State2 exits.
- Keep `reason: STATE_2_ABORT` and replay semantics unchanged.
- Show CVD delta, threshold, ratio, and margin for matched exit timing residuals.
- Regenerate SOL artifact/report only after semantic equivalence check.
- Keep BTC baseline SHA and Core5 gate intact.

## Implementation Path
1. Extend Python replay indicators with reverse-spike abs-SMA, threshold, multiplier, ratio, and margin.
2. Persist the values under `state2_*` fields on State2 exit rows.
3. Parse and render those fields in the diff residual table.
4. Regenerate SOL probe, compare old/new artifacts with `state2_*` stripped, then promote SOL artifact.
5. Regenerate Core5 reports and record evidence.
