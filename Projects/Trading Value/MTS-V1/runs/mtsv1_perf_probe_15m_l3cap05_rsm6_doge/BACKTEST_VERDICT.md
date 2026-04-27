# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 1 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 3/4
- Portfolio total R: 36.932300
- Portfolio avg R/trade: 0.355118
- Trade inputs: runs\mtsv1_perf_probe_15m_l3cap05_rsm6_doge\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| DOGE/USDT:USDT | 2.209 | 2.014 | 0.049 | 104 | 0.396 | 2.093 | no | avg RR < 2.5 |
