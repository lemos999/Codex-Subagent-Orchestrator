# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 6 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:00:00+00:00 to 2026-04-24T05:00:00+00:00
- Walk-forward pass windows: 0/4
- Trade inputs: runs\mtsv1_perf_probe_state2\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BTC/USDT:USDT | 1.970 | 2.679 | 0.026 | 46 | 0.402 | 0.468 | no | trades < 100, Wilson <= BE, avg RR < 2.5 |
| ETH/USDT:USDT | 1.417 | 2.101 | 0.033 | 45 | 0.391 | 0.311 | no | trades < 100, Wilson <= BE, avg RR < 2.5 |
| SOL/USDT:USDT | 2.131 | 3.889 | 0.012 | 39 | 0.510 | 0.732 | no | trades < 100, Wilson <= BE, avg RR < 2.5 |
| XRP/USDT:USDT | 2.369 | 2.941 | 0.012 | 35 | 0.409 | 0.260 | no | trades < 100, Wilson <= BE, avg RR < 2.5 |
| BNB/USDT:USDT | 1.484 | 3.340 | 0.041 | 36 | 0.345 | 0.704 | no | trades < 100, Wilson <= BE, avg RR < 2.5 |
| DOGE/USDT:USDT | 1.959 | 2.511 | 0.019 | 44 | 0.379 | 0.334 | no | trades < 100, Wilson <= BE, avg RR < 2.5 |
