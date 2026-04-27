# MTS-V1 SOL TradingView/Python Diff

## Inputs
- TradingView raw CSV: `samples\tradingview_mtsv1_SOL_entry15_raw.csv`
- Python JSONL: `runs\mtsv1_tv_sol_15m_binanceusdm_profile\trades_l2hold60_probe.jsonl`
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
| Python | all `SOL` filled entries | 115 | `{'ENTRY_L1': 62, 'ENTRY_L2': 50, 'ENTRY_L3': 3}` | `{'long': 48, 'short': 67}` |
| Python | TradingView date window | 63 | `{'ENTRY_L1': 35, 'ENTRY_L2': 27, 'ENTRY_L3': 1}` | `{'long': 40, 'short': 23}` |

## Match Summary

| Metric | Value |
|---|---:|
| matched_common_window_tv_trades | 40 / 71 |
| common_window_match_rate | 0.563380 |
| unmatched_tv_trades | 31 |
| avg_abs_time_delta_minutes | 1.875 |
| avg_abs_entry_price_delta_pct | 0.000299 |
| exit_timestamp_matches | 26 / 40 |
| exit_price_within_0_15 | 34 / 40 |
| exit_price_within_1_0 | 40 / 40 |
| avg_abs_exit_price_delta | 0.074425 |
| max_abs_exit_price_delta | 0.520000 |
| unmatched_classification | `{'event-layer-drift': 2, 'missing-python-cycle': 19, 'outside_python_artifact': 2, 'same-cycle-shift': 8}` |
| matched_exit_timing_residuals | `{'python_exit_early': 5, 'python_exit_late': 9}` |
| matched_exit_cause_buckets | `{'non_state2_abort': 9, 'same_bar_close_or_fill_ordering': 1, 'state2_reverse_spike': 4}` |

## Exit Reason Summary

| Python exit reason | Matched entries | Exit timestamp matches | Exit price <=0.15 | Exit price <=1.0 |
|---|---:|---:|---:|---:|
| HARD_SL | 19 | 10 | 18 | 19 |
| STATE_2_ABORT | 21 | 16 | 16 | 21 |

## State2 Trigger Source Summary

| Python State2 trigger | Matched State2 exits | Exit timestamp matches | Python exit early | Python exit late |
|---|---:|---:|---:|---:|
| htf_cross | 4 | 4 | 0 | 0 |
| reverse_spike | 16 | 12 | 4 | 0 |
| unknown | 1 | 0 | 1 | 0 |

## Matched Exit Timing Residuals

