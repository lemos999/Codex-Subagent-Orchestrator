# MTS-V1 SOL TradingView/Python Diff

## Inputs
- TradingView raw CSV: `samples\tradingview_mtsv1_SOL_entry15_raw.csv`
- Python JSONL: `runs\mtsv1_tv_sol_15m_binanceusdm_profile\trades_confirm2_probe.jsonl`
- Match tolerance: `15.0m`
- TradingView entry range: `2026-03-06T08:15:00Z` to `2026-04-25T11:15:00Z`
- TradingView raw rows: `71`
- TradingView common-window rows: `71`
- TradingView rows before Python artifact: `0`
- TradingView tail after Python artifact: `0`

## Counts

| Source | Scope | Count | By event | By side |
|---|---|---:|---|---|
| TradingView | common-window closed trades | 71 | `{'ENTRY_L1': 37, 'ENTRY_L2': 33, 'ENTRY_L3': 1}` | `{'long': 41, 'short': 30}` |
| TradingView | raw capture rows | 71 | | |
| TradingView | outside Python artifact | 0 | `{'before': 0, 'tail': 0}` | |
| Python | all `SOL` filled entries | 68 | `{'ENTRY_L1': 35, 'ENTRY_L2': 32, 'ENTRY_L3': 1}` | `{'long': 31, 'short': 37}` |
| Python | TradingView date window | 38 | `{'ENTRY_L1': 20, 'ENTRY_L2': 18}` | `{'long': 27, 'short': 11}` |

## Match Summary

| Metric | Value |
|---|---:|
| matched_common_window_tv_trades | 28 / 71 |
| common_window_match_rate | 0.394366 |
| unmatched_tv_trades | 43 |
| avg_abs_time_delta_minutes | 2.679 |
| avg_abs_entry_price_delta_pct | 0.000341 |
| exit_timestamp_matches | 12 / 28 |
| exit_price_within_0_15 | 19 / 28 |
| exit_price_within_1_0 | 24 / 28 |
| avg_abs_exit_price_delta | 0.449899 |
| max_abs_exit_price_delta | 2.550000 |
| unmatched_classification | `{'event-layer-drift': 2, 'missing-python-cycle': 34, 'outside_python_artifact': 2, 'same-cycle-shift': 5}` |
| matched_exit_timing_residuals | `{'python_exit_late': 16}` |
| matched_exit_cause_buckets | `{'entry_cycle_drift': 1, 'non_state2_abort': 10, 'state2_htf_cross': 5}` |

## Exit Reason Summary

| Python exit reason | Matched entries | Exit timestamp matches | Exit price <=0.15 | Exit price <=1.0 |
|---|---:|---:|---:|---:|
| HARD_SL | 20 | 10 | 17 | 20 |
| STATE_2_ABORT | 8 | 2 | 2 | 4 |

## State2 Trigger Source Summary

| Python State2 trigger | Matched State2 exits | Exit timestamp matches | Python exit early | Python exit late |
|---|---:|---:|---:|---:|
| htf_cross | 8 | 2 | 0 | 6 |

## Matched Exit Timing Residuals

