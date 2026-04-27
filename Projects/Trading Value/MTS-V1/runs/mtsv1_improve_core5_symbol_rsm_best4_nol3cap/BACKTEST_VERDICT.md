# MTS-V1 Backtest Verdict

- Status: PASS
- Scope: 5 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 3/4
- Portfolio total R: 290.655399
- Portfolio avg R/trade: 0.532336
- Trade inputs: runs\mtsv1_improve_core5_symbol_rsm_best4_nol3cap\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BTC/USDT:USDT | 2.123 | 2.086 | 0.054 | 101 | 0.288 | 3.459 | yes | pass |
| ETH/USDT:USDT | 2.074 | 1.912 | 0.100 | 113 | 0.305 | 2.998 | yes | pass |
| SOL/USDT:USDT | 2.595 | 2.427 | 0.062 | 100 | 0.366 | 2.849 | yes | pass |
| XRP/USDT:USDT | 2.993 | 2.646 | 0.039 | 100 | 0.356 | 3.234 | yes | pass |
| BNB/USDT:USDT | 1.901 | 1.670 | 0.085 | 132 | 0.301 | 2.738 | yes | pass |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 3.833 | 3.535 | 0.074 | 125 | 0.364 | 4.355 | yes |
| 2 | 0.069 | 1.018 | 0.141 | 132 | 0.231 | 2.340 | no |
| 3 | 3.606 | 2.823 | 0.090 | 135 | 0.420 | 2.782 | yes |
| 4 | 2.016 | 1.616 | 0.147 | 154 | 0.310 | 2.602 | yes |