| Trade | Timing bucket | Cause bucket | Python State2 trigger | Event | Side | TV entry UTC | TV exit UTC | Python entry UTC | Python exit UTC | Signed exit delta | CVD delta | Reverse threshold | Reverse ratio | Prev ratio | Prev pulse | Confirm bars | Last fill | Last fill age | L2 filled | Python exit reason | Python entry reason |
|---:|---|---|---|---|---|---|---|---|---|---:|---:|---:|---:|---:|---|---:|---|---:|---|---|---|
| 23 | python_exit_late | non_state2_abort |  | ENTRY_L2 | short | 2026-03-21T13:15:00Z | 2026-03-21T14:00:00Z | 2026-03-21T13:30:00Z | 2026-03-23T11:00:00Z | +2700.0m |  |  |  |  |  |  |  |  |  | HARD_SL | L2_FILL_ON_CLOSE |
| 65 | python_exit_early | state2_reverse_spike | reverse_spike | ENTRY_L2 | long | 2026-04-20T10:45:00Z | 2026-04-21T12:30:00Z | 2026-04-20T10:45:00Z | 2026-04-20T14:45:00Z | -1305.0m | -121376.0080 | 121189.8383 | 1.0015 | 0.1803 | false | 1 | ENTRY_L2/L2_FILL_ON_CLOSE | 240.0m | true | STATE_2_ABORT | L2_FILL_ON_CLOSE |
| 64 | python_exit_early | state2_reverse_spike | reverse_spike | ENTRY_L1 | long | 2026-04-20T10:45:00Z | 2026-04-21T12:30:00Z | 2026-04-20T10:45:00Z | 2026-04-20T14:45:00Z | -1305.0m | -121376.0080 | 121189.8383 | 1.0015 | 0.1803 | false | 1 | ENTRY_L2/L2_FILL_ON_CLOSE | 240.0m | true | STATE_2_ABORT | L1_FILL |
| 56 | python_exit_early | state2_reverse_spike | reverse_spike | ENTRY_L1 | short | 2026-04-13T01:15:00Z | 2026-04-13T12:45:00Z | 2026-04-13T01:15:00Z | 2026-04-13T06:15:00Z | -390.0m | 68821.0200 | 52390.8597 | 1.3136 | 0.3154 | false | 1 | ENTRY_L2/L2_FILL | 270.0m | true | STATE_2_ABORT | L1_FILL |
| 57 | python_exit_early | state2_reverse_spike | reverse_spike | ENTRY_L2 | short | 2026-04-13T01:45:00Z | 2026-04-13T12:45:00Z | 2026-04-13T01:45:00Z | 2026-04-13T06:15:00Z | -390.0m | 68821.0200 | 52390.8597 | 1.3136 | 0.3154 | false | 1 | ENTRY_L2/L2_FILL | 270.0m | true | STATE_2_ABORT | L2_FILL |
| 53 | python_exit_late | non_state2_abort |  | ENTRY_L2 | long | 2026-04-11T03:45:00Z | 2026-04-11T06:00:00Z | 2026-04-11T03:45:00Z | 2026-04-11T11:15:00Z | +315.0m |  |  |  |  |  |  |  |  |  | HARD_SL | L2_FILL_ON_CLOSE |
| 52 | python_exit_late | non_state2_abort |  | ENTRY_L1 | long | 2026-04-11T03:45:00Z | 2026-04-11T06:00:00Z | 2026-04-11T03:45:00Z | 2026-04-11T11:15:00Z | +315.0m |  |  |  |  |  |  |  |  |  | HARD_SL | L1_FILL |
| 62 | python_exit_late | non_state2_abort |  | ENTRY_L1 | long | 2026-04-18T02:30:00Z | 2026-04-18T03:45:00Z | 2026-04-18T02:30:00Z | 2026-04-18T08:00:00Z | +255.0m |  |  |  |  |  |  |  |  |  | HARD_SL | L1_FILL |
| 63 | python_exit_late | non_state2_abort |  | ENTRY_L2 | long | 2026-04-18T03:00:00Z | 2026-04-18T03:45:00Z | 2026-04-18T03:00:00Z | 2026-04-18T08:00:00Z | +255.0m |  |  |  |  |  |  |  |  |  | HARD_SL | L2_FILL |
| 16 | python_exit_late | non_state2_abort |  | ENTRY_L1 | long | 2026-03-17T08:00:00Z | 2026-03-17T10:45:00Z | 2026-03-17T08:00:00Z | 2026-03-17T12:30:00Z | +105.0m |  |  |  |  |  |  |  |  |  | HARD_SL | L1_FILL_ON_CLOSE |
| 17 | python_exit_late | non_state2_abort |  | ENTRY_L2 | long | 2026-03-17T09:00:00Z | 2026-03-17T10:45:00Z | 2026-03-17T09:00:00Z | 2026-03-17T12:30:00Z | +105.0m |  |  |  |  |  |  |  |  |  | HARD_SL | L2_FILL |
| 60 | python_exit_late | non_state2_abort |  | ENTRY_L1 | long | 2026-04-15T04:45:00Z | 2026-04-15T05:30:00Z | 2026-04-15T04:45:00Z | 2026-04-15T07:15:00Z | +105.0m |  |  |  |  |  |  |  |  |  | HARD_SL | L1_FILL_ON_CLOSE |
| 61 | python_exit_late | non_state2_abort |  | ENTRY_L2 | long | 2026-04-15T05:15:00Z | 2026-04-15T05:30:00Z | 2026-04-15T05:15:00Z | 2026-04-15T07:15:00Z | +105.0m |  |  |  |  |  |  |  |  |  | HARD_SL | L2_FILL |
| 69 | python_exit_early | same_bar_close_or_fill_ordering | unknown | ENTRY_L2 | long | 2026-04-23T17:00:00Z | 2026-04-23T17:30:00Z | 2026-04-23T17:00:00Z | 2026-04-23T17:00:00Z | -30.0m | -123314.6250 | 115195.3905 | 1.0705 | 0.5571 | false | 1 | ENTRY_L2/L2_FILL | 0.0m | true | STATE_2_ABORT | L2_FILL |

