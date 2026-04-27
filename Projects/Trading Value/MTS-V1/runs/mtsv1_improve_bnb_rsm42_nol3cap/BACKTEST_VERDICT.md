# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 1 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 1/4
- Portfolio total R: 39.919343
- Portfolio avg R/trade: 0.319355
- Trade inputs: runs\mtsv1_improve_bnb_rsm42_nol3cap\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BNB/USDT:USDT | 1.670 | 1.586 | 0.108 | 125 | 0.274 | 2.920 | yes | pass |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 1.671 | 2.953 | 0.033 | 31 | 0.237 | 4.675 | yes |
| 2 | -1.478 | 0.519 | 0.115 | 32 | 0.089 | 2.250 | no |
| 3 | 1.203 | 1.941 | 0.054 | 29 | 0.284 | 2.389 | no |
| 4 | 1.024 | 1.596 | 0.054 | 33 | 0.247 | 2.455 | no |
