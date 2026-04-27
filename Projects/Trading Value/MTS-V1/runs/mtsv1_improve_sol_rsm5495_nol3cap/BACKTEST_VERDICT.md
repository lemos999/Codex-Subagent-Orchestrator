# MTS-V1 Backtest Verdict

- Status: PASS
- Scope: 1 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 3/4
- Portfolio total R: 62.817652
- Portfolio avg R/trade: 0.628177
- Trade inputs: runs\mtsv1_improve_sol_rsm5495_nol3cap\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| SOL/USDT:USDT | 2.595 | 2.427 | 0.062 | 100 | 0.366 | 2.849 | yes | pass |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 1.976 | 4.659 | 0.020 | 24 | 0.279 | 5.506 | yes |
| 2 | -0.967 | 0.618 | 0.078 | 21 | 0.172 | 1.236 | no |
| 3 | 1.889 | 2.840 | 0.031 | 28 | 0.391 | 2.130 | yes |
| 4 | 1.382 | 2.273 | 0.024 | 27 | 0.276 | 2.842 | yes |
