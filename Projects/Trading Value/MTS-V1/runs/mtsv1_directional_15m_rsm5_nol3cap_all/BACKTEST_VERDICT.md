# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 6 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 3/4
- Portfolio total R: 302.838329
- Portfolio avg R/trade: 0.426533
- Trade inputs: runs\mtsv1_directional_15m_rsm5_nol3cap_all\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BTC/USDT:USDT | 1.910 | 1.761 | 0.057 | 122 | 0.311 | 2.715 | yes | pass |
| ETH/USDT:USDT | 1.845 | 1.751 | 0.106 | 130 | 0.298 | 2.895 | yes | pass |
| SOL/USDT:USDT | 2.567 | 2.350 | 0.064 | 105 | 0.365 | 2.790 | yes | pass |
| XRP/USDT:USDT | 2.825 | 2.131 | 0.042 | 120 | 0.325 | 3.088 | yes | pass |
| BNB/USDT:USDT | 1.618 | 1.558 | 0.119 | 118 | 0.283 | 2.718 | yes | pass |
| DOGE/USDT:USDT | 2.229 | 1.855 | 0.086 | 115 | 0.398 | 1.954 | no | avg RR < 2.5 |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 3.971 | 3.053 | 0.106 | 163 | 0.403 | 3.327 | yes |
| 2 | -0.898 | 0.832 | 0.200 | 176 | 0.238 | 1.931 | no |
| 3 | 3.903 | 2.561 | 0.106 | 176 | 0.427 | 2.561 | yes |
| 4 | 2.237 | 1.603 | 0.172 | 195 | 0.314 | 2.620 | yes |
