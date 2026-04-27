# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 1 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 0/4
- Portfolio total R: -16.836975
- Portfolio avg R/trade: -0.323788
- Trade inputs: runs\mtsv1_improve_doge_rsm64_hold10_nol3cap\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| DOGE/USDT:USDT | -2.907 | 0.393 | 0.200 | 52 | 0.282 | 0.580 | no | Sharpe < 1.0, PF < 1.3, MDD > 20%, trades < 100, Wilson <= BE, avg RR < 2.5 |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | -1.908 | 0.195 | 0.046 | 8 | 0.071 | 0.584 | no |
| 2 | -2.232 | 0.328 | 0.082 | 21 | 0.208 | 0.532 | no |
| 3 | -1.632 | 0.241 | 0.040 | 9 | 0.121 | 0.482 | no |
| 4 | -0.433 | 0.776 | 0.046 | 14 | 0.326 | 0.582 | no |
