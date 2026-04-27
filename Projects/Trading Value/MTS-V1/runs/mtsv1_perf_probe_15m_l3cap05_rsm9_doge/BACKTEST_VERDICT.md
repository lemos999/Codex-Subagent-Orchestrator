# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 1 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 3/4
- Portfolio total R: 49.058050
- Portfolio avg R/trade: 0.539099
- Trade inputs: runs\mtsv1_perf_probe_15m_l3cap05_rsm9_doge\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| DOGE/USDT:USDT | 2.438 | 2.550 | 0.049 | 91 | 0.415 | 2.387 | no | trades < 100, avg RR < 2.5 |
