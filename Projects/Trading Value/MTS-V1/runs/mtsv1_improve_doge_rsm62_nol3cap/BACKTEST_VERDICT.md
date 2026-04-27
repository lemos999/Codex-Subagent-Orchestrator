# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 1 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 3/4
- Portfolio total R: 38.808960
- Portfolio avg R/trade: 0.384247
- Trade inputs: runs\mtsv1_improve_doge_rsm62_nol3cap\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| DOGE/USDT:USDT | 2.089 | 1.809 | 0.072 | 101 | 0.371 | 2.078 | no | avg RR < 2.5 |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 1.272 | 2.214 | 0.041 | 25 | 0.300 | 2.398 | yes |
| 2 | -0.422 | 0.792 | 0.080 | 28 | 0.179 | 1.673 | no |
| 3 | 1.744 | 2.486 | 0.028 | 27 | 0.373 | 1.989 | yes |
| 4 | 1.510 | 2.432 | 0.046 | 21 | 0.324 | 2.211 | yes |
