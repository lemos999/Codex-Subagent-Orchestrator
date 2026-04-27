# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 6 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:00:00+00:00 to 2026-04-24T05:00:00+00:00
- Walk-forward pass windows: 0/4
- Portfolio total R: 164.868075
- Portfolio avg R/trade: 0.363146
- Trade inputs: runs\mtsv1_perf_probe_30m_l3cap05_all\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BTC/USDT:USDT | 1.415 | 1.776 | 0.070 | 84 | 0.418 | 1.615 | no | trades < 100, avg RR < 2.5 |
| ETH/USDT:USDT | 1.606 | 1.701 | 0.042 | 81 | 0.341 | 2.126 | no | trades < 100, avg RR < 2.5 |
| SOL/USDT:USDT | 2.958 | 3.362 | 0.031 | 70 | 0.427 | 2.831 | no | trades < 100 |
| XRP/USDT:USDT | 1.924 | 1.908 | 0.042 | 70 | 0.386 | 1.908 | no | trades < 100, avg RR < 2.5 |
| BNB/USDT:USDT | 2.057 | 2.110 | 0.036 | 77 | 0.410 | 1.951 | no | trades < 100, avg RR < 2.5 |
| DOGE/USDT:USDT | 2.452 | 2.341 | 0.031 | 72 | 0.401 | 2.214 | no | trades < 100, avg RR < 2.5 |
