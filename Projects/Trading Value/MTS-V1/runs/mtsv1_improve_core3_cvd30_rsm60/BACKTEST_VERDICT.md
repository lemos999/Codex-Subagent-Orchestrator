# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 3 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 2/4
- Portfolio total R: 154.716847
- Portfolio avg R/trade: 0.500702
- Trade inputs: runs\mtsv1_improve_core3_cvd30_rsm60\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BTC/USDT:USDT | 1.733 | 1.745 | 0.058 | 106 | 0.291 | 2.878 | yes | pass |
| BNB/USDT:USDT | 1.419 | 1.542 | 0.113 | 105 | 0.276 | 2.718 | yes | pass |
| XRP/USDT:USDT | 3.111 | 2.787 | 0.029 | 98 | 0.345 | 3.565 | no | trades < 100 |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 2.965 | 3.746 | 0.036 | 70 | 0.346 | 4.448 | yes |
| 2 | -0.549 | 0.846 | 0.125 | 74 | 0.194 | 2.134 | no |
| 3 | 2.621 | 2.598 | 0.063 | 75 | 0.358 | 2.969 | yes |
| 4 | 1.187 | 1.430 | 0.105 | 90 | 0.274 | 2.470 | no |
