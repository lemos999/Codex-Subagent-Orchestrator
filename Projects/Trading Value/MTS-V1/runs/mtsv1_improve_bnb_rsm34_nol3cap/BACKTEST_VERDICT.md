# MTS-V1 Backtest Verdict

- Status: PASS
- Scope: 1 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 2/4
- Portfolio total R: 44.262247
- Portfolio avg R/trade: 0.325458
- Trade inputs: runs\mtsv1_improve_bnb_rsm34_nol3cap\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BNB/USDT:USDT | 1.923 | 1.668 | 0.077 | 136 | 0.305 | 2.694 | yes | pass |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 1.621 | 2.685 | 0.052 | 36 | 0.248 | 4.219 | yes |
| 2 | -0.910 | 0.661 | 0.076 | 32 | 0.133 | 1.984 | no |
| 3 | 1.476 | 2.124 | 0.054 | 31 | 0.348 | 1.992 | yes |
| 4 | 0.866 | 1.459 | 0.055 | 37 | 0.241 | 2.397 | no |
