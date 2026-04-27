# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 1 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 0/4
- Portfolio total R: 19.747195
- Portfolio avg R/trade: 0.106168
- Trade inputs: runs\mtsv1_improve_bnb_rsm15_nol3cap\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BNB/USDT:USDT | 1.126 | 1.282 | 0.140 | 186 | 0.351 | 1.775 | no | PF < 1.3, Wilson <= BE, avg RR < 2.5 |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 0.652 | 1.300 | 0.031 | 50 | 0.294 | 1.796 | no |
| 2 | -2.148 | 0.440 | 0.105 | 40 | 0.201 | 0.913 | no |
| 3 | 1.120 | 1.653 | 0.070 | 46 | 0.322 | 1.967 | no |
| 4 | 1.235 | 1.682 | 0.047 | 50 | 0.330 | 1.975 | no |
