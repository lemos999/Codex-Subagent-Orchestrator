# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 1 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 2/4
- Portfolio total R: 35.978831
- Portfolio avg R/trade: 0.210403
- Trade inputs: runs\mtsv1_improve_bnb_rsm20_nol3cap\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BNB/USDT:USDT | 1.630 | 1.504 | 0.120 | 171 | 0.327 | 2.279 | no | avg RR < 2.5 |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 1.335 | 2.252 | 0.037 | 44 | 0.257 | 3.577 | yes |
| 2 | -1.748 | 0.454 | 0.104 | 37 | 0.154 | 1.226 | no |
| 3 | 1.320 | 1.818 | 0.069 | 42 | 0.334 | 2.000 | yes |
| 4 | 1.182 | 1.661 | 0.044 | 48 | 0.307 | 2.136 | no |
