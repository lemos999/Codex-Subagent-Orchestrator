# MTS-V1 Backtest Verdict

- Status: PASS
- Scope: 1 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 2/4
- Portfolio total R: 47.096310
- Portfolio avg R/trade: 0.309844
- Trade inputs: runs\mtsv1_improve_bnb_rsm27_nol3cap\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BNB/USDT:USDT | 2.019 | 1.681 | 0.102 | 152 | 0.290 | 2.965 | yes | pass |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 1.425 | 2.390 | 0.053 | 41 | 0.236 | 4.142 | yes |
| 2 | -1.025 | 0.632 | 0.100 | 35 | 0.142 | 1.826 | no |
| 3 | 1.654 | 2.202 | 0.054 | 35 | 0.330 | 2.332 | yes |
| 4 | 1.232 | 1.741 | 0.058 | 41 | 0.216 | 3.358 | no |
