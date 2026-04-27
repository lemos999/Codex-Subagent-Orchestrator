# MTS-V1 BTC TradingView/Python Diff

## Inputs
- TradingView raw CSV: `samples\tradingview_mtsv1_BTC_entry15_raw.csv`
- Python JSONL: `runs\mtsv1_tv_btc_15m_profile\trades.jsonl`
- Match tolerance: `15.0m`
- TradingView entry range: `2026-03-07T03:15:00Z` to `2026-04-24T14:45:00Z`

## Counts

| Source | Scope | Count | By event | By side |
|---|---|---:|---|---|
| TradingView | raw closed trades | 64 | `{'ENTRY_L1': 34, 'ENTRY_L2': 30}` | `{'long': 40, 'short': 24}` |
| Python | all `BTC` filled entries | 118 | `{'ENTRY_L1': 76, 'ENTRY_L2': 42}` | `{'long': 82, 'short': 36}` |
| Python | TradingView date window | 89 | `{'ENTRY_L1': 58, 'ENTRY_L2': 31}` | `{'long': 62, 'short': 27}` |

## Match Summary

| Metric | Value |
|---|---:|
| matched_tv_trades | 11 / 64 |
| match_rate | 0.171875 |
| unmatched_tv_trades | 53 |
| avg_abs_time_delta_minutes | 4.091 |
| avg_abs_entry_price_delta_pct | 0.000336 |

## Unmatched TradingView Trades

| Trade | Event | Side | TV entry UTC | TV entry price | TV pnl pct |
|---:|---|---|---|---:|---:|
| 3 | ENTRY_L2 | long | 2026-03-09T18:00:00Z | 68403.8000 | 0.021600 |
| 5 | ENTRY_L2 | long | 2026-03-10T18:15:00Z | 70289.0000 | -0.013600 |
| 6 | ENTRY_L1 | long | 2026-03-12T14:00:00Z | 70336.5000 | -0.011200 |
| 7 | ENTRY_L2 | long | 2026-03-12T14:15:00Z | 69906.8000 | -0.005100 |
| 8 | ENTRY_L1 | long | 2026-03-14T21:30:00Z | 70644.4000 | 0.010900 |
| 9 | ENTRY_L2 | long | 2026-03-14T21:45:00Z | 70697.1000 | 0.010200 |
| 12 | ENTRY_L1 | long | 2026-03-17T17:00:00Z | 74110.4000 | -0.007500 |
| 13 | ENTRY_L2 | long | 2026-03-17T23:45:00Z | 73882.7000 | -0.004400 |
| 15 | ENTRY_L2 | short | 2026-03-18T21:30:00Z | 71292.5000 | -0.002400 |
| 17 | ENTRY_L1 | short | 2026-03-21T04:45:00Z | 70608.0000 | -0.004800 |
| 18 | ENTRY_L2 | short | 2026-03-21T05:15:00Z | 70718.9000 | -0.003200 |
| 19 | ENTRY_L1 | short | 2026-03-23T01:45:00Z | 67875.6000 | -0.009000 |
| 20 | ENTRY_L2 | short | 2026-03-23T02:15:00Z | 67849.4000 | -0.009400 |
| 22 | ENTRY_L2 | long | 2026-03-25T15:00:00Z | 70788.1000 | -0.008400 |
| 21 | ENTRY_L1 | long | 2026-03-25T15:00:00Z | 70858.6000 | -0.009400 |
| 23 | ENTRY_L1 | short | 2026-03-28T03:00:00Z | 66110.7000 | -0.005500 |
| 24 | ENTRY_L2 | short | 2026-03-28T04:15:00Z | 66249.2000 | -0.003400 |
| 26 | ENTRY_L2 | short | 2026-03-30T00:15:00Z | 66636.4000 | 0.001500 |
| 27 | ENTRY_L1 | short | 2026-03-30T11:30:00Z | 67565.8000 | -0.007200 |
| 28 | ENTRY_L2 | short | 2026-03-30T12:00:00Z | 67744.1000 | -0.004500 |

## Worst Nearest Filled-Entry Deltas

