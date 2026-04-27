# Findings

## Scope
- Added replay-only `reverse_spike_confirm_bars` / `--reverse-spike-confirm-bars`.
- Accepted profile default remains `reverse_spike_confirm_bars=1`.
- Added diagnostic telemetry for previous reverse-spike pulse and last recognized fill:
  - `state2_reverse_spike_prev`
  - `state2_reverse_spike_ratio_prev`
  - `state2_reverse_spike_confirm_bars`
  - `state2_last_fill_event`
  - `state2_last_fill_reason`
  - `state2_minutes_since_last_fill`
  - `state2_l2_filled`
- Updated SOL diff residual rows to show previous pulse, confirm bars, last fill, fill age, and L2-filled state.

## Default Safety
- Default SOL replay produced `253` events / `65` exits.
- Stripping `state2_*` fields from old official SOL artifact and new default probe gave:
  - `old_rows=254 new_rows=254 stripped_equal=True`
- The official SOL artifact was updated only for telemetry fields.
- New SOL artifact SHA256:
  - `EEC7A0BD5C1D8B61A78E66AB88DF9A66F802EB754A4AB625D28809922CCE1AF8`

## Confirmation Probe
Command candidate:

```powershell
python offline_replay.py --symbols SOL/USDT:USDT --cache-dir ..\predictive_runner_paper\cache_180d --days 90 --output runs\mtsv1_tv_sol_15m_binanceusdm_profile\trades_confirm2_probe.jsonl --entry-timeframe 15m --execution-timeframe 15m --htf-timeframe 4h --symbol-reverse-spike-multipliers BTC=6.3,ETH=6.8,SOL=5.5,XRP=6.3,BNB=2.5 --cvd-entry-mode pine-ltf --reverse-spike-confirm-bars 2
```

Probe output:
- `events=140`
- `exits=35`
- Report: `Projects/Trading Value/MTS-V1/parity_reports/sol_diff_confirm2.md`

## Result
`reverse_spike_confirm_bars=2` is rejected.

Compared with official SOL:
- Entry matches regressed from `40/69` to `28/71`.
- Exit timestamp matches regressed from `27/40` to `12/28`.
- Exit price <= `0.15` regressed from `33/40` to `19/28`.
- Python exits fell from `65` to `35`, creating broad missing-cycle drift.

## Residual Insight
The official SOL residual telemetry shows the early reverse-spike exits are isolated pulses, not confirmed consecutive pulses:
- 4/20 trades `64/65`: current ratio `1.0015`, previous ratio `0.1803`, previous pulse `false`, last fill `ENTRY_L2/L2_FILL_ON_CLOSE`, last-fill age `240.0m`.
- 4/13 trades `56/57`: current ratio `1.3136`, previous ratio `0.3154`, previous pulse `false`, last fill `ENTRY_L2/L2_FILL`, last-fill age `270.0m`.
- 3/25 trades `29/30`: current ratio `1.1030`, previous ratio `0.2134`, previous pulse `false`, last-fill age `15.0m`.
- 4/23 trade `69`: current ratio `1.0705`, previous ratio `0.5571`, previous pulse `false`, last-fill age `0.0m`.

This explains why `confirm_bars=2` removes early pulses, but it also removes too many valid exits and breaks cycle alignment.

## Promotion Decision
Do not promote `reverse_spike_confirm_bars=2`.

## Next Recommended Task
Inspect CVD input parity around the isolated pulse bars, especially TradingView LTF `request.security()` behavior versus Python 15m OHLCV-derived `(close-open)*volume`.

No ETH/BNB expansion and no live-ready claim.
