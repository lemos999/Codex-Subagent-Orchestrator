# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 3 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 1/4
- Portfolio total R: 151.559547
- Portfolio avg R/trade: 0.476602
- Trade inputs: runs\mtsv1_directional_15m_rsm6_tptouch_core3\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BTC/USDT:USDT | 1.955 | 1.901 | 0.057 | 107 | 0.305 | 2.943 | yes | pass |
| BNB/USDT:USDT | 1.427 | 1.533 | 0.126 | 108 | 0.285 | 2.606 | yes | pass |
| XRP/USDT:USDT | 2.846 | 2.481 | 0.039 | 103 | 0.336 | 3.327 | yes | pass |
