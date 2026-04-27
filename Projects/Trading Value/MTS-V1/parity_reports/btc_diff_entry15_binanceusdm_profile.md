# MTS-V1 BTC TradingView/Python Diff

## Inputs
- TradingView raw CSV: `samples\tradingview_mtsv1_BTC_entry15_raw.csv`
- Python JSONL: `runs\mtsv1_tv_btc_15m_binanceusdm_profile\trades.jsonl`
- Match tolerance: `15.0m`
- TradingView entry range: `2026-03-07T03:15:00Z` to `2026-04-24T14:45:00Z`

## Counts

| Source | Scope | Count | By event | By side |
|---|---|---:|---|---|
| TradingView | raw closed trades | 64 | `{'ENTRY_L1': 34, 'ENTRY_L2': 30}` | `{'long': 40, 'short': 24}` |
| Python | all `BTC` filled entries | 70 | `{'ENTRY_L1': 37, 'ENTRY_L2': 33}` | `{'long': 44, 'short': 26}` |
| Python | TradingView date window | 64 | `{'ENTRY_L1': 34, 'ENTRY_L2': 30}` | `{'long': 40, 'short': 24}` |

## Match Summary

| Metric | Value |
|---|---:|
| matched_tv_trades | 64 / 64 |
| match_rate | 1.000000 |
| unmatched_tv_trades | 0 |
| avg_abs_time_delta_minutes | 0.000 |
| avg_abs_entry_price_delta_pct | 0.000000 |

## Unmatched TradingView Trades

| Trade | Event | Side | TV entry UTC | TV entry price | TV pnl pct |
|---:|---|---|---|---:|---:|

## Worst Nearest Filled-Entry Deltas

| Trade | Event | Side | TV entry UTC | Nearest Python UTC | Delta | TV price | Python price | Python reason |
|---:|---|---|---|---|---:|---:|---:|---|
| 1 | ENTRY_L1 | short | 2026-03-07T03:15:00Z | 2026-03-07T03:15:00Z | 0.0m | 68202.7000 | 68202.7000 | L1_FILL_ON_CLOSE |
| 3 | ENTRY_L2 | long | 2026-03-09T18:00:00Z | 2026-03-09T18:00:00Z | 0.0m | 68403.8000 | 68403.8000 | L2_FILL_ON_CLOSE |
| 2 | ENTRY_L1 | long | 2026-03-09T18:00:00Z | 2026-03-09T18:00:00Z | 0.0m | 68455.0000 | 68455.0662 | L1_FILL |
| 5 | ENTRY_L2 | long | 2026-03-10T18:15:00Z | 2026-03-10T18:15:00Z | 0.0m | 70289.0000 | 70289.0000 | L2_FILL_ON_CLOSE |
| 4 | ENTRY_L1 | long | 2026-03-10T18:15:00Z | 2026-03-10T18:15:00Z | 0.0m | 70248.8000 | 70248.8742 | L1_FILL |
| 6 | ENTRY_L1 | long | 2026-03-12T14:00:00Z | 2026-03-12T14:00:00Z | 0.0m | 70336.5000 | 70336.5000 | L1_FILL_ON_CLOSE |
| 7 | ENTRY_L2 | long | 2026-03-12T14:15:00Z | 2026-03-12T14:15:00Z | 0.0m | 69906.8000 | 69906.8000 | L2_FILL_ON_CLOSE |
| 8 | ENTRY_L1 | long | 2026-03-14T21:30:00Z | 2026-03-14T21:30:00Z | 0.0m | 70644.4000 | 70644.4352 | L1_FILL |
| 9 | ENTRY_L2 | long | 2026-03-14T21:45:00Z | 2026-03-14T21:45:00Z | 0.0m | 70697.1000 | 70697.1242 | L2_FILL |
| 10 | ENTRY_L1 | long | 2026-03-15T15:00:00Z | 2026-03-15T15:00:00Z | 0.0m | 71567.7000 | 71567.7099 | L1_FILL |
| 11 | ENTRY_L2 | long | 2026-03-15T15:30:00Z | 2026-03-15T15:30:00Z | 0.0m | 71421.4000 | 71421.4362 | L2_FILL |
| 12 | ENTRY_L1 | long | 2026-03-17T17:00:00Z | 2026-03-17T17:00:00Z | 0.0m | 74110.4000 | 74110.4516 | L1_FILL |

## Interpretation Notes
- This report compares TradingView filled trade rows only against Python `ENTRY_L1/L2/L3` rows.
- It intentionally does not compare TradingView rows to Python `ENTRY_SIGNAL`, because that is a pre-fill trigger.
- TradingView `net_pnl_pct` is not the same unit as Python `r_multiple`; use price/time/side first, then handle PnL separately.
- If Python date-window counts are much larger than TradingView counts, the next check is profile parity: chart timeframe, `entry_timeframe`, `execution_timeframe`, RSM overrides, and available TradingView history.
