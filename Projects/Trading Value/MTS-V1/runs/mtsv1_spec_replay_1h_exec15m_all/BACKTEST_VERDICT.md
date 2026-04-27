# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 6 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:00:00+00:00 to 2026-04-24T05:00:00+00:00
- Walk-forward pass windows: 0/4
- Portfolio total R: 118.617751
- Portfolio avg R/trade: 0.466999
- Trade inputs: runs\mtsv1_spec_replay_1h_exec15m_all\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BTC/USDT:USDT | 2.193 | 3.122 | 0.031 | 46 | 0.402 | 2.622 | no | trades < 100 |
| ETH/USDT:USDT | 1.404 | 2.085 | 0.033 | 46 | 0.361 | 2.085 | no | trades < 100, avg RR < 2.5 |
| SOL/USDT:USDT | 2.235 | 4.343 | 0.011 | 40 | 0.495 | 2.339 | no | trades < 100, avg RR < 2.5 |
| XRP/USDT:USDT | 2.266 | 2.735 | 0.013 | 38 | 0.397 | 2.214 | no | trades < 100, avg RR < 2.5 |
| BNB/USDT:USDT | 1.675 | 4.353 | 0.036 | 39 | 0.386 | 3.731 | no | trades < 100 |
| DOGE/USDT:USDT | 2.223 | 2.923 | 0.022 | 45 | 0.433 | 2.136 | no | trades < 100, avg RR < 2.5 |
