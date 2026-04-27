# MTS-V1 Backtest Verdict

- Status: PASS
- Scope: 1 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 2/4
- Portfolio total R: 43.825690
- Portfolio avg R/trade: 0.332013
- Trade inputs: runs\mtsv1_improve_bnb_rsm36_nol3cap\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BNB/USDT:USDT | 1.901 | 1.670 | 0.085 | 132 | 0.301 | 2.738 | yes | pass |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 1.584 | 2.675 | 0.052 | 34 | 0.239 | 4.321 | yes |
| 2 | -1.051 | 0.620 | 0.085 | 32 | 0.110 | 2.215 | no |
| 3 | 1.476 | 2.124 | 0.054 | 31 | 0.348 | 1.992 | yes |
| 4 | 0.989 | 1.549 | 0.054 | 35 | 0.256 | 2.324 | no |
