# MTS-V1 SOL CVD Input Parity Diagnostic

## Inputs
- TradingView raw CSV: `samples\tradingview_mtsv1_SOL_entry15_raw.csv`
- Python JSONL: `runs\mtsv1_tv_sol_15m_binanceusdm_profile\trades.jsonl`
- OHLCV cache: `..\predictive_runner_paper\cache_180d`
- LTF / `request.security()` timeframe: `15m`
- Reverse spike multiplier: `5.5`
- Match tolerance: `15.0m`

## Summary

| Metric | Value |
|---|---:|
| reverse_spike_exit_timing_residuals | 7 |
| isolated_python_pulse_no_tv_exit_pulse | 3 |
| python_formula_pulses_at_tv_exit | 4 |
| python_formula_interval_pulses_between_exits | 4 |
| classifications | `{'isolated_python_pulse_no_tv_exit_pulse': 3, 'python_formula_pulses_at_tv_exit': 4}` |

## Residual CVD Inputs

| Trade | Class | Side | TV exit UTC | Python exit UTC | Exit delta | Py delta | Py threshold | Py ratio | Prev ratio | Prev pulse | TV-exit delta | TV-exit threshold | TV-exit ratio | TV-exit pulse | Other pulse between exits | Other pulse ratio |
|---:|---|---|---|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---|---|---:|
| 65 | python_formula_pulses_at_tv_exit | long | 2026-04-21T12:30:00Z | 2026-04-20T14:45:00Z | -1305.0m | -121376.0080 | 121189.8383 | 1.0015 | 0.1803 | false | -113983.5840 | 71086.3692 | 1.6035 | true | 2026-04-20T23:00:00Z | 1.1571 |
| 64 | python_formula_pulses_at_tv_exit | long | 2026-04-21T12:30:00Z | 2026-04-20T14:45:00Z | -1305.0m | -121376.0080 | 121189.8383 | 1.0015 | 0.1803 | false | -113983.5840 | 71086.3692 | 1.6035 | true | 2026-04-20T23:00:00Z | 1.1571 |
| 56 | python_formula_pulses_at_tv_exit | short | 2026-04-13T12:45:00Z | 2026-04-13T06:15:00Z | -390.0m | 68821.0200 | 52390.8597 | 1.3136 | 0.3154 | false | 107811.4830 | 68074.3555 | 1.5837 | true | 2026-04-13T12:45:00Z | 1.5837 |
| 57 | python_formula_pulses_at_tv_exit | short | 2026-04-13T12:45:00Z | 2026-04-13T06:15:00Z | -390.0m | 68821.0200 | 52390.8597 | 1.3136 | 0.3154 | false | 107811.4830 | 68074.3555 | 1.5837 | true | 2026-04-13T12:45:00Z | 1.5837 |
| 29 | isolated_python_pulse_no_tv_exit_pulse | long | 2026-03-25T15:00:00Z | 2026-03-25T14:00:00Z | -60.0m | -197422.1980 | 178994.1598 | 1.1030 | 0.2134 | false | -113552.2000 | 216905.4643 | 0.5235 | false |  |  |
| 30 | isolated_python_pulse_no_tv_exit_pulse | long | 2026-03-25T15:00:00Z | 2026-03-25T14:00:00Z | -60.0m | -197422.1980 | 178994.1598 | 1.1030 | 0.2134 | false | -113552.2000 | 216905.4643 | 0.5235 | false |  |  |
| 69 | isolated_python_pulse_no_tv_exit_pulse | long | 2026-04-23T17:30:00Z | 2026-04-23T17:00:00Z | -30.0m | -123314.6250 | 115195.3905 | 1.0705 | 0.5571 | false | -115392.0560 | 177020.8825 | 0.6519 | false |  |  |

## CVD Bar Inputs

| Trade | Anchor | UTC | Open | Close | Volume | Delta | Abs SMA20 | Threshold | Ratio | Pulse |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 65 | python_exit | 2026-04-20T14:45:00Z | 85.2600 | 84.7400 | 233415.4000 | -121376.0080 | 22034.5160 | 121189.8383 | 1.0015 | true |
| 65 | tv_exit | 2026-04-21T12:30:00Z | 85.7800 | 85.2600 | 219199.2000 | -113983.5840 | 12924.7944 | 71086.3692 | 1.6035 | true |
| 64 | python_exit | 2026-04-20T14:45:00Z | 85.2600 | 84.7400 | 233415.4000 | -121376.0080 | 22034.5160 | 121189.8383 | 1.0015 | true |
| 64 | tv_exit | 2026-04-21T12:30:00Z | 85.7800 | 85.2600 | 219199.2000 | -113983.5840 | 12924.7944 | 71086.3692 | 1.6035 | true |
| 56 | python_exit | 2026-04-13T06:15:00Z | 82.0100 | 82.3100 | 229403.4000 | 68821.0200 | 9525.6108 | 52390.8597 | 1.3136 | true |
| 56 | tv_exit | 2026-04-13T12:45:00Z | 82.1000 | 82.4900 | 276439.7000 | 107811.4830 | 12377.1556 | 68074.3555 | 1.5837 | true |
| 57 | python_exit | 2026-04-13T06:15:00Z | 82.0100 | 82.3100 | 229403.4000 | 68821.0200 | 9525.6108 | 52390.8597 | 1.3136 | true |
| 57 | tv_exit | 2026-04-13T12:45:00Z | 82.1000 | 82.4900 | 276439.7000 | 107811.4830 | 12377.1556 | 68074.3555 | 1.5837 | true |
| 29 | python_exit | 2026-03-25T14:00:00Z | 92.7100 | 92.3300 | 519532.1000 | -197422.1980 | 32544.3927 | 178994.1598 | 1.1030 | true |
| 29 | tv_exit | 2026-03-25T15:00:00Z | 91.9100 | 91.4100 | 227104.4000 | -113552.2000 | 39437.3571 | 216905.4643 | 0.5235 | false |
| 30 | python_exit | 2026-03-25T14:00:00Z | 92.7100 | 92.3300 | 519532.1000 | -197422.1980 | 32544.3927 | 178994.1598 | 1.1030 | true |
| 30 | tv_exit | 2026-03-25T15:00:00Z | 91.9100 | 91.4100 | 227104.4000 | -113552.2000 | 39437.3571 | 216905.4643 | 0.5235 | false |
| 69 | python_exit | 2026-04-23T17:00:00Z | 85.7700 | 85.3200 | 274032.5000 | -123314.6250 | 20944.6165 | 115195.3905 | 1.0705 | true |
| 69 | tv_exit | 2026-04-23T17:30:00Z | 84.9700 | 84.7100 | 443815.6000 | -115392.0560 | 32185.6150 | 177020.8825 | 0.6519 | false |

## Python CVD Formula
- Pine source uses `delta_bar = request.security(syminfo.tickerid, ltf, (close - open) * volume, barmerge.gaps_off, barmerge.lookahead_off)`.
- This report reconstructs the same formula from the local OHLCV cache and the accepted symbol RSM.
- TradingView Strategy Report CSV exports do not include `delta_bar`, `cvd_abs_sma_20`, or reverse-spike plot values, so this is a Python-side input reconstruction, not a direct TV plot export comparison.
- If `python_formula_pulses_at_tv_exit` is zero, the remaining mismatch needs either a TradingView CVD plot export or another non-CVD order/state timing explanation before changing replay semantics.
