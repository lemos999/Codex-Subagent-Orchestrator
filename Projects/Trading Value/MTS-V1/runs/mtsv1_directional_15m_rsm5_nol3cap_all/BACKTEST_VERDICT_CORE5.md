# MTS-V1 Backtest Verdict

- Status: PASS
- Scope: 5 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 3/4
- Portfolio total R: 259.783624
- Portfolio avg R/trade: 0.436611
- Trade inputs: runs\mtsv1_directional_15m_rsm5_nol3cap_all\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BTC/USDT:USDT | 1.910 | 1.761 | 0.057 | 122 | 0.311 | 2.715 | yes | pass |
| ETH/USDT:USDT | 1.845 | 1.751 | 0.106 | 130 | 0.298 | 2.895 | yes | pass |
| SOL/USDT:USDT | 2.567 | 2.350 | 0.064 | 105 | 0.365 | 2.790 | yes | pass |
| XRP/USDT:USDT | 2.825 | 2.131 | 0.042 | 120 | 0.325 | 3.088 | yes | pass |
| BNB/USDT:USDT | 1.618 | 1.558 | 0.119 | 118 | 0.283 | 2.718 | yes | pass |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 3.779 | 3.198 | 0.088 | 135 | 0.385 | 3.655 | yes |
| 2 | -0.803 | 0.836 | 0.164 | 145 | 0.228 | 1.983 | no |
| 3 | 3.467 | 2.506 | 0.100 | 147 | 0.404 | 2.683 | yes |
| 4 | 1.779 | 1.501 | 0.150 | 168 | 0.289 | 2.701 | yes |
