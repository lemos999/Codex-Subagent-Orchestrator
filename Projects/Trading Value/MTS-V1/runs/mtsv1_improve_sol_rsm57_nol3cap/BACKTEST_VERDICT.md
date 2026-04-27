# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 1 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 3/4
- Portfolio total R: 69.266366
- Portfolio avg R/trade: 0.706800
- Trade inputs: runs\mtsv1_improve_sol_rsm57_nol3cap\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| SOL/USDT:USDT | 2.818 | 2.675 | 0.040 | 98 | 0.383 | 2.903 | no | trades < 100 |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 2.045 | 4.910 | 0.020 | 24 | 0.279 | 5.803 | yes |
| 2 | -0.424 | 0.810 | 0.049 | 21 | 0.208 | 1.316 | no |
| 3 | 1.920 | 2.928 | 0.031 | 27 | 0.407 | 2.013 | yes |
| 4 | 1.497 | 2.488 | 0.024 | 26 | 0.288 | 2.903 | yes |
