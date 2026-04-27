# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 6 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 0/4
- Portfolio total R: 269.350387
- Portfolio avg R/trade: 0.300950
- Trade inputs: runs\mtsv1_perf_probe_15m_l3cap025_all\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BTC/USDT:USDT | 2.056 | 1.775 | 0.076 | 157 | 0.383 | 2.095 | no | avg RR < 2.5 |
| ETH/USDT:USDT | 1.991 | 1.658 | 0.056 | 154 | 0.365 | 2.097 | no | avg RR < 2.5 |
| SOL/USDT:USDT | 3.026 | 2.771 | 0.032 | 138 | 0.425 | 2.692 | yes | pass |
| XRP/USDT:USDT | 1.907 | 1.701 | 0.077 | 163 | 0.338 | 2.438 | no | avg RR < 2.5 |
| BNB/USDT:USDT | 2.584 | 2.048 | 0.060 | 146 | 0.347 | 2.775 | yes | pass |
| DOGE/USDT:USDT | 1.653 | 1.553 | 0.057 | 137 | 0.379 | 1.824 | no | avg RR < 2.5 |