| Trade | Timing bucket | Cause bucket | Python State2 trigger | Event | Side | TV entry UTC | TV exit UTC | Python entry UTC | Python exit UTC | Signed exit delta | CVD delta | Reverse threshold | Reverse ratio | Prev ratio | Prev pulse | Confirm bars | Last fill | Last fill age | L2 filled | Python exit reason | Python entry reason |
|---:|---|---|---|---|---|---|---|---|---|---:|---:|---:|---:|---:|---|---:|---|---:|---|---|---|
| 19 | python_exit_late | non_state2_abort |  | ENTRY_L2 | short | 2026-03-18T18:30:00Z | 2026-03-19T03:15:00Z | 2026-03-18T18:30:00Z | 2026-03-23T11:00:00Z | +6225.0m |  |  |  |  |  |  |  | m |  | HARD_SL | L2_FILL_ON_CLOSE |
| 18 | python_exit_late | non_state2_abort |  | ENTRY_L1 | short | 2026-03-18T18:30:00Z | 2026-03-19T03:15:00Z | 2026-03-18T18:30:00Z | 2026-03-23T11:00:00Z | +6225.0m |  |  |  |  |  |  |  | m |  | HARD_SL | L1_FILL |
| 31 | python_exit_late | state2_htf_cross | htf_cross | ENTRY_L1 | short | 2026-03-27T06:15:00Z | 2026-03-28T06:15:00Z | 2026-03-27T06:15:00Z | 2026-03-30T15:45:00Z | +3450.0m | -26127.6400 | 195980.2663 | -0.1333 | 0.4048 | false | 2 | ENTRY_L1/L1_FILL | 4890.0m | false | STATE_2_ABORT | L1_FILL |
| 65 | python_exit_late | state2_htf_cross | htf_cross | ENTRY_L2 | long | 2026-04-20T10:45:00Z | 2026-04-21T12:30:00Z | 2026-04-20T10:45:00Z | 2026-04-23T03:45:00Z | +2355.0m | 2912.5460 | 132867.1418 | -0.0219 | 0.1449 | false | 2 | ENTRY_L2/L2_FILL_ON_CLOSE | 3900.0m | true | STATE_2_ABORT | L2_FILL_ON_CLOSE |
| 64 | python_exit_late | state2_htf_cross | htf_cross | ENTRY_L1 | long | 2026-04-20T10:45:00Z | 2026-04-21T12:30:00Z | 2026-04-20T10:45:00Z | 2026-04-23T03:45:00Z | +2355.0m | 2912.5460 | 132867.1418 | -0.0219 | 0.1449 | false | 2 | ENTRY_L2/L2_FILL_ON_CLOSE | 3900.0m | true | STATE_2_ABORT | L1_FILL |
| 11 | python_exit_late | state2_htf_cross | htf_cross | ENTRY_L1 | long | 2026-03-12T15:15:00Z | 2026-03-13T14:45:00Z | 2026-03-12T15:15:00Z | 2026-03-13T23:45:00Z | +540.0m | 2315.7350 | 70828.7234 | -0.0327 | -0.0092 | false | 2 | ENTRY_L2/L2_FILL | 1905.0m | true | STATE_2_ABORT | L1_FILL_ON_CLOSE |
| 12 | python_exit_late | state2_htf_cross | htf_cross | ENTRY_L2 | long | 2026-03-12T16:00:00Z | 2026-03-13T14:45:00Z | 2026-03-12T16:00:00Z | 2026-03-13T23:45:00Z | +540.0m | 2315.7350 | 70828.7234 | -0.0327 | -0.0092 | false | 2 | ENTRY_L2/L2_FILL | 1905.0m | true | STATE_2_ABORT | L2_FILL |
| 39 | python_exit_late | non_state2_abort |  | ENTRY_L1 | long | 2026-04-01T01:30:00Z | 2026-04-01T12:45:00Z | 2026-04-01T01:30:00Z | 2026-04-01T21:30:00Z | +525.0m |  |  |  |  |  |  |  | m |  | HARD_SL | L1_FILL_ON_CLOSE |
| 40 | python_exit_late | non_state2_abort |  | ENTRY_L2 | long | 2026-04-01T01:45:00Z | 2026-04-01T12:45:00Z | 2026-04-01T01:45:00Z | 2026-04-01T21:30:00Z | +525.0m |  |  |  |  |  |  |  | m |  | HARD_SL | L2_FILL_ON_CLOSE |
| 53 | python_exit_late | non_state2_abort |  | ENTRY_L2 | long | 2026-04-11T03:45:00Z | 2026-04-11T06:00:00Z | 2026-04-11T03:45:00Z | 2026-04-11T11:15:00Z | +315.0m |  |  |  |  |  |  |  | m |  | HARD_SL | L2_FILL_ON_CLOSE |
| 52 | python_exit_late | non_state2_abort |  | ENTRY_L1 | long | 2026-04-11T03:45:00Z | 2026-04-11T06:00:00Z | 2026-04-11T03:45:00Z | 2026-04-11T11:15:00Z | +315.0m |  |  |  |  |  |  |  | m |  | HARD_SL | L1_FILL |
| 59 | python_exit_late | entry_cycle_drift | htf_cross | ENTRY_L2 | long | 2026-04-13T18:00:00Z | 2026-04-14T14:30:00Z | 2026-04-13T18:15:00Z | 2026-04-14T19:45:00Z | +315.0m | -9401.8740 | 299174.8650 | 0.0314 | 0.0479 | false | 2 | ENTRY_L2/L2_FILL_ON_CLOSE | 1530.0m | true | STATE_2_ABORT | L2_FILL_ON_CLOSE |
| 62 | python_exit_late | non_state2_abort |  | ENTRY_L1 | long | 2026-04-18T02:30:00Z | 2026-04-18T03:45:00Z | 2026-04-18T02:30:00Z | 2026-04-18T08:00:00Z | +255.0m |  |  |  |  |  |  |  | m |  | HARD_SL | L1_FILL |
| 63 | python_exit_late | non_state2_abort |  | ENTRY_L2 | long | 2026-04-18T03:00:00Z | 2026-04-18T03:45:00Z | 2026-04-18T03:00:00Z | 2026-04-18T08:00:00Z | +255.0m |  |  |  |  |  |  |  | m |  | HARD_SL | L2_FILL |
| 60 | python_exit_late | non_state2_abort |  | ENTRY_L1 | long | 2026-04-15T04:45:00Z | 2026-04-15T05:30:00Z | 2026-04-15T04:45:00Z | 2026-04-15T07:15:00Z | +105.0m |  |  |  |  |  |  |  | m |  | HARD_SL | L1_FILL_ON_CLOSE |
| 61 | python_exit_late | non_state2_abort |  | ENTRY_L2 | long | 2026-04-15T05:15:00Z | 2026-04-15T05:30:00Z | 2026-04-15T05:15:00Z | 2026-04-15T07:15:00Z | +105.0m |  |  |  |  |  |  |  | m |  | HARD_SL | L2_FILL |

