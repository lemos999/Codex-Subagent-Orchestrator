# MTS-V1 Backtest Verdict

- Status: PASS
- Scope: 5 symbols x 90d x entry_tf=15m
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 3/4
- Portfolio total R: 296.054456
- Portfolio avg R/trade: 0.518484
- Trade inputs: runs\mtsv1_improve_core5_symbol_rsm_best5_nol3cap\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BTC/USDT:USDT | 2.123 | 2.086 | 0.054 | 101 | 0.288 | 3.459 | yes | pass |
| ETH/USDT:USDT | 2.074 | 1.912 | 0.100 | 113 | 0.305 | 2.998 | yes | pass |
| SOL/USDT:USDT | 2.595 | 2.427 | 0.062 | 100 | 0.366 | 2.849 | yes | pass |
| XRP/USDT:USDT | 2.993 | 2.646 | 0.039 | 100 | 0.356 | 3.234 | yes | pass |
| BNB/USDT:USDT | 2.105 | 1.707 | 0.101 | 157 | 0.316 | 2.686 | yes | pass |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 3.768 | 3.472 | 0.071 | 132 | 0.358 | 4.430 | yes |
| 2 | 0.015 | 1.004 | 0.137 | 135 | 0.239 | 2.223 | no |
| 3 | 3.702 | 2.839 | 0.090 | 140 | 0.418 | 2.839 | yes |
| 4 | 2.227 | 1.682 | 0.152 | 164 | 0.319 | 2.628 | yes |
