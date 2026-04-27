# MTS-V1 Backtest Verdict

- Status: PASS
- Scope: 1 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 2/4
- Portfolio total R: 42.952767
- Portfolio avg R/trade: 0.357940
- Trade inputs: runs\mtsv1_improve_bnb_rsm47_nol3cap\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BNB/USDT:USDT | 1.800 | 1.651 | 0.115 | 120 | 0.286 | 2.851 | yes | pass |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 1.587 | 2.717 | 0.039 | 30 | 0.246 | 4.076 | yes |
| 2 | -1.241 | 0.544 | 0.120 | 30 | 0.095 | 2.178 | no |
| 3 | 1.450 | 2.208 | 0.053 | 27 | 0.307 | 2.378 | yes |
| 4 | 1.024 | 1.596 | 0.054 | 33 | 0.247 | 2.455 | no |