## Worst Matched Exit Price Residuals

| Trade | Event | Side | TV entry UTC | TV exit UTC | Python entry UTC | Python exit UTC | TV exit price | Python exit price | Abs delta | Python exit reason | Python entry reason |
|---:|---|---|---|---|---|---|---:|---:|---:|---|---|
| 11 | ENTRY_L1 | long | 2026-03-12T15:15:00Z | 2026-03-13T14:45:00Z | 2026-03-12T15:15:00Z | 2026-03-13T23:45:00Z | 90.6700 | 88.1200 | 2.5500 | STATE_2_ABORT | L1_FILL_ON_CLOSE |
| 12 | ENTRY_L2 | long | 2026-03-12T16:00:00Z | 2026-03-13T14:45:00Z | 2026-03-12T16:00:00Z | 2026-03-13T23:45:00Z | 90.6700 | 88.1200 | 2.5500 | STATE_2_ABORT | L2_FILL |
| 59 | ENTRY_L2 | long | 2026-04-13T18:00:00Z | 2026-04-14T14:30:00Z | 2026-04-13T18:15:00Z | 2026-04-14T19:45:00Z | 86.4100 | 83.8900 | 2.5200 | STATE_2_ABORT | L2_FILL_ON_CLOSE |
| 31 | ENTRY_L1 | short | 2026-03-27T06:15:00Z | 2026-03-28T06:15:00Z | 2026-03-27T06:15:00Z | 2026-03-30T15:45:00Z | 83.0800 | 84.4500 | 1.3700 | STATE_2_ABORT | L1_FILL |
| 39 | ENTRY_L1 | long | 2026-04-01T01:30:00Z | 2026-04-01T12:45:00Z | 2026-04-01T01:30:00Z | 2026-04-01T21:30:00Z | 82.9800 | 82.0636 | 0.9164 | HARD_SL | L1_FILL_ON_CLOSE |
| 40 | ENTRY_L2 | long | 2026-04-01T01:45:00Z | 2026-04-01T12:45:00Z | 2026-04-01T01:45:00Z | 2026-04-01T21:30:00Z | 82.9800 | 82.0636 | 0.9164 | HARD_SL | L2_FILL_ON_CLOSE |
| 65 | ENTRY_L2 | long | 2026-04-20T10:45:00Z | 2026-04-21T12:30:00Z | 2026-04-20T10:45:00Z | 2026-04-23T03:45:00Z | 85.2600 | 85.7300 | 0.4700 | STATE_2_ABORT | L2_FILL_ON_CLOSE |
| 64 | ENTRY_L1 | long | 2026-04-20T10:45:00Z | 2026-04-21T12:30:00Z | 2026-04-20T10:45:00Z | 2026-04-23T03:45:00Z | 85.2600 | 85.7300 | 0.4700 | STATE_2_ABORT | L1_FILL |
| 69 | ENTRY_L2 | long | 2026-04-23T17:00:00Z | 2026-04-23T17:30:00Z | 2026-04-23T17:00:00Z | 2026-04-23T17:15:00Z | 84.8100 | 85.0750 | 0.2650 | HARD_SL | L2_FILL |
| 43 | ENTRY_L1 | short | 2026-04-04T11:00:00Z | 2026-04-04T14:45:00Z | 2026-04-04T11:00:00Z | 2026-04-04T15:00:00Z | 80.3200 | 80.4433 | 0.1233 | HARD_SL | L1_FILL_ON_CLOSE |
| 60 | ENTRY_L1 | long | 2026-04-15T04:45:00Z | 2026-04-15T05:30:00Z | 2026-04-15T04:45:00Z | 2026-04-15T07:15:00Z | 82.9800 | 82.8994 | 0.0806 | HARD_SL | L1_FILL_ON_CLOSE |
| 61 | ENTRY_L2 | long | 2026-04-15T05:15:00Z | 2026-04-15T05:30:00Z | 2026-04-15T05:15:00Z | 2026-04-15T07:15:00Z | 82.9800 | 82.8994 | 0.0806 | HARD_SL | L2_FILL |
| 1 | ENTRY_L1 | long | 2026-03-06T08:15:00Z | 2026-03-06T09:15:00Z | 2026-03-06T08:30:00Z | 2026-03-06T09:15:00Z | 87.4400 | 87.3842 | 0.0558 | HARD_SL | L1_FILL_ON_CLOSE |
| 2 | ENTRY_L2 | long | 2026-03-06T08:45:00Z | 2026-03-06T09:15:00Z | 2026-03-06T09:00:00Z | 2026-03-06T09:15:00Z | 87.4400 | 87.3842 | 0.0558 | HARD_SL | L2_FILL |
| 29 | ENTRY_L1 | long | 2026-03-25T12:45:00Z | 2026-03-25T15:00:00Z | 2026-03-25T12:30:00Z | 2026-03-25T15:00:00Z | 91.7800 | 91.8104 | 0.0304 | HARD_SL | L1_FILL_ON_CLOSE |
| 30 | ENTRY_L2 | long | 2026-03-25T13:45:00Z | 2026-03-25T15:00:00Z | 2026-03-25T13:45:00Z | 2026-03-25T15:00:00Z | 91.7800 | 91.8104 | 0.0304 | HARD_SL | L2_FILL |
| 10 | ENTRY_L2 | long | 2026-03-10T18:30:00Z | 2026-03-11T09:45:00Z | 2026-03-10T18:30:00Z | 2026-03-11T09:45:00Z | 84.8200 | 84.8046 | 0.0154 | HARD_SL | L2_FILL_ON_CLOSE |
| 9 | ENTRY_L1 | long | 2026-03-10T18:30:00Z | 2026-03-11T09:45:00Z | 2026-03-10T18:30:00Z | 2026-03-11T09:45:00Z | 84.8200 | 84.8046 | 0.0154 | HARD_SL | L1_FILL |
| 53 | ENTRY_L2 | long | 2026-04-11T03:45:00Z | 2026-04-11T06:00:00Z | 2026-04-11T03:45:00Z | 2026-04-11T11:15:00Z | 83.8600 | 83.8704 | 0.0104 | HARD_SL | L2_FILL_ON_CLOSE |
| 52 | ENTRY_L1 | long | 2026-04-11T03:45:00Z | 2026-04-11T06:00:00Z | 2026-04-11T03:45:00Z | 2026-04-11T11:15:00Z | 83.8600 | 83.8704 | 0.0104 | HARD_SL | L1_FILL |
| 37 | ENTRY_L1 | short | 2026-03-31T04:30:00Z | 2026-03-31T19:45:00Z | 2026-03-31T04:15:00Z | 2026-03-31T19:45:00Z | 82.6700 | 82.6600 | 0.0100 | STATE_2_ABORT | L1_FILL_ON_CLOSE |
| 38 | ENTRY_L2 | short | 2026-03-31T05:45:00Z | 2026-03-31T19:45:00Z | 2026-03-31T05:45:00Z | 2026-03-31T19:45:00Z | 82.6700 | 82.6600 | 0.0100 | STATE_2_ABORT | L2_FILL |
| 19 | ENTRY_L2 | short | 2026-03-18T18:30:00Z | 2026-03-19T03:15:00Z | 2026-03-18T18:30:00Z | 2026-03-23T11:00:00Z | 91.3000 | 91.2909 | 0.0091 | HARD_SL | L2_FILL_ON_CLOSE |
| 18 | ENTRY_L1 | short | 2026-03-18T18:30:00Z | 2026-03-19T03:15:00Z | 2026-03-18T18:30:00Z | 2026-03-23T11:00:00Z | 91.3000 | 91.2909 | 0.0091 | HARD_SL | L1_FILL |
| 62 | ENTRY_L1 | long | 2026-04-18T02:30:00Z | 2026-04-18T03:45:00Z | 2026-04-18T02:30:00Z | 2026-04-18T08:00:00Z | 88.2800 | 88.2716 | 0.0084 | HARD_SL | L1_FILL |
| 63 | ENTRY_L2 | long | 2026-04-18T03:00:00Z | 2026-04-18T03:45:00Z | 2026-04-18T03:00:00Z | 2026-04-18T08:00:00Z | 88.2800 | 88.2716 | 0.0084 | HARD_SL | L2_FILL |
| 41 | ENTRY_L1 | short | 2026-04-03T03:15:00Z | 2026-04-03T07:30:00Z | 2026-04-03T03:15:00Z | 2026-04-03T07:30:00Z | 79.9200 | 79.9171 | 0.0029 | HARD_SL | L1_FILL_ON_CLOSE |
| 42 | ENTRY_L2 | short | 2026-04-03T04:00:00Z | 2026-04-03T07:30:00Z | 2026-04-03T04:00:00Z | 2026-04-03T07:30:00Z | 79.9200 | 79.9171 | 0.0029 | HARD_SL | L2_FILL |

