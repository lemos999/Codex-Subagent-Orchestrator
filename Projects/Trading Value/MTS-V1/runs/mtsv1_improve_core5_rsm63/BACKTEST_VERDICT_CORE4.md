# MTS-V1 Backtest Verdict

- Status: PASS
- Scope: 4 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 2/4
- Portfolio total R: 206.727879
- Portfolio avg R/trade: 0.488718
- Trade inputs: runs\mtsv1_improve_core5_rsm63\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BTC/USDT:USDT | 2.123 | 2.086 | 0.054 | 101 | 0.288 | 3.459 | yes | pass |
| ETH/USDT:USDT | 1.764 | 1.710 | 0.117 | 118 | 0.299 | 2.774 | yes | pass |
| XRP/USDT:USDT | 2.993 | 2.646 | 0.039 | 100 | 0.356 | 3.234 | yes | pass |
| BNB/USDT:USDT | 1.399 | 1.538 | 0.129 | 104 | 0.288 | 2.563 | yes | pass |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 2.934 | 3.031 | 0.074 | 95 | 0.356 | 3.666 | yes |
| 2 | 0.051 | 1.014 | 0.142 | 108 | 0.210 | 2.519 | no |
| 3 | 3.248 | 3.143 | 0.086 | 97 | 0.397 | 3.208 | yes |
| 4 | 1.353 | 1.423 | 0.153 | 123 | 0.286 | 2.467 | no |
