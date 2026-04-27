# MTS-V1 Backtest Verdict

- Status: PASS
- Scope: 1 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 3/4
- Portfolio total R: 49.224747
- Portfolio avg R/trade: 0.313533
- Trade inputs: runs\mtsv1_improve_bnb_rsm25_nol3cap\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BNB/USDT:USDT | 2.105 | 1.707 | 0.101 | 157 | 0.316 | 2.686 | yes | pass |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 1.453 | 2.449 | 0.053 | 41 | 0.236 | 4.245 | yes |
| 2 | -1.220 | 0.572 | 0.100 | 35 | 0.142 | 1.654 | no |
| 3 | 1.703 | 2.221 | 0.054 | 36 | 0.345 | 2.221 | yes |
| 4 | 1.429 | 1.848 | 0.045 | 45 | 0.290 | 2.529 | yes |
