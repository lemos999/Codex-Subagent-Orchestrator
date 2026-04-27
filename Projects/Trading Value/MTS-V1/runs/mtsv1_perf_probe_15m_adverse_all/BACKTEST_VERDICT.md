# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 6 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 0/4
- Portfolio total R: 98.190518
- Portfolio avg R/trade: 1.345076
- Trade inputs: runs\mtsv1_perf_probe_15m_adverse_all\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BTC/USDT:USDT | 1.367 | 59.405 | 0.004 | 2 | 0.095 | 59.405 | no | trades < 100 |
| ETH/USDT:USDT | 0.149 | 1.188 | 0.093 | 11 | 0.016 | 11.881 | no | Sharpe < 1.0, PF < 1.3, trades < 100, Wilson <= BE |
| SOL/USDT:USDT | 1.389 | 113.423 | 0.004 | 2 | 0.095 | 113.423 | no | trades < 100 |
| XRP/USDT:USDT | 1.086 | 22.354 | 0.015 | 4 | 0.046 | 67.061 | no | trades < 100 |
| BNB/USDT:USDT | 0.988 | 10.522 | 0.023 | 5 | 0.036 | 42.089 | no | Sharpe < 1.0, trades < 100 |
| DOGE/USDT:USDT | -1.782 | 0.338 | 0.325 | 49 | 0.004 | 16.210 | no | Sharpe < 1.0, PF < 1.3, MDD > 20%, trades < 100, Wilson <= BE |
