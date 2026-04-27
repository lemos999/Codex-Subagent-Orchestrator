# MTS-V1 Backtest Verdict

- Status: PASS
- Scope: 1 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 2/4
- Portfolio total R: 43.169466
- Portfolio avg R/trade: 0.353848
- Trade inputs: runs\mtsv1_improve_bnb_rsm44_nol3cap\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BNB/USDT:USDT | 1.816 | 1.665 | 0.108 | 122 | 0.281 | 2.951 | yes | pass |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 1.671 | 2.953 | 0.033 | 31 | 0.237 | 4.675 | yes |
| 2 | -1.098 | 0.595 | 0.115 | 31 | 0.092 | 2.478 | no |
| 3 | 1.336 | 2.138 | 0.054 | 27 | 0.307 | 2.302 | yes |
| 4 | 1.024 | 1.596 | 0.054 | 33 | 0.247 | 2.455 | no |
