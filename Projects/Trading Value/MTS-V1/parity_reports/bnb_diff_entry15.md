# MTS-V1 BNB TradingView/Python Diff

## Inputs
- TradingView raw CSV: `samples\tradingview_mtsv1_BNB_entry15_raw.csv`
- Python JSONL: `runs\mtsv1_tv_bnb_15m_binanceusdm_profile\trades.jsonl`
- Match tolerance: `15.0m`
- TradingView entry range: `2026-03-06T21:30:00Z` to `2026-04-20T06:00:00Z`
- TradingView raw rows: `85`
- TradingView common-window rows: `77`
- TradingView rows before Python artifact: `0`
- TradingView tail after Python artifact: `8`

## Counts

| Source | Scope | Count | By event | By side |
|---|---|---:|---|---|
| TradingView | common-window closed trades | 77 | `{'ENTRY_L1': 42, 'ENTRY_L2': 33, 'ENTRY_L3': 2}` | `{'long': 39, 'short': 38}` |
| TradingView | raw capture rows | 85 | | |
| TradingView | outside Python artifact | 8 | `{'before': 0, 'tail': 8}` | |
| Python | all `BNB` filled entries | 130 | `{'ENTRY_L1': 71, 'ENTRY_L2': 58, 'ENTRY_L3': 1}` | `{'long': 51, 'short': 79}` |
| Python | TradingView date window | 67 | `{'ENTRY_L1': 36, 'ENTRY_L2': 31}` | `{'long': 37, 'short': 30}` |

## Match Summary

| Metric | Value |
|---|---:|
| matched_common_window_tv_trades | 38 / 77 |
| common_window_match_rate | 0.493506 |
| unmatched_tv_trades | 39 |
| avg_abs_time_delta_minutes | 1.974 |
| avg_abs_entry_price_delta_pct | 0.000739 |
| exit_timestamp_matches | 25 / 38 |
| exit_price_within_0_15 | 1 / 38 |
| exit_price_within_1_0 | 27 / 38 |
| avg_abs_exit_price_delta | 1.015404 |
| max_abs_exit_price_delta | 3.580000 |
| unmatched_classification | `{'missing-python-cycle': 31, 'same-cycle-shift': 8}` |
| matched_exit_timing_residuals | `{'python_exit_early': 7, 'python_exit_late': 6}` |
| matched_exit_cause_buckets | `{'entry_cycle_drift': 3, 'non_state2_abort': 2, 'unknown_state2_abort': 8}` |

## Exit Reason Summary

| Python exit reason | Matched entries | Exit timestamp matches | Exit price <=0.15 | Exit price <=1.0 |
|---|---:|---:|---:|---:|
| HARD_SL | 12 | 10 | 0 | 8 |
| STATE_2_ABORT | 26 | 15 | 1 | 19 |

## State2 Trigger Source Summary

| Python State2 trigger | Matched State2 exits | Exit timestamp matches | Python exit early | Python exit late |
|---|---:|---:|---:|---:|
| unknown_state2_abort | 26 | 15 | 7 | 4 |

## Matched Exit Timing Residuals

