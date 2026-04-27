# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 1 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 3/4
- Portfolio total R: 48.159486
- Portfolio avg R/trade: 0.491423
- Trade inputs: runs\mtsv1_improve_doge_rsm65_nol3cap\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| DOGE/USDT:USDT | 2.209 | 2.021 | 0.069 | 98 | 0.374 | 2.285 | no | trades < 100, avg RR < 2.5 |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 1.463 | 3.406 | 0.030 | 23 | 0.330 | 3.123 | yes |
| 2 | -0.457 | 0.779 | 0.083 | 28 | 0.179 | 1.644 | no |
| 3 | 1.730 | 2.558 | 0.028 | 26 | 0.355 | 2.192 | yes |
| 4 | 1.510 | 2.432 | 0.046 | 21 | 0.324 | 2.211 | yes |
