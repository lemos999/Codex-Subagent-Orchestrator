# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 3 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 0/4
- Portfolio total R: 129.745423
- Portfolio avg R/trade: 1.297454
- Trade inputs: runs\mtsv1_directional_15m_rsm6_sig_both_core3\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BTC/USDT:USDT | 1.364 | 4.386 | 0.056 | 29 | 0.227 | 7.176 | no | trades < 100 |
| BNB/USDT:USDT | 1.470 | 3.510 | 0.070 | 29 | 0.227 | 5.744 | no | trades < 100 |
| XRP/USDT:USDT | 0.853 | 1.635 | 0.100 | 42 | 0.210 | 3.270 | no | Sharpe < 1.0, trades < 100, Wilson <= BE |
