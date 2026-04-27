# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 1 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 1/4
- Portfolio total R: 54.498491
- Portfolio avg R/trade: 0.478057
- Trade inputs: runs\mtsv1_improve_eth_rsm67_nol3cap\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| ETH/USDT:USDT | 1.995 | 1.857 | 0.100 | 114 | 0.302 | 2.954 | yes | pass |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 0.725 | 1.623 | 0.055 | 26 | 0.255 | 2.214 | no |
| 2 | 0.802 | 1.504 | 0.070 | 33 | 0.198 | 3.009 | no |
| 3 | 1.637 | 3.594 | 0.035 | 22 | 0.347 | 2.995 | yes |
| 4 | 0.740 | 1.471 | 0.055 | 33 | 0.174 | 3.384 | no |
