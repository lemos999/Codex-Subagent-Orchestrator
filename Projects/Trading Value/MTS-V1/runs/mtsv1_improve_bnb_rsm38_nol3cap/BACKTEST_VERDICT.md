# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 1 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 1/4
- Portfolio total R: 43.294094
- Portfolio avg R/trade: 0.338235
- Trade inputs: runs\mtsv1_improve_bnb_rsm38_nol3cap\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BNB/USDT:USDT | 1.844 | 1.647 | 0.104 | 128 | 0.289 | 2.839 | yes | pass |

## Walk-Forward Windows

| Window | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass |
|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | 1.687 | 2.960 | 0.042 | 32 | 0.255 | 4.327 | yes |
| 2 | -1.354 | 0.545 | 0.110 | 32 | 0.089 | 2.364 | no |
| 3 | 1.284 | 1.951 | 0.054 | 30 | 0.302 | 2.230 | no |
| 4 | 1.219 | 1.726 | 0.054 | 34 | 0.264 | 2.466 | no |
