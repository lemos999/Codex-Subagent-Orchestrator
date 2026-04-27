# MTS-V1 Backtest Verdict

- Status: PASS
- Scope: 5 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 3/4
- Portfolio total R: 281.311428
- Portfolio avg R/trade: 0.524835
- Trade inputs: runs\mtsv1_improve_core5_symbol_rsm_best_nol3cap\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BTC/USDT:USDT | 2.123 | 2.086 | 0.054 | 101 | 0.288 | 3.459 | yes | pass |
| ETH/USDT:USDT | 1.986 | 1.871 | 0.100 | 112 | 0.299 | 3.002 | yes | pass |
| SOL/USDT:USDT | 2.567 | 2.350 | 0.064 | 105 | 0.365 | 2.790 | yes | pass |
| XRP/USDT:USDT | 2.993 | 2.646 | 0.039 | 100 | 0.356 | 3.234 | yes | pass |
| BNB/USDT:USDT | 1.618 | 1.558 | 0.119 | 118 | 0.283 | 2.718 | yes | pass |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 3.765 | 3.449 | 0.074 | 122 | 0.373 | 4.065 | yes |
| 2 | -0.069 | 0.983 | 0.146 | 130 | 0.221 | 2.379 | no |
| 3 | 3.546 | 2.837 | 0.089 | 130 | 0.415 | 2.837 | yes |
| 4 | 1.947 | 1.587 | 0.158 | 154 | 0.304 | 2.627 | yes |
