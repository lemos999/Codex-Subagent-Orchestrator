# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 1 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 0/4
- Portfolio total R: -12.312507
- Portfolio avg R/trade: -0.189423
- Trade inputs: runs\mtsv1_improve_doge_rsm64_hold15_nol3cap\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| DOGE/USDT:USDT | -1.700 | 0.624 | 0.154 | 65 | 0.346 | 0.728 | no | Sharpe < 1.0, PF < 1.3, trades < 100, Wilson <= BE, avg RR < 2.5 |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | -1.908 | 0.195 | 0.046 | 8 | 0.071 | 0.584 | no |
| 2 | -1.588 | 0.463 | 0.077 | 22 | 0.233 | 0.669 | no |
| 3 | -0.052 | 0.975 | 0.050 | 20 | 0.342 | 0.798 | no |
| 4 | -0.400 | 0.798 | 0.046 | 15 | 0.301 | 0.698 | no |
