# MTS-V1 Backtest Verdict

- Status: PASS
- Scope: 3 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 2/4
- Portfolio total R: 160.230318
- Portfolio avg R/trade: 0.525345
- Trade inputs: runs\mtsv1_improve_core3_rsm63\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BTC/USDT:USDT | 2.123 | 2.086 | 0.054 | 101 | 0.288 | 3.459 | yes | pass |
| BNB/USDT:USDT | 1.399 | 1.538 | 0.129 | 104 | 0.288 | 2.563 | yes | pass |
| XRP/USDT:USDT | 2.993 | 2.646 | 0.039 | 100 | 0.356 | 3.234 | yes | pass |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 2.953 | 3.863 | 0.034 | 68 | 0.343 | 4.611 | yes |
| 2 | -0.337 | 0.893 | 0.133 | 74 | 0.182 | 2.411 | no |
| 3 | 2.836 | 2.978 | 0.059 | 74 | 0.376 | 3.143 | yes |
| 4 | 1.338 | 1.481 | 0.113 | 89 | 0.298 | 2.285 | no |
