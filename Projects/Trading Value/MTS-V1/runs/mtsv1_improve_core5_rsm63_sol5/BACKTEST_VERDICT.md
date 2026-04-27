# MTS-V1 Backtest Verdict

- Status: PASS
- Scope: 5 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 3/4
- Portfolio total R: 269.434782
- Portfolio avg R/trade: 0.510293
- Trade inputs: runs\mtsv1_improve_core5_rsm63_sol5\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BTC/USDT:USDT | 2.123 | 2.086 | 0.054 | 101 | 0.288 | 3.459 | yes | pass |
| ETH/USDT:USDT | 1.764 | 1.710 | 0.117 | 118 | 0.299 | 2.774 | yes | pass |
| SOL/USDT:USDT | 2.567 | 2.350 | 0.064 | 105 | 0.365 | 2.790 | yes | pass |
| XRP/USDT:USDT | 2.993 | 2.646 | 0.039 | 100 | 0.356 | 3.234 | yes | pass |
| BNB/USDT:USDT | 1.399 | 1.538 | 0.129 | 104 | 0.288 | 2.563 | yes | pass |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 3.511 | 3.295 | 0.072 | 120 | 0.372 | 3.895 | yes |
| 2 | -0.222 | 0.946 | 0.149 | 130 | 0.221 | 2.291 | no |
| 3 | 3.756 | 3.094 | 0.088 | 126 | 0.429 | 2.904 | yes |
| 4 | 1.723 | 1.507 | 0.172 | 152 | 0.302 | 2.512 | yes |
