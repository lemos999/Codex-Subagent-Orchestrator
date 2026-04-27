# MTS-V1 BTC TradingView/Python Diff

## Inputs
- TradingView raw CSV: `C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value\MTS-V1\samples\tradingview_mtsv1_BTC_raw.csv`
- Python JSONL: `runs\mtsv1_tv_btc_15m_profile\trades.jsonl`
- Match tolerance: `60.0m`
- TradingView entry range: `2026-03-02T04:15:00Z` to `2026-04-24T16:30:00Z`

## Counts

| Source | Scope | Count | By event | By side |
|---|---|---:|---|---|
| TradingView | raw closed trades | 31 | `{'ENTRY_L1': 17, 'ENTRY_L2': 14}` | `{'long': 17, 'short': 14}` |
| Python | all `BTC` filled entries | 118 | `{'ENTRY_L1': 76, 'ENTRY_L2': 42}` | `{'long': 82, 'short': 36}` |
| Python | TradingView date window | 106 | `{'ENTRY_L1': 68, 'ENTRY_L2': 38}` | `{'long': 76, 'short': 30}` |

## Match Summary

| Metric | Value |
|---|---:|
| matched_tv_trades | 1 / 31 |
| match_rate | 0.032258 |
| unmatched_tv_trades | 30 |
| avg_abs_time_delta_minutes | 45.000 |
| avg_abs_entry_price_delta_pct | 0.000888 |

## Unmatched TradingView Trades

| Trade | Event | Side | TV entry UTC | TV entry price | TV pnl pct |
|---:|---|---|---|---:|---:|
| 1 | ENTRY_L1 | long | 2026-03-02T04:15:00Z | 66904.4000 | -0.018600 |
| 2 | ENTRY_L2 | long | 2026-03-02T07:00:00Z | 65802.3000 | -0.002100 |
| 3 | ENTRY_L1 | long | 2026-03-03T15:45:00Z | 67692.5000 | 0.054500 |
| 4 | ENTRY_L1 | long | 2026-03-11T18:30:00Z | 70376.8000 | -0.007300 |
| 5 | ENTRY_L1 | long | 2026-03-12T16:45:00Z | 70250.0000 | 0.037700 |
| 6 | ENTRY_L2 | long | 2026-03-12T18:45:00Z | 69808.4000 | 0.044300 |
| 7 | ENTRY_L1 | short | 2026-03-20T14:00:00Z | 70018.3000 | -0.013900 |
| 8 | ENTRY_L2 | short | 2026-03-21T14:00:00Z | 70896.4000 | -0.001400 |
| 10 | ENTRY_L2 | short | 2026-03-23T11:00:00Z | 70931.8000 | 0.011800 |
| 9 | ENTRY_L1 | short | 2026-03-23T11:00:00Z | 70374.9000 | 0.003900 |
| 11 | ENTRY_L1 | short | 2026-03-31T15:00:00Z | 67127.2000 | -0.020700 |
| 12 | ENTRY_L2 | short | 2026-03-31T16:30:00Z | 67445.4000 | -0.015800 |

## Worst Nearest Filled-Entry Deltas

| Trade | Event | Side | TV entry UTC | Nearest Python UTC | Delta | TV price | Python price | Python reason |
|---:|---|---|---|---|---:|---:|---:|---|
| 10 | ENTRY_L2 | short | 2026-03-23T11:00:00Z | 2026-03-27T02:00:00Z | 5220.0m | 70931.8000 | 69054.2842 | L2_FILL |
| 8 | ENTRY_L2 | short | 2026-03-21T14:00:00Z | 2026-03-19T04:00:00Z | 3480.0m | 70896.4000 | 71140.7050 | L2_FILL |
| 22 | ENTRY_L2 | short | 2026-04-05T17:00:00Z | 2026-04-03T14:15:00Z | 3045.0m | 67253.8000 | 66929.3854 | L2_FILL |
| 20 | ENTRY_L2 | short | 2026-04-05T15:15:00Z | 2026-04-03T14:15:00Z | 2940.0m | 67381.3000 | 66929.3854 | L2_FILL |
| 26 | ENTRY_L2 | long | 2026-04-11T15:00:00Z | 2026-04-09T15:30:00Z | 2850.0m | 72669.0000 | 71831.9686 | L2_FILL |
| 23 | ENTRY_L1 | long | 2026-04-10T07:45:00Z | 2026-04-11T15:30:00Z | 1905.0m | 71400.5000 | 72725.4557 | L1_FILL |
| 6 | ENTRY_L2 | long | 2026-03-12T18:45:00Z | 2026-03-11T15:30:00Z | 1635.0m | 69808.4000 | 69670.1928 | L2_FILL |
| 31 | ENTRY_L2 | long | 2026-04-24T16:30:00Z | 2026-04-23T19:15:00Z | 1275.0m | 77596.9000 | 77838.7464 | L2_FILL |
| 30 | ENTRY_L1 | long | 2026-04-24T15:00:00Z | 2026-04-23T18:45:00Z | 1215.0m | 77599.5000 | 77784.6144 | L1_FILL |
| 17 | ENTRY_L1 | short | 2026-04-04T08:45:00Z | 2026-04-03T13:00:00Z | 1185.0m | 66907.8000 | 66542.0407 | L1_FILL |
| 18 | ENTRY_L2 | short | 2026-04-04T09:00:00Z | 2026-04-03T14:15:00Z | 1125.0m | 66948.0000 | 66929.3854 | L2_FILL |
| 1 | ENTRY_L1 | long | 2026-03-02T04:15:00Z | 2026-03-02T22:30:00Z | 1095.0m | 66904.4000 | 69314.9313 | L1_FILL |

## Interpretation Notes
- This report compares TradingView filled trade rows only against Python `ENTRY_L1/L2/L3` rows.
- It intentionally does not compare TradingView rows to Python `ENTRY_SIGNAL`, because that is a pre-fill trigger.
- TradingView `net_pnl_pct` is not the same unit as Python `r_multiple`; use price/time/side first, then handle PnL separately.
- If Python date-window counts are much larger than TradingView counts, the next check is profile parity: chart timeframe, `entry_timeframe`, `execution_timeframe`, RSM overrides, and available TradingView history.
