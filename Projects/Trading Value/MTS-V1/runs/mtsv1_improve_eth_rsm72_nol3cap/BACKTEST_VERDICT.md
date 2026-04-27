# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 1 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 1/4
- Portfolio total R: 52.634008
- Portfolio avg R/trade: 0.469946
- Trade inputs: runs\mtsv1_improve_eth_rsm72_nol3cap\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| ETH/USDT:USDT | 1.962 | 1.833 | 0.100 | 112 | 0.299 | 2.941 | yes | pass |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 0.725 | 1.623 | 0.055 | 26 | 0.255 | 2.214 | no |
| 2 | 0.941 | 1.644 | 0.070 | 32 | 0.204 | 3.139 | no |
| 3 | 1.501 | 3.214 | 0.035 | 21 | 0.324 | 2.922 | yes |
| 4 | 0.740 | 1.471 | 0.055 | 33 | 0.174 | 3.384 | no |
