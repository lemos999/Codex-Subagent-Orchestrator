# MTS-V1 Backtest Verdict

> Historical/stale root verdict. This file records the original no-input 1h/DOGE-inclusive baseline and is not the accepted MTS-V1 profile. Current accepted profile data lives in `mts_profile.py` and `runs/mtsv1_improve_core5_symbol_rsm_best5_nol3cap/BACKTEST_VERDICT.md`.

- Status: FAIL
- Scope: 6 symbols x 90d x entry_tf=1h
- Walk-forward pass windows: 0/4
- Trade inputs: none

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BTC/USDT:USDT | 0.000 | 0.000 | 1.000 | 0 | 0.000 | 0.000 | no | no trades |
| ETH/USDT:USDT | 0.000 | 0.000 | 1.000 | 0 | 0.000 | 0.000 | no | no trades |
| SOL/USDT:USDT | 0.000 | 0.000 | 1.000 | 0 | 0.000 | 0.000 | no | no trades |
| XRP/USDT:USDT | 0.000 | 0.000 | 1.000 | 0 | 0.000 | 0.000 | no | no trades |
| BNB/USDT:USDT | 0.000 | 0.000 | 1.000 | 0 | 0.000 | 0.000 | no | no trades |
| DOGE/USDT:USDT | 0.000 | 0.000 | 1.000 | 0 | 0.000 | 0.000 | no | no trades |

## Failure Cause
- no local trade input
