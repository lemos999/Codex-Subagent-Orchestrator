# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 1 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 3/4
- Portfolio total R: 53.534824
- Portfolio avg R/trade: 0.581900
- Trade inputs: runs\mtsv1_directional_15m_rsm7_nol3cap_DOGE\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| DOGE/USDT:USDT | 2.456 | 2.256 | 0.057 | 92 | 0.389 | 2.356 | no | trades < 100, avg RR < 2.5 |
