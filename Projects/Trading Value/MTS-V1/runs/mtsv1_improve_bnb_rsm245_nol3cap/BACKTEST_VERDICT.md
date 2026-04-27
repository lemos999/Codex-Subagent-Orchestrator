# MTS-V1 Backtest Verdict

- Status: PASS
- Scope: 1 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 3/4
- Portfolio total R: 46.977961
- Portfolio avg R/trade: 0.299223
- Trade inputs: runs\mtsv1_improve_bnb_rsm245_nol3cap\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BNB/USDT:USDT | 2.026 | 1.679 | 0.099 | 157 | 0.316 | 2.643 | yes | pass |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 1.285 | 2.262 | 0.054 | 41 | 0.236 | 3.921 | yes |
| 2 | -1.149 | 0.588 | 0.095 | 35 | 0.142 | 1.700 | no |
| 3 | 1.703 | 2.221 | 0.054 | 36 | 0.345 | 2.221 | yes |
| 4 | 1.429 | 1.848 | 0.045 | 45 | 0.290 | 2.529 | yes |
