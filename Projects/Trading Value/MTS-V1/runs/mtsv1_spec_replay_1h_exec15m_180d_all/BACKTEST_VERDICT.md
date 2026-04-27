# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 6 symbols x 180d x entry_tf=1h
- Coverage: 2025-10-26T05:00:00+00:00 to 2026-04-24T05:00:00+00:00
- Walk-forward pass windows: 0/4
- Portfolio total R: 154.021150
- Portfolio avg R/trade: 0.346115
- Trade inputs: runs\mtsv1_spec_replay_1h_exec15m_180d_all\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BTC/USDT:USDT | 2.256 | 2.347 | 0.034 | 78 | 0.392 | 2.347 | no | trades < 100, avg RR < 2.5 |
| ETH/USDT:USDT | 1.148 | 1.513 | 0.074 | 84 | 0.384 | 1.586 | no | trades < 100, Wilson <= BE, avg RR < 2.5 |
| SOL/USDT:USDT | 2.313 | 2.808 | 0.029 | 72 | 0.468 | 2.006 | no | trades < 100, avg RR < 2.5 |
| XRP/USDT:USDT | 1.510 | 3.174 | 0.076 | 72 | 0.414 | 2.840 | no | trades < 100 |
| BNB/USDT:USDT | 2.075 | 3.464 | 0.033 | 65 | 0.389 | 3.359 | no | trades < 100 |
| DOGE/USDT:USDT | 0.609 | 1.227 | 0.114 | 74 | 0.389 | 1.227 | no | Sharpe < 1.0, PF < 1.3, trades < 100, Wilson <= BE, avg RR < 2.5 |
