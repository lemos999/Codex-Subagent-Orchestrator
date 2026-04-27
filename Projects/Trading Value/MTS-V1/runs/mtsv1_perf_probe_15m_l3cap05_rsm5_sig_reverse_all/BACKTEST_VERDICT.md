# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 6 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 0/4
- Portfolio total R: 221.876851
- Portfolio avg R/trade: 0.330174
- Trade inputs: runs\mtsv1_perf_probe_15m_l3cap05_rsm5_sig_reverse_all\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BTC/USDT:USDT | 1.576 | 1.663 | 0.062 | 114 | 0.302 | 2.646 | yes | pass |
| ETH/USDT:USDT | 1.551 | 1.754 | 0.092 | 116 | 0.272 | 3.209 | yes | pass |
| SOL/USDT:USDT | 1.971 | 2.107 | 0.053 | 105 | 0.347 | 2.703 | yes | pass |
| XRP/USDT:USDT | 1.837 | 1.664 | 0.062 | 117 | 0.333 | 2.310 | no | avg RR < 2.5 |
| BNB/USDT:USDT | 1.804 | 1.742 | 0.092 | 111 | 0.294 | 2.862 | yes | pass |
| DOGE/USDT:USDT | 1.179 | 1.443 | 0.075 | 109 | 0.368 | 1.703 | no | Wilson <= BE, avg RR < 2.5 |