| Trade | Timing bucket | Cause bucket | Python State2 trigger | Event | Side | TV entry UTC | TV exit UTC | Python entry UTC | Python exit UTC | Signed exit delta | CVD delta | Reverse threshold | Reverse ratio | Prev ratio | Prev pulse | Confirm bars | Last fill | Last fill age | L2 filled | Python exit reason | Python entry reason |
|---:|---|---|---|---|---|---|---|---|---|---:|---:|---:|---:|---:|---|---:|---|---:|---|---|---|
| 25 | python_exit_late | entry_cycle_drift | unknown_state2_abort | ENTRY_L1 | short | 2026-03-22T15:30:00Z | 2026-03-22T22:15:00Z | 2026-03-22T15:45:00Z | 2026-03-23T07:30:00Z | +555.0m |  |  |  |  |  |  |  |  |  | STATE_2_ABORT | L1_FILL |
| 26 | python_exit_late | unknown_state2_abort | unknown_state2_abort | ENTRY_L2 | short | 2026-03-22T17:00:00Z | 2026-03-22T22:15:00Z | 2026-03-22T17:00:00Z | 2026-03-23T07:30:00Z | +555.0m |  |  |  |  |  |  |  |  |  | STATE_2_ABORT | L2_FILL |
| 60 | python_exit_early | unknown_state2_abort | unknown_state2_abort | ENTRY_L1 | long | 2026-04-11T05:00:00Z | 2026-04-11T13:00:00Z | 2026-04-11T05:00:00Z | 2026-04-11T06:00:00Z | -420.0m |  |  |  |  |  |  |  |  |  | STATE_2_ABORT | L1_FILL |
| 61 | python_exit_early | entry_cycle_drift | unknown_state2_abort | ENTRY_L2 | long | 2026-04-11T05:15:00Z | 2026-04-11T13:00:00Z | 2026-04-11T05:00:00Z | 2026-04-11T06:00:00Z | -420.0m |  |  |  |  |  |  |  |  |  | STATE_2_ABORT | L2_FILL_ON_CLOSE |
| 50 | python_exit_late | non_state2_abort |  | ENTRY_L2 | short | 2026-04-05T04:15:00Z | 2026-04-05T10:30:00Z | 2026-04-05T04:15:00Z | 2026-04-05T15:15:00Z | +285.0m |  |  |  |  |  |  |  |  |  | HARD_SL | L2_FILL_ON_CLOSE |
| 49 | python_exit_late | non_state2_abort |  | ENTRY_L1 | short | 2026-04-05T04:15:00Z | 2026-04-05T10:30:00Z | 2026-04-05T04:15:00Z | 2026-04-05T15:15:00Z | +285.0m |  |  |  |  |  |  |  |  |  | HARD_SL | L1_FILL |
| 31 | python_exit_early | unknown_state2_abort | unknown_state2_abort | ENTRY_L1 | short | 2026-03-27T05:30:00Z | 2026-03-27T23:45:00Z | 2026-03-27T05:30:00Z | 2026-03-27T21:00:00Z | -165.0m |  |  |  |  |  |  |  |  |  | STATE_2_ABORT | L1_FILL |
| 32 | python_exit_early | entry_cycle_drift | unknown_state2_abort | ENTRY_L2 | short | 2026-03-27T07:15:00Z | 2026-03-27T23:45:00Z | 2026-03-27T07:00:00Z | 2026-03-27T21:00:00Z | -165.0m |  |  |  |  |  |  |  |  |  | STATE_2_ABORT | L2_FILL |
| 46 | python_exit_late | unknown_state2_abort | unknown_state2_abort | ENTRY_L1 | short | 2026-04-03T13:45:00Z | 2026-04-04T03:00:00Z | 2026-04-03T13:45:00Z | 2026-04-04T05:45:00Z | +165.0m |  |  |  |  |  |  |  |  |  | STATE_2_ABORT | L1_FILL |
| 47 | python_exit_late | unknown_state2_abort | unknown_state2_abort | ENTRY_L2 | short | 2026-04-03T14:15:00Z | 2026-04-04T03:00:00Z | 2026-04-03T14:15:00Z | 2026-04-04T05:45:00Z | +165.0m |  |  |  |  |  |  |  |  |  | STATE_2_ABORT | L2_FILL |
| 42 | python_exit_early | unknown_state2_abort | unknown_state2_abort | ENTRY_L2 | short | 2026-03-31T23:45:00Z | 2026-04-01T01:45:00Z | 2026-03-31T23:45:00Z | 2026-04-01T00:45:00Z | -60.0m |  |  |  |  |  |  |  |  |  | STATE_2_ABORT | L2_FILL |
| 58 | python_exit_early | unknown_state2_abort | unknown_state2_abort | ENTRY_L1 | long | 2026-04-10T16:15:00Z | 2026-04-10T21:30:00Z | 2026-04-10T16:15:00Z | 2026-04-10T20:30:00Z | -60.0m |  |  |  |  |  |  |  |  |  | STATE_2_ABORT | L1_FILL |
| 59 | python_exit_early | unknown_state2_abort | unknown_state2_abort | ENTRY_L2 | long | 2026-04-10T16:30:00Z | 2026-04-10T21:30:00Z | 2026-04-10T16:30:00Z | 2026-04-10T20:30:00Z | -60.0m |  |  |  |  |  |  |  |  |  | STATE_2_ABORT | L2_FILL |

## Worst Matched Exit Price Residuals

