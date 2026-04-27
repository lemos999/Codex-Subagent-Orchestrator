# MTS-V1 Backtest Verdict

- Status: PASS
- Scope: 4 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 3/4
- Portfolio total R: 197.076721
- Portfolio avg R/trade: 0.402197
- Trade inputs: runs\mtsv1_directional_15m_rsm5_nol3cap_all\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BTC/USDT:USDT | 1.910 | 1.761 | 0.057 | 122 | 0.311 | 2.715 | yes | pass |
| ETH/USDT:USDT | 1.845 | 1.751 | 0.106 | 130 | 0.298 | 2.895 | yes | pass |
| XRP/USDT:USDT | 2.825 | 2.131 | 0.042 | 120 | 0.325 | 3.088 | yes | pass |
| BNB/USDT:USDT | 1.618 | 1.558 | 0.119 | 118 | 0.283 | 2.718 | yes | pass |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 3.249 | 2.942 | 0.098 | 110 | 0.373 | 3.403 | yes |
| 2 | -0.525 | 0.878 | 0.148 | 123 | 0.220 | 2.121 | no |
| 3 | 2.930 | 2.418 | 0.099 | 118 | 0.370 | 2.866 | yes |
| 4 | 1.426 | 1.424 | 0.130 | 139 | 0.271 | 2.700 | yes |
