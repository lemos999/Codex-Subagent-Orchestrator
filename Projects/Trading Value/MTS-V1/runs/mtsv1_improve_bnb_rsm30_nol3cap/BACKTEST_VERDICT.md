# MTS-V1 Backtest Verdict

- Status: PASS
- Scope: 1 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 2/4
- Portfolio total R: 46.363854
- Portfolio avg R/trade: 0.315400
- Trade inputs: runs\mtsv1_improve_bnb_rsm30_nol3cap\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BNB/USDT:USDT | 1.973 | 1.670 | 0.093 | 147 | 0.300 | 2.794 | yes | pass |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 1.479 | 2.429 | 0.052 | 41 | 0.236 | 4.210 | yes |
| 2 | -0.929 | 0.659 | 0.092 | 33 | 0.151 | 1.758 | no |
| 3 | 1.628 | 2.174 | 0.054 | 34 | 0.341 | 2.174 | yes |
| 4 | 0.960 | 1.543 | 0.055 | 39 | 0.227 | 2.755 | no |
