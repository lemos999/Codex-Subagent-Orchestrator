# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 1 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 3/4
- Portfolio total R: 70.095629
- Portfolio avg R/trade: 0.737849
- Trade inputs: runs\mtsv1_improve_sol_rsm60_nol3cap\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| SOL/USDT:USDT | 2.877 | 2.780 | 0.036 | 95 | 0.386 | 2.962 | no | trades < 100 |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 2.119 | 5.399 | 0.020 | 23 | 0.292 | 5.890 | yes |
| 2 | -0.297 | 0.855 | 0.044 | 19 | 0.191 | 1.466 | no |
| 3 | 1.915 | 2.967 | 0.026 | 27 | 0.407 | 2.040 | yes |
| 4 | 1.497 | 2.488 | 0.024 | 26 | 0.288 | 2.903 | yes |
