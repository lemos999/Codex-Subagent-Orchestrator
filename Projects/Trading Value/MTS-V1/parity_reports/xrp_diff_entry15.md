# MTS-V1 XRP TradingView/Python Diff

## Inputs
- TradingView raw CSV: `samples\tradingview_mtsv1_XRP_entry15_raw.csv`
- Python JSONL: `runs\mtsv1_tv_xrp_15m_binanceusdm_profile\trades.jsonl`
- Match tolerance: `15.0m`
- TradingView entry range: `2026-03-06T08:30:00Z` to `2026-04-22T15:00:00Z`
- TradingView raw rows: `58`
- TradingView common-window rows: `52`
- TradingView rows before Python artifact: `0`
- TradingView tail after Python artifact: `6`

## Counts

| Source | Scope | Count | By event | By side |
|---|---|---:|---|---|
| TradingView | common-window closed trades | 52 | `{'ENTRY_L1': 28, 'ENTRY_L2': 23, 'ENTRY_L3': 1}` | `{'long': 37, 'short': 15}` |
| TradingView | raw capture rows | 58 | | |
| TradingView | outside Python artifact | 6 | `{'before': 0, 'tail': 6}` | |
| Python | all `XRP` filled entries | 127 | `{'ENTRY_L1': 64, 'ENTRY_L2': 58, 'ENTRY_L3': 5}` | `{'long': 57, 'short': 70}` |
| Python | TradingView date window | 63 | `{'ENTRY_L1': 32, 'ENTRY_L2': 29, 'ENTRY_L3': 2}` | `{'long': 43, 'short': 20}` |

## Match Summary

| Metric | Value |
|---|---:|
| matched_common_window_tv_trades | 24 / 52 |
| common_window_match_rate | 0.461538 |
| unmatched_tv_trades | 28 |
| avg_abs_time_delta_minutes | 1.875 |
| avg_abs_entry_price_delta_pct | 0.000271 |
| exit_timestamp_matches | 13 / 24 |
| exit_price_within_0_15 | 24 / 24 |
| exit_price_within_1_0 | 24 / 24 |
| avg_abs_exit_price_delta | 0.007446 |
| max_abs_exit_price_delta | 0.021400 |
| unmatched_classification | `{'event-layer-drift': 3, 'missing-python-cycle': 22, 'same-cycle-shift': 3}` |
| matched_exit_timing_residuals | `{'python_exit_early': 5, 'python_exit_late': 6}` |
| matched_exit_cause_buckets | `{'unknown_state2_abort': 11}` |

## Exit Reason Summary

| Python exit reason | Matched entries | Exit timestamp matches | Exit price <=0.15 | Exit price <=1.0 |
|---|---:|---:|---:|---:|
| STATE_2_ABORT | 24 | 13 | 24 | 24 |

## State2 Trigger Source Summary

| Python State2 trigger | Matched State2 exits | Exit timestamp matches | Python exit early | Python exit late |
|---|---:|---:|---:|---:|
| unknown_state2_abort | 24 | 13 | 5 | 6 |

## Matched Exit Timing Residuals

