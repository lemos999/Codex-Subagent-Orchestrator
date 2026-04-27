# MTS-V1 ETH TradingView/Python Diff

## Inputs
- TradingView raw CSV: `samples\tradingview_mtsv1_ETH_entry15_raw.csv`
- Python JSONL: `runs\mtsv1_tv_eth_15m_binanceusdm_profile\trades.jsonl`
- Match tolerance: `15.0m`
- TradingView entry range: `2026-03-06T21:30:00Z` to `2026-04-23T07:45:00Z`
- TradingView raw rows: `69`
- TradingView common-window rows: `65`
- TradingView rows before Python artifact: `0`
- TradingView tail after Python artifact: `4`

## Counts

| Source | Scope | Count | By event | By side |
|---|---|---:|---|---|
| TradingView | common-window closed trades | 65 | `{'ENTRY_L1': 34, 'ENTRY_L2': 31}` | `{'long': 40, 'short': 25}` |
| TradingView | raw capture rows | 69 | | |
| TradingView | outside Python artifact | 4 | `{'before': 0, 'tail': 4}` | |
| Python | all `ETH` filled entries | 118 | `{'ENTRY_L1': 62, 'ENTRY_L2': 55, 'ENTRY_L3': 1}` | `{'long': 51, 'short': 67}` |
| Python | TradingView date window | 63 | `{'ENTRY_L1': 33, 'ENTRY_L2': 30}` | `{'long': 38, 'short': 25}` |

## Match Summary

| Metric | Value |
|---|---:|
| matched_common_window_tv_trades | 48 / 65 |
| common_window_match_rate | 0.738462 |
| unmatched_tv_trades | 17 |
| avg_abs_time_delta_minutes | 0.938 |
| avg_abs_entry_price_delta_pct | 0.000199 |
| exit_timestamp_matches | 41 / 48 |
| exit_price_within_0_15 | 16 / 48 |
| exit_price_within_1_0 | 37 / 48 |
| avg_abs_exit_price_delta | 2.323117 |
| max_abs_exit_price_delta | 18.520000 |
| unmatched_classification | `{'event-layer-drift': 1, 'missing-python-cycle': 10, 'same-cycle-shift': 6}` |
| matched_exit_timing_residuals | `{'python_exit_early': 3, 'python_exit_late': 4}` |
| matched_exit_cause_buckets | `{'non_state2_abort': 2, 'unknown_state2_abort': 5}` |

## Exit Reason Summary

| Python exit reason | Matched entries | Exit timestamp matches | Exit price <=0.15 | Exit price <=1.0 |
|---|---:|---:|---:|---:|
| EVASION | 2 | 2 | 0 | 2 |
| HARD_SL | 22 | 20 | 6 | 16 |
| STATE_2_ABORT | 24 | 19 | 10 | 19 |

## State2 Trigger Source Summary

| Python State2 trigger | Matched State2 exits | Exit timestamp matches | Python exit early | Python exit late |
|---|---:|---:|---:|---:|
| unknown_state2_abort | 24 | 19 | 3 | 2 |

## Matched Exit Timing Residuals

