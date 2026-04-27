# MTS-V1 Backtest Verdict

- Status: PASS
- Scope: 1 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 2/4
- Portfolio total R: 46.549184
- Portfolio avg R/trade: 0.325519
- Trade inputs: runs\mtsv1_improve_bnb_rsm32_nol3cap\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BNB/USDT:USDT | 1.971 | 1.668 | 0.078 | 143 | 0.302 | 2.749 | yes | pass |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 1.563 | 2.542 | 0.052 | 39 | 0.249 | 4.067 | yes |
| 2 | -0.930 | 0.654 | 0.077 | 32 | 0.133 | 1.963 | no |
| 3 | 1.580 | 2.108 | 0.054 | 34 | 0.341 | 2.108 | yes |
| 4 | 0.916 | 1.518 | 0.055 | 38 | 0.234 | 2.602 | no |
