# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 3 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 2/4
- Portfolio total R: 159.059545
- Portfolio avg R/trade: 0.528437
- Trade inputs: runs\mtsv1_improve_core3_cvd30_rsm62\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BTC/USDT:USDT | 1.834 | 1.867 | 0.054 | 101 | 0.270 | 3.372 | yes | pass |
| BNB/USDT:USDT | 1.394 | 1.543 | 0.115 | 102 | 0.276 | 2.710 | yes | pass |
| XRP/USDT:USDT | 3.111 | 2.787 | 0.029 | 98 | 0.345 | 3.565 | no | trades < 100 |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 2.929 | 3.726 | 0.034 | 68 | 0.329 | 4.720 | yes |
| 2 | -0.245 | 0.918 | 0.121 | 73 | 0.185 | 2.433 | no |
| 3 | 2.814 | 2.979 | 0.062 | 70 | 0.372 | 3.154 | yes |
| 4 | 1.122 | 1.401 | 0.113 | 90 | 0.264 | 2.540 | no |
