# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 1 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 3/4
- Portfolio total R: 40.858601
- Portfolio avg R/trade: 0.400575
- Trade inputs: runs\mtsv1_directional_15m_rsm6_nol3cap_DOGE\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| DOGE/USDT:USDT | 2.128 | 1.848 | 0.072 | 102 | 0.367 | 2.163 | no | avg RR < 2.5 |
