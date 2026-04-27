# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 5 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 3/4
- Portfolio total R: 271.924867
- Portfolio avg R/trade: 0.526986
- Trade inputs: runs\mtsv1_improve_core5_rsm63\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BTC/USDT:USDT | 2.123 | 2.086 | 0.054 | 101 | 0.288 | 3.459 | yes | pass |
| ETH/USDT:USDT | 1.764 | 1.710 | 0.117 | 118 | 0.299 | 2.774 | yes | pass |
| SOL/USDT:USDT | 2.707 | 2.702 | 0.037 | 93 | 0.375 | 3.009 | no | trades < 100 |
| XRP/USDT:USDT | 2.993 | 2.646 | 0.039 | 100 | 0.356 | 3.234 | yes | pass |
| BNB/USDT:USDT | 1.399 | 1.538 | 0.129 | 104 | 0.288 | 2.563 | yes | pass |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 3.512 | 3.338 | 0.072 | 118 | 0.362 | 4.094 | yes |
| 2 | -0.037 | 0.991 | 0.151 | 127 | 0.226 | 2.321 | no |
| 3 | 3.752 | 3.197 | 0.086 | 122 | 0.429 | 2.994 | yes |
| 4 | 1.702 | 1.504 | 0.172 | 149 | 0.308 | 2.428 | yes |