| Trade | Event | Side | TV entry UTC | TV exit UTC | Python entry UTC | Python exit UTC | TV exit price | Python exit price | Abs delta | Python exit reason | Python entry reason |
|---:|---|---|---|---|---|---|---:|---:|---:|---|---|
| 25 | ENTRY_L1 | short | 2026-03-22T15:30:00Z | 2026-03-22T22:15:00Z | 2026-03-22T15:45:00Z | 2026-03-23T07:30:00Z | 628.3800 | 624.8000 | 3.5800 | STATE_2_ABORT | L1_FILL |
| 26 | ENTRY_L2 | short | 2026-03-22T17:00:00Z | 2026-03-22T22:15:00Z | 2026-03-22T17:00:00Z | 2026-03-23T07:30:00Z | 628.3800 | 624.8000 | 3.5800 | STATE_2_ABORT | L2_FILL |
| 42 | ENTRY_L2 | short | 2026-03-31T23:45:00Z | 2026-04-01T01:45:00Z | 2026-03-31T23:45:00Z | 2026-04-01T00:45:00Z | 615.8000 | 618.9000 | 3.1000 | STATE_2_ABORT | L2_FILL |
| 73 | ENTRY_L1 | long | 2026-04-18T18:00:00Z | 2026-04-18T18:15:00Z | 2026-04-18T18:00:00Z | 2026-04-18T18:30:00Z | 632.6100 | 629.5362 | 3.0738 | HARD_SL | L1_FILL |
| 74 | ENTRY_L2 | long | 2026-04-18T18:15:00Z | 2026-04-18T18:15:00Z | 2026-04-18T18:15:00Z | 2026-04-18T18:30:00Z | 632.6100 | 629.5362 | 3.0738 | HARD_SL | L2_FILL |
| 31 | ENTRY_L1 | short | 2026-03-27T05:30:00Z | 2026-03-27T23:45:00Z | 2026-03-27T05:30:00Z | 2026-03-27T21:00:00Z | 613.7200 | 611.7000 | 2.0200 | STATE_2_ABORT | L1_FILL |
| 32 | ENTRY_L2 | short | 2026-03-27T07:15:00Z | 2026-03-27T23:45:00Z | 2026-03-27T07:00:00Z | 2026-03-27T21:00:00Z | 613.7200 | 611.7000 | 2.0200 | STATE_2_ABORT | L2_FILL |
| 55 | ENTRY_L2 | long | 2026-04-06T21:00:00Z | 2026-04-06T22:15:00Z | 2026-04-06T21:00:00Z | 2026-04-06T22:30:00Z | 604.9900 | 603.3349 | 1.6551 | HARD_SL | L2_FILL |
| 54 | ENTRY_L1 | long | 2026-04-06T21:00:00Z | 2026-04-06T22:15:00Z | 2026-04-06T20:45:00Z | 2026-04-06T22:30:00Z | 604.9900 | 603.3349 | 1.6551 | HARD_SL | L1_FILL |
| 58 | ENTRY_L1 | long | 2026-04-10T16:15:00Z | 2026-04-10T21:30:00Z | 2026-04-10T16:15:00Z | 2026-04-10T20:30:00Z | 607.0600 | 608.4000 | 1.3400 | STATE_2_ABORT | L1_FILL |
| 59 | ENTRY_L2 | long | 2026-04-10T16:30:00Z | 2026-04-10T21:30:00Z | 2026-04-10T16:30:00Z | 2026-04-10T20:30:00Z | 607.0600 | 608.4000 | 1.3400 | STATE_2_ABORT | L2_FILL |
| 71 | ENTRY_L1 | long | 2026-04-16T13:30:00Z | 2026-04-16T13:45:00Z | 2026-04-16T13:30:00Z | 2026-04-16T13:45:00Z | 618.0500 | 617.3000 | 0.7500 | STATE_2_ABORT | L1_FILL |
| 72 | ENTRY_L2 | long | 2026-04-16T13:45:00Z | 2026-04-16T13:45:00Z | 2026-04-16T13:45:00Z | 2026-04-16T13:45:00Z | 618.0500 | 617.3000 | 0.7500 | STATE_2_ABORT | L2_FILL |
| 63 | ENTRY_L1 | long | 2026-04-12T11:00:00Z | 2026-04-12T12:45:00Z | 2026-04-12T11:00:00Z | 2026-04-12T12:45:00Z | 593.1100 | 592.4000 | 0.7100 | STATE_2_ABORT | L1_FILL_ON_CLOSE |
| 64 | ENTRY_L2 | long | 2026-04-12T12:45:00Z | 2026-04-12T12:45:00Z | 2026-04-12T12:45:00Z | 2026-04-12T12:45:00Z | 593.1100 | 592.4000 | 0.7100 | STATE_2_ABORT | L2_FILL |
| 40 | ENTRY_L1 | short | 2026-03-31T23:15:00Z | 2026-04-01T01:00:00Z | 2026-03-31T23:15:00Z | 2026-04-01T00:45:00Z | 619.5600 | 618.9000 | 0.6600 | STATE_2_ABORT | L1_FILL_ON_CLOSE |
| 67 | ENTRY_L1 | short | 2026-04-13T08:00:00Z | 2026-04-13T11:00:00Z | 2026-04-13T08:00:00Z | 2026-04-13T11:00:00Z | 598.9300 | 598.3000 | 0.6300 | STATE_2_ABORT | L1_FILL_ON_CLOSE |
| 68 | ENTRY_L2 | short | 2026-04-13T09:00:00Z | 2026-04-13T11:00:00Z | 2026-04-13T09:00:00Z | 2026-04-13T11:00:00Z | 598.9300 | 598.3000 | 0.6300 | STATE_2_ABORT | L2_FILL |
| 70 | ENTRY_L2 | long | 2026-04-13T12:15:00Z | 2026-04-13T13:15:00Z | 2026-04-13T12:15:00Z | 2026-04-13T13:15:00Z | 597.4100 | 596.8000 | 0.6100 | STATE_2_ABORT | L2_FILL_ON_CLOSE |
| 69 | ENTRY_L1 | long | 2026-04-13T12:15:00Z | 2026-04-13T13:15:00Z | 2026-04-13T12:00:00Z | 2026-04-13T13:15:00Z | 597.4100 | 596.8000 | 0.6100 | STATE_2_ABORT | L1_FILL_ON_CLOSE |
| 60 | ENTRY_L1 | long | 2026-04-11T05:00:00Z | 2026-04-11T13:00:00Z | 2026-04-11T05:00:00Z | 2026-04-11T06:00:00Z | 604.6400 | 604.1000 | 0.5400 | STATE_2_ABORT | L1_FILL |
| 61 | ENTRY_L2 | long | 2026-04-11T05:15:00Z | 2026-04-11T13:00:00Z | 2026-04-11T05:00:00Z | 2026-04-11T06:00:00Z | 604.6400 | 604.1000 | 0.5400 | STATE_2_ABORT | L2_FILL_ON_CLOSE |
| 45 | ENTRY_L1 | short | 2026-04-03T08:45:00Z | 2026-04-03T11:15:00Z | 2026-04-03T08:45:00Z | 2026-04-03T11:15:00Z | 587.0400 | 586.6000 | 0.4400 | STATE_2_ABORT | L1_FILL |
| 50 | ENTRY_L2 | short | 2026-04-05T04:15:00Z | 2026-04-05T10:30:00Z | 2026-04-05T04:15:00Z | 2026-04-05T15:15:00Z | 595.0700 | 594.6327 | 0.4373 | HARD_SL | L2_FILL_ON_CLOSE |
| 49 | ENTRY_L1 | short | 2026-04-05T04:15:00Z | 2026-04-05T10:30:00Z | 2026-04-05T04:15:00Z | 2026-04-05T15:15:00Z | 595.0700 | 594.6327 | 0.4373 | HARD_SL | L1_FILL |
| 33 | ENTRY_L1 | short | 2026-03-28T02:45:00Z | 2026-03-28T06:15:00Z | 2026-03-28T02:45:00Z | 2026-03-28T06:15:00Z | 613.7200 | 613.3000 | 0.4200 | STATE_2_ABORT | L1_FILL |
| 29 | ENTRY_L1 | long | 2026-03-25T23:15:00Z | 2026-03-26T02:15:00Z | 2026-03-25T23:15:00Z | 2026-03-26T02:15:00Z | 644.7100 | 644.3186 | 0.3914 | HARD_SL | L1_FILL |
| 30 | ENTRY_L2 | long | 2026-03-25T23:30:00Z | 2026-03-26T02:15:00Z | 2026-03-25T23:30:00Z | 2026-03-26T02:15:00Z | 644.7100 | 644.3186 | 0.3914 | HARD_SL | L2_FILL |
| 11 | ENTRY_L2 | long | 2026-03-11T05:30:00Z | 2026-03-11T11:00:00Z | 2026-03-11T05:30:00Z | 2026-03-11T11:00:00Z | 636.3400 | 636.0168 | 0.3232 | HARD_SL | L2_FILL_ON_CLOSE |
| 10 | ENTRY_L1 | long | 2026-03-11T05:30:00Z | 2026-03-11T11:00:00Z | 2026-03-11T05:30:00Z | 2026-03-11T11:00:00Z | 636.3400 | 636.0168 | 0.3232 | HARD_SL | L1_FILL |
| 1 | ENTRY_L1 | short | 2026-03-06T21:30:00Z | 2026-03-07T03:00:00Z | 2026-03-06T21:30:00Z | 2026-03-07T03:00:00Z | 629.5200 | 629.2000 | 0.3200 | STATE_2_ABORT | L1_FILL |
| 46 | ENTRY_L1 | short | 2026-04-03T13:45:00Z | 2026-04-04T03:00:00Z | 2026-04-03T13:45:00Z | 2026-04-04T05:45:00Z | 588.9900 | 589.3000 | 0.3100 | STATE_2_ABORT | L1_FILL |