## Unmatched Classification

| Bucket | Count |
|---|---:|
| event-layer-drift | 2 |
| missing-python-cycle | 34 |
| outside_python_artifact | 2 |
| same-cycle-shift | 5 |

## Unmatched TradingView Trades

| Trade | Class | Event | Side | TV entry UTC | TV entry price | TV pnl pct | Nearest Python UTC | Nearest event | Nearest side | Delta | Python reason |
|---:|---|---|---|---|---:|---:|---|---|---|---:|---|
| 4 | missing-python-cycle | ENTRY_L2 | short | 2026-03-07T14:30:00Z | 84.1500 | 0.013500 | 2026-03-06T09:00:00Z | ENTRY_L2 | long | 1770.0m | L2_FILL |
| 3 | missing-python-cycle | ENTRY_L1 | short | 2026-03-07T14:30:00Z | 84.3900 | 0.016400 | 2026-03-06T09:00:00Z | ENTRY_L2 | long | 1770.0m | L2_FILL |
| 6 | missing-python-cycle | ENTRY_L2 | short | 2026-03-08T05:30:00Z | 82.5400 | 0.910000 | 2026-03-09T03:15:00Z | ENTRY_L1 | short | 1305.0m | L1_FILL |
| 5 | missing-python-cycle | ENTRY_L1 | short | 2026-03-08T05:30:00Z | 82.7200 | 0.690000 | 2026-03-09T03:15:00Z | ENTRY_L1 | short | 1305.0m | L1_FILL |
| 7 | missing-python-cycle | ENTRY_L1 | long | 2026-03-09T21:30:00Z | 85.6600 | 0.004700 | 2026-03-09T03:15:00Z | ENTRY_L1 | short | 1095.0m | L1_FILL |
| 8 | missing-python-cycle | ENTRY_L2 | long | 2026-03-09T22:30:00Z | 85.6500 | 0.004800 | 2026-03-09T03:15:00Z | ENTRY_L1 | short | 1155.0m | L1_FILL |
| 14 | missing-python-cycle | ENTRY_L2 | long | 2026-03-14T14:30:00Z | 86.6000 | 0.013900 | 2026-03-14T19:00:00Z | ENTRY_L1 | long | 270.0m | L1_FILL |
| 13 | missing-python-cycle | ENTRY_L1 | long | 2026-03-14T14:30:00Z | 86.9700 | 0.009500 | 2026-03-14T19:00:00Z | ENTRY_L1 | long | 270.0m | L1_FILL |
| 15 | missing-python-cycle | ENTRY_L1 | long | 2026-03-15T19:15:00Z | 88.0500 | 0.058400 | 2026-03-14T19:00:00Z | ENTRY_L1 | long | 1455.0m | L1_FILL |
| 16 | missing-python-cycle | ENTRY_L1 | long | 2026-03-17T08:00:00Z | 94.4300 | 0.240000 | 2026-03-18T18:30:00Z | ENTRY_L1 | short | 2070.0m | L1_FILL |
| 17 | missing-python-cycle | ENTRY_L2 | long | 2026-03-17T09:00:00Z | 94.0600 | 0.850000 | 2026-03-18T18:30:00Z | ENTRY_L1 | short | 2010.0m | L1_FILL |
| 21 | missing-python-cycle | ENTRY_L2 | short | 2026-03-20T05:30:00Z | 89.3800 | 0.780000 | 2026-03-18T18:30:00Z | ENTRY_L1 | short | 2100.0m | L1_FILL |
| 20 | missing-python-cycle | ENTRY_L1 | short | 2026-03-20T05:30:00Z | 89.1400 | 0.050000 | 2026-03-18T18:30:00Z | ENTRY_L1 | short | 2100.0m | L1_FILL |
| 22 | missing-python-cycle | ENTRY_L1 | short | 2026-03-21T13:00:00Z | 90.0500 | 0.260000 | 2026-03-18T18:30:00Z | ENTRY_L1 | short | 3990.0m | L1_FILL |
| 23 | missing-python-cycle | ENTRY_L2 | short | 2026-03-21T13:15:00Z | 90.1300 | 0.170000 | 2026-03-18T18:30:00Z | ENTRY_L1 | short | 4005.0m | L1_FILL |
| 24 | missing-python-cycle | ENTRY_L1 | short | 2026-03-21T18:45:00Z | 89.7200 | 0.530000 | 2026-03-18T18:30:00Z | ENTRY_L1 | short | 4335.0m | L1_FILL |
| 25 | missing-python-cycle | ENTRY_L2 | short | 2026-03-21T19:00:00Z | 89.8300 | 0.410000 | 2026-03-18T18:30:00Z | ENTRY_L1 | short | 4350.0m | L1_FILL |
| 27 | missing-python-cycle | ENTRY_L2 | short | 2026-03-22T22:45:00Z | 86.6900 | 0.920000 | 2026-03-25T12:30:00Z | ENTRY_L1 | long | 3705.0m | L1_FILL_ON_CLOSE |
| 26 | missing-python-cycle | ENTRY_L1 | short | 2026-03-22T22:45:00Z | 86.3300 | 0.340000 | 2026-03-25T12:30:00Z | ENTRY_L1 | long | 3705.0m | L1_FILL_ON_CLOSE |
| 28 | missing-python-cycle | ENTRY_L3 | short | 2026-03-23T11:00:00Z | 90.5500 | 0.180000 | 2026-03-25T12:30:00Z | ENTRY_L1 | long | 2970.0m | L1_FILL_ON_CLOSE |
| 32 | missing-python-cycle | ENTRY_L1 | short | 2026-03-28T13:45:00Z | 83.3000 | 0.550000 | 2026-03-27T06:15:00Z | ENTRY_L1 | short | 1890.0m | L1_FILL |
| 33 | missing-python-cycle | ENTRY_L2 | short | 2026-03-28T15:15:00Z | 83.5000 | 0.310000 | 2026-03-27T06:15:00Z | ENTRY_L1 | short | 1980.0m | L1_FILL |
| 34 | missing-python-cycle | ENTRY_L1 | short | 2026-03-28T18:30:00Z | 83.4300 | 0.011500 | 2026-03-27T06:15:00Z | ENTRY_L1 | short | 2175.0m | L1_FILL |
| 35 | missing-python-cycle | ENTRY_L1 | short | 2026-03-30T15:00:00Z | 84.0700 | 0.450000 | 2026-03-31T04:15:00Z | ENTRY_L1 | short | 795.0m | L1_FILL_ON_CLOSE |
| 36 | missing-python-cycle | ENTRY_L2 | short | 2026-03-30T15:30:00Z | 84.2200 | 0.270000 | 2026-03-31T04:15:00Z | ENTRY_L1 | short | 765.0m | L1_FILL_ON_CLOSE |
| 44 | event-layer-drift | ENTRY_L2 | short | 2026-04-04T11:15:00Z | 80.1500 | 0.210000 | 2026-04-04T11:00:00Z | ENTRY_L1 | short | 15.0m | L1_FILL_ON_CLOSE |
| 45 | missing-python-cycle | ENTRY_L1 | short | 2026-04-04T23:00:00Z | 80.7600 | 0.010200 | 2026-04-04T11:45:00Z | ENTRY_L2 | short | 675.0m | L2_FILL |
| 47 | same-cycle-shift | ENTRY_L2 | long | 2026-04-08T03:30:00Z | 84.5700 | 0.410000 | 2026-04-08T07:30:00Z | ENTRY_L2 | long | 240.0m | L2_FILL_ON_CLOSE |
| 46 | same-cycle-shift | ENTRY_L1 | long | 2026-04-08T03:30:00Z | 84.5400 | 0.380000 | 2026-04-08T07:30:00Z | ENTRY_L1 | long | 240.0m | L1_FILL |
| 48 | missing-python-cycle | ENTRY_L1 | long | 2026-04-08T12:00:00Z | 84.4100 | 0.520000 | 2026-04-08T07:30:00Z | ENTRY_L1 | long | 270.0m | L1_FILL |
| 49 | missing-python-cycle | ENTRY_L2 | long | 2026-04-08T12:15:00Z | 84.3800 | 0.490000 | 2026-04-08T07:30:00Z | ENTRY_L1 | long | 285.0m | L1_FILL |
| 51 | missing-python-cycle | ENTRY_L2 | long | 2026-04-09T11:15:00Z | 82.1300 | 0.230000 | 2026-04-08T07:30:00Z | ENTRY_L1 | long | 1665.0m | L1_FILL |

