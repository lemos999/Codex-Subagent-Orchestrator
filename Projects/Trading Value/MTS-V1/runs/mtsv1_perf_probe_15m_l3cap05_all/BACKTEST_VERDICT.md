# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 6 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 0/4
- Portfolio total R: 280.258829
- Portfolio avg R/trade: 0.311399
- Trade inputs: runs\mtsv1_perf_probe_15m_l3cap05_all\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BTC/USDT:USDT | 2.031 | 1.746 | 0.078 | 157 | 0.364 | 2.226 | no | avg RR < 2.5 |
| ETH/USDT:USDT | 2.192 | 1.828 | 0.060 | 158 | 0.368 | 2.298 | no | avg RR < 2.5 |
| SOL/USDT:USDT | 3.148 | 2.795 | 0.030 | 139 | 0.422 | 2.755 | yes | pass |
| XRP/USDT:USDT | 1.936 | 1.680 | 0.059 | 163 | 0.338 | 2.407 | no | avg RR < 2.5 |
| BNB/USDT:USDT | 2.153 | 1.816 | 0.077 | 148 | 0.311 | 2.899 | yes | pass |
| DOGE/USDT:USDT | 1.915 | 1.665 | 0.062 | 135 | 0.385 | 1.903 | no | avg RR < 2.5 |