## Unmatched Classification

| Bucket | Count |
|---|---:|
| missing-python-cycle | 31 |
| same-cycle-shift | 8 |

## Unmatched TradingView Trades

| Trade | Class | Event | Side | TV entry UTC | TV entry price | TV pnl pct | Nearest Python UTC | Nearest event | Nearest side | Delta | Python reason |
|---:|---|---|---|---|---:|---:|---|---|---|---:|---|
| 4 | missing-python-cycle | ENTRY_L1 | short | 2026-03-08T00:15:00Z | 620.6700 | 0.002000 | 2026-03-07T08:15:00Z | ENTRY_L2 | short | 960.0m | L2_FILL |
| 5 | missing-python-cycle | ENTRY_L1 | short | 2026-03-08T12:00:00Z | 620.5200 | 0.001000 | 2026-03-09T03:15:00Z | ENTRY_L1 | short | 915.0m | L1_FILL |
| 6 | missing-python-cycle | ENTRY_L1 | short | 2026-03-08T22:30:00Z | 613.6300 | 0.850000 | 2026-03-09T03:15:00Z | ENTRY_L1 | short | 285.0m | L1_FILL |
| 7 | missing-python-cycle | ENTRY_L2 | short | 2026-03-08T22:45:00Z | 613.6900 | 0.840000 | 2026-03-09T03:15:00Z | ENTRY_L1 | short | 270.0m | L1_FILL |
| 9 | same-cycle-shift | ENTRY_L2 | long | 2026-03-10T14:00:00Z | 639.1200 | 0.010000 | 2026-03-10T18:00:00Z | ENTRY_L2 | long | 240.0m | L2_FILL_ON_CLOSE |
| 8 | same-cycle-shift | ENTRY_L1 | long | 2026-03-10T14:00:00Z | 639.9100 | 0.130000 | 2026-03-10T18:00:00Z | ENTRY_L1 | long | 240.0m | L1_FILL |
| 12 | missing-python-cycle | ENTRY_L1 | long | 2026-03-12T17:45:00Z | 651.8800 | 0.031400 | 2026-03-14T02:15:00Z | ENTRY_L1 | long | 1950.0m | L1_FILL |
| 13 | missing-python-cycle | ENTRY_L2 | long | 2026-03-12T18:15:00Z | 649.9700 | 0.034400 | 2026-03-14T02:15:00Z | ENTRY_L1 | long | 1920.0m | L1_FILL |
| 15 | same-cycle-shift | ENTRY_L2 | long | 2026-03-14T04:45:00Z | 655.4700 | 0.420000 | 2026-03-14T05:30:00Z | ENTRY_L2 | long | 45.0m | L2_FILL_ON_CLOSE |
| 14 | same-cycle-shift | ENTRY_L1 | long | 2026-03-14T04:45:00Z | 655.7700 | 0.470000 | 2026-03-14T05:30:00Z | ENTRY_L1 | long | 45.0m | L1_FILL |
| 16 | missing-python-cycle | ENTRY_L1 | long | 2026-03-15T16:15:00Z | 660.3700 | 0.300000 | 2026-03-14T19:15:00Z | ENTRY_L2 | long | 1260.0m | L2_FILL |
| 17 | missing-python-cycle | ENTRY_L2 | long | 2026-03-15T16:30:00Z | 659.4500 | 0.170000 | 2026-03-14T19:15:00Z | ENTRY_L2 | long | 1275.0m | L2_FILL |
| 18 | missing-python-cycle | ENTRY_L1 | long | 2026-03-18T07:45:00Z | 673.7300 | 0.270000 | 2026-03-19T03:30:00Z | ENTRY_L1 | short | 1185.0m | L1_FILL_ON_CLOSE |
| 19 | missing-python-cycle | ENTRY_L2 | long | 2026-03-18T10:30:00Z | 672.6600 | 0.120000 | 2026-03-19T03:30:00Z | ENTRY_L1 | short | 1020.0m | L1_FILL_ON_CLOSE |
| 21 | missing-python-cycle | ENTRY_L1 | short | 2026-03-20T06:15:00Z | 641.8500 | 0.370000 | 2026-03-20T01:00:00Z | ENTRY_L2 | short | 315.0m | L2_FILL |
| 22 | missing-python-cycle | ENTRY_L2 | short | 2026-03-20T07:30:00Z | 644.0700 | 0.020000 | 2026-03-20T01:00:00Z | ENTRY_L2 | short | 390.0m | L2_FILL |
| 24 | missing-python-cycle | ENTRY_L2 | short | 2026-03-20T22:00:00Z | 643.7800 | 0.060000 | 2026-03-21T04:30:00Z | ENTRY_L1 | short | 390.0m | L1_FILL_ON_CLOSE |
| 23 | missing-python-cycle | ENTRY_L1 | short | 2026-03-20T22:00:00Z | 643.2400 | 0.140000 | 2026-03-21T04:30:00Z | ENTRY_L1 | short | 390.0m | L1_FILL_ON_CLOSE |
| 27 | missing-python-cycle | ENTRY_L1 | short | 2026-03-23T10:15:00Z | 625.8700 | 0.640000 | 2026-03-23T23:30:00Z | ENTRY_L1 | long | 795.0m | L1_FILL_ON_CLOSE |
| 28 | missing-python-cycle | ENTRY_L2 | short | 2026-03-23T10:30:00Z | 625.2300 | 0.740000 | 2026-03-23T23:30:00Z | ENTRY_L1 | long | 780.0m | L1_FILL_ON_CLOSE |
| 34 | same-cycle-shift | ENTRY_L2 | short | 2026-03-28T03:30:00Z | 611.4900 | 0.360000 | 2026-03-28T06:00:00Z | ENTRY_L2 | short | 150.0m | L2_FILL |
| 35 | missing-python-cycle | ENTRY_L1 | short | 2026-03-29T07:30:00Z | 613.0000 | 0.000100 | 2026-03-30T00:15:00Z | ENTRY_L1 | short | 1005.0m | L1_FILL |
| 36 | missing-python-cycle | ENTRY_L2 | short | 2026-03-29T08:00:00Z | 613.7700 | 0.001400 | 2026-03-30T00:15:00Z | ENTRY_L1 | short | 975.0m | L1_FILL |
| 39 | missing-python-cycle | ENTRY_L1 | short | 2026-03-31T04:00:00Z | 613.3700 | 0.001800 | 2026-03-31T23:15:00Z | ENTRY_L1 | short | 1155.0m | L1_FILL_ON_CLOSE |
| 41 | same-cycle-shift | ENTRY_L2 | short | 2026-03-31T23:45:00Z | 617.9900 | 0.250000 | 2026-03-31T23:45:00Z | ENTRY_L2 | short | 0.0m | L2_FILL |
| 44 | missing-python-cycle | ENTRY_L3 | short | 2026-04-01T00:45:00Z | 618.9500 | 0.430000 | 2026-03-31T23:45:00Z | ENTRY_L2 | short | 60.0m | L2_FILL |
| 43 | missing-python-cycle | ENTRY_L3 | short | 2026-04-01T00:45:00Z | 618.9500 | 0.005100 | 2026-03-31T23:45:00Z | ENTRY_L2 | short | 60.0m | L2_FILL |
| 48 | missing-python-cycle | ENTRY_L1 | short | 2026-04-04T14:00:00Z | 590.4800 | 0.000100 | 2026-04-05T04:15:00Z | ENTRY_L1 | short | 855.0m | L1_FILL |
| 51 | missing-python-cycle | ENTRY_L1 | long | 2026-04-06T13:15:00Z | 605.6500 | 0.001300 | 2026-04-06T20:45:00Z | ENTRY_L1 | long | 450.0m | L1_FILL |
| 52 | missing-python-cycle | ENTRY_L1 | long | 2026-04-06T15:15:00Z | 607.6500 | 0.260000 | 2026-04-06T20:45:00Z | ENTRY_L1 | long | 330.0m | L1_FILL |
| 53 | missing-python-cycle | ENTRY_L2 | long | 2026-04-06T16:45:00Z | 606.6500 | 0.100000 | 2026-04-06T20:45:00Z | ENTRY_L1 | long | 240.0m | L1_FILL |
| 56 | missing-python-cycle | ENTRY_L1 | long | 2026-04-08T13:15:00Z | 613.8100 | 0.730000 | 2026-04-08T22:15:00Z | ENTRY_L1 | long | 540.0m | L1_FILL |

