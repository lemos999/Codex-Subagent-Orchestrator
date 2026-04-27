# MTS-V1 BTC TradingView/Python Diff

## Inputs
- TradingView raw CSV: `samples\tradingview_mtsv1_BTC_entry15_raw.csv`
- Python JSONL: `runs\mtsv1_tv_btc_15m_binanceusdm_profile\trades.jsonl`
- Match tolerance: `60.0m`
- TradingView entry range: `2026-03-07T03:15:00Z` to `2026-04-24T14:45:00Z`

## Counts

| Source | Scope | Count | By event | By side |
|---|---|---:|---|---|
| TradingView | raw closed trades | 64 | `{'ENTRY_L1': 34, 'ENTRY_L2': 30}` | `{'long': 40, 'short': 24}` |
| Python | all `BTC` filled entries | 94 | `{'ENTRY_L1': 52, 'ENTRY_L2': 42}` | `{'long': 59, 'short': 35}` |
| Python | TradingView date window | 86 | `{'ENTRY_L1': 48, 'ENTRY_L2': 38}` | `{'long': 53, 'short': 33}` |

## Match Summary

| Metric | Value |
|---|---:|
| matched_tv_trades | 49 / 64 |
| match_rate | 0.765625 |
| unmatched_tv_trades | 15 |
| avg_abs_time_delta_minutes | 4.898 |
| avg_abs_entry_price_delta_pct | 0.000543 |

## Unmatched TradingView Trades

| Trade | Event | Side | TV entry UTC | TV entry price | TV pnl pct |
|---:|---|---|---|---:|---:|
| 3 | ENTRY_L2 | long | 2026-03-09T18:00:00Z | 68403.8000 | 0.021600 |
| 6 | ENTRY_L1 | long | 2026-03-12T14:00:00Z | 70336.5000 | -0.011200 |
| 7 | ENTRY_L2 | long | 2026-03-12T14:15:00Z | 69906.8000 | -0.005100 |
| 15 | ENTRY_L2 | short | 2026-03-18T21:30:00Z | 71292.5000 | -0.002400 |
| 19 | ENTRY_L1 | short | 2026-03-23T01:45:00Z | 67875.6000 | -0.009000 |
| 20 | ENTRY_L2 | short | 2026-03-23T02:15:00Z | 67849.4000 | -0.009400 |
| 23 | ENTRY_L1 | short | 2026-03-28T03:00:00Z | 66110.7000 | -0.005500 |
| 24 | ENTRY_L2 | short | 2026-03-28T04:15:00Z | 66249.2000 | -0.003400 |
| 26 | ENTRY_L2 | short | 2026-03-30T00:15:00Z | 66636.4000 | 0.001500 |
| 32 | ENTRY_L2 | short | 2026-04-02T14:30:00Z | 66748.8000 | -0.004000 |
| 43 | ENTRY_L1 | long | 2026-04-10T05:00:00Z | 72080.8000 | -0.007100 |
| 44 | ENTRY_L2 | long | 2026-04-10T06:30:00Z | 71841.9000 | -0.003800 |
| 46 | ENTRY_L2 | long | 2026-04-11T13:00:00Z | 72651.6000 | -0.001300 |
| 59 | ENTRY_L2 | long | 2026-04-21T17:15:00Z | 75291.2000 | -0.006200 |
| 58 | ENTRY_L1 | long | 2026-04-21T17:15:00Z | 75213.7000 | -0.005200 |

## Worst Nearest Filled-Entry Deltas

