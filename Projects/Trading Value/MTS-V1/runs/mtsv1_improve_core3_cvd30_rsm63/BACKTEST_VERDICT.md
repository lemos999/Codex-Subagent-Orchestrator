# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 3 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 2/4
- Portfolio total R: 161.642252
- Portfolio avg R/trade: 0.544250
- Trade inputs: runs\mtsv1_improve_core3_cvd30_rsm63\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BTC/USDT:USDT | 1.858 | 1.885 | 0.054 | 100 | 0.273 | 3.351 | yes | pass |
| BNB/USDT:USDT | 1.389 | 1.548 | 0.118 | 101 | 0.279 | 2.677 | yes | pass |
| XRP/USDT:USDT | 3.227 | 2.948 | 0.029 | 96 | 0.352 | 3.633 | no | trades < 100 |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 2.869 | 3.669 | 0.034 | 68 | 0.329 | 4.648 | yes |
| 2 | -0.158 | 0.946 | 0.119 | 72 | 0.188 | 2.460 | no |
| 3 | 2.814 | 2.979 | 0.062 | 70 | 0.372 | 3.154 | yes |
| 4 | 1.282 | 1.481 | 0.113 | 87 | 0.274 | 2.546 | no |
