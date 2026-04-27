# Findings

## Implemented Diagnostic

- Added `offline_replay.py --state2-reverse-min-minutes-since-l2`.
- Default is `0.0`; accepted profile behavior is unchanged.
- Added unit coverage that recent-L2 reverse-only signals are suppressed while HTF-cross signals still trigger.
- Added metadata fields:
  - `state2_reverse_spike_effective`
  - `state2_reverse_l2_hold_blocked`
  - `state2_reverse_min_minutes_since_l2`

## Probe Results

Official SOL baseline:

- Entry matches: `40/69`.
- Exit timestamp matches: `27/40`.
- Exit price <=`0.15`: `33/40`.
- Exit price <=`1.0`: `40/40`.

`60` minute L2 hold:

- Artifact: `Projects/Trading Value/MTS-V1/runs/mtsv1_tv_sol_15m_binanceusdm_profile/trades_l2hold60_probe.jsonl`.
- Report: `Projects/Trading Value/MTS-V1/parity_reports/sol_diff_l2hold60.md`.
- Replay: `241` events / `62` exits.
- Entry matches: `40/71`.
- Exit timestamp matches: `26/40`.
- Exit price <=`0.15`: `34/40`.

`300` minute L2 hold:

- Artifact: `Projects/Trading Value/MTS-V1/runs/mtsv1_tv_sol_15m_binanceusdm_profile/trades_l2hold300_probe.jsonl`.
- Report: `Projects/Trading Value/MTS-V1/parity_reports/sol_diff_l2hold300.md`.
- Replay: `223` events / `57` exits.
- Entry matches: `39/71`.
- Exit timestamp matches: `27/39`.
- Exit price <=`0.15`: `37/39`.

## Decision

Reject both L2-hold candidates. The longer hold improves price residuals, but cycle and entry alignment regress, so it is not a safe semantic parity fix.

## Next Candidate Direction

The next SOL priority should inspect entry-cycle/order-state drift and direct TradingView CVD plot-value evidence for isolated pulse bars. Another L2 hold window is not the recommended next move.