| Trade | Timing bucket | Cause bucket | Python State2 trigger | Event | Side | TV entry UTC | TV exit UTC | Python entry UTC | Python exit UTC | Signed exit delta | CVD delta | Reverse threshold | Reverse ratio | Prev ratio | Prev pulse | Confirm bars | Last fill | Last fill age | L2 filled | Python exit reason | Python entry reason |
|---:|---|---|---|---|---|---|---|---|---|---:|---:|---:|---:|---:|---|---:|---|---:|---|---|---|
| 3 | python_exit_early | unknown_state2_abort | unknown_state2_abort | ENTRY_L1 | short | 2026-03-07T03:15:00Z | 2026-03-08T10:15:00Z | 2026-03-07T03:15:00Z | 2026-03-07T11:00:00Z | -1395.0m |  |  |  |  |  |  |  |  |  | STATE_2_ABORT | L1_FILL_ON_CLOSE |
| 4 | python_exit_early | unknown_state2_abort | unknown_state2_abort | ENTRY_L2 | short | 2026-03-07T08:15:00Z | 2026-03-08T10:15:00Z | 2026-03-07T08:15:00Z | 2026-03-07T11:00:00Z | -1395.0m |  |  |  |  |  |  |  |  |  | STATE_2_ABORT | L2_FILL |
| 7 | python_exit_late | unknown_state2_abort | unknown_state2_abort | ENTRY_L1 | long | 2026-03-10T14:45:00Z | 2026-03-11T02:30:00Z | 2026-03-10T14:45:00Z | 2026-03-11T05:30:00Z | +180.0m |  |  |  |  |  |  |  |  |  | STATE_2_ABORT | L1_FILL |
| 8 | python_exit_late | unknown_state2_abort | unknown_state2_abort | ENTRY_L2 | long | 2026-03-10T19:30:00Z | 2026-03-11T02:30:00Z | 2026-03-10T19:30:00Z | 2026-03-11T05:30:00Z | +180.0m |  |  |  |  |  |  |  |  |  | STATE_2_ABORT | L2_FILL |
| 19 | python_exit_late | non_state2_abort |  | ENTRY_L2 | short | 2026-03-20T16:45:00Z | 2026-03-20T21:15:00Z | 2026-03-20T16:45:00Z | 2026-03-20T22:00:00Z | +45.0m |  |  |  |  |  |  |  |  |  | HARD_SL | L2_FILL_ON_CLOSE |
| 18 | python_exit_late | non_state2_abort |  | ENTRY_L1 | short | 2026-03-20T16:45:00Z | 2026-03-20T21:15:00Z | 2026-03-20T16:45:00Z | 2026-03-20T22:00:00Z | +45.0m |  |  |  |  |  |  |  |  |  | HARD_SL | L1_FILL |
| 17 | python_exit_early | unknown_state2_abort | unknown_state2_abort | ENTRY_L1 | short | 2026-03-19T03:30:00Z | 2026-03-20T08:00:00Z | 2026-03-19T03:30:00Z | 2026-03-20T07:30:00Z | -30.0m |  |  |  |  |  |  |  |  |  | STATE_2_ABORT | L1_FILL_ON_CLOSE |

## Worst Matched Exit Price Residuals

