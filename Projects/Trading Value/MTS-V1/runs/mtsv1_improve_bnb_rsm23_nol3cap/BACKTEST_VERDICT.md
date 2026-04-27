# MTS-V1 Backtest Verdict

- Status: PASS
- Scope: 1 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 3/4
- Portfolio total R: 40.493306
- Portfolio avg R/trade: 0.251511
- Trade inputs: runs\mtsv1_improve_bnb_rsm23_nol3cap\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BNB/USDT:USDT | 1.805 | 1.577 | 0.120 | 161 | 0.313 | 2.518 | yes | pass |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 1.088 | 1.942 | 0.055 | 42 | 0.230 | 3.495 | yes |
| 2 | -1.676 | 0.464 | 0.100 | 36 | 0.158 | 1.207 | no |
| 3 | 1.594 | 2.079 | 0.055 | 38 | 0.325 | 2.310 | yes |
| 4 | 1.490 | 1.908 | 0.040 | 45 | 0.290 | 2.611 | yes |
