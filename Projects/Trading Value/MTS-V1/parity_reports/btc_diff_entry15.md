# MTS-V1 BTC TradingView/Python Diff

## Inputs
- TradingView raw CSV: `samples\tradingview_mtsv1_BTC_entry15_raw.csv`
- Python JSONL: `runs\mtsv1_tv_btc_15m_binanceusdm_profile\trades.jsonl`
- Match tolerance: `15.0m`
- TradingView entry range: `2026-03-07T03:15:00Z` to `2026-04-24T14:45:00Z`
- TradingView raw rows: `64`
- TradingView common-window rows: `64`
- TradingView rows before Python artifact: `0`
- TradingView tail after Python artifact: `0`

## Counts

| Source | Scope | Count | By event | By side |
|---|---|---:|---|---|
| TradingView | common-window closed trades | 64 | `{'ENTRY_L1': 34, 'ENTRY_L2': 30}` | `{'long': 40, 'short': 24}` |
| TradingView | raw capture rows | 64 | | |
| TradingView | outside Python artifact | 0 | `{'before': 0, 'tail': 0}` | |
| Python | all `BTC` filled entries | 107 | `{'ENTRY_L1': 56, 'ENTRY_L2': 51}` | `{'long': 44, 'short': 63}` |
| Python | TradingView date window | 64 | `{'ENTRY_L1': 34, 'ENTRY_L2': 30}` | `{'long': 40, 'short': 24}` |

## Match Summary

| Metric | Value |
|---|---:|
| matched_common_window_tv_trades | 64 / 64 |
| common_window_match_rate | 1.000000 |
| unmatched_tv_trades | 0 |
| avg_abs_time_delta_minutes | 0.000 |
| avg_abs_entry_price_delta_pct | 0.000000 |
| exit_timestamp_matches | 64 / 64 |
| exit_price_within_0_15 | 62 / 64 |
| exit_price_within_1_0 | 64 / 64 |
| avg_abs_exit_price_delta | 0.042008 |
| max_abs_exit_price_delta | 0.179403 |
| unmatched_classification | `{}` |
| matched_exit_timing_residuals | `{}` |
| matched_exit_cause_buckets | `{}` |

## Exit Reason Summary

| Python exit reason | Matched entries | Exit timestamp matches | Exit price <=0.15 | Exit price <=1.0 |
|---|---:|---:|---:|---:|
| EVASION | 2 | 2 | 2 | 2 |
| HARD_SL | 36 | 36 | 34 | 36 |
| STATE_2_ABORT | 26 | 26 | 26 | 26 |

## State2 Trigger Source Summary

| Python State2 trigger | Matched State2 exits | Exit timestamp matches | Python exit early | Python exit late |
|---|---:|---:|---:|---:|
| unknown_state2_abort | 26 | 26 | 0 | 0 |

## Matched Exit Timing Residuals

| Trade | Timing bucket | Cause bucket | Python State2 trigger | Event | Side | TV entry UTC | TV exit UTC | Python entry UTC | Python exit UTC | Signed exit delta | CVD delta | Reverse threshold | Reverse ratio | Prev ratio | Prev pulse | Confirm bars | Last fill | Last fill age | L2 filled | Python exit reason | Python entry reason |
|---:|---|---|---|---|---|---|---|---|---|---:|---:|---:|---:|---:|---|---:|---|---:|---|---|---|

## Worst Matched Exit Price Residuals

