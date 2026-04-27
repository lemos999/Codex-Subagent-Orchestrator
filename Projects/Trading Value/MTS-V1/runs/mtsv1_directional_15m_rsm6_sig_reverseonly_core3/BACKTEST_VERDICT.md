# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 3 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 1/4
- Portfolio total R: 86.582637
- Portfolio avg R/trade: 0.301682
- Trade inputs: runs\mtsv1_directional_15m_rsm6_sig_reverseonly_core3\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BTC/USDT:USDT | 1.393 | 1.574 | 0.085 | 97 | 0.272 | 2.789 | no | trades < 100 |
| BNB/USDT:USDT | 0.865 | 1.309 | 0.133 | 99 | 0.230 | 2.871 | no | Sharpe < 1.0, trades < 100, Wilson <= BE |
| XRP/USDT:USDT | 1.312 | 1.519 | 0.076 | 91 | 0.271 | 2.670 | no | trades < 100, Wilson <= BE |
