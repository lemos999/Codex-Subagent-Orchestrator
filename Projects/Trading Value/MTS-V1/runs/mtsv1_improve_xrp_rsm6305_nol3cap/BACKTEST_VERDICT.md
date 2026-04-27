# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 1 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 3/4
- Portfolio total R: 66.380347
- Portfolio avg R/trade: 0.670509
- Trade inputs: runs\mtsv1_improve_xrp_rsm6305_nol3cap\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| XRP/USDT:USDT | 3.006 | 2.668 | 0.039 | 99 | 0.360 | 3.201 | no | trades < 100 |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 2.131 | 4.271 | 0.029 | 21 | 0.324 | 3.882 | yes |
| 2 | -0.007 | 0.996 | 0.046 | 22 | 0.197 | 1.743 | no |
| 3 | 1.774 | 3.630 | 0.025 | 26 | 0.288 | 4.235 | yes |
| 4 | 1.848 | 2.691 | 0.019 | 30 | 0.302 | 3.075 | yes |
