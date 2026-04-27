# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 1 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 0/4
- Portfolio total R: -9.805540
- Portfolio avg R/trade: -0.233465
- Trade inputs: runs\mtsv1_improve_doge_rsm64_hold05_nol3cap\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| DOGE/USDT:USDT | -0.662 | 0.631 | 0.239 | 42 | 0.153 | 1.778 | no | Sharpe < 1.0, PF < 1.3, MDD > 20%, trades < 100, Wilson <= BE, avg RR < 2.5 |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | -3.048 | 0.082 | 0.042 | 7 | 0.026 | 0.494 | no |
| 2 | -3.958 | 0.123 | 0.119 | 20 | 0.112 | 0.369 | no |
| 3 | -2.373 | 0.101 | 0.040 | 8 | 0.071 | 0.304 | no |
| 4 | 0.711 | 3.071 | 0.046 | 7 | 0.158 | 4.094 | no |
