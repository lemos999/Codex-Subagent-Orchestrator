# MTS-V1 Backtest Verdict

- Status: PASS
- Scope: 1 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 2/4
- Portfolio total R: 44.285358
- Portfolio avg R/trade: 0.289447
- Trade inputs: runs\mtsv1_improve_bnb_rsm255_nol3cap\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BNB/USDT:USDT | 1.912 | 1.641 | 0.102 | 153 | 0.294 | 2.842 | yes | pass |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 1.425 | 2.390 | 0.053 | 41 | 0.236 | 4.142 | yes |
| 2 | -1.220 | 0.572 | 0.100 | 35 | 0.142 | 1.654 | no |
| 3 | 1.684 | 2.205 | 0.054 | 36 | 0.345 | 2.205 | yes |
| 4 | 1.078 | 1.642 | 0.058 | 41 | 0.216 | 3.167 | no |
