# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 1 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 1/4
- Portfolio total R: 47.846130
- Portfolio avg R/trade: 0.412467
- Trade inputs: runs\mtsv1_improve_eth_rsm66_nol3cap\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| ETH/USDT:USDT | 1.823 | 1.749 | 0.102 | 116 | 0.304 | 2.760 | yes | pass |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 0.584 | 1.426 | 0.055 | 27 | 0.276 | 1.782 | no |
| 2 | 0.802 | 1.504 | 0.070 | 33 | 0.198 | 3.009 | no |
| 3 | 1.637 | 3.594 | 0.035 | 22 | 0.347 | 2.995 | yes |
| 4 | 0.492 | 1.301 | 0.078 | 34 | 0.168 | 3.122 | no |
