# MTS-V1 Backtest Verdict

- Status: PASS
- Scope: 3 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 2/4
- Portfolio total R: 157.036849
- Portfolio avg R/trade: 0.506570
- Trade inputs: runs\mtsv1_improve_core3_rsm62\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BTC/USDT:USDT | 2.099 | 2.065 | 0.054 | 102 | 0.285 | 3.477 | yes | pass |
| BNB/USDT:USDT | 1.404 | 1.533 | 0.128 | 105 | 0.285 | 2.595 | yes | pass |
| XRP/USDT:USDT | 2.846 | 2.481 | 0.039 | 103 | 0.336 | 3.327 | yes | pass |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 3.013 | 3.922 | 0.034 | 68 | 0.343 | 4.682 | yes |
| 2 | -0.426 | 0.867 | 0.135 | 75 | 0.180 | 2.386 | no |
| 3 | 2.836 | 2.978 | 0.059 | 74 | 0.376 | 3.143 | yes |
| 4 | 1.124 | 1.382 | 0.113 | 93 | 0.275 | 2.397 | no |