| Trade | Timing bucket | Cause bucket | Python State2 trigger | Event | Side | TV entry UTC | TV exit UTC | Python entry UTC | Python exit UTC | Signed exit delta | CVD delta | Reverse threshold | Reverse ratio | Prev ratio | Prev pulse | Confirm bars | Last fill | Last fill age | L2 filled | Python exit reason | Python entry reason |
|---:|---|---|---|---|---|---|---|---|---|---:|---:|---:|---:|---:|---|---:|---|---:|---|---|---|
| 30 | python_exit_early | unknown_state2_abort | unknown_state2_abort | ENTRY_L1 | short | 2026-04-03T12:45:00Z | 2026-04-04T10:30:00Z | 2026-04-03T12:45:00Z | 2026-04-03T21:45:00Z | -765.0m |  |  |  |  |  |  |  |  |  | STATE_2_ABORT | L1_FILL_ON_CLOSE |
| 26 | python_exit_late | unknown_state2_abort | unknown_state2_abort | ENTRY_L1 | short | 2026-03-31T12:00:00Z | 2026-03-31T13:45:00Z | 2026-03-31T12:00:00Z | 2026-03-31T19:45:00Z | +360.0m |  |  |  |  |  |  |  |  |  | STATE_2_ABORT | L1_FILL |
| 27 | python_exit_late | unknown_state2_abort | unknown_state2_abort | ENTRY_L2 | short | 2026-03-31T12:15:00Z | 2026-03-31T13:45:00Z | 2026-03-31T12:15:00Z | 2026-03-31T19:45:00Z | +360.0m |  |  |  |  |  |  |  |  |  | STATE_2_ABORT | L2_FILL |
| 8 | python_exit_early | unknown_state2_abort | unknown_state2_abort | ENTRY_L2 | long | 2026-03-11T15:30:00Z | 2026-03-12T03:45:00Z | 2026-03-11T15:30:00Z | 2026-03-12T01:00:00Z | -165.0m |  |  |  |  |  |  |  |  |  | STATE_2_ABORT | L2_FILL_ON_CLOSE |
| 7 | python_exit_early | unknown_state2_abort | unknown_state2_abort | ENTRY_L1 | long | 2026-03-11T15:30:00Z | 2026-03-12T03:45:00Z | 2026-03-11T15:30:00Z | 2026-03-12T01:00:00Z | -165.0m |  |  |  |  |  |  |  |  |  | STATE_2_ABORT | L1_FILL |
| 11 | python_exit_early | unknown_state2_abort | unknown_state2_abort | ENTRY_L1 | long | 2026-03-14T00:00:00Z | 2026-03-14T06:30:00Z | 2026-03-14T00:00:00Z | 2026-03-14T04:45:00Z | -105.0m |  |  |  |  |  |  |  |  |  | STATE_2_ABORT | L1_FILL |
| 12 | python_exit_early | unknown_state2_abort | unknown_state2_abort | ENTRY_L2 | long | 2026-03-14T00:30:00Z | 2026-03-14T06:30:00Z | 2026-03-14T00:30:00Z | 2026-03-14T04:45:00Z | -105.0m |  |  |  |  |  |  |  |  |  | STATE_2_ABORT | L2_FILL |
| 9 | python_exit_late | unknown_state2_abort | unknown_state2_abort | ENTRY_L1 | long | 2026-03-12T14:00:00Z | 2026-03-12T14:30:00Z | 2026-03-12T14:00:00Z | 2026-03-12T15:45:00Z | +75.0m |  |  |  |  |  |  |  |  |  | STATE_2_ABORT | L1_FILL_ON_CLOSE |
| 10 | python_exit_late | unknown_state2_abort | unknown_state2_abort | ENTRY_L2 | long | 2026-03-12T14:15:00Z | 2026-03-12T14:30:00Z | 2026-03-12T14:15:00Z | 2026-03-12T15:45:00Z | +75.0m |  |  |  |  |  |  |  |  |  | STATE_2_ABORT | L2_FILL_ON_CLOSE |
| 13 | python_exit_late | unknown_state2_abort | unknown_state2_abort | ENTRY_L1 | long | 2026-03-18T06:15:00Z | 2026-03-18T10:30:00Z | 2026-03-18T06:15:00Z | 2026-03-18T11:30:00Z | +60.0m |  |  |  |  |  |  |  |  |  | STATE_2_ABORT | L1_FILL |
| 14 | python_exit_late | unknown_state2_abort | unknown_state2_abort | ENTRY_L2 | long | 2026-03-18T06:30:00Z | 2026-03-18T10:30:00Z | 2026-03-18T06:30:00Z | 2026-03-18T11:30:00Z | +60.0m |  |  |  |  |  |  |  |  |  | STATE_2_ABORT | L2_FILL |

## Worst Matched Exit Price Residuals