## Worst Matched Exit Price Residuals

| Trade | Event | Side | TV entry UTC | TV exit UTC | Python entry UTC | Python exit UTC | TV exit price | Python exit price | Abs delta | Python exit reason | Python entry reason |
|---:|---|---|---|---|---|---|---:|---:|---:|---|---|
| 65 | ENTRY_L2 | long | 2026-04-20T10:45:00Z | 2026-04-21T12:30:00Z | 2026-04-20T10:45:00Z | 2026-04-20T14:45:00Z | 85.2600 | 84.7400 | 0.5200 | STATE_2_ABORT | L2_FILL_ON_CLOSE |
| 64 | ENTRY_L1 | long | 2026-04-20T10:45:00Z | 2026-04-21T12:30:00Z | 2026-04-20T10:45:00Z | 2026-04-20T14:45:00Z | 85.2600 | 84.7400 | 0.5200 | STATE_2_ABORT | L1_FILL |
| 69 | ENTRY_L2 | long | 2026-04-23T17:00:00Z | 2026-04-23T17:30:00Z | 2026-04-23T17:00:00Z | 2026-04-23T17:00:00Z | 84.8100 | 85.3200 | 0.5100 | STATE_2_ABORT | L2_FILL |
| 23 | ENTRY_L2 | short | 2026-03-21T13:15:00Z | 2026-03-21T14:00:00Z | 2026-03-21T13:30:00Z | 2026-03-23T11:00:00Z | 90.2800 | 90.5295 | 0.2495 | HARD_SL | L2_FILL_ON_CLOSE |
| 56 | ENTRY_L1 | short | 2026-04-13T01:15:00Z | 2026-04-13T12:45:00Z | 2026-04-13T01:15:00Z | 2026-04-13T06:15:00Z | 82.5000 | 82.3100 | 0.1900 | STATE_2_ABORT | L1_FILL |
| 57 | ENTRY_L2 | short | 2026-04-13T01:45:00Z | 2026-04-13T12:45:00Z | 2026-04-13T01:45:00Z | 2026-04-13T06:15:00Z | 82.5000 | 82.3100 | 0.1900 | STATE_2_ABORT | L2_FILL |
| 19 | ENTRY_L2 | short | 2026-03-18T18:30:00Z | 2026-03-19T03:15:00Z | 2026-03-18T18:30:00Z | 2026-03-19T03:15:00Z | 91.3000 | 91.2100 | 0.0900 | STATE_2_ABORT | L2_FILL_ON_CLOSE |
| 18 | ENTRY_L1 | short | 2026-03-18T18:30:00Z | 2026-03-19T03:15:00Z | 2026-03-18T18:30:00Z | 2026-03-19T03:15:00Z | 91.3000 | 91.2100 | 0.0900 | STATE_2_ABORT | L1_FILL |
| 60 | ENTRY_L1 | long | 2026-04-15T04:45:00Z | 2026-04-15T05:30:00Z | 2026-04-15T04:45:00Z | 2026-04-15T07:15:00Z | 82.9800 | 82.8994 | 0.0806 | HARD_SL | L1_FILL_ON_CLOSE |
| 61 | ENTRY_L2 | long | 2026-04-15T05:15:00Z | 2026-04-15T05:30:00Z | 2026-04-15T05:15:00Z | 2026-04-15T07:15:00Z | 82.9800 | 82.8994 | 0.0806 | HARD_SL | L2_FILL |
| 1 | ENTRY_L1 | long | 2026-03-06T08:15:00Z | 2026-03-06T09:15:00Z | 2026-03-06T08:30:00Z | 2026-03-06T09:15:00Z | 87.4400 | 87.3842 | 0.0558 | HARD_SL | L1_FILL_ON_CLOSE |
| 2 | ENTRY_L2 | long | 2026-03-06T08:45:00Z | 2026-03-06T09:15:00Z | 2026-03-06T09:00:00Z | 2026-03-06T09:15:00Z | 87.4400 | 87.3842 | 0.0558 | HARD_SL | L2_FILL |
| 29 | ENTRY_L1 | long | 2026-03-25T12:45:00Z | 2026-03-25T15:00:00Z | 2026-03-25T12:30:00Z | 2026-03-25T15:00:00Z | 91.7800 | 91.8104 | 0.0304 | HARD_SL | L1_FILL_ON_CLOSE |
| 30 | ENTRY_L2 | long | 2026-03-25T13:45:00Z | 2026-03-25T15:00:00Z | 2026-03-25T13:45:00Z | 2026-03-25T15:00:00Z | 91.7800 | 91.8104 | 0.0304 | HARD_SL | L2_FILL |
| 7 | ENTRY_L1 | long | 2026-03-09T21:30:00Z | 2026-03-10T13:30:00Z | 2026-03-09T21:30:00Z | 2026-03-10T13:30:00Z | 86.0600 | 86.0900 | 0.0300 | STATE_2_ABORT | L1_FILL |
| 8 | ENTRY_L2 | long | 2026-03-09T22:30:00Z | 2026-03-10T13:30:00Z | 2026-03-09T22:30:00Z | 2026-03-10T13:30:00Z | 86.0600 | 86.0900 | 0.0300 | STATE_2_ABORT | L2_FILL |
| 34 | ENTRY_L1 | short | 2026-03-28T18:30:00Z | 2026-03-29T11:00:00Z | 2026-03-28T18:30:00Z | 2026-03-29T11:00:00Z | 82.4700 | 82.5000 | 0.0300 | STATE_2_ABORT | L1_FILL |
| 11 | ENTRY_L1 | long | 2026-03-12T15:15:00Z | 2026-03-13T14:45:00Z | 2026-03-12T15:15:00Z | 2026-03-13T14:45:00Z | 90.6700 | 90.6500 | 0.0200 | STATE_2_ABORT | L1_FILL_ON_CLOSE |
| 12 | ENTRY_L2 | long | 2026-03-12T16:00:00Z | 2026-03-13T14:45:00Z | 2026-03-12T16:00:00Z | 2026-03-13T14:45:00Z | 90.6700 | 90.6500 | 0.0200 | STATE_2_ABORT | L2_FILL |
| 10 | ENTRY_L2 | long | 2026-03-10T18:30:00Z | 2026-03-11T09:45:00Z | 2026-03-10T18:30:00Z | 2026-03-11T09:45:00Z | 84.8200 | 84.8046 | 0.0154 | HARD_SL | L2_FILL_ON_CLOSE |
| 9 | ENTRY_L1 | long | 2026-03-10T18:30:00Z | 2026-03-11T09:45:00Z | 2026-03-10T18:30:00Z | 2026-03-11T09:45:00Z | 84.8200 | 84.8046 | 0.0154 | HARD_SL | L1_FILL |
| 21 | ENTRY_L2 | short | 2026-03-20T05:30:00Z | 2026-03-20T08:00:00Z | 2026-03-20T05:30:00Z | 2026-03-20T08:00:00Z | 90.0800 | 90.0668 | 0.0132 | HARD_SL | L2_FILL_ON_CLOSE |
| 20 | ENTRY_L1 | short | 2026-03-20T05:30:00Z | 2026-03-20T08:00:00Z | 2026-03-20T05:30:00Z | 2026-03-20T08:00:00Z | 90.0800 | 90.0668 | 0.0132 | HARD_SL | L1_FILL |
| 53 | ENTRY_L2 | long | 2026-04-11T03:45:00Z | 2026-04-11T06:00:00Z | 2026-04-11T03:45:00Z | 2026-04-11T11:15:00Z | 83.8600 | 83.8704 | 0.0104 | HARD_SL | L2_FILL_ON_CLOSE |
| 52 | ENTRY_L1 | long | 2026-04-11T03:45:00Z | 2026-04-11T06:00:00Z | 2026-04-11T03:45:00Z | 2026-04-11T11:15:00Z | 83.8600 | 83.8704 | 0.0104 | HARD_SL | L1_FILL |
| 31 | ENTRY_L1 | short | 2026-03-27T06:15:00Z | 2026-03-28T06:15:00Z | 2026-03-27T06:15:00Z | 2026-03-28T06:15:00Z | 83.0800 | 83.0900 | 0.0100 | STATE_2_ABORT | L1_FILL |
| 37 | ENTRY_L1 | short | 2026-03-31T04:30:00Z | 2026-03-31T19:45:00Z | 2026-03-31T04:15:00Z | 2026-03-31T19:45:00Z | 82.6700 | 82.6600 | 0.0100 | STATE_2_ABORT | L1_FILL_ON_CLOSE |
| 38 | ENTRY_L2 | short | 2026-03-31T05:45:00Z | 2026-03-31T19:45:00Z | 2026-03-31T05:45:00Z | 2026-03-31T19:45:00Z | 82.6700 | 82.6600 | 0.0100 | STATE_2_ABORT | L2_FILL |
| 15 | ENTRY_L1 | long | 2026-03-15T19:15:00Z | 2026-03-16T14:15:00Z | 2026-03-15T19:15:00Z | 2026-03-16T14:15:00Z | 93.1900 | 93.1800 | 0.0100 | STATE_2_ABORT | L1_FILL |
| 62 | ENTRY_L1 | long | 2026-04-18T02:30:00Z | 2026-04-18T03:45:00Z | 2026-04-18T02:30:00Z | 2026-04-18T08:00:00Z | 88.2800 | 88.2716 | 0.0084 | HARD_SL | L1_FILL |
| 63 | ENTRY_L2 | long | 2026-04-18T03:00:00Z | 2026-04-18T03:45:00Z | 2026-04-18T03:00:00Z | 2026-04-18T08:00:00Z | 88.2800 | 88.2716 | 0.0084 | HARD_SL | L2_FILL |
| 67 | ENTRY_L2 | long | 2026-04-21T15:15:00Z | 2026-04-21T17:15:00Z | 2026-04-21T15:15:00Z | 2026-04-21T17:15:00Z | 84.9100 | 84.9163 | 0.0063 | HARD_SL | L2_FILL_ON_CLOSE |

