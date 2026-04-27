# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 5 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 1/4
- Portfolio total R: 277.686974
- Portfolio avg R/trade: 0.469860
- Trade inputs: runs\mtsv1_perf_probe_15m_l3cap05_rsm5_all\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BTC/USDT:USDT | 2.024 | 1.919 | 0.053 | 119 | 0.327 | 2.741 | yes | pass |
| ETH/USDT:USDT | 2.262 | 2.245 | 0.082 | 124 | 0.329 | 3.213 | yes | pass |
| SOL/USDT:USDT | 2.820 | 2.902 | 0.040 | 107 | 0.411 | 2.848 | yes | pass |
| XRP/USDT:USDT | 2.691 | 2.127 | 0.040 | 124 | 0.336 | 2.945 | yes | pass |
| BNB/USDT:USDT | 2.085 | 1.883 | 0.096 | 117 | 0.333 | 2.614 | yes | pass |