| Trade | Event | Side | TV entry UTC | TV exit UTC | Python entry UTC | Python exit UTC | TV exit price | Python exit price | Abs delta | Python exit reason | Python entry reason |
|---:|---|---|---|---|---|---|---:|---:|---:|---|---|
| 13 | ENTRY_L1 | long | 2026-03-18T06:15:00Z | 2026-03-18T10:30:00Z | 2026-03-18T06:15:00Z | 2026-03-18T11:30:00Z | 1.5127 | 1.4913 | 0.0214 | STATE_2_ABORT | L1_FILL |
| 14 | ENTRY_L2 | long | 2026-03-18T06:30:00Z | 2026-03-18T10:30:00Z | 2026-03-18T06:30:00Z | 2026-03-18T11:30:00Z | 1.5127 | 1.4913 | 0.0214 | STATE_2_ABORT | L2_FILL |
| 26 | ENTRY_L1 | short | 2026-03-31T12:00:00Z | 2026-03-31T13:45:00Z | 2026-03-31T12:00:00Z | 2026-03-31T19:45:00Z | 1.3273 | 1.3442 | 0.0169 | STATE_2_ABORT | L1_FILL |
| 27 | ENTRY_L2 | short | 2026-03-31T12:15:00Z | 2026-03-31T13:45:00Z | 2026-03-31T12:15:00Z | 2026-03-31T19:45:00Z | 1.3273 | 1.3442 | 0.0169 | STATE_2_ABORT | L2_FILL |
| 11 | ENTRY_L1 | long | 2026-03-14T00:00:00Z | 2026-03-14T06:30:00Z | 2026-03-14T00:00:00Z | 2026-03-14T04:45:00Z | 1.3857 | 1.3971 | 0.0114 | STATE_2_ABORT | L1_FILL |
| 12 | ENTRY_L2 | long | 2026-03-14T00:30:00Z | 2026-03-14T06:30:00Z | 2026-03-14T00:30:00Z | 2026-03-14T04:45:00Z | 1.3857 | 1.3971 | 0.0114 | STATE_2_ABORT | L2_FILL |
| 9 | ENTRY_L1 | long | 2026-03-12T14:00:00Z | 2026-03-12T14:30:00Z | 2026-03-12T14:00:00Z | 2026-03-12T15:45:00Z | 1.3693 | 1.3784 | 0.0091 | STATE_2_ABORT | L1_FILL_ON_CLOSE |
| 10 | ENTRY_L2 | long | 2026-03-12T14:15:00Z | 2026-03-12T14:30:00Z | 2026-03-12T14:15:00Z | 2026-03-12T15:45:00Z | 1.3693 | 1.3784 | 0.0091 | STATE_2_ABORT | L2_FILL_ON_CLOSE |
| 44 | ENTRY_L1 | long | 2026-04-16T10:00:00Z | 2026-04-16T13:45:00Z | 2026-04-16T10:00:00Z | 2026-04-16T13:45:00Z | 1.3986 | 1.4065 | 0.0079 | STATE_2_ABORT | L1_FILL |
| 45 | ENTRY_L2 | long | 2026-04-16T10:15:00Z | 2026-04-16T13:45:00Z | 2026-04-16T10:15:00Z | 2026-04-16T13:45:00Z | 1.3986 | 1.4065 | 0.0079 | STATE_2_ABORT | L2_FILL |
| 30 | ENTRY_L1 | short | 2026-04-03T12:45:00Z | 2026-04-04T10:30:00Z | 2026-04-03T12:45:00Z | 2026-04-03T21:45:00Z | 1.3108 | 1.3175 | 0.0067 | STATE_2_ABORT | L1_FILL_ON_CLOSE |
| 20 | ENTRY_L1 | long | 2026-03-24T09:30:00Z | 2026-03-24T13:15:00Z | 2026-03-24T09:30:00Z | 2026-03-24T13:30:00Z | 1.4091 | 1.4033 | 0.0058 | STATE_2_ABORT | L1_FILL_ON_CLOSE |
| 21 | ENTRY_L2 | long | 2026-03-24T10:00:00Z | 2026-03-24T13:15:00Z | 2026-03-24T10:00:00Z | 2026-03-24T13:30:00Z | 1.4091 | 1.4033 | 0.0058 | STATE_2_ABORT | L2_FILL |
| 8 | ENTRY_L2 | long | 2026-03-11T15:30:00Z | 2026-03-12T03:45:00Z | 2026-03-11T15:30:00Z | 2026-03-12T01:00:00Z | 1.3727 | 1.3784 | 0.0057 | STATE_2_ABORT | L2_FILL_ON_CLOSE |
| 7 | ENTRY_L1 | long | 2026-03-11T15:30:00Z | 2026-03-12T03:45:00Z | 2026-03-11T15:30:00Z | 2026-03-12T01:00:00Z | 1.3727 | 1.3784 | 0.0057 | STATE_2_ABORT | L1_FILL |
| 41 | ENTRY_L1 | long | 2026-04-11T13:45:00Z | 2026-04-12T01:30:00Z | 2026-04-11T14:00:00Z | 2026-04-12T01:30:00Z | 1.3374 | 1.3324 | 0.0050 | STATE_2_ABORT | L1_FILL_ON_CLOSE |
| 42 | ENTRY_L2 | long | 2026-04-11T14:30:00Z | 2026-04-12T01:30:00Z | 2026-04-11T14:15:00Z | 2026-04-12T01:30:00Z | 1.3374 | 1.3324 | 0.0050 | STATE_2_ABORT | L2_FILL_ON_CLOSE |
| 46 | ENTRY_L1 | long | 2026-04-19T01:45:00Z | 2026-04-19T06:00:00Z | 2026-04-19T01:30:00Z | 2026-04-19T06:00:00Z | 1.4221 | 1.4194 | 0.0027 | STATE_2_ABORT | L1_FILL |
| 32 | ENTRY_L2 | short | 2026-04-04T15:00:00Z | 2026-04-04T19:00:00Z | 2026-04-04T15:00:00Z | 2026-04-04T19:00:00Z | 1.3187 | 1.3207 | 0.0020 | STATE_2_ABORT | L2_FILL |
| 34 | ENTRY_L2 | long | 2026-04-06T12:45:00Z | 2026-04-06T17:00:00Z | 2026-04-06T12:45:00Z | 2026-04-06T17:00:00Z | 1.3346 | 1.3349 | 0.0003 | STATE_2_ABORT | L2_FILL_ON_CLOSE |
| 33 | ENTRY_L1 | long | 2026-04-06T12:45:00Z | 2026-04-06T17:00:00Z | 2026-04-06T12:45:00Z | 2026-04-06T17:00:00Z | 1.3346 | 1.3349 | 0.0003 | STATE_2_ABORT | L1_FILL |
| 19 | ENTRY_L1 | short | 2026-03-23T19:00:00Z | 2026-03-24T07:00:00Z | 2026-03-23T19:00:00Z | 2026-03-24T07:00:00Z | 1.4227 | 1.4228 | 0.0001 | STATE_2_ABORT | L1_FILL_ON_CLOSE |
| 25 | ENTRY_L2 | short | 2026-03-29T07:00:00Z | 2026-03-29T22:45:00Z | 2026-03-29T07:00:00Z | 2026-03-29T22:45:00Z | 1.3183 | 1.3184 | 0.0001 | STATE_2_ABORT | L2_FILL_ON_CLOSE |
| 24 | ENTRY_L1 | short | 2026-03-29T07:00:00Z | 2026-03-29T22:45:00Z | 2026-03-29T07:00:00Z | 2026-03-29T22:45:00Z | 1.3183 | 1.3184 | 0.0001 | STATE_2_ABORT | L1_FILL |

