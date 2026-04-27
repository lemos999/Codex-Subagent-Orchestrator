# MTS-V1 Backtest Verdict

- Status: PASS
- Scope: 1 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 2/4
- Portfolio total R: 40.199550
- Portfolio avg R/trade: 0.337811
- Trade inputs: runs\mtsv1_improve_bnb_rsm49_nol3cap\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BNB/USDT:USDT | 1.735 | 1.609 | 0.118 | 119 | 0.288 | 2.743 | yes | pass |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 1.516 | 2.535 | 0.039 | 30 | 0.246 | 3.802 | yes |
| 2 | -1.241 | 0.544 | 0.120 | 30 | 0.095 | 2.178 | no |
| 3 | 1.493 | 2.284 | 0.053 | 26 | 0.321 | 2.284 | yes |
| 4 | 0.954 | 1.539 | 0.060 | 33 | 0.247 | 2.368 | no |
