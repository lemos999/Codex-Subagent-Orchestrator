# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 6 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 1/4
- Portfolio total R: 330.682676
- Portfolio avg R/trade: 0.583215
- Trade inputs: runs\mtsv1_directional_15m_rsm7_nol3cap_all\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BTC/USDT:USDT | 1.951 | 2.025 | 0.061 | 94 | 0.253 | 3.923 | no | trades < 100 |
| ETH/USDT:USDT | 1.986 | 1.871 | 0.100 | 112 | 0.299 | 3.002 | yes | pass |
| SOL/USDT:USDT | 2.514 | 3.076 | 0.030 | 81 | 0.376 | 3.313 | no | trades < 100 |
| XRP/USDT:USDT | 2.980 | 2.731 | 0.030 | 91 | 0.373 | 3.049 | no | trades < 100 |
| BNB/USDT:USDT | 1.348 | 1.541 | 0.135 | 97 | 0.272 | 2.729 | no | trades < 100 |
| DOGE/USDT:USDT | 2.456 | 2.256 | 0.057 | 92 | 0.389 | 2.356 | no | trades < 100, avg RR < 2.5 |
