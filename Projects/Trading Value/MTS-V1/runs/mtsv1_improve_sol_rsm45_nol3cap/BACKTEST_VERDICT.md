# MTS-V1 Backtest Verdict

- Status: PASS
- Scope: 1 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 3/4
- Portfolio total R: 61.416745
- Portfolio avg R/trade: 0.543511
- Trade inputs: runs\mtsv1_improve_sol_rsm45_nol3cap\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| SOL/USDT:USDT | 2.550 | 2.260 | 0.069 | 113 | 0.363 | 2.748 | yes | pass |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 1.607 | 3.443 | 0.025 | 26 | 0.288 | 4.017 | yes |
| 2 | -0.752 | 0.714 | 0.087 | 26 | 0.194 | 1.348 | no |
| 3 | 2.039 | 3.197 | 0.032 | 30 | 0.361 | 2.798 | yes |
| 4 | 1.639 | 2.526 | 0.023 | 31 | 0.292 | 3.067 | yes |
