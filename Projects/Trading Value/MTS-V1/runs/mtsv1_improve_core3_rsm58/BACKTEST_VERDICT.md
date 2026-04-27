# MTS-V1 Backtest Verdict

- Status: PASS
- Scope: 3 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 2/4
- Portfolio total R: 142.173508
- Portfolio avg R/trade: 0.434781
- Trade inputs: runs\mtsv1_improve_core3_rsm58\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BTC/USDT:USDT | 1.813 | 1.721 | 0.060 | 110 | 0.313 | 2.581 | yes | pass |
| BNB/USDT:USDT | 1.353 | 1.490 | 0.127 | 111 | 0.277 | 2.645 | yes | pass |
| XRP/USDT:USDT | 3.187 | 2.547 | 0.032 | 106 | 0.352 | 3.197 | yes | pass |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 2.973 | 3.591 | 0.040 | 72 | 0.361 | 4.013 | yes |
| 2 | -0.663 | 0.823 | 0.133 | 79 | 0.203 | 2.003 | no |
| 3 | 2.880 | 2.554 | 0.061 | 80 | 0.381 | 2.685 | yes |
| 4 | 1.098 | 1.363 | 0.104 | 96 | 0.275 | 2.376 | no |
