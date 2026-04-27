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
| Python | all `BTC` filled entries | 71 | `{'ENTRY_L1': 38, 'ENTRY_L2': 33}` | `{'long': 45, 'short': 26}` |
| Python | TradingView date window | 65 | `{'ENTRY_L1': 35, 'ENTRY_L2': 30}` | `{'long': 41, 'short': 24}` |

## Match Summary

| Metric | Value |
|---|---:|
| matched_tv_trades | 61 / 64 |
| match_rate | 0.953125 |
| unmatched_tv_trades | 3 |
| avg_abs_time_delta_minutes | 0.246 |
| avg_abs_entry_price_delta_pct | 0.000136 |

## Unmatched TradingView Trades

| Trade | Event | Side | TV entry UTC | TV entry price | TV pnl pct |
|---:|---|---|---|---:|---:|
| 32 | ENTRY_L2 | short | 2026-04-02T14:30:00Z | 66748.8000 | -0.004000 |
| 59 | ENTRY_L2 | long | 2026-04-21T17:15:00Z | 75291.2000 | -0.006200 |
| 58 | ENTRY_L1 | long | 2026-04-21T17:15:00Z | 75213.7000 | -0.005200 |

## Worst Nearest Filled-Entry Deltas

| Trade | Event | Side | TV entry UTC | Nearest Python UTC | Delta | TV price | Python price | Python reason |
|---:|---|---|---|---|---:|---:|---:|---|
| 59 | ENTRY_L2 | long | 2026-04-21T17:15:00Z | 2026-04-23T00:30:00Z | 1875.0m | 75291.2000 | 78384.2000 | L2_FILL_ON_CLOSE |
| 32 | ENTRY_L2 | short | 2026-04-02T14:30:00Z | 2026-04-02T08:15:00Z | 375.0m | 66748.8000 | 66748.7178 | L2_FILL |
| 58 | ENTRY_L1 | long | 2026-04-21T17:15:00Z | 2026-04-21T21:15:00Z | 240.0m | 75213.7000 | 75537.5000 | L1_FILL_ON_CLOSE |
| 20 | ENTRY_L2 | short | 2026-03-23T02:15:00Z | 2026-03-23T02:00:00Z | 15.0m | 67849.4000 | 67875.6000 | L2_FILL |
| 1 | ENTRY_L1 | short | 2026-03-07T03:15:00Z | 2026-03-07T03:15:00Z | 0.0m | 68202.7000 | 68202.7000 | L1_FILL_ON_CLOSE |
| 3 | ENTRY_L2 | long | 2026-03-09T18:00:00Z | 2026-03-09T18:00:00Z | 0.0m | 68403.8000 | 68403.8000 | L2_FILL_ON_CLOSE |
| 2 | ENTRY_L1 | long | 2026-03-09T18:00:00Z | 2026-03-09T18:00:00Z | 0.0m | 68455.0000 | 68455.0662 | L1_FILL |
| 5 | ENTRY_L2 | long | 2026-03-10T18:15:00Z | 2026-03-10T18:15:00Z | 0.0m | 70289.0000 | 70289.0000 | L2_FILL_ON_CLOSE |
| 4 | ENTRY_L1 | long | 2026-03-10T18:15:00Z | 2026-03-10T18:15:00Z | 0.0m | 70248.8000 | 70248.8742 | L1_FILL |
| 6 | ENTRY_L1 | long | 2026-03-12T14:00:00Z | 2026-03-12T14:00:00Z | 0.0m | 70336.5000 | 70336.5000 | L1_FILL_ON_CLOSE |
| 7 | ENTRY_L2 | long | 2026-03-12T14:15:00Z | 2026-03-12T14:15:00Z | 0.0m | 69906.8000 | 69985.1108 | L2_FILL |
| 8 | ENTRY_L1 | long | 2026-03-14T21:30:00Z | 2026-03-14T21:30:00Z | 0.0m | 70644.4000 | 70644.4352 | L1_FILL |
| 9 | ENTRY_L2 | long | 2026-03-14T21:45:00Z | 2026-03-14T21:45:00Z | 0.0m | 70697.1000 | 70697.1242 | L2_FILL |
| 10 | ENTRY_L1 | long | 2026-03-15T15:00:00Z | 2026-03-15T15:00:00Z | 0.0m | 71567.7000 | 71567.7099 | L1_FILL |
| 11 | ENTRY_L2 | long | 2026-03-15T15:30:00Z | 2026-03-15T15:30:00Z | 0.0m | 71421.4000 | 71421.4362 | L2_FILL |
| 12 | ENTRY_L1 | long | 2026-03-17T17:00:00Z | 2026-03-17T17:00:00Z | 0.0m | 74110.4000 | 74110.4516 | L1_FILL |
| 13 | ENTRY_L2 | long | 2026-03-17T23:45:00Z | 2026-03-17T23:45:00Z | 0.0m | 73882.7000 | 73882.7596 | L2_FILL |
| 14 | ENTRY_L1 | short | 2026-03-18T21:15:00Z | 2026-03-18T21:15:00Z | 0.0m | 71203.4000 | 71203.4000 | L1_FILL_ON_CLOSE |
| 15 | ENTRY_L2 | short | 2026-03-18T21:30:00Z | 2026-03-18T21:30:00Z | 0.0m | 71292.5000 | 71203.4000 | L2_FILL |
| 16 | ENTRY_L1 | short | 2026-03-19T03:45:00Z | 2026-03-19T03:45:00Z | 0.0m | 71217.1000 | 71217.0488 | L1_FILL |

## Interpretation Notes
- This report compares TradingView filled trade rows only against Python `ENTRY_L1/L2/L3` rows.
- It intentionally does not compare TradingView rows to Python `ENTRY_SIGNAL`, because that is a pre-fill trigger.
- TradingView `net_pnl_pct` is not the same unit as Python `r_multiple`; use price/time/side first, then handle PnL separately.
- If Python date-window counts are much larger than TradingView counts, the next check is profile parity: chart timeframe, `entry_timeframe`, `execution_timeframe`, RSM overrides, and available TradingView history.
