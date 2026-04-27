# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 1 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 2/4
- Portfolio total R: 47.260074
- Portfolio avg R/trade: 0.492292
- Trade inputs: runs\mtsv1_perf_probe_15m_l3cap10_rsm7_doge\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| DOGE/USDT:USDT | 2.270 | 2.187 | 0.053 | 96 | 0.392 | 2.280 | no | trades < 100, avg RR < 2.5 |
