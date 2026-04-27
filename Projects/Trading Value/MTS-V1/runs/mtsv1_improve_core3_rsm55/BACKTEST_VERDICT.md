# MTS-V1 Backtest Verdict

- Status: PASS
- Scope: 3 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 2/4
- Portfolio total R: 142.094447
- Portfolio avg R/trade: 0.421645
- Trade inputs: runs\mtsv1_improve_core3_rsm55\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BTC/USDT:USDT | 1.818 | 1.712 | 0.059 | 112 | 0.307 | 2.646 | yes | pass |
| BNB/USDT:USDT | 1.428 | 1.522 | 0.126 | 112 | 0.274 | 2.739 | yes | pass |
| XRP/USDT:USDT | 3.069 | 2.357 | 0.042 | 113 | 0.338 | 3.192 | yes | pass |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 3.006 | 3.418 | 0.040 | 77 | 0.360 | 3.893 | yes |
| 2 | -0.797 | 0.792 | 0.133 | 81 | 0.187 | 2.123 | no |
| 3 | 2.909 | 2.567 | 0.060 | 81 | 0.376 | 2.765 | yes |
| 4 | 1.062 | 1.348 | 0.097 | 98 | 0.269 | 2.426 | no |