## Unmatched Classification

| Bucket | Count |
|---|---:|
| event-layer-drift | 3 |
| missing-python-cycle | 22 |
| same-cycle-shift | 3 |

## Unmatched TradingView Trades

| Trade | Class | Event | Side | TV entry UTC | TV entry price | TV pnl pct | Nearest Python UTC | Nearest event | Nearest side | Delta | Python reason |
|---:|---|---|---|---|---:|---:|---|---|---|---:|---|
| 1 | missing-python-cycle | ENTRY_L1 | long | 2026-03-06T08:30:00Z | 1.4025 | 0.790000 | 2026-03-07T12:00:00Z | ENTRY_L1 | short | 1650.0m | L1_FILL_ON_CLOSE |
| 2 | missing-python-cycle | ENTRY_L2 | long | 2026-03-06T09:00:00Z | 1.4007 | 0.660000 | 2026-03-07T12:00:00Z | ENTRY_L1 | short | 1620.0m | L1_FILL_ON_CLOSE |
| 4 | missing-python-cycle | ENTRY_L2 | short | 2026-03-07T17:15:00Z | 1.3628 | 0.500000 | 2026-03-07T12:30:00Z | ENTRY_L2 | short | 285.0m | L2_FILL |
| 3 | missing-python-cycle | ENTRY_L1 | short | 2026-03-07T17:15:00Z | 1.3639 | 0.420000 | 2026-03-07T12:30:00Z | ENTRY_L2 | short | 285.0m | L2_FILL |
| 5 | same-cycle-shift | ENTRY_L1 | long | 2026-03-09T18:45:00Z | 1.3609 | 0.012600 | 2026-03-09T21:30:00Z | ENTRY_L1 | long | 165.0m | L1_FILL |
| 6 | same-cycle-shift | ENTRY_L2 | long | 2026-03-09T19:00:00Z | 1.3606 | 0.012900 | 2026-03-09T22:00:00Z | ENTRY_L2 | long | 180.0m | L2_FILL |
| 16 | missing-python-cycle | ENTRY_L2 | short | 2026-03-19T19:00:00Z | 1.4475 | 0.220000 | 2026-03-19T06:00:00Z | ENTRY_L2 | short | 780.0m | L2_FILL |
| 15 | missing-python-cycle | ENTRY_L1 | short | 2026-03-19T19:00:00Z | 1.4508 | 0.990000 | 2026-03-19T06:00:00Z | ENTRY_L2 | short | 780.0m | L2_FILL |
| 18 | missing-python-cycle | ENTRY_L2 | short | 2026-03-21T20:15:00Z | 1.4402 | 0.009200 | 2026-03-23T19:00:00Z | ENTRY_L1 | short | 2805.0m | L1_FILL_ON_CLOSE |
| 17 | missing-python-cycle | ENTRY_L1 | short | 2026-03-21T20:15:00Z | 1.4393 | 0.008600 | 2026-03-23T19:00:00Z | ENTRY_L1 | short | 2805.0m | L1_FILL_ON_CLOSE |
| 22 | missing-python-cycle | ENTRY_L3 | long | 2026-03-24T13:15:00Z | 1.4090 | 0.003100 | 2026-03-24T10:00:00Z | ENTRY_L2 | long | 195.0m | L2_FILL |
| 23 | missing-python-cycle | ENTRY_L1 | short | 2026-03-28T18:15:00Z | 1.3448 | 0.009000 | 2026-03-29T07:00:00Z | ENTRY_L1 | short | 765.0m | L1_FILL |
| 29 | missing-python-cycle | ENTRY_L2 | long | 2026-04-01T16:00:00Z | 1.3520 | 0.790000 | 2026-04-01T05:30:00Z | ENTRY_L1 | long | 630.0m | L1_FILL |
| 28 | missing-python-cycle | ENTRY_L1 | long | 2026-04-01T16:00:00Z | 1.3524 | 0.820000 | 2026-04-01T05:30:00Z | ENTRY_L1 | long | 630.0m | L1_FILL |
| 31 | event-layer-drift | ENTRY_L1 | short | 2026-04-04T15:00:00Z | 1.3129 | 0.440000 | 2026-04-04T15:00:00Z | ENTRY_L2 | short | 0.0m | L2_FILL |
| 35 | missing-python-cycle | ENTRY_L1 | long | 2026-04-07T17:30:00Z | 1.3077 | 0.035100 | 2026-04-07T10:30:00Z | ENTRY_L2 | long | 420.0m | L2_FILL |
| 36 | missing-python-cycle | ENTRY_L2 | long | 2026-04-07T18:45:00Z | 1.3000 | 0.041200 | 2026-04-07T10:30:00Z | ENTRY_L2 | long | 495.0m | L2_FILL |
| 37 | missing-python-cycle | ENTRY_L1 | long | 2026-04-09T07:45:00Z | 1.3308 | 0.530000 | 2026-04-08T22:15:00Z | ENTRY_L2 | long | 570.0m | L2_FILL |
| 38 | missing-python-cycle | ENTRY_L2 | long | 2026-04-09T08:00:00Z | 1.3309 | 0.540000 | 2026-04-08T22:15:00Z | ENTRY_L2 | long | 585.0m | L2_FILL |
| 39 | missing-python-cycle | ENTRY_L1 | long | 2026-04-10T16:00:00Z | 1.3508 | 0.440000 | 2026-04-10T06:30:00Z | ENTRY_L2 | long | 570.0m | L2_FILL |
| 40 | missing-python-cycle | ENTRY_L2 | long | 2026-04-10T16:30:00Z | 1.3507 | 0.440000 | 2026-04-10T06:30:00Z | ENTRY_L2 | long | 600.0m | L2_FILL |
| 43 | missing-python-cycle | ENTRY_L1 | long | 2026-04-13T12:45:00Z | 1.3313 | 0.015100 | 2026-04-14T10:30:00Z | ENTRY_L1 | long | 1305.0m | L1_FILL |
| 47 | same-cycle-shift | ENTRY_L2 | long | 2026-04-19T02:00:00Z | 1.4304 | 0.580000 | 2026-04-19T01:30:00Z | ENTRY_L2 | long | 30.0m | L2_FILL_ON_CLOSE |
| 48 | missing-python-cycle | ENTRY_L1 | long | 2026-04-20T09:00:00Z | 1.4140 | 0.001200 | 2026-04-21T01:00:00Z | ENTRY_L1 | long | 960.0m | L1_FILL_ON_CLOSE |
| 49 | missing-python-cycle | ENTRY_L2 | long | 2026-04-20T09:15:00Z | 1.4150 | 0.000500 | 2026-04-21T01:00:00Z | ENTRY_L1 | long | 945.0m | L1_FILL_ON_CLOSE |
| 50 | missing-python-cycle | ENTRY_L1 | long | 2026-04-20T15:15:00Z | 1.4337 | 0.400000 | 2026-04-21T01:00:00Z | ENTRY_L1 | long | 585.0m | L1_FILL_ON_CLOSE |
| 52 | event-layer-drift | ENTRY_L2 | long | 2026-04-22T15:00:00Z | 1.4534 | 0.620000 | 2026-04-22T15:00:00Z | ENTRY_L1 | long | 0.0m | L1_FILL |
| 51 | event-layer-drift | ENTRY_L1 | long | 2026-04-22T15:00:00Z | 1.4545 | 0.690000 | 2026-04-22T15:00:00Z | ENTRY_L1 | long | 0.0m | L1_FILL |