## Worst Nearest Filled-Entry Deltas

| Trade | Event | Side | TV entry UTC | Nearest Python UTC | Delta | TV price | Python price | Python reason |
|---:|---|---|---|---|---:|---:|---:|---|
| 28 | ENTRY_L3 | short | 2026-03-23T11:00:00Z |  |  | 90.5500 |  |  |
| 56 | ENTRY_L1 | short | 2026-04-13T01:15:00Z | 2026-04-04T11:00:00Z | 12375.0m | 82.0300 | 80.1200 | L1_FILL_ON_CLOSE |
| 57 | ENTRY_L2 | short | 2026-04-13T01:45:00Z | 2026-04-04T11:45:00Z | 12360.0m | 82.2400 | 80.2072 | L2_FILL |
| 17 | ENTRY_L2 | long | 2026-03-17T09:00:00Z | 2026-03-12T16:00:00Z | 6780.0m | 94.0600 | 86.0223 | L2_FILL |
| 27 | ENTRY_L2 | short | 2026-03-22T22:45:00Z | 2026-03-18T18:30:00Z | 6015.0m | 86.6900 | 90.0000 | L2_FILL_ON_CLOSE |
| 26 | ENTRY_L1 | short | 2026-03-22T22:45:00Z | 2026-03-18T18:30:00Z | 6015.0m | 86.3300 | 90.2101 | L1_FILL |
| 25 | ENTRY_L2 | short | 2026-03-21T19:00:00Z | 2026-03-18T18:30:00Z | 4350.0m | 89.8300 | 90.0000 | L2_FILL_ON_CLOSE |
| 24 | ENTRY_L1 | short | 2026-03-21T18:45:00Z | 2026-03-18T18:30:00Z | 4335.0m | 89.7200 | 90.2101 | L1_FILL |
| 23 | ENTRY_L2 | short | 2026-03-21T13:15:00Z | 2026-03-18T18:30:00Z | 4005.0m | 90.1300 | 90.0000 | L2_FILL_ON_CLOSE |
| 22 | ENTRY_L1 | short | 2026-03-21T13:00:00Z | 2026-03-18T18:30:00Z | 3990.0m | 90.0500 | 90.2101 | L1_FILL |
| 33 | ENTRY_L2 | short | 2026-03-28T15:15:00Z | 2026-03-31T05:45:00Z | 3750.0m | 83.5000 | 83.7306 | L2_FILL |
| 16 | ENTRY_L1 | long | 2026-03-17T08:00:00Z | 2026-03-14T19:00:00Z | 3660.0m | 94.4300 | 86.9397 | L1_FILL |
| 14 | ENTRY_L2 | long | 2026-03-14T14:30:00Z | 2026-03-12T16:00:00Z | 2790.0m | 86.6000 | 86.0223 | L2_FILL |
| 70 | ENTRY_L1 | long | 2026-04-25T11:15:00Z | 2026-04-23T15:00:00Z | 2655.0m | 86.3500 | 85.7627 | L1_FILL |
| 71 | ENTRY_L2 | long | 2026-04-25T11:15:00Z | 2026-04-23T17:00:00Z | 2535.0m | 86.3300 | 85.7101 | L2_FILL |
| 4 | ENTRY_L2 | short | 2026-03-07T14:30:00Z | 2026-03-09T03:15:00Z | 2205.0m | 84.1500 | 83.5400 | L2_FILL_ON_CLOSE |
| 3 | ENTRY_L1 | short | 2026-03-07T14:30:00Z | 2026-03-09T03:15:00Z | 2205.0m | 84.3900 | 84.3921 | L1_FILL |
| 34 | ENTRY_L1 | short | 2026-03-28T18:30:00Z | 2026-03-27T06:15:00Z | 2175.0m | 83.4300 | 86.3221 | L1_FILL |
| 21 | ENTRY_L2 | short | 2026-03-20T05:30:00Z | 2026-03-18T18:30:00Z | 2100.0m | 89.3800 | 90.0000 | L2_FILL_ON_CLOSE |
| 20 | ENTRY_L1 | short | 2026-03-20T05:30:00Z | 2026-03-18T18:30:00Z | 2100.0m | 89.1400 | 90.2101 | L1_FILL |
| 32 | ENTRY_L1 | short | 2026-03-28T13:45:00Z | 2026-03-27T06:15:00Z | 1890.0m | 83.3000 | 86.3221 | L1_FILL |
| 67 | ENTRY_L2 | long | 2026-04-21T15:15:00Z | 2026-04-20T10:45:00Z | 1710.0m | 85.6700 | 84.8200 | L2_FILL_ON_CLOSE |
| 66 | ENTRY_L1 | long | 2026-04-21T15:15:00Z | 2026-04-20T10:45:00Z | 1710.0m | 86.0100 | 84.8050 | L1_FILL |
| 51 | ENTRY_L2 | long | 2026-04-09T11:15:00Z | 2026-04-08T07:30:00Z | 1665.0m | 82.1300 | 84.3300 | L2_FILL_ON_CLOSE |
| 50 | ENTRY_L1 | long | 2026-04-09T11:15:00Z | 2026-04-08T07:30:00Z | 1665.0m | 82.0600 | 84.4442 | L1_FILL |
| 15 | ENTRY_L1 | long | 2026-03-15T19:15:00Z | 2026-03-14T19:00:00Z | 1455.0m | 88.0500 | 86.9397 | L1_FILL |
| 6 | ENTRY_L2 | short | 2026-03-08T05:30:00Z | 2026-03-09T03:15:00Z | 1305.0m | 82.5400 | 83.5400 | L2_FILL_ON_CLOSE |
| 5 | ENTRY_L1 | short | 2026-03-08T05:30:00Z | 2026-03-09T03:15:00Z | 1305.0m | 82.7200 | 84.3921 | L1_FILL |
| 7 | ENTRY_L1 | long | 2026-03-09T21:30:00Z | 2026-03-10T18:30:00Z | 1260.0m | 85.6600 | 86.2956 | L1_FILL |
| 8 | ENTRY_L2 | long | 2026-03-09T22:30:00Z | 2026-03-10T18:30:00Z | 1200.0m | 85.6500 | 86.1800 | L2_FILL_ON_CLOSE |
| 36 | ENTRY_L2 | short | 2026-03-30T15:30:00Z | 2026-03-31T05:45:00Z | 855.0m | 84.2200 | 83.7306 | L2_FILL |
| 35 | ENTRY_L1 | short | 2026-03-30T15:00:00Z | 2026-03-31T04:15:00Z | 795.0m | 84.0700 | 83.3000 | L1_FILL_ON_CLOSE |

## Interpretation Notes
- This report compares TradingView filled trade rows only against Python `ENTRY_L1/L2/L3` rows.
- It intentionally does not compare TradingView rows to Python `ENTRY_SIGNAL`, because that is a pre-fill trigger.
- TradingView `net_pnl_pct` is not the same unit as Python `r_multiple`; use price/time/side first, then handle PnL separately.
- If Python date-window counts are much larger than TradingView counts, the next check is profile parity: chart timeframe, `entry_timeframe`, `execution_timeframe`, RSM overrides, and available TradingView history.
