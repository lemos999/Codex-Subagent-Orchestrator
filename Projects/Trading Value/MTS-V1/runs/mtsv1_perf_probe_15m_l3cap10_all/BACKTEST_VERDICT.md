# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 6 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 0/4
- Portfolio total R: 275.789436
- Portfolio avg R/trade: 0.299121
- Trade inputs: runs\mtsv1_perf_probe_15m_l3cap10_all\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BTC/USDT:USDT | 1.624 | 1.541 | 0.088 | 164 | 0.354 | 2.069 | no | avg RR < 2.5 |
| ETH/USDT:USDT | 2.141 | 1.681 | 0.054 | 163 | 0.362 | 2.178 | no | avg RR < 2.5 |
| SOL/USDT:USDT | 3.069 | 2.576 | 0.034 | 141 | 0.415 | 2.613 | yes | pass |
| XRP/USDT:USDT | 1.981 | 1.700 | 0.070 | 169 | 0.343 | 2.404 | no | avg RR < 2.5 |
| BNB/USDT:USDT | 2.207 | 1.839 | 0.081 | 146 | 0.328 | 2.711 | yes | pass |
| DOGE/USDT:USDT | 1.711 | 1.547 | 0.073 | 139 | 0.359 | 1.978 | no | avg RR < 2.5 |
