# MTS-V1 Backtest Verdict

- Status: PASS
- Scope: 5 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 3/4
- Portfolio total R: 289.119159
- Portfolio avg R/trade: 0.541422
- Trade inputs: runs\mtsv1_improve_core5_symbol_rsm_best2_nol3cap\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BTC/USDT:USDT | 2.123 | 2.086 | 0.054 | 101 | 0.288 | 3.459 | yes | pass |
| ETH/USDT:USDT | 2.074 | 1.912 | 0.100 | 113 | 0.305 | 2.998 | yes | pass |
| SOL/USDT:USDT | 2.595 | 2.427 | 0.062 | 100 | 0.366 | 2.849 | yes | pass |
| XRP/USDT:USDT | 2.993 | 2.646 | 0.039 | 100 | 0.356 | 3.234 | yes | pass |
| BNB/USDT:USDT | 1.784 | 1.657 | 0.115 | 120 | 0.286 | 2.862 | yes | pass |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 3.862 | 3.599 | 0.074 | 121 | 0.369 | 4.319 | yes |
| 2 | -0.021 | 0.995 | 0.146 | 130 | 0.228 | 2.321 | no |
| 3 | 3.544 | 2.839 | 0.090 | 131 | 0.412 | 2.883 | yes |
| 4 | 2.032 | 1.626 | 0.147 | 152 | 0.308 | 2.635 | yes |
