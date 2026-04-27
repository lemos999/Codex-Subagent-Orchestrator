# MTS-V1 Backtest Verdict

- Status: PASS
- Scope: 3 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 2/4
- Portfolio total R: 151.559547
- Portfolio avg R/trade: 0.476602
- Trade inputs: runs\mtsv1_directional_15m_rsm6_nol3cap_core3\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BTC/USDT:USDT | 1.955 | 1.901 | 0.057 | 107 | 0.305 | 2.943 | yes | pass |
| BNB/USDT:USDT | 1.427 | 1.533 | 0.126 | 108 | 0.285 | 2.606 | yes | pass |
| XRP/USDT:USDT | 2.846 | 2.481 | 0.039 | 103 | 0.336 | 3.327 | yes | pass |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 3.005 | 3.900 | 0.036 | 70 | 0.359 | 4.373 | yes |
| 2 | -0.761 | 0.798 | 0.140 | 76 | 0.188 | 2.090 | no |
| 3 | 2.637 | 2.601 | 0.060 | 79 | 0.362 | 2.953 | yes |
| 4 | 1.198 | 1.413 | 0.104 | 93 | 0.285 | 2.341 | no |
