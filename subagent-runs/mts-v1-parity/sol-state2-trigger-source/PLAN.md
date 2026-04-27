# Plan

## Remaining Task
SOL `STATE_2_ABORT` trigger-source telemetry/reconstruction.

## Success Criteria
- Python JSONL keeps `reason: STATE_2_ABORT` unchanged.
- State2 exits expose `state2_trigger_source`, `state2_reverse_spike`, and `state2_htf_cross`.
- SOL diff/trace reports show trigger-source split for matched State2 exits.
- SOL replay output is semantically unchanged after removing telemetry-only `state2_*` fields.
- BTC Core5 baseline and SHA remain unchanged.
- No live-ready claim is added.

## Implementation Path
1. Add telemetry fields at the `offline_replay.py` exit row boundary.
2. Parse telemetry in `btc_parity_diff.py`.
3. Render State2 trigger-source summaries in diff and trace reports.
4. Regenerate SOL artifact/report only, then rerun Core5 baseline gate.
5. Record evidence and next task.