## Worst Nearest Filled-Entry Deltas

| Trade | Event | Side | TV entry UTC | Nearest Python UTC | Delta | TV price | Python price | Python reason |
|---:|---|---|---|---|---:|---:|---:|---|
| 1 | ENTRY_L1 | long | 2026-03-06T08:30:00Z | 2026-03-09T21:30:00Z | 5100.0m | 1.4025 | 1.3696 | L1_FILL |
| 2 | ENTRY_L2 | long | 2026-03-06T09:00:00Z | 2026-03-09T22:00:00Z | 5100.0m | 1.4007 | 1.3703 | L2_FILL |
| 18 | ENTRY_L2 | short | 2026-03-21T20:15:00Z | 2026-03-19T06:00:00Z | 3735.0m | 1.4402 | 1.4724 | L2_FILL |
| 17 | ENTRY_L1 | short | 2026-03-21T20:15:00Z | 2026-03-23T19:00:00Z | 2805.0m | 1.4393 | 1.4371 | L1_FILL_ON_CLOSE |
| 51 | ENTRY_L1 | long | 2026-04-22T15:00:00Z | 2026-04-21T01:00:00Z | 2280.0m | 1.4545 | 1.4294 | L1_FILL_ON_CLOSE |
| 52 | ENTRY_L2 | long | 2026-04-22T15:00:00Z | 2026-04-21T02:00:00Z | 2220.0m | 1.4534 | 1.4230 | L2_FILL |
| 22 | ENTRY_L3 | long | 2026-03-24T13:15:00Z | 2026-03-25T15:15:00Z | 1560.0m | 1.4090 | 1.4028 | L3_FILL |
| 43 | ENTRY_L1 | long | 2026-04-13T12:45:00Z | 2026-04-14T10:30:00Z | 1305.0m | 1.3313 | 1.3687 | L1_FILL |
| 49 | ENTRY_L2 | long | 2026-04-20T09:15:00Z | 2026-04-21T02:00:00Z | 1005.0m | 1.4150 | 1.4230 | L2_FILL |
| 48 | ENTRY_L1 | long | 2026-04-20T09:00:00Z | 2026-04-21T01:00:00Z | 960.0m | 1.4140 | 1.4294 | L1_FILL_ON_CLOSE |
| 15 | ENTRY_L1 | short | 2026-03-19T19:00:00Z | 2026-03-19T05:00:00Z | 840.0m | 1.4508 | 1.4662 | L1_FILL |
| 16 | ENTRY_L2 | short | 2026-03-19T19:00:00Z | 2026-03-19T06:00:00Z | 780.0m | 1.4475 | 1.4724 | L2_FILL |
| 23 | ENTRY_L1 | short | 2026-03-28T18:15:00Z | 2026-03-29T07:00:00Z | 765.0m | 1.3448 | 1.3349 | L1_FILL |
| 39 | ENTRY_L1 | long | 2026-04-10T16:00:00Z | 2026-04-10T05:15:00Z | 645.0m | 1.3508 | 1.3473 | L1_FILL_ON_CLOSE |
| 29 | ENTRY_L2 | long | 2026-04-01T16:00:00Z | 2026-04-01T05:30:00Z | 630.0m | 1.3520 | 1.3413 | L2_FILL_ON_CLOSE |
| 28 | ENTRY_L1 | long | 2026-04-01T16:00:00Z | 2026-04-01T05:30:00Z | 630.0m | 1.3524 | 1.3412 | L1_FILL |
| 37 | ENTRY_L1 | long | 2026-04-09T07:45:00Z | 2026-04-08T21:30:00Z | 615.0m | 1.3308 | 1.3535 | L1_FILL |
| 40 | ENTRY_L2 | long | 2026-04-10T16:30:00Z | 2026-04-10T06:30:00Z | 600.0m | 1.3507 | 1.3419 | L2_FILL |
| 38 | ENTRY_L2 | long | 2026-04-09T08:00:00Z | 2026-04-08T22:15:00Z | 585.0m | 1.3309 | 1.3470 | L2_FILL |
| 50 | ENTRY_L1 | long | 2026-04-20T15:15:00Z | 2026-04-21T01:00:00Z | 585.0m | 1.4337 | 1.4294 | L1_FILL_ON_CLOSE |
| 35 | ENTRY_L1 | long | 2026-04-07T17:30:00Z | 2026-04-07T08:00:00Z | 570.0m | 1.3077 | 1.3123 | L1_FILL_ON_CLOSE |
| 36 | ENTRY_L2 | long | 2026-04-07T18:45:00Z | 2026-04-07T10:30:00Z | 495.0m | 1.3000 | 1.3086 | L2_FILL |
| 3 | ENTRY_L1 | short | 2026-03-07T17:15:00Z | 2026-03-07T12:00:00Z | 315.0m | 1.3639 | 1.3651 | L1_FILL_ON_CLOSE |
| 4 | ENTRY_L2 | short | 2026-03-07T17:15:00Z | 2026-03-07T12:30:00Z | 285.0m | 1.3628 | 1.3663 | L2_FILL |
| 31 | ENTRY_L1 | short | 2026-04-04T15:00:00Z | 2026-04-04T11:30:00Z | 210.0m | 1.3129 | 1.3127 | L1_FILL |
| 6 | ENTRY_L2 | long | 2026-03-09T19:00:00Z | 2026-03-09T22:00:00Z | 180.0m | 1.3606 | 1.3703 | L2_FILL |
| 5 | ENTRY_L1 | long | 2026-03-09T18:45:00Z | 2026-03-09T21:30:00Z | 165.0m | 1.3609 | 1.3696 | L1_FILL |
| 47 | ENTRY_L2 | long | 2026-04-19T02:00:00Z | 2026-04-19T01:30:00Z | 30.0m | 1.4304 | 1.4295 | L2_FILL_ON_CLOSE |
| 41 | ENTRY_L1 | long | 2026-04-11T13:45:00Z | 2026-04-11T14:00:00Z | 15.0m | 1.3441 | 1.3459 | L1_FILL_ON_CLOSE |
| 42 | ENTRY_L2 | long | 2026-04-11T14:30:00Z | 2026-04-11T14:15:00Z | 15.0m | 1.3416 | 1.3436 | L2_FILL_ON_CLOSE |
| 46 | ENTRY_L1 | long | 2026-04-19T01:45:00Z | 2026-04-19T01:30:00Z | 15.0m | 1.4310 | 1.4314 | L1_FILL |
| 8 | ENTRY_L2 | long | 2026-03-11T15:30:00Z | 2026-03-11T15:30:00Z | 0.0m | 1.3782 | 1.3783 | L2_FILL_ON_CLOSE |

## Interpretation Notes
- This report compares TradingView filled trade rows only against Python `ENTRY_L1/L2/L3` rows.
- It intentionally does not compare TradingView rows to Python `ENTRY_SIGNAL`, because that is a pre-fill trigger.
- TradingView `net_pnl_pct` is not the same unit as Python `r_multiple`; use price/time/side first, then handle PnL separately.
- If Python date-window counts are much larger than TradingView counts, the next check is profile parity: chart timeframe, `entry_timeframe`, `execution_timeframe`, RSM overrides, and available TradingView history.