| Trade | Event | Side | TV entry UTC | TV exit UTC | Python entry UTC | Python exit UTC | TV exit price | Python exit price | Abs delta | Python exit reason | Python entry reason |
|---:|---|---|---|---|---|---|---:|---:|---:|---|---|
| 41 | ENTRY_L1 | long | 2026-04-08T21:00:00Z | 2026-04-09T00:30:00Z | 2026-04-08T21:00:00Z | 2026-04-09T00:30:00Z | 70766.2000 | 70766.3794 | 0.1794 | HARD_SL | L1_FILL |
| 42 | ENTRY_L2 | long | 2026-04-08T22:15:00Z | 2026-04-09T00:30:00Z | 2026-04-08T22:15:00Z | 2026-04-09T00:30:00Z | 70766.2000 | 70766.3794 | 0.1794 | HARD_SL | L2_FILL |
| 54 | ENTRY_L1 | long | 2026-04-18T02:30:00Z | 2026-04-18T04:30:00Z | 2026-04-18T02:30:00Z | 2026-04-18T04:30:00Z | 76854.3000 | 76854.4351 | 0.1351 | HARD_SL | L1_FILL |
| 55 | ENTRY_L2 | long | 2026-04-18T03:15:00Z | 2026-04-18T04:30:00Z | 2026-04-18T03:15:00Z | 2026-04-18T04:30:00Z | 76854.3000 | 76854.4351 | 0.1351 | HARD_SL | L2_FILL |
| 52 | ENTRY_L1 | long | 2026-04-15T14:00:00Z | 2026-04-16T13:45:00Z | 2026-04-15T14:00:00Z | 2026-04-16T13:45:00Z | 73440.0000 | 73440.1218 | 0.1218 | HARD_SL | L1_FILL |
| 53 | ENTRY_L2 | long | 2026-04-15T14:30:00Z | 2026-04-16T13:45:00Z | 2026-04-15T14:30:00Z | 2026-04-16T13:45:00Z | 73440.0000 | 73440.1218 | 0.1218 | HARD_SL | L2_FILL |
| 17 | ENTRY_L1 | short | 2026-03-21T04:45:00Z | 2026-03-21T14:00:00Z | 2026-03-21T04:45:00Z | 2026-03-21T14:00:00Z | 70946.6000 | 70946.4868 | 0.1132 | HARD_SL | L1_FILL |
| 18 | ENTRY_L2 | short | 2026-03-21T05:15:00Z | 2026-03-21T14:00:00Z | 2026-03-21T05:15:00Z | 2026-03-21T14:00:00Z | 70946.6000 | 70946.4868 | 0.1132 | HARD_SL | L2_FILL |
| 23 | ENTRY_L1 | short | 2026-03-28T03:00:00Z | 2026-03-28T07:45:00Z | 2026-03-28T03:00:00Z | 2026-03-28T07:45:00Z | 66474.6000 | 66474.4893 | 0.1107 | HARD_SL | L1_FILL |
| 24 | ENTRY_L2 | short | 2026-03-28T04:15:00Z | 2026-03-28T07:45:00Z | 2026-03-28T04:15:00Z | 2026-03-28T07:45:00Z | 66474.6000 | 66474.4893 | 0.1107 | HARD_SL | L2_FILL |
| 35 | ENTRY_L1 | short | 2026-04-04T18:30:00Z | 2026-04-04T19:15:00Z | 2026-04-04T18:30:00Z | 2026-04-04T19:15:00Z | 67482.1000 | 67481.9904 | 0.1096 | HARD_SL | L1_FILL_ON_CLOSE |
| 36 | ENTRY_L2 | short | 2026-04-04T19:00:00Z | 2026-04-04T19:15:00Z | 2026-04-04T19:00:00Z | 2026-04-04T19:15:00Z | 67482.1000 | 67481.9904 | 0.1096 | HARD_SL | L2_FILL |
| 22 | ENTRY_L2 | long | 2026-03-25T15:00:00Z | 2026-03-26T05:45:00Z | 2026-03-25T15:00:00Z | 2026-03-26T05:45:00Z | 70191.9000 | 70191.9913 | 0.0913 | HARD_SL | L2_FILL_ON_CLOSE |
| 21 | ENTRY_L1 | long | 2026-03-25T15:00:00Z | 2026-03-26T05:45:00Z | 2026-03-25T15:00:00Z | 2026-03-26T05:45:00Z | 70191.9000 | 70191.9913 | 0.0913 | HARD_SL | L1_FILL |
| 33 | ENTRY_L1 | short | 2026-04-03T05:45:00Z | 2026-04-03T07:30:00Z | 2026-04-03T05:45:00Z | 2026-04-03T07:30:00Z | 66939.3000 | 66939.2127 | 0.0873 | HARD_SL | L1_FILL_ON_CLOSE |
| 34 | ENTRY_L2 | short | 2026-04-03T06:00:00Z | 2026-04-03T07:30:00Z | 2026-04-03T06:00:00Z | 2026-04-03T07:30:00Z | 66939.3000 | 66939.2127 | 0.0873 | HARD_SL | L2_FILL_ON_CLOSE |
| 27 | ENTRY_L1 | short | 2026-03-30T11:30:00Z | 2026-03-30T13:15:00Z | 2026-03-30T11:30:00Z | 2026-03-30T13:15:00Z | 68049.8000 | 68049.7131 | 0.0869 | HARD_SL | L1_FILL_ON_CLOSE |
| 28 | ENTRY_L2 | short | 2026-03-30T12:00:00Z | 2026-03-30T13:15:00Z | 2026-03-30T12:00:00Z | 2026-03-30T13:15:00Z | 68049.8000 | 68049.7131 | 0.0869 | HARD_SL | L2_FILL |
| 43 | ENTRY_L1 | long | 2026-04-10T05:00:00Z | 2026-04-10T07:45:00Z | 2026-04-10T05:00:00Z | 2026-04-10T07:45:00Z | 71569.2000 | 71569.2583 | 0.0583 | HARD_SL | L1_FILL |
| 44 | ENTRY_L2 | long | 2026-04-10T06:30:00Z | 2026-04-10T07:45:00Z | 2026-04-10T06:30:00Z | 2026-04-10T07:45:00Z | 71569.2000 | 71569.2583 | 0.0583 | HARD_SL | L2_FILL |
| 57 | ENTRY_L2 | long | 2026-04-19T05:00:00Z | 2026-04-19T07:00:00Z | 2026-04-19T05:00:00Z | 2026-04-19T07:00:00Z | 75230.1000 | 75230.1514 | 0.0514 | HARD_SL | L2_FILL_ON_CLOSE |
| 56 | ENTRY_L1 | long | 2026-04-19T05:00:00Z | 2026-04-19T07:00:00Z | 2026-04-19T05:00:00Z | 2026-04-19T07:00:00Z | 75230.1000 | 75230.1514 | 0.0514 | HARD_SL | L1_FILL |
| 19 | ENTRY_L1 | short | 2026-03-23T01:45:00Z | 2026-03-23T03:00:00Z | 2026-03-23T01:45:00Z | 2026-03-23T03:00:00Z | 68485.8000 | 68485.7490 | 0.0510 | HARD_SL | L1_FILL_ON_CLOSE |
| 20 | ENTRY_L2 | short | 2026-03-23T02:15:00Z | 2026-03-23T03:00:00Z | 2026-03-23T02:15:00Z | 2026-03-23T03:00:00Z | 68485.8000 | 68485.7490 | 0.0510 | HARD_SL | L2_FILL |
| 64 | ENTRY_L2 | long | 2026-04-24T14:45:00Z | 2026-04-24T17:30:00Z | 2026-04-24T14:45:00Z | 2026-04-24T17:30:00Z | 77441.8000 | 77441.8481 | 0.0481 | HARD_SL | L2_FILL_ON_CLOSE |
| 63 | ENTRY_L1 | long | 2026-04-24T14:45:00Z | 2026-04-24T17:30:00Z | 2026-04-24T14:45:00Z | 2026-04-24T17:30:00Z | 77441.8000 | 77441.8481 | 0.0481 | HARD_SL | L1_FILL |
| 5 | ENTRY_L2 | long | 2026-03-10T18:15:00Z | 2026-03-11T09:30:00Z | 2026-03-10T18:15:00Z | 2026-03-11T09:30:00Z | 69329.6000 | 69329.6423 | 0.0423 | HARD_SL | L2_FILL_ON_CLOSE |
| 4 | ENTRY_L1 | long | 2026-03-10T18:15:00Z | 2026-03-11T09:30:00Z | 2026-03-10T18:15:00Z | 2026-03-11T09:30:00Z | 69329.6000 | 69329.6423 | 0.0423 | HARD_SL | L1_FILL |
| 62 | ENTRY_L2 | long | 2026-04-23T00:30:00Z | 2026-04-23T02:30:00Z | 2026-04-23T00:30:00Z | 2026-04-23T02:30:00Z | 77824.0000 | 77824.0376 | 0.0376 | HARD_SL | L2_FILL_ON_CLOSE |
| 61 | ENTRY_L1 | long | 2026-04-23T00:30:00Z | 2026-04-23T02:30:00Z | 2026-04-23T00:30:00Z | 2026-04-23T02:30:00Z | 77824.0000 | 77824.0376 | 0.0376 | HARD_SL | L1_FILL |
| 48 | ENTRY_L2 | long | 2026-04-11T23:00:00Z | 2026-04-12T01:30:00Z | 2026-04-11T23:00:00Z | 2026-04-12T01:30:00Z | 72771.0000 | 72771.0203 | 0.0203 | HARD_SL | L2_FILL_ON_CLOSE |
| 47 | ENTRY_L1 | long | 2026-04-11T23:00:00Z | 2026-04-12T01:30:00Z | 2026-04-11T23:00:00Z | 2026-04-12T01:30:00Z | 72771.0000 | 72771.0203 | 0.0203 | HARD_SL | L1_FILL |

