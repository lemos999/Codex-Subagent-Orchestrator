# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 1 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 3/4
- Portfolio total R: 45.848164
- Portfolio avg R/trade: 0.449492
- Trade inputs: runs\mtsv1_perf_probe_15m_l3cap05_rsm65_doge\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| DOGE/USDT:USDT | 2.316 | 2.261 | 0.045 | 102 | 0.395 | 2.351 | no | avg RR < 2.5 |
