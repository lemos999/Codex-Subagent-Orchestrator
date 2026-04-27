# MTS-V1 Backtest Verdict

- Status: PASS
- Scope: 1 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 3/4
- Portfolio total R: 45.233373
- Portfolio avg R/trade: 0.282709
- Trade inputs: runs\mtsv1_improve_bnb_rsm24_nol3cap\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BNB/USDT:USDT | 1.944 | 1.637 | 0.100 | 160 | 0.310 | 2.656 | yes | pass |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 1.220 | 2.129 | 0.055 | 42 | 0.230 | 3.833 | yes |
| 2 | -1.042 | 0.613 | 0.095 | 35 | 0.142 | 1.772 | no |
| 3 | 1.545 | 2.021 | 0.055 | 38 | 0.325 | 2.246 | yes |
| 4 | 1.429 | 1.848 | 0.045 | 45 | 0.290 | 2.529 | yes |
