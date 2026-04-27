# MTS-V1 BTC TradingView/Python Diff

## Inputs
- TradingView raw CSV: `C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value\MTS-V1\samples\tradingview_mtsv1_BTC_raw.csv`
- Python JSONL: `runs\mtsv1_tv_btc_pine_default_profile\trades.jsonl`
- Match tolerance: `15.0m`
- TradingView entry range: `2026-03-02T04:15:00Z` to `2026-04-24T16:30:00Z`

## Counts

| Source | Scope | Count | By event | By side |
|---|---|---:|---|---|
| TradingView | raw closed trades | 31 | `{'ENTRY_L1': 17, 'ENTRY_L2': 14}` | `{'long': 17, 'short': 14}` |
| Python | all `BTC` filled entries | 34 | `{'ENTRY_L1': 22, 'ENTRY_L2': 12}` | `{'long': 14, 'short': 20}` |
| Python | TradingView date window | 28 | `{'ENTRY_L1': 18, 'ENTRY_L2': 10}` | `{'long': 13, 'short': 15}` |

## Match Summary

| Metric | Value |
|---|---:|
| matched_tv_trades | 6 / 31 |
| match_rate | 0.193548 |
| unmatched_tv_trades | 25 |
| avg_abs_time_delta_minutes | 2.500 |
| avg_abs_entry_price_delta_pct | 0.000068 |

## Unmatched TradingView Trades

| Trade | Event | Side | TV entry UTC | TV entry price | TV pnl pct |
|---:|---|---|---|---:|---:|
| 1 | ENTRY_L1 | long | 2026-03-02T04:15:00Z | 66904.4000 | -0.018600 |
| 2 | ENTRY_L2 | long | 2026-03-02T07:00:00Z | 65802.3000 | -0.002100 |
| 3 | ENTRY_L1 | long | 2026-03-03T15:45:00Z | 67692.5000 | 0.054500 |
| 4 | ENTRY_L1 | long | 2026-03-11T18:30:00Z | 70376.8000 | -0.007300 |
| 5 | ENTRY_L1 | long | 2026-03-12T16:45:00Z | 70250.0000 | 0.037700 |
| 6 | ENTRY_L2 | long | 2026-03-12T18:45:00Z | 69808.4000 | 0.044300 |
| 10 | ENTRY_L2 | short | 2026-03-23T11:00:00Z | 70931.8000 | 0.011800 |
| 9 | ENTRY_L1 | short | 2026-03-23T11:00:00Z | 70374.9000 | 0.003900 |
| 11 | ENTRY_L1 | short | 2026-03-31T15:00:00Z | 67127.2000 | -0.020700 |
| 12 | ENTRY_L2 | short | 2026-03-31T16:30:00Z | 67445.4000 | -0.015800 |
| 13 | ENTRY_L1 | long | 2026-04-02T00:45:00Z | 68565.1000 | -0.015000 |
| 14 | ENTRY_L2 | long | 2026-04-02T01:00:00Z | 68105.3000 | -0.008300 |

## Worst Nearest Filled-Entry Deltas

| Trade | Event | Side | TV entry UTC | Nearest Python UTC | Delta | TV price | Python price | Python reason |
|---:|---|---|---|---|---:|---:|---:|---|
| 2 | ENTRY_L2 | long | 2026-03-02T07:00:00Z | 2026-03-10T20:15:00Z | 12315.0m | 65802.3000 | 70195.8610 | L2_FILL |
| 31 | ENTRY_L2 | long | 2026-04-24T16:30:00Z | 2026-04-16T17:15:00Z | 11475.0m | 77596.9000 | 73900.9002 | L2_FILL |
| 14 | ENTRY_L2 | long | 2026-04-02T01:00:00Z | 2026-03-26T06:00:00Z | 9780.0m | 68105.3000 | 69821.2372 | L2_FILL |
| 24 | ENTRY_L2 | long | 2026-04-10T07:45:00Z | 2026-04-16T17:15:00Z | 9210.0m | 71461.2000 | 73900.9002 | L2_FILL |
| 13 | ENTRY_L1 | long | 2026-04-02T00:45:00Z | 2026-04-07T21:00:00Z | 8415.0m | 68565.1000 | 70104.1516 | L1_FILL |
| 26 | ENTRY_L2 | long | 2026-04-11T15:00:00Z | 2026-04-16T17:15:00Z | 7335.0m | 72669.0000 | 73900.9002 | L2_FILL |
| 30 | ENTRY_L1 | long | 2026-04-24T15:00:00Z | 2026-04-20T11:00:00Z | 6000.0m | 77599.5000 | 74956.7125 | L1_FILL |
| 23 | ENTRY_L1 | long | 2026-04-10T07:45:00Z | 2026-04-07T21:00:00Z | 3525.0m | 71400.5000 | 70104.1516 | L1_FILL |
| 25 | ENTRY_L1 | long | 2026-04-11T14:45:00Z | 2026-04-13T13:30:00Z | 2805.0m | 72660.9000 | 70994.9656 | L1_FILL |
| 6 | ENTRY_L2 | long | 2026-03-12T18:45:00Z | 2026-03-10T20:15:00Z | 2790.0m | 69808.4000 | 70195.8610 | L2_FILL |
| 10 | ENTRY_L2 | short | 2026-03-23T11:00:00Z | 2026-03-21T14:00:00Z | 2700.0m | 70931.8000 | 70895.6994 | L2_FILL |
| 5 | ENTRY_L1 | long | 2026-03-12T16:45:00Z | 2026-03-10T20:00:00Z | 2685.0m | 70250.0000 | 70021.9257 | L1_FILL |

## Interpretation Notes
- This report compares TradingView filled trade rows only against Python `ENTRY_L1/L2/L3` rows.
- It intentionally does not compare TradingView rows to Python `ENTRY_SIGNAL`, because that is a pre-fill trigger.
- TradingView `net_pnl_pct` is not the same unit as Python `r_multiple`; use price/time/side first, then handle PnL separately.
- If Python date-window counts are much larger than TradingView counts, the next check is profile parity: chart timeframe, `entry_timeframe`, `execution_timeframe`, RSM overrides, and available TradingView history.
