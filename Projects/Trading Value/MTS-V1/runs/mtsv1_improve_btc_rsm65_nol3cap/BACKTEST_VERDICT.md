# MTS-V1 Backtest Verdict

- Status: PASS
- Scope: 1 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 2/4
- Portfolio total R: 58.336208
- Portfolio avg R/trade: 0.583362
- Trade inputs: runs\mtsv1_improve_btc_rsm65_nol3cap\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BTC/USDT:USDT | 2.074 | 2.065 | 0.058 | 100 | 0.282 | 3.516 | yes | pass |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 2.197 | 7.256 | 0.014 | 20 | 0.299 | 7.256 | yes |
| 2 | 0.264 | 1.181 | 0.052 | 25 | 0.143 | 3.036 | no |
| 3 | 1.411 | 2.386 | 0.031 | 28 | 0.265 | 3.181 | yes |
| 4 | -0.055 | 0.970 | 0.070 | 27 | 0.159 | 2.304 | no |