| Trade | Event | Side | TV entry UTC | TV exit UTC | Python entry UTC | Python exit UTC | TV exit price | Python exit price | Abs delta | Python exit reason | Python entry reason |
|---:|---|---|---|---|---|---|---:|---:|---:|---|---|
| 3 | ENTRY_L1 | short | 2026-03-07T03:15:00Z | 2026-03-08T10:15:00Z | 2026-03-07T03:15:00Z | 2026-03-07T11:00:00Z | 1974.7100 | 1993.2300 | 18.5200 | STATE_2_ABORT | L1_FILL_ON_CLOSE |
| 4 | ENTRY_L2 | short | 2026-03-07T08:15:00Z | 2026-03-08T10:15:00Z | 2026-03-07T08:15:00Z | 2026-03-07T11:00:00Z | 1974.7100 | 1993.2300 | 18.5200 | STATE_2_ABORT | L2_FILL |
| 17 | ENTRY_L1 | short | 2026-03-19T03:30:00Z | 2026-03-20T08:00:00Z | 2026-03-19T03:30:00Z | 2026-03-20T07:30:00Z | 2169.5400 | 2151.9700 | 17.5700 | STATE_2_ABORT | L1_FILL_ON_CLOSE |
| 19 | ENTRY_L2 | short | 2026-03-20T16:45:00Z | 2026-03-20T21:15:00Z | 2026-03-20T16:45:00Z | 2026-03-20T22:00:00Z | 2151.2200 | 2160.0404 | 8.8204 | HARD_SL | L2_FILL_ON_CLOSE |
| 18 | ENTRY_L1 | short | 2026-03-20T16:45:00Z | 2026-03-20T21:15:00Z | 2026-03-20T16:45:00Z | 2026-03-20T22:00:00Z | 2151.2200 | 2160.0404 | 8.8204 | HARD_SL | L1_FILL |
| 62 | ENTRY_L1 | long | 2026-04-22T19:30:00Z | 2026-04-22T23:15:00Z | 2026-04-22T19:30:00Z | 2026-04-22T23:30:00Z | 2385.2300 | 2377.8129 | 7.4171 | HARD_SL | L1_FILL |
| 63 | ENTRY_L2 | long | 2026-04-22T19:45:00Z | 2026-04-22T23:15:00Z | 2026-04-22T19:45:00Z | 2026-04-22T23:30:00Z | 2385.2300 | 2377.8129 | 7.4171 | HARD_SL | L2_FILL |
| 7 | ENTRY_L1 | long | 2026-03-10T14:45:00Z | 2026-03-11T02:30:00Z | 2026-03-10T14:45:00Z | 2026-03-11T05:30:00Z | 2021.6900 | 2016.2100 | 5.4800 | STATE_2_ABORT | L1_FILL |
| 8 | ENTRY_L2 | long | 2026-03-10T19:30:00Z | 2026-03-11T02:30:00Z | 2026-03-10T19:30:00Z | 2026-03-11T05:30:00Z | 2021.6900 | 2016.2100 | 5.4800 | STATE_2_ABORT | L2_FILL |
| 25 | ENTRY_L1 | long | 2026-03-25T13:00:00Z | 2026-03-25T15:00:00Z | 2026-03-25T13:00:00Z | 2026-03-25T15:15:00Z | 2156.7500 | 2155.5735 | 1.1765 | HARD_SL | L1_FILL |
| 26 | ENTRY_L2 | long | 2026-03-25T14:00:00Z | 2026-03-25T15:00:00Z | 2026-03-25T14:00:00Z | 2026-03-25T15:15:00Z | 2156.7500 | 2155.5735 | 1.1765 | HARD_SL | L2_FILL |
| 61 | ENTRY_L2 | long | 2026-04-21T11:30:00Z | 2026-04-21T12:30:00Z | 2026-04-21T11:30:00Z | 2026-04-21T12:30:00Z | 2306.0800 | 2305.1724 | 0.9076 | HARD_SL | L2_FILL_ON_CLOSE |
| 60 | ENTRY_L1 | long | 2026-04-21T11:30:00Z | 2026-04-21T12:30:00Z | 2026-04-21T11:30:00Z | 2026-04-21T12:30:00Z | 2306.0800 | 2305.1724 | 0.9076 | HARD_SL | L1_FILL |
| 5 | ENTRY_L1 | short | 2026-03-08T22:30:00Z | 2026-03-09T00:30:00Z | 2026-03-08T22:30:00Z | 2026-03-09T00:30:00Z | 1963.9800 | 1964.8286 | 0.8486 | HARD_SL | L1_FILL |
| 6 | ENTRY_L2 | short | 2026-03-08T22:45:00Z | 2026-03-09T00:30:00Z | 2026-03-08T22:45:00Z | 2026-03-09T00:30:00Z | 1963.9800 | 1964.8286 | 0.8486 | HARD_SL | L2_FILL |
| 37 | ENTRY_L1 | short | 2026-04-02T22:30:00Z | 2026-04-03T12:30:00Z | 2026-04-02T22:30:00Z | 2026-04-03T12:30:00Z | 2075.6400 | 2076.4562 | 0.8162 | HARD_SL | L1_FILL |
| 38 | ENTRY_L2 | short | 2026-04-02T22:45:00Z | 2026-04-03T12:30:00Z | 2026-04-02T22:45:00Z | 2026-04-03T12:30:00Z | 2075.6400 | 2076.4562 | 0.8162 | HARD_SL | L2_FILL |
| 58 | ENTRY_L1 | long | 2026-04-20T08:00:00Z | 2026-04-21T11:00:00Z | 2026-04-20T08:00:00Z | 2026-04-21T11:00:00Z | 2316.7400 | 2316.1700 | 0.5700 | STATE_2_ABORT | L1_FILL_ON_CLOSE |
| 59 | ENTRY_L2 | long | 2026-04-20T08:45:00Z | 2026-04-21T11:00:00Z | 2026-04-20T08:45:00Z | 2026-04-21T11:00:00Z | 2316.7400 | 2316.1700 | 0.5700 | STATE_2_ABORT | L2_FILL |
| 54 | ENTRY_L1 | long | 2026-04-16T13:30:00Z | 2026-04-16T13:45:00Z | 2026-04-16T13:30:00Z | 2026-04-16T13:45:00Z | 2307.1400 | 2306.7000 | 0.4400 | EVASION | L1_FILL |
| 55 | ENTRY_L2 | long | 2026-04-16T13:45:00Z | 2026-04-16T13:45:00Z | 2026-04-16T13:45:00Z | 2026-04-16T13:45:00Z | 2307.1400 | 2306.7000 | 0.4400 | EVASION | L2_FILL |
| 15 | ENTRY_L1 | long | 2026-03-17T22:15:00Z | 2026-03-18T00:15:00Z | 2026-03-17T22:15:00Z | 2026-03-18T00:15:00Z | 2308.8000 | 2308.3632 | 0.4368 | HARD_SL | L1_FILL |
| 16 | ENTRY_L2 | long | 2026-03-17T22:30:00Z | 2026-03-18T00:15:00Z | 2026-03-17T22:30:00Z | 2026-03-18T00:15:00Z | 2308.8000 | 2308.3632 | 0.4368 | HARD_SL | L2_FILL |
| 10 | ENTRY_L2 | long | 2026-03-11T11:30:00Z | 2026-03-12T14:15:00Z | 2026-03-11T11:30:00Z | 2026-03-12T14:15:00Z | 2057.6000 | 2057.2100 | 0.3900 | STATE_2_ABORT | L2_FILL |
| 29 | ENTRY_L1 | short | 2026-03-28T09:45:00Z | 2026-03-28T13:30:00Z | 2026-03-28T09:45:00Z | 2026-03-28T13:30:00Z | 2007.6000 | 2007.9082 | 0.3082 | HARD_SL | L1_FILL |
| 30 | ENTRY_L2 | short | 2026-03-28T10:00:00Z | 2026-03-28T13:30:00Z | 2026-03-28T10:00:00Z | 2026-03-28T13:30:00Z | 2007.6000 | 2007.9082 | 0.3082 | HARD_SL | L2_FILL |
| 36 | ENTRY_L2 | long | 2026-04-01T18:00:00Z | 2026-04-02T01:00:00Z | 2026-04-01T18:00:00Z | 2026-04-02T01:00:00Z | 2139.2900 | 2139.0800 | 0.2100 | STATE_2_ABORT | L2_FILL_ON_CLOSE |
| 35 | ENTRY_L1 | long | 2026-04-01T18:00:00Z | 2026-04-02T01:00:00Z | 2026-04-01T18:00:00Z | 2026-04-02T01:00:00Z | 2139.2900 | 2139.0800 | 0.2100 | STATE_2_ABORT | L1_FILL |
| 49 | ENTRY_L2 | short | 2026-04-13T06:45:00Z | 2026-04-13T12:45:00Z | 2026-04-13T06:45:00Z | 2026-04-13T12:45:00Z | 2191.4800 | 2191.2700 | 0.2100 | STATE_2_ABORT | L2_FILL_ON_CLOSE |
| 48 | ENTRY_L1 | short | 2026-04-13T06:45:00Z | 2026-04-13T12:45:00Z | 2026-04-13T06:45:00Z | 2026-04-13T12:45:00Z | 2191.4800 | 2191.2700 | 0.2100 | STATE_2_ABORT | L1_FILL |
| 47 | ENTRY_L1 | long | 2026-04-12T17:15:00Z | 2026-04-12T22:00:00Z | 2026-04-12T17:15:00Z | 2026-04-12T22:00:00Z | 2195.5600 | 2195.4000 | 0.1600 | STATE_2_ABORT | L1_FILL_ON_CLOSE |
| 24 | ENTRY_L1 | long | 2026-03-25T03:30:00Z | 2026-03-25T12:15:00Z | 2026-03-25T03:30:00Z | 2026-03-25T12:15:00Z | 2170.9800 | 2170.8300 | 0.1500 | STATE_2_ABORT | L1_FILL_ON_CLOSE |

