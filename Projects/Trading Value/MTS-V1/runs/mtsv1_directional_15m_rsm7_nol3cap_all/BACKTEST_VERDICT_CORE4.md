# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 4 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 2/4
- Portfolio total R: 206.986866
- Portfolio avg R/trade: 0.525347
- Trade inputs: runs\mtsv1_directional_15m_rsm7_nol3cap_all\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BTC/USDT:USDT | 1.951 | 2.025 | 0.061 | 94 | 0.253 | 3.923 | no | trades < 100 |
| ETH/USDT:USDT | 1.986 | 1.871 | 0.100 | 112 | 0.299 | 3.002 | yes | pass |
| XRP/USDT:USDT | 2.980 | 2.731 | 0.030 | 91 | 0.373 | 3.049 | no | trades < 100 |
| BNB/USDT:USDT | 1.348 | 1.541 | 0.135 | 97 | 0.272 | 2.729 | no | trades < 100 |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 2.954 | 3.154 | 0.072 | 91 | 0.342 | 4.021 | yes |
| 2 | 0.234 | 1.073 | 0.141 | 98 | 0.206 | 2.683 | no |
| 3 | 3.196 | 3.148 | 0.081 | 89 | 0.404 | 3.078 | yes |
| 4 | 1.100 | 1.340 | 0.181 | 116 | 0.265 | 2.547 | no |