| Trade | Event | Side | TV entry UTC | Nearest Python UTC | Delta | TV price | Python price | Python reason |
|---:|---|---|---|---|---:|---:|---:|---|
| 20 | ENTRY_L2 | short | 2026-03-23T02:15:00Z | 2026-03-19T04:00:00Z | 5655.0m | 67849.4000 | 71140.7050 | L2_FILL |
| 38 | ENTRY_L2 | short | 2026-04-05T22:30:00Z | 2026-04-03T14:15:00Z | 3375.0m | 67937.4000 | 66929.3854 | L2_FILL |
| 48 | ENTRY_L2 | long | 2026-04-11T23:00:00Z | 2026-04-09T15:30:00Z | 3330.0m | 73009.9000 | 71831.9686 | L2_FILL |
| 18 | ENTRY_L2 | short | 2026-03-21T05:15:00Z | 2026-03-19T04:00:00Z | 2955.0m | 70718.9000 | 71140.7050 | L2_FILL |
| 46 | ENTRY_L2 | long | 2026-04-11T13:00:00Z | 2026-04-09T15:30:00Z | 2730.0m | 72651.6000 | 71831.9686 | L2_FILL |
| 43 | ENTRY_L1 | long | 2026-04-10T05:00:00Z | 2026-04-11T15:30:00Z | 2070.0m | 72080.8000 | 72725.4557 | L1_FILL |
| 36 | ENTRY_L2 | short | 2026-04-04T19:00:00Z | 2026-04-03T14:15:00Z | 1725.0m | 67312.6000 | 66929.3854 | L2_FILL |
| 40 | ENTRY_L2 | long | 2026-04-08T11:30:00Z | 2026-04-09T15:30:00Z | 1680.0m | 71402.7000 | 71831.9686 | L2_FILL |
| 32 | ENTRY_L2 | short | 2026-04-02T14:30:00Z | 2026-04-03T14:15:00Z | 1425.0m | 66748.8000 | 66929.3854 | L2_FILL |
| 7 | ENTRY_L2 | long | 2026-03-12T14:15:00Z | 2026-03-11T15:30:00Z | 1365.0m | 69906.8000 | 69670.1928 | L2_FILL |
| 28 | ENTRY_L2 | short | 2026-03-30T12:00:00Z | 2026-03-29T14:00:00Z | 1320.0m | 67744.1000 | 66746.7654 | L2_FILL |
| 5 | ENTRY_L2 | long | 2026-03-10T18:15:00Z | 2026-03-11T15:30:00Z | 1275.0m | 70289.0000 | 69670.1928 | L2_FILL |
| 54 | ENTRY_L1 | long | 2026-04-18T02:30:00Z | 2026-04-18T23:30:00Z | 1260.0m | 77220.0000 | 75742.9755 | L1_FILL |
| 55 | ENTRY_L2 | long | 2026-04-18T03:15:00Z | 2026-04-19T00:00:00Z | 1245.0m | 77162.8000 | 75642.5128 | L2_FILL |
| 63 | ENTRY_L1 | long | 2026-04-24T14:45:00Z | 2026-04-23T18:45:00Z | 1200.0m | 77906.2000 | 77784.6144 | L1_FILL |
| 64 | ENTRY_L2 | long | 2026-04-24T14:45:00Z | 2026-04-23T19:15:00Z | 1170.0m | 77986.4000 | 77838.7464 | L2_FILL |
| 17 | ENTRY_L1 | short | 2026-03-21T04:45:00Z | 2026-03-20T11:00:00Z | 1065.0m | 70608.0000 | 70741.6502 | L1_FILL |
| 42 | ENTRY_L2 | long | 2026-04-08T22:15:00Z | 2026-04-09T15:30:00Z | 1035.0m | 71157.5000 | 71831.9686 | L2_FILL |
| 23 | ENTRY_L1 | short | 2026-03-28T03:00:00Z | 2026-03-28T19:45:00Z | 1005.0m | 66110.7000 | 66816.5273 | L1_FILL |
| 24 | ENTRY_L2 | short | 2026-03-28T04:15:00Z | 2026-03-28T21:00:00Z | 1005.0m | 66249.2000 | 66858.1488 | L2_FILL |

## Interpretation Notes
- This report compares TradingView filled trade rows only against Python `ENTRY_L1/L2/L3` rows.
- It intentionally does not compare TradingView rows to Python `ENTRY_SIGNAL`, because that is a pre-fill trigger.
- TradingView `net_pnl_pct` is not the same unit as Python `r_multiple`; use price/time/side first, then handle PnL separately.
- If Python date-window counts are much larger than TradingView counts, the next check is profile parity: chart timeframe, `entry_timeframe`, `execution_timeframe`, RSM overrides, and available TradingView history.
