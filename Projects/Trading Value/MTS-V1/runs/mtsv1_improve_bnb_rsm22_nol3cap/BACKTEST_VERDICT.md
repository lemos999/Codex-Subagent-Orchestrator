# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 1 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 2/4
- Portfolio total R: 41.503160
- Portfolio avg R/trade: 0.254621
- Trade inputs: runs\mtsv1_improve_bnb_rsm22_nol3cap\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BNB/USDT:USDT | 1.863 | 1.604 | 0.121 | 163 | 0.321 | 2.481 | no | avg RR < 2.5 |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 1.358 | 2.264 | 0.047 | 43 | 0.244 | 3.820 | yes |
| 2 | -1.760 | 0.452 | 0.105 | 37 | 0.154 | 1.220 | no |
| 3 | 1.655 | 2.156 | 0.055 | 38 | 0.325 | 2.396 | yes |
| 4 | 1.270 | 1.746 | 0.040 | 45 | 0.309 | 2.183 | no |
