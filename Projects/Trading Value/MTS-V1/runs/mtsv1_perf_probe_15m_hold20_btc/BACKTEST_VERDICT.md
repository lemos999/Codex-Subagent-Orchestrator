# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 1 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 0/4
- Portfolio total R: 25.430122
- Portfolio avg R/trade: 4.238354
- Trade inputs: runs\mtsv1_perf_probe_15m_hold20_btc\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BTC/USDT:USDT | 1.188 | 29.280 | 0.007 | 6 | 0.300 | 14.640 | no | trades < 100 |
