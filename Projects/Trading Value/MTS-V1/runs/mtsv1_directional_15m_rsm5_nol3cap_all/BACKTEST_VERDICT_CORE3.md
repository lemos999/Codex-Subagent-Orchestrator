# MTS-V1 Backtest Verdict

- Status: PASS
- Scope: 3 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 2/4
- Portfolio total R: 145.918916
- Portfolio avg R/trade: 0.405330
- Trade inputs: runs\mtsv1_directional_15m_rsm5_nol3cap_all\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BTC/USDT:USDT | 1.910 | 1.761 | 0.057 | 122 | 0.311 | 2.715 | yes | pass |
| BNB/USDT:USDT | 1.618 | 1.558 | 0.119 | 118 | 0.283 | 2.718 | yes | pass |
| XRP/USDT:USDT | 2.825 | 2.131 | 0.042 | 120 | 0.325 | 3.088 | yes | pass |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 3.022 | 3.254 | 0.057 | 83 | 0.355 | 3.853 | yes |
| 2 | -0.741 | 0.805 | 0.131 | 83 | 0.192 | 2.100 | no |
| 3 | 2.568 | 2.205 | 0.088 | 89 | 0.350 | 2.702 | yes |
| 4 | 1.404 | 1.469 | 0.094 | 105 | 0.285 | 2.486 | no |