## Worst Nearest Filled-Entry Deltas

| Trade | Event | Side | TV entry UTC | Nearest Python UTC | Delta | TV price | Python price | Python reason |
|---:|---|---|---|---|---:|---:|---:|---|
| 44 | ENTRY_L3 | short | 2026-04-01T00:45:00Z |  |  | 618.9500 |  |  |
| 43 | ENTRY_L3 | short | 2026-04-01T00:45:00Z |  |  | 618.9500 |  |  |
| 19 | ENTRY_L2 | long | 2026-03-18T10:30:00Z | 2026-03-14T19:15:00Z | 5235.0m | 672.6600 | 652.5786 | L2_FILL |
| 18 | ENTRY_L1 | long | 2026-03-18T07:45:00Z | 2026-03-14T19:00:00Z | 5085.0m | 673.7300 | 652.8980 | L1_FILL |
| 77 | ENTRY_L1 | long | 2026-04-20T06:00:00Z | 2026-04-18T18:00:00Z | 2160.0m | 619.7300 | 632.7290 | L1_FILL |
| 13 | ENTRY_L2 | long | 2026-03-12T18:15:00Z | 2026-03-14T05:30:00Z | 2115.0m | 649.9700 | 654.8000 | L2_FILL_ON_CLOSE |
| 12 | ENTRY_L1 | long | 2026-03-12T17:45:00Z | 2026-03-14T02:15:00Z | 1950.0m | 651.8800 | 655.2416 | L1_FILL |
| 16 | ENTRY_L1 | long | 2026-03-15T16:15:00Z | 2026-03-14T19:00:00Z | 1275.0m | 660.3700 | 652.8980 | L1_FILL |
| 17 | ENTRY_L2 | long | 2026-03-15T16:30:00Z | 2026-03-14T19:15:00Z | 1275.0m | 659.4500 | 652.5786 | L2_FILL |
| 39 | ENTRY_L1 | short | 2026-03-31T04:00:00Z | 2026-03-31T23:15:00Z | 1155.0m | 613.3700 | 616.4000 | L1_FILL_ON_CLOSE |
| 4 | ENTRY_L1 | short | 2026-03-08T00:15:00Z | 2026-03-07T05:45:00Z | 1110.0m | 620.6700 | 628.0821 | L1_FILL |
| 27 | ENTRY_L1 | short | 2026-03-23T10:15:00Z | 2026-03-22T15:45:00Z | 1110.0m | 625.8700 | 629.1281 | L1_FILL |
| 28 | ENTRY_L2 | short | 2026-03-23T10:30:00Z | 2026-03-22T17:00:00Z | 1050.0m | 625.2300 | 630.4360 | L2_FILL |
| 35 | ENTRY_L1 | short | 2026-03-29T07:30:00Z | 2026-03-30T00:15:00Z | 1005.0m | 613.0000 | 609.4368 | L1_FILL |
| 36 | ENTRY_L2 | short | 2026-03-29T08:00:00Z | 2026-03-30T00:15:00Z | 975.0m | 613.7700 | 610.3000 | L2_FILL_ON_CLOSE |
| 5 | ENTRY_L1 | short | 2026-03-08T12:00:00Z | 2026-03-09T03:15:00Z | 915.0m | 620.5200 | 626.4304 | L1_FILL |
| 48 | ENTRY_L1 | short | 2026-04-04T14:00:00Z | 2026-04-05T04:15:00Z | 855.0m | 590.4800 | 592.9105 | L1_FILL |
| 56 | ENTRY_L1 | long | 2026-04-08T13:15:00Z | 2026-04-08T22:15:00Z | 540.0m | 613.8100 | 604.4156 | L1_FILL |
| 57 | ENTRY_L2 | long | 2026-04-08T13:30:00Z | 2026-04-08T22:15:00Z | 525.0m | 612.5000 | 604.6000 | L2_FILL_ON_CLOSE |
| 62 | ENTRY_L1 | long | 2026-04-11T15:15:00Z | 2026-04-11T07:00:00Z | 495.0m | 605.9800 | 605.1986 | L1_FILL |
| 51 | ENTRY_L1 | long | 2026-04-06T13:15:00Z | 2026-04-06T20:45:00Z | 450.0m | 605.6500 | 605.8240 | L1_FILL |
| 65 | ENTRY_L1 | long | 2026-04-12T18:30:00Z | 2026-04-12T11:00:00Z | 450.0m | 592.7800 | 594.5000 | L1_FILL_ON_CLOSE |
| 66 | ENTRY_L2 | long | 2026-04-12T20:00:00Z | 2026-04-12T12:45:00Z | 435.0m | 592.3400 | 593.4932 | L2_FILL |
| 24 | ENTRY_L2 | short | 2026-03-20T22:00:00Z | 2026-03-21T05:00:00Z | 420.0m | 643.7800 | 641.7798 | L2_FILL |
| 22 | ENTRY_L2 | short | 2026-03-20T07:30:00Z | 2026-03-20T01:00:00Z | 390.0m | 644.0700 | 641.4226 | L2_FILL |
| 23 | ENTRY_L1 | short | 2026-03-20T22:00:00Z | 2026-03-21T04:30:00Z | 390.0m | 643.2400 | 641.6000 | L1_FILL_ON_CLOSE |
| 21 | ENTRY_L1 | short | 2026-03-20T06:15:00Z | 2026-03-20T00:30:00Z | 345.0m | 641.8500 | 639.6576 | L1_FILL |
| 52 | ENTRY_L1 | long | 2026-04-06T15:15:00Z | 2026-04-06T20:45:00Z | 330.0m | 607.6500 | 605.8240 | L1_FILL |
| 6 | ENTRY_L1 | short | 2026-03-08T22:30:00Z | 2026-03-09T03:15:00Z | 285.0m | 613.6300 | 626.4304 | L1_FILL |
| 7 | ENTRY_L2 | short | 2026-03-08T22:45:00Z | 2026-03-09T03:15:00Z | 270.0m | 613.6900 | 623.1000 | L2_FILL_ON_CLOSE |
| 53 | ENTRY_L2 | long | 2026-04-06T16:45:00Z | 2026-04-06T21:00:00Z | 255.0m | 606.6500 | 605.8022 | L2_FILL |
| 9 | ENTRY_L2 | long | 2026-03-10T14:00:00Z | 2026-03-10T18:00:00Z | 240.0m | 639.1200 | 642.4000 | L2_FILL_ON_CLOSE |

## Interpretation Notes
- This report compares TradingView filled trade rows only against Python `ENTRY_L1/L2/L3` rows.
- It intentionally does not compare TradingView rows to Python `ENTRY_SIGNAL`, because that is a pre-fill trigger.
- TradingView `net_pnl_pct` is not the same unit as Python `r_multiple`; use price/time/side first, then handle PnL separately.
- If Python date-window counts are much larger than TradingView counts, the next check is profile parity: chart timeframe, `entry_timeframe`, `execution_timeframe`, RSM overrides, and available TradingView history.