## Unmatched Classification

| Bucket | Count |
|---|---:|
| event-layer-drift | 2 |
| missing-python-cycle | 19 |
| outside_python_artifact | 2 |
| same-cycle-shift | 8 |

## Unmatched TradingView Trades

| Trade | Class | Event | Side | TV entry UTC | TV entry price | TV pnl pct | Nearest Python UTC | Nearest event | Nearest side | Delta | Python reason |
|---:|---|---|---|---|---:|---:|---|---|---|---:|---|
| 4 | missing-python-cycle | ENTRY_L2 | short | 2026-03-07T14:30:00Z | 84.1500 | 0.013500 | 2026-03-06T09:00:00Z | ENTRY_L2 | long | 1770.0m | L2_FILL |
| 3 | missing-python-cycle | ENTRY_L1 | short | 2026-03-07T14:30:00Z | 84.3900 | 0.016400 | 2026-03-06T09:00:00Z | ENTRY_L2 | long | 1770.0m | L2_FILL |
| 6 | missing-python-cycle | ENTRY_L2 | short | 2026-03-08T05:30:00Z | 82.5400 | 0.910000 | 2026-03-09T03:15:00Z | ENTRY_L1 | short | 1305.0m | L1_FILL |
| 5 | missing-python-cycle | ENTRY_L1 | short | 2026-03-08T05:30:00Z | 82.7200 | 0.690000 | 2026-03-09T03:15:00Z | ENTRY_L1 | short | 1305.0m | L1_FILL |
| 14 | missing-python-cycle | ENTRY_L2 | long | 2026-03-14T14:30:00Z | 86.6000 | 0.013900 | 2026-03-14T19:00:00Z | ENTRY_L1 | long | 270.0m | L1_FILL |
| 13 | missing-python-cycle | ENTRY_L1 | long | 2026-03-14T14:30:00Z | 86.9700 | 0.009500 | 2026-03-14T19:00:00Z | ENTRY_L1 | long | 270.0m | L1_FILL |
| 22 | same-cycle-shift | ENTRY_L1 | short | 2026-03-21T13:00:00Z | 90.0500 | 0.260000 | 2026-03-21T13:30:00Z | ENTRY_L1 | short | 30.0m | L1_FILL |
| 24 | missing-python-cycle | ENTRY_L1 | short | 2026-03-21T18:45:00Z | 89.7200 | 0.530000 | 2026-03-21T13:30:00Z | ENTRY_L1 | short | 315.0m | L1_FILL |
| 25 | missing-python-cycle | ENTRY_L2 | short | 2026-03-21T19:00:00Z | 89.8300 | 0.410000 | 2026-03-21T13:30:00Z | ENTRY_L1 | short | 330.0m | L1_FILL |
| 27 | missing-python-cycle | ENTRY_L2 | short | 2026-03-22T22:45:00Z | 86.6900 | 0.920000 | 2026-03-21T13:30:00Z | ENTRY_L1 | short | 1995.0m | L1_FILL |
| 26 | missing-python-cycle | ENTRY_L1 | short | 2026-03-22T22:45:00Z | 86.3300 | 0.340000 | 2026-03-21T13:30:00Z | ENTRY_L1 | short | 1995.0m | L1_FILL |
| 28 | missing-python-cycle | ENTRY_L3 | short | 2026-03-23T11:00:00Z | 90.5500 | 0.180000 | 2026-03-21T13:30:00Z | ENTRY_L1 | short | 2730.0m | L1_FILL |
| 32 | missing-python-cycle | ENTRY_L1 | short | 2026-03-28T13:45:00Z | 83.3000 | 0.550000 | 2026-03-28T18:30:00Z | ENTRY_L1 | short | 285.0m | L1_FILL |
| 33 | missing-python-cycle | ENTRY_L2 | short | 2026-03-28T15:15:00Z | 83.5000 | 0.310000 | 2026-03-28T18:30:00Z | ENTRY_L1 | short | 195.0m | L1_FILL |
| 41 | missing-python-cycle | ENTRY_L1 | short | 2026-04-03T03:15:00Z | 79.1600 | 0.960000 | 2026-04-02T22:00:00Z | ENTRY_L2 | short | 315.0m | L2_FILL |
| 42 | missing-python-cycle | ENTRY_L2 | short | 2026-04-03T04:00:00Z | 79.2700 | 0.820000 | 2026-04-02T22:00:00Z | ENTRY_L2 | short | 360.0m | L2_FILL |
| 44 | event-layer-drift | ENTRY_L2 | short | 2026-04-04T11:15:00Z | 80.1500 | 0.210000 | 2026-04-04T11:00:00Z | ENTRY_L1 | short | 15.0m | L1_FILL_ON_CLOSE |
| 45 | same-cycle-shift | ENTRY_L1 | short | 2026-04-04T23:00:00Z | 80.7600 | 0.010200 | 2026-04-04T21:30:00Z | ENTRY_L1 | short | 90.0m | L1_FILL_ON_CLOSE |
| 47 | same-cycle-shift | ENTRY_L2 | long | 2026-04-08T03:30:00Z | 84.5700 | 0.410000 | 2026-04-08T07:30:00Z | ENTRY_L2 | long | 240.0m | L2_FILL_ON_CLOSE |
| 46 | same-cycle-shift | ENTRY_L1 | long | 2026-04-08T03:30:00Z | 84.5400 | 0.380000 | 2026-04-08T07:30:00Z | ENTRY_L1 | long | 240.0m | L1_FILL |
| 48 | missing-python-cycle | ENTRY_L1 | long | 2026-04-08T12:00:00Z | 84.4100 | 0.520000 | 2026-04-08T07:30:00Z | ENTRY_L1 | long | 270.0m | L1_FILL |
| 49 | missing-python-cycle | ENTRY_L2 | long | 2026-04-08T12:15:00Z | 84.3800 | 0.490000 | 2026-04-08T07:30:00Z | ENTRY_L1 | long | 285.0m | L1_FILL |
| 51 | same-cycle-shift | ENTRY_L2 | long | 2026-04-09T11:15:00Z | 82.1300 | 0.230000 | 2026-04-09T09:30:00Z | ENTRY_L2 | long | 105.0m | L2_FILL_ON_CLOSE |
| 50 | same-cycle-shift | ENTRY_L1 | long | 2026-04-09T11:15:00Z | 82.0600 | 0.150000 | 2026-04-09T09:30:00Z | ENTRY_L1 | long | 105.0m | L1_FILL |
| 54 | same-cycle-shift | ENTRY_L1 | long | 2026-04-12T11:00:00Z | 82.1800 | 0.260000 | 2026-04-12T11:30:00Z | ENTRY_L1 | long | 30.0m | L1_FILL |
| 55 | same-cycle-shift | ENTRY_L2 | long | 2026-04-12T12:45:00Z | 82.0300 | 0.070000 | 2026-04-12T11:45:00Z | ENTRY_L2 | long | 60.0m | L2_FILL |
| 58 | missing-python-cycle | ENTRY_L1 | long | 2026-04-13T16:00:00Z | 82.9000 | 0.042300 | 2026-04-13T10:30:00Z | ENTRY_L3 | long | 330.0m | L3_FILL |
| 59 | missing-python-cycle | ENTRY_L2 | long | 2026-04-13T18:00:00Z | 82.8900 | 0.042500 | 2026-04-13T10:30:00Z | ENTRY_L3 | long | 450.0m | L3_FILL |
| 68 | event-layer-drift | ENTRY_L1 | long | 2026-04-23T17:00:00Z | 85.7100 | 0.050000 | 2026-04-23T17:00:00Z | ENTRY_L2 | long | 0.0m | L2_FILL |
| 71 | outside_python_artifact | ENTRY_L2 | long | 2026-04-25T11:15:00Z | 86.3300 | 0.190000 | 2026-04-23T17:00:00Z | ENTRY_L2 | long | 2535.0m | L2_FILL |
| 70 | outside_python_artifact | ENTRY_L1 | long | 2026-04-25T11:15:00Z | 86.3500 | 0.210000 | 2026-04-23T17:00:00Z | ENTRY_L2 | long | 2535.0m | L2_FILL |

