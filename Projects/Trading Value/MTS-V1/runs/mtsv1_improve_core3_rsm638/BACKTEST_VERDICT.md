# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 3 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 2/4
- Portfolio total R: 159.325080
- Portfolio avg R/trade: 0.524096
- Trade inputs: runs\mtsv1_improve_core3_rsm638\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BTC/USDT:USDT | 2.123 | 2.086 | 0.054 | 101 | 0.288 | 3.459 | yes | pass |
| BNB/USDT:USDT | 1.399 | 1.538 | 0.129 | 104 | 0.288 | 2.563 | yes | pass |
| XRP/USDT:USDT | 3.001 | 2.664 | 0.039 | 99 | 0.360 | 3.197 | no | trades < 100 |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 2.949 | 3.859 | 0.034 | 68 | 0.343 | 4.606 | yes |
| 2 | -0.337 | 0.893 | 0.133 | 74 | 0.182 | 2.411 | no |
| 3 | 2.836 | 2.978 | 0.059 | 74 | 0.376 | 3.143 | yes |
| 4 | 1.330 | 1.474 | 0.113 | 88 | 0.302 | 2.233 | no |
