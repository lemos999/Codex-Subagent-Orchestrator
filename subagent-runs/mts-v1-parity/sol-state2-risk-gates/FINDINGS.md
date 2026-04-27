# Findings

## SOL Timing Candidate
- Probe: `reverse_spike_min_ratio=1.5`.
- Output artifact: `Projects/Trading Value/MTS-V1/runs/mtsv1_tv_sol_15m_binanceusdm_profile/trades_minratio_1500_probe.jsonl`.
- Diff report: `Projects/Trading Value/MTS-V1/parity_reports/sol_diff_minratio_1500.md`.
- Result: rejected.

Compared with the official SOL artifact:
- Entry matches regressed from `40/69` to `35/71`.
- Exit timestamp matches were `26/35`, not a strict improvement.
- Exit price `<=0.15` regressed from `33/40` to `29/35`.
- Missing Python cycles increased, so this does not explain SOL parity safely.

## Risk Gate Implementation
- Added `risk_gate.py` with:
  - MMR leverage cap formula: `floor(1 / (0.20 + 0.01 + mmr))`, capped by configured user leverage.
  - Daily max-loss fail-closed decision at `daily_pnl_pct <= -daily_max_loss_pct`.
  - Structured payload for paper/live promotion checks.
- Added MTS paper runner strict mode:
  - `--require-risk-ready`
  - `--daily-pnl-pct`
  - strict mode blocks before replay when risk gate fails.
- Added Pine effective leverage cap to `f_qty_at_price()` using symbol-specific MMR inputs.

## CLI Evidence
- Missing MMR strict probe blocked before replay:
  - `events=0`, `exits=0`, `blocked=true`, failure `BTC/USDT:USDT: missing maintenance margin rate`.
- Daily max-loss strict probe with fixture MMR blocked before replay:
  - `events=0`, `exits=0`, `blocked=true`, failure `daily max-loss reached: -5.0000% <= -5.0000%`.

## Promotion Decision
- Do not promote `reverse_spike_min_ratio=1.5`.
- Promote local risk gate implementation as a paper/live safety prerequisite.
- Live-readiness is still not granted because direct exchange MMR wiring and live daily PnL accounting remain external production checks.
