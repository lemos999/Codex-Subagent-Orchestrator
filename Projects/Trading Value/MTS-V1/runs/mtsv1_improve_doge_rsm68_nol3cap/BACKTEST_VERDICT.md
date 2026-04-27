# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 1 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 3/4
- Portfolio total R: 50.124392
- Portfolio avg R/trade: 0.533238
- Trade inputs: runs\mtsv1_improve_doge_rsm68_nol3cap\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| DOGE/USDT:USDT | 2.325 | 2.149 | 0.057 | 94 | 0.391 | 2.242 | no | trades < 100, avg RR < 2.5 |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 1.496 | 3.560 | 0.027 | 22 | 0.347 | 2.967 | yes |
| 2 | -0.369 | 0.804 | 0.069 | 26 | 0.194 | 1.519 | no |
| 3 | 1.730 | 2.558 | 0.028 | 26 | 0.355 | 2.192 | yes |
| 4 | 1.619 | 2.681 | 0.046 | 20 | 0.342 | 2.193 | yes |
