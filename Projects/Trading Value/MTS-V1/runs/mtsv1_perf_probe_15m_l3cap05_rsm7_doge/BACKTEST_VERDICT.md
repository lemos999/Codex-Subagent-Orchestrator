# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 1 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 3/4
- Portfolio total R: 50.135420
- Portfolio avg R/trade: 0.522244
- Trade inputs: runs\mtsv1_perf_probe_15m_l3cap05_rsm7_doge\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| DOGE/USDT:USDT | 2.523 | 2.522 | 0.038 | 96 | 0.412 | 2.419 | no | trades < 100, avg RR < 2.5 |