## Unmatched Classification

| Bucket | Count |
|---|---:|
| event-layer-drift | 1 |
| missing-python-cycle | 10 |
| same-cycle-shift | 6 |

## Unmatched TradingView Trades

| Trade | Class | Event | Side | TV entry UTC | TV entry price | TV pnl pct | Nearest Python UTC | Nearest event | Nearest side | Delta | Python reason |
|---:|---|---|---|---|---:|---:|---|---|---|---:|---|
| 9 | event-layer-drift | ENTRY_L1 | long | 2026-03-11T11:15:00Z | 2023.8400 | 0.016700 | 2026-03-11T11:30:00Z | ENTRY_L2 | long | 15.0m | L2_FILL |
| 11 | same-cycle-shift | ENTRY_L1 | long | 2026-03-12T20:45:00Z | 2061.4400 | 0.014300 | 2026-03-12T21:30:00Z | ENTRY_L1 | long | 45.0m | L1_FILL |
| 14 | same-cycle-shift | ENTRY_L2 | long | 2026-03-14T14:00:00Z | 2071.7600 | 0.012400 | 2026-03-14T14:30:00Z | ENTRY_L2 | long | 30.0m | L2_FILL |
| 21 | missing-python-cycle | ENTRY_L2 | short | 2026-03-21T09:30:00Z | 2156.8000 | 0.300000 | 2026-03-21T23:00:00Z | ENTRY_L1 | short | 810.0m | L1_FILL_ON_CLOSE |
| 20 | missing-python-cycle | ENTRY_L1 | short | 2026-03-21T09:30:00Z | 2154.3900 | 0.410000 | 2026-03-21T23:00:00Z | ENTRY_L1 | short | 810.0m | L1_FILL_ON_CLOSE |
| 23 | missing-python-cycle | ENTRY_L2 | short | 2026-03-22T15:45:00Z | 2081.9600 | 0.700000 | 2026-03-21T23:00:00Z | ENTRY_L1 | short | 1005.0m | L1_FILL_ON_CLOSE |
| 22 | missing-python-cycle | ENTRY_L1 | short | 2026-03-22T15:45:00Z | 2080.5600 | 0.770000 | 2026-03-21T23:00:00Z | ENTRY_L1 | short | 1005.0m | L1_FILL_ON_CLOSE |
| 34 | same-cycle-shift | ENTRY_L2 | short | 2026-03-31T12:15:00Z | 2050.5500 | 0.700000 | 2026-03-31T13:15:00Z | ENTRY_L2 | short | 60.0m | L2_FILL_ON_CLOSE |
| 33 | same-cycle-shift | ENTRY_L1 | short | 2026-03-31T12:15:00Z | 2039.3500 | 0.260000 | 2026-03-31T13:15:00Z | ENTRY_L1 | short | 60.0m | L1_FILL |
| 44 | missing-python-cycle | ENTRY_L2 | long | 2026-04-09T08:00:00Z | 2177.8300 | 0.580000 | 2026-04-08T22:00:00Z | ENTRY_L2 | long | 600.0m | L2_FILL |
| 43 | missing-python-cycle | ENTRY_L1 | long | 2026-04-09T08:00:00Z | 2176.1600 | 0.500000 | 2026-04-08T22:00:00Z | ENTRY_L2 | long | 600.0m | L2_FILL |
| 46 | missing-python-cycle | ENTRY_L2 | long | 2026-04-12T01:30:00Z | 2226.2900 | 0.610000 | 2026-04-12T17:15:00Z | ENTRY_L1 | long | 945.0m | L1_FILL_ON_CLOSE |
| 45 | missing-python-cycle | ENTRY_L1 | long | 2026-04-12T01:30:00Z | 2224.0000 | 0.510000 | 2026-04-12T17:15:00Z | ENTRY_L1 | long | 945.0m | L1_FILL_ON_CLOSE |
| 51 | same-cycle-shift | ENTRY_L2 | long | 2026-04-14T11:15:00Z | 2368.4000 | 0.000700 | 2026-04-14T10:45:00Z | ENTRY_L2 | long | 30.0m | L2_FILL_ON_CLOSE |
| 50 | same-cycle-shift | ENTRY_L1 | long | 2026-04-14T11:15:00Z | 2371.8700 | 0.080000 | 2026-04-14T10:45:00Z | ENTRY_L1 | long | 30.0m | L1_FILL |
| 65 | missing-python-cycle | ENTRY_L2 | long | 2026-04-23T07:45:00Z | 2342.8100 | 0.510000 | 2026-04-22T19:45:00Z | ENTRY_L2 | long | 720.0m | L2_FILL |
| 64 | missing-python-cycle | ENTRY_L1 | long | 2026-04-23T07:45:00Z | 2349.8800 | 0.810000 | 2026-04-22T19:45:00Z | ENTRY_L2 | long | 720.0m | L2_FILL |

