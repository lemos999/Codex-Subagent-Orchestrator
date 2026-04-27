# MTS-V1 Backtest Verdict

- Status: PASS
- Scope: 1 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 3/4
- Portfolio total R: 48.502961
- Portfolio avg R/trade: 0.310916
- Trade inputs: runs\mtsv1_improve_bnb_rsm252_nol3cap\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BNB/USDT:USDT | 2.077 | 1.699 | 0.101 | 156 | 0.312 | 2.718 | yes | pass |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 1.453 | 2.449 | 0.053 | 41 | 0.236 | 4.245 | yes |
| 2 | -1.220 | 0.572 | 0.100 | 35 | 0.142 | 1.654 | no |
| 3 | 1.684 | 2.205 | 0.054 | 36 | 0.345 | 2.205 | yes |
| 4 | 1.392 | 1.834 | 0.045 | 44 | 0.277 | 2.649 | yes |
