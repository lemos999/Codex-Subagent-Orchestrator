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
| Python | all `BTC` filled entries | 107 | `{'ENTRY_L1': 56, 'ENTRY_L2': 51}` | `{'long': 44, 'short': 63}` |
| Python | TradingView date window | 64 | `{'ENTRY_L1': 34, 'ENTRY_L2': 30}` | `{'long': 40, 'short': 24}` |

## Match Summary

| Metric | Value |
|---|---:|
| matched_tv_trades | 64 / 64 |
| match_rate | 1.000000 |
| unmatched_tv_trades | 0 |
| avg_abs_time_delta_minutes | 0.000 |
| avg_abs_entry_price_delta_pct | 0.000000 |
| exit_timestamp_matches | 64 / 64 |
| exit_price_within_0_15 | 56 / 64 |
| exit_price_within_1_0 | 64 / 64 |
| avg_abs_exit_price_delta | 0.069745 |
| max_abs_exit_price_delta | 0.691901 |

## Unmatched TradingView Trades

| Trade | Event | Side | TV entry UTC | TV entry price | TV pnl pct |
|---:|---|---|---|---:|---:|

## Worst Nearest Filled-Entry Deltas

| Trade | Event | Side | TV entry UTC | Nearest Python UTC | Delta | TV price | Python price | Python reason |
|---:|---|---|---|---|---:|---:|---:|---|
| 1 | ENTRY_L1 | short | 2026-03-07T03:15:00Z | 2026-03-07T03:15:00Z | 0.0m | 68202.7000 | 68202.7000 | L1_FILL_ON_CLOSE |
| 3 | ENTRY_L2 | long | 2026-03-09T18:00:00Z | 2026-03-09T18:00:00Z | 0.0m | 68403.8000 | 68403.8000 | L2_FILL_ON_CLOSE |
| 2 | ENTRY_L1 | long | 2026-03-09T18:00:00Z | 2026-03-09T18:00:00Z | 0.0m | 68455.0000 | 68455.0662 | L1_FILL |

## Interpretation Notes
- This report compares TradingView filled trade rows only against Python `ENTRY_L1/L2/L3` rows.
- It intentionally does not compare TradingView rows to Python `ENTRY_SIGNAL`, because that is a pre-fill trigger.
- TradingView `net_pnl_pct` is not the same unit as Python `r_multiple`; use price/time/side first, then handle PnL separately.
- If Python date-window counts are much larger than TradingView counts, the next check is profile parity: chart timeframe, `entry_timeframe`, `execution_timeframe`, RSM overrides, and available TradingView history.
