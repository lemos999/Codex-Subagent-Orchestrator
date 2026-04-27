# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 1 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 3/4
- Portfolio total R: 46.968261
- Portfolio avg R/trade: 0.489253
- Trade inputs: runs\mtsv1_perf_probe_15m_l3cap025_rsm7_doge\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| DOGE/USDT:USDT | 2.417 | 2.465 | 0.047 | 96 | 0.412 | 2.364 | no | trades < 100, avg RR < 2.5 |
