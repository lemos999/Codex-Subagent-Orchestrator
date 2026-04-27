# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 6 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 0/4
- Portfolio total R: 245.668025
- Portfolio avg R/trade: 0.259417
- Trade inputs: runs\mtsv1_perf_probe_15m_all\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BTC/USDT:USDT | 1.622 | 1.511 | 0.080 | 165 | 0.346 | 2.102 | no | avg RR < 2.5 |
| ETH/USDT:USDT | 1.620 | 1.451 | 0.079 | 169 | 0.348 | 2.002 | no | avg RR < 2.5 |
| SOL/USDT:USDT | 2.512 | 2.082 | 0.063 | 146 | 0.374 | 2.524 | yes | pass |
| XRP/USDT:USDT | 1.515 | 1.450 | 0.074 | 178 | 0.324 | 2.237 | no | avg RR < 2.5 |
| BNB/USDT:USDT | 1.973 | 1.670 | 0.093 | 147 | 0.300 | 2.794 | yes | pass |
| DOGE/USDT:USDT | 1.833 | 1.562 | 0.075 | 142 | 0.364 | 1.959 | no | avg RR < 2.5 |