| Trade | Event | Side | TV entry UTC | Nearest Python UTC | Delta | TV price | Python price | Python reason |
|---:|---|---|---|---|---:|---:|---:|---|
| 59 | ENTRY_L2 | long | 2026-04-21T17:15:00Z | 2026-04-23T00:30:00Z | 1875.0m | 75291.2000 | 78523.6106 | L2_FILL |
| 43 | ENTRY_L1 | long | 2026-04-10T05:00:00Z | 2026-04-09T05:00:00Z | 1440.0m | 72080.8000 | 70840.0000 | L1_FILL_ON_CLOSE |
| 7 | ENTRY_L2 | long | 2026-03-12T14:15:00Z | 2026-03-11T20:45:00Z | 1050.0m | 69906.8000 | 70473.3794 | L2_FILL |
| 19 | ENTRY_L1 | short | 2026-03-23T01:45:00Z | 2026-03-23T19:00:00Z | 1035.0m | 67875.6000 | 70903.2000 | L1_FILL_ON_CLOSE |
| 20 | ENTRY_L2 | short | 2026-03-23T02:15:00Z | 2026-03-23T19:00:00Z | 1005.0m | 67849.4000 | 71023.7776 | L2_FILL |
| 23 | ENTRY_L1 | short | 2026-03-28T03:00:00Z | 2026-03-28T19:45:00Z | 1005.0m | 66110.7000 | 66816.8937 | L1_FILL |
| 44 | ENTRY_L2 | long | 2026-04-10T06:30:00Z | 2026-04-09T13:45:00Z | 1005.0m | 71841.9000 | 70654.9462 | L2_FILL |
| 24 | ENTRY_L2 | short | 2026-03-28T04:15:00Z | 2026-03-28T19:45:00Z | 930.0m | 66249.2000 | 66860.6754 | L2_FILL |
| 26 | ENTRY_L2 | short | 2026-03-30T00:15:00Z | 2026-03-30T11:30:00Z | 675.0m | 66636.4000 | 67695.8806 | L2_FILL |
| 46 | ENTRY_L2 | long | 2026-04-11T13:00:00Z | 2026-04-11T23:00:00Z | 600.0m | 72651.6000 | 73297.8680 | L2_FILL |
| 6 | ENTRY_L1 | long | 2026-03-12T14:00:00Z | 2026-03-12T07:30:00Z | 390.0m | 70336.5000 | 69642.9000 | L1_FILL_ON_CLOSE |
| 15 | ENTRY_L2 | short | 2026-03-18T21:30:00Z | 2026-03-19T04:00:00Z | 390.0m | 71292.5000 | 71140.5208 | L2_FILL |
| 32 | ENTRY_L2 | short | 2026-04-02T14:30:00Z | 2026-04-02T08:00:00Z | 390.0m | 66748.8000 | 66687.1650 | L2_FILL |
| 58 | ENTRY_L1 | long | 2026-04-21T17:15:00Z | 2026-04-21T21:15:00Z | 240.0m | 75213.7000 | 75537.5000 | L1_FILL_ON_CLOSE |
| 3 | ENTRY_L2 | long | 2026-03-09T18:00:00Z | 2026-03-09T19:15:00Z | 75.0m | 68403.8000 | 68816.2112 | L2_FILL |
| 64 | ENTRY_L2 | long | 2026-04-24T14:45:00Z | 2026-04-24T15:45:00Z | 60.0m | 77986.4000 | 78142.8726 | L2_FILL |
| 11 | ENTRY_L2 | long | 2026-03-15T15:30:00Z | 2026-03-15T16:15:00Z | 45.0m | 71421.4000 | 71365.2600 | L2_FILL |
| 28 | ENTRY_L2 | short | 2026-03-30T12:00:00Z | 2026-03-30T11:30:00Z | 30.0m | 67744.1000 | 67695.8806 | L2_FILL |
| 53 | ENTRY_L2 | long | 2026-04-15T14:30:00Z | 2026-04-15T14:00:00Z | 30.0m | 73997.1000 | 73997.1540 | L2_FILL |
| 9 | ENTRY_L2 | long | 2026-03-14T21:45:00Z | 2026-03-14T21:30:00Z | 15.0m | 70697.1000 | 70660.4768 | L2_FILL |

## Interpretation Notes
- This report compares TradingView filled trade rows only against Python `ENTRY_L1/L2/L3` rows.
- It intentionally does not compare TradingView rows to Python `ENTRY_SIGNAL`, because that is a pre-fill trigger.
- TradingView `net_pnl_pct` is not the same unit as Python `r_multiple`; use price/time/side first, then handle PnL separately.
- If Python date-window counts are much larger than TradingView counts, the next check is profile parity: chart timeframe, `entry_timeframe`, `execution_timeframe`, RSM overrides, and available TradingView history.