## Worst Nearest Filled-Entry Deltas

| Trade | Event | Side | TV entry UTC | Nearest Python UTC | Delta | TV price | Python price | Python reason |
|---:|---|---|---|---|---:|---:|---:|---|
| 46 | ENTRY_L2 | long | 2026-04-12T01:30:00Z | 2026-04-14T10:45:00Z | 3435.0m | 2226.2900 | 2374.0100 | L2_FILL_ON_CLOSE |
| 23 | ENTRY_L2 | short | 2026-03-22T15:45:00Z | 2026-03-23T11:00:00Z | 1155.0m | 2081.9600 | 2153.3315 | L2_FILL |
| 21 | ENTRY_L2 | short | 2026-03-21T09:30:00Z | 2026-03-20T16:45:00Z | 1005.0m | 2156.8000 | 2136.4400 | L2_FILL_ON_CLOSE |
| 22 | ENTRY_L1 | short | 2026-03-22T15:45:00Z | 2026-03-21T23:00:00Z | 1005.0m | 2080.5600 | 2145.3400 | L1_FILL_ON_CLOSE |
| 45 | ENTRY_L1 | long | 2026-04-12T01:30:00Z | 2026-04-12T17:15:00Z | 945.0m | 2224.0000 | 2191.9600 | L1_FILL_ON_CLOSE |
| 20 | ENTRY_L1 | short | 2026-03-21T09:30:00Z | 2026-03-21T23:00:00Z | 810.0m | 2154.3900 | 2145.3400 | L1_FILL_ON_CLOSE |
| 64 | ENTRY_L1 | long | 2026-04-23T07:45:00Z | 2026-04-22T19:30:00Z | 735.0m | 2349.8800 | 2403.3529 | L1_FILL |
| 65 | ENTRY_L2 | long | 2026-04-23T07:45:00Z | 2026-04-22T19:45:00Z | 720.0m | 2342.8100 | 2393.4799 | L2_FILL |
| 43 | ENTRY_L1 | long | 2026-04-09T08:00:00Z | 2026-04-08T21:45:00Z | 615.0m | 2176.1600 | 2212.5702 | L1_FILL |
| 44 | ENTRY_L2 | long | 2026-04-09T08:00:00Z | 2026-04-08T22:00:00Z | 600.0m | 2177.8300 | 2211.5536 | L2_FILL |
| 34 | ENTRY_L2 | short | 2026-03-31T12:15:00Z | 2026-03-31T13:15:00Z | 60.0m | 2050.5500 | 2057.4000 | L2_FILL_ON_CLOSE |
| 33 | ENTRY_L1 | short | 2026-03-31T12:15:00Z | 2026-03-31T13:15:00Z | 60.0m | 2039.3500 | 2059.8817 | L1_FILL |
| 9 | ENTRY_L1 | long | 2026-03-11T11:15:00Z | 2026-03-11T10:30:00Z | 45.0m | 2023.8400 | 2028.6400 | L1_FILL_ON_CLOSE |
| 11 | ENTRY_L1 | long | 2026-03-12T20:45:00Z | 2026-03-12T21:30:00Z | 45.0m | 2061.4400 | 2059.1977 | L1_FILL |
| 14 | ENTRY_L2 | long | 2026-03-14T14:00:00Z | 2026-03-14T14:30:00Z | 30.0m | 2071.7600 | 2071.0113 | L2_FILL |
| 51 | ENTRY_L2 | long | 2026-04-14T11:15:00Z | 2026-04-14T10:45:00Z | 30.0m | 2368.4000 | 2374.0100 | L2_FILL_ON_CLOSE |
| 50 | ENTRY_L1 | long | 2026-04-14T11:15:00Z | 2026-04-14T10:45:00Z | 30.0m | 2371.8700 | 2372.1957 | L1_FILL |
| 12 | ENTRY_L2 | long | 2026-03-12T21:15:00Z | 2026-03-12T21:30:00Z | 15.0m | 2064.2300 | 2059.5700 | L2_FILL_ON_CLOSE |
| 39 | ENTRY_L1 | long | 2026-04-06T15:00:00Z | 2026-04-06T14:45:00Z | 15.0m | 2155.2000 | 2155.4200 | L1_FILL_ON_CLOSE |
| 41 | ENTRY_L1 | long | 2026-04-07T19:00:00Z | 2026-04-07T19:15:00Z | 15.0m | 2087.2700 | 2087.0641 | L1_FILL |
| 1 | ENTRY_L1 | short | 2026-03-06T21:30:00Z | 2026-03-06T21:30:00Z | 0.0m | 1974.9700 | 1975.0427 | L1_FILL |
| 2 | ENTRY_L2 | short | 2026-03-06T21:45:00Z | 2026-03-06T21:45:00Z | 0.0m | 1982.9400 | 1983.0701 | L2_FILL |
| 3 | ENTRY_L1 | short | 2026-03-07T03:15:00Z | 2026-03-07T03:15:00Z | 0.0m | 1982.9800 | 1982.7500 | L1_FILL_ON_CLOSE |
| 4 | ENTRY_L2 | short | 2026-03-07T08:15:00Z | 2026-03-07T08:15:00Z | 0.0m | 1986.4500 | 1986.1085 | L2_FILL |
| 5 | ENTRY_L1 | short | 2026-03-08T22:30:00Z | 2026-03-08T22:30:00Z | 0.0m | 1937.7800 | 1939.1270 | L1_FILL |
| 6 | ENTRY_L2 | short | 2026-03-08T22:45:00Z | 2026-03-08T22:45:00Z | 0.0m | 1936.9700 | 1937.6276 | L2_FILL |
| 7 | ENTRY_L1 | long | 2026-03-10T14:45:00Z | 2026-03-10T14:45:00Z | 0.0m | 2041.5300 | 2041.0837 | L1_FILL |
| 8 | ENTRY_L2 | long | 2026-03-10T19:30:00Z | 2026-03-10T19:30:00Z | 0.0m | 2027.5600 | 2027.3808 | L2_FILL |
| 10 | ENTRY_L2 | long | 2026-03-11T11:30:00Z | 2026-03-11T11:30:00Z | 0.0m | 2018.3700 | 2018.7277 | L2_FILL |
| 13 | ENTRY_L1 | long | 2026-03-14T13:00:00Z | 2026-03-14T13:00:00Z | 0.0m | 2072.6100 | 2072.5525 | L1_FILL |
| 15 | ENTRY_L1 | long | 2026-03-17T22:15:00Z | 2026-03-17T22:15:00Z | 0.0m | 2330.3800 | 2330.5601 | L1_FILL |
| 16 | ENTRY_L2 | long | 2026-03-17T22:30:00Z | 2026-03-17T22:30:00Z | 0.0m | 2326.8300 | 2326.1034 | L2_FILL |

## Interpretation Notes
- This report compares TradingView filled trade rows only against Python `ENTRY_L1/L2/L3` rows.
- It intentionally does not compare TradingView rows to Python `ENTRY_SIGNAL`, because that is a pre-fill trigger.
- TradingView `net_pnl_pct` is not the same unit as Python `r_multiple`; use price/time/side first, then handle PnL separately.
- If Python date-window counts are much larger than TradingView counts, the next check is profile parity: chart timeframe, `entry_timeframe`, `execution_timeframe`, RSM overrides, and available TradingView history.