## Worst Nearest Filled-Entry Deltas

| Trade | Event | Side | TV entry UTC | Nearest Python UTC | Delta | TV price | Python price | Python reason |
|---:|---|---|---|---|---:|---:|---:|---|
| 28 | ENTRY_L3 | short | 2026-03-23T11:00:00Z |  |  | 90.5500 |  |  |
| 33 | ENTRY_L2 | short | 2026-03-28T15:15:00Z | 2026-03-30T15:30:00Z | 2895.0m | 83.5000 | 84.2465 | L2_FILL |
| 14 | ENTRY_L2 | long | 2026-03-14T14:30:00Z | 2026-03-12T16:00:00Z | 2790.0m | 86.6000 | 86.0223 | L2_FILL |
| 70 | ENTRY_L1 | long | 2026-04-25T11:15:00Z | 2026-04-23T15:00:00Z | 2655.0m | 86.3500 | 85.7627 | L1_FILL |
| 71 | ENTRY_L2 | long | 2026-04-25T11:15:00Z | 2026-04-23T17:00:00Z | 2535.0m | 86.3300 | 85.7101 | L2_FILL |
| 4 | ENTRY_L2 | short | 2026-03-07T14:30:00Z | 2026-03-09T03:15:00Z | 2205.0m | 84.1500 | 83.5400 | L2_FILL_ON_CLOSE |
| 3 | ENTRY_L1 | short | 2026-03-07T14:30:00Z | 2026-03-09T03:15:00Z | 2205.0m | 84.3900 | 84.3921 | L1_FILL |
| 27 | ENTRY_L2 | short | 2026-03-22T22:45:00Z | 2026-03-21T13:30:00Z | 1995.0m | 86.6900 | 90.0500 | L2_FILL_ON_CLOSE |
| 26 | ENTRY_L1 | short | 2026-03-22T22:45:00Z | 2026-03-21T13:30:00Z | 1995.0m | 86.3300 | 90.2538 | L1_FILL |
| 6 | ENTRY_L2 | short | 2026-03-08T05:30:00Z | 2026-03-09T03:15:00Z | 1305.0m | 82.5400 | 83.5400 | L2_FILL_ON_CLOSE |
| 5 | ENTRY_L1 | short | 2026-03-08T05:30:00Z | 2026-03-09T03:15:00Z | 1305.0m | 82.7200 | 84.3921 | L1_FILL |
| 59 | ENTRY_L2 | long | 2026-04-13T18:00:00Z | 2026-04-13T08:00:00Z | 600.0m | 82.8900 | 82.0865 | L2_FILL |
| 58 | ENTRY_L1 | long | 2026-04-13T16:00:00Z | 2026-04-13T07:30:00Z | 510.0m | 82.9000 | 82.0100 | L1_FILL_ON_CLOSE |
| 41 | ENTRY_L1 | short | 2026-04-03T03:15:00Z | 2026-04-02T20:45:00Z | 390.0m | 79.1600 | 79.1100 | L1_FILL_ON_CLOSE |
| 42 | ENTRY_L2 | short | 2026-04-03T04:00:00Z | 2026-04-02T22:00:00Z | 360.0m | 79.2700 | 79.0764 | L2_FILL |
| 25 | ENTRY_L2 | short | 2026-03-21T19:00:00Z | 2026-03-21T13:30:00Z | 330.0m | 89.8300 | 90.0500 | L2_FILL_ON_CLOSE |
| 24 | ENTRY_L1 | short | 2026-03-21T18:45:00Z | 2026-03-21T13:30:00Z | 315.0m | 89.7200 | 90.2538 | L1_FILL |
| 32 | ENTRY_L1 | short | 2026-03-28T13:45:00Z | 2026-03-28T18:30:00Z | 285.0m | 83.3000 | 83.3655 | L1_FILL |
| 49 | ENTRY_L2 | long | 2026-04-08T12:15:00Z | 2026-04-08T07:30:00Z | 285.0m | 84.3800 | 84.3300 | L2_FILL_ON_CLOSE |
| 13 | ENTRY_L1 | long | 2026-03-14T14:30:00Z | 2026-03-14T19:00:00Z | 270.0m | 86.9700 | 86.9397 | L1_FILL |
| 48 | ENTRY_L1 | long | 2026-04-08T12:00:00Z | 2026-04-08T07:30:00Z | 270.0m | 84.4100 | 84.4442 | L1_FILL |
| 47 | ENTRY_L2 | long | 2026-04-08T03:30:00Z | 2026-04-08T07:30:00Z | 240.0m | 84.5700 | 84.3300 | L2_FILL_ON_CLOSE |
| 46 | ENTRY_L1 | long | 2026-04-08T03:30:00Z | 2026-04-08T07:30:00Z | 240.0m | 84.5400 | 84.4442 | L1_FILL |
| 68 | ENTRY_L1 | long | 2026-04-23T17:00:00Z | 2026-04-23T15:00:00Z | 120.0m | 85.7100 | 85.7627 | L1_FILL |
| 51 | ENTRY_L2 | long | 2026-04-09T11:15:00Z | 2026-04-09T09:30:00Z | 105.0m | 82.1300 | 82.1800 | L2_FILL_ON_CLOSE |
| 50 | ENTRY_L1 | long | 2026-04-09T11:15:00Z | 2026-04-09T09:30:00Z | 105.0m | 82.0600 | 82.0680 | L1_FILL |
| 45 | ENTRY_L1 | short | 2026-04-04T23:00:00Z | 2026-04-04T21:30:00Z | 90.0m | 80.7600 | 80.8700 | L1_FILL_ON_CLOSE |
| 55 | ENTRY_L2 | long | 2026-04-12T12:45:00Z | 2026-04-12T11:45:00Z | 60.0m | 82.0300 | 82.1464 | L2_FILL |
| 22 | ENTRY_L1 | short | 2026-03-21T13:00:00Z | 2026-03-21T13:30:00Z | 30.0m | 90.0500 | 90.2538 | L1_FILL |
| 44 | ENTRY_L2 | short | 2026-04-04T11:15:00Z | 2026-04-04T11:45:00Z | 30.0m | 80.1500 | 80.2072 | L2_FILL |
| 54 | ENTRY_L1 | long | 2026-04-12T11:00:00Z | 2026-04-12T11:30:00Z | 30.0m | 82.1800 | 82.2360 | L1_FILL |
| 1 | ENTRY_L1 | long | 2026-03-06T08:15:00Z | 2026-03-06T08:30:00Z | 15.0m | 88.3600 | 88.3600 | L1_FILL_ON_CLOSE |

## Interpretation Notes
- This report compares TradingView filled trade rows only against Python `ENTRY_L1/L2/L3` rows.
- It intentionally does not compare TradingView rows to Python `ENTRY_SIGNAL`, because that is a pre-fill trigger.
- TradingView `net_pnl_pct` is not the same unit as Python `r_multiple`; use price/time/side first, then handle PnL separately.
- If Python date-window counts are much larger than TradingView counts, the next check is profile parity: chart timeframe, `entry_timeframe`, `execution_timeframe`, RSM overrides, and available TradingView history.
