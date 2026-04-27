# MTS-V1 Backtest Verdict

- Status: PASS
- Scope: 1 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 2/4
- Portfolio total R: 44.319054
- Portfolio avg R/trade: 0.297443
- Trade inputs: runs\mtsv1_improve_bnb_rsm28_nol3cap\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BNB/USDT:USDT | 1.915 | 1.641 | 0.101 | 149 | 0.290 | 2.886 | yes | pass |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 1.435 | 2.412 | 0.052 | 40 | 0.221 | 4.480 | yes |
| 2 | -1.025 | 0.632 | 0.100 | 35 | 0.142 | 1.826 | no |
| 3 | 1.627 | 2.166 | 0.054 | 35 | 0.330 | 2.293 | yes |
| 4 | 1.021 | 1.591 | 0.058 | 39 | 0.227 | 2.841 | no |