## Unmatched Classification

| Bucket | Count |
|---|---:|

## Unmatched TradingView Trades

| Trade | Class | Event | Side | TV entry UTC | TV entry price | TV pnl pct | Nearest Python UTC | Nearest event | Nearest side | Delta | Python reason |
|---:|---|---|---|---|---:|---:|---|---|---|---:|---|

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
| 13 | ENTRY_L2 | long | 2026-03-17T23:45:00Z | 2026-03-17T23:45:00Z | 0.0m | 73882.7000 | 73882.7596 | L2_FILL |
| 14 | ENTRY_L1 | short | 2026-03-18T21:15:00Z | 2026-03-18T21:15:00Z | 0.0m | 71203.4000 | 71203.4000 | L1_FILL_ON_CLOSE |
| 15 | ENTRY_L2 | short | 2026-03-18T21:30:00Z | 2026-03-18T21:30:00Z | 0.0m | 71292.5000 | 71292.5000 | L2_FILL_ON_CLOSE |
| 16 | ENTRY_L1 | short | 2026-03-19T03:45:00Z | 2026-03-19T03:45:00Z | 0.0m | 71217.1000 | 71217.0488 | L1_FILL |
| 17 | ENTRY_L1 | short | 2026-03-21T04:45:00Z | 2026-03-21T04:45:00Z | 0.0m | 70608.0000 | 70607.9637 | L1_FILL |
| 18 | ENTRY_L2 | short | 2026-03-21T05:15:00Z | 2026-03-21T05:15:00Z | 0.0m | 70718.9000 | 70718.8530 | L2_FILL |
| 19 | ENTRY_L1 | short | 2026-03-23T01:45:00Z | 2026-03-23T01:45:00Z | 0.0m | 67875.6000 | 67875.6000 | L1_FILL_ON_CLOSE |
| 20 | ENTRY_L2 | short | 2026-03-23T02:15:00Z | 2026-03-23T02:15:00Z | 0.0m | 67849.4000 | 67849.3242 | L2_FILL |
| 22 | ENTRY_L2 | long | 2026-03-25T15:00:00Z | 2026-03-25T15:00:00Z | 0.0m | 70788.1000 | 70788.1000 | L2_FILL_ON_CLOSE |
| 21 | ENTRY_L1 | long | 2026-03-25T15:00:00Z | 2026-03-25T15:00:00Z | 0.0m | 70858.6000 | 70858.6915 | L1_FILL |
| 23 | ENTRY_L1 | short | 2026-03-28T03:00:00Z | 2026-03-28T03:00:00Z | 0.0m | 66110.7000 | 66110.6186 | L1_FILL |
| 24 | ENTRY_L2 | short | 2026-03-28T04:15:00Z | 2026-03-28T04:15:00Z | 0.0m | 66249.2000 | 66249.1592 | L2_FILL |
| 25 | ENTRY_L1 | short | 2026-03-29T22:15:00Z | 2026-03-29T22:15:00Z | 0.0m | 66337.5000 | 66337.4104 | L1_FILL |
| 26 | ENTRY_L2 | short | 2026-03-30T00:15:00Z | 2026-03-30T00:15:00Z | 0.0m | 66636.4000 | 66636.3260 | L2_FILL |
| 27 | ENTRY_L1 | short | 2026-03-30T11:30:00Z | 2026-03-30T11:30:00Z | 0.0m | 67565.8000 | 67565.8000 | L1_FILL_ON_CLOSE |
| 28 | ENTRY_L2 | short | 2026-03-30T12:00:00Z | 2026-03-30T12:00:00Z | 0.0m | 67744.1000 | 67744.0846 | L2_FILL |
| 29 | ENTRY_L1 | short | 2026-03-31T15:45:00Z | 2026-03-31T15:45:00Z | 0.0m | 66700.0000 | 66700.0000 | L1_FILL_ON_CLOSE |
| 30 | ENTRY_L2 | short | 2026-03-31T16:30:00Z | 2026-03-31T16:30:00Z | 0.0m | 67234.3000 | 67234.2852 | L2_FILL |
| 31 | ENTRY_L1 | short | 2026-04-02T08:00:00Z | 2026-04-02T08:00:00Z | 0.0m | 66743.9000 | 66743.9000 | L1_FILL_ON_CLOSE |
| 32 | ENTRY_L2 | short | 2026-04-02T14:30:00Z | 2026-04-02T14:30:00Z | 0.0m | 66748.8000 | 66748.7178 | L2_FILL |

## Interpretation Notes
- This report compares TradingView filled trade rows only against Python `ENTRY_L1/L2/L3` rows.
- It intentionally does not compare TradingView rows to Python `ENTRY_SIGNAL`, because that is a pre-fill trigger.
- TradingView `net_pnl_pct` is not the same unit as Python `r_multiple`; use price/time/side first, then handle PnL separately.
- If Python date-window counts are much larger than TradingView counts, the next check is profile parity: chart timeframe, `entry_timeframe`, `execution_timeframe`, RSM overrides, and available TradingView history.
