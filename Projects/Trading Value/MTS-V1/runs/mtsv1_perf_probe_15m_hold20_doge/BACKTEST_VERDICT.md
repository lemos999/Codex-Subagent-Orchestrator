# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 1 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 1/4
- Portfolio total R: 12.669466
- Portfolio avg R/trade: 0.120662
- Trade inputs: runs\mtsv1_perf_probe_15m_hold20_doge\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| DOGE/USDT:USDT | 0.860 | 1.304 | 0.103 | 105 | 0.356 | 1.609 | no | Sharpe < 1.0, Wilson <= BE, avg RR < 2.5 |
