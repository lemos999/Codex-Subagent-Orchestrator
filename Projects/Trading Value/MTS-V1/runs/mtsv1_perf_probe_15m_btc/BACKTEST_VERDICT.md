# MTS-V1 Backtest Verdict

- Status: FAIL
- Scope: 6 symbols x 90d x entry_tf=1h
- Coverage: 2026-01-24T05:15:00+00:00 to 2026-04-24T05:15:00+00:00
- Walk-forward pass windows: 0/4
- Trade inputs: runs\mtsv1_perf_probe_15m_btc\trades.jsonl

| Symbol | Sharpe | PF | MDD | Trades | Wilson 95% Lower | Avg RR | Pass | Reason |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| BTC/USDT:USDT | 1.622 | 1.511 | 0.080 | 165 | 0.346 | 0.242 | no | Wilson <= BE, avg RR < 2.5 |
| ETH/USDT:USDT | 0.000 | 0.000 | 1.000 | 0 | 0.000 | 0.000 | no | no trades |
| SOL/USDT:USDT | 0.000 | 0.000 | 1.000 | 0 | 0.000 | 0.000 | no | no trades |
| XRP/USDT:USDT | 0.000 | 0.000 | 1.000 | 0 | 0.000 | 0.000 | no | no trades |
| BNB/USDT:USDT | 0.000 | 0.000 | 1.000 | 0 | 0.000 | 0.000 | no | no trades |
| DOGE/USDT:USDT | 0.000 | 0.000 | 1.000 | 0 | 0.000 | 0.000 | no | no trades |

## Failure Cause
- missing symbols=['BNB/USDT:USDT', 'DOGE/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT', 'XRP/USDT:USDT']
