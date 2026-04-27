# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 1 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 1/4
- Portfolio total R: 42.761768
- Portfolio avg R/trade: 0.339379
- Trade inputs: runs\mtsv1_improve_bnb_rsm40_nol3cap\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BNB/USDT:USDT | 1.827 | 1.650 | 0.103 | 126 | 0.286 | 2.869 | yes | pass |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 1.771 | 3.224 | 0.033 | 31 | 0.264 | 4.464 | yes |
| 2 | -1.354 | 0.545 | 0.110 | 32 | 0.089 | 2.364 | no |
| 3 | 1.284 | 1.951 | 0.054 | 30 | 0.302 | 2.230 | no |
| 4 | 1.049 | 1.618 | 0.054 | 33 | 0.247 | 2.489 | no |
