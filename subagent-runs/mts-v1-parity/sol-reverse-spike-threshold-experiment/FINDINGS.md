# Findings

## Scope
- Added `reverse_spike_min_ratio` as a replay experiment option.
- Default value is `1.0`, preserving the existing strict Pine-style `delta > threshold` / `delta < -threshold` behavior.
- Added focused unit coverage for threshold-edge filtering and strong-pulse preservation.
- Did not change `strategy.pine`, official BTC artifact, or official SOL artifact.

## Experiment
Command candidate:

```powershell
python offline_replay.py --symbols SOL/USDT:USDT --cache-dir ..\predictive_runner_paper\cache_180d --days 90 --output runs\mtsv1_tv_sol_15m_binanceusdm_profile\trades_minratio_1005_probe.jsonl --entry-timeframe 15m --execution-timeframe 15m --htf-timeframe 4h --symbol-reverse-spike-multipliers BTC=6.3,ETH=6.8,SOL=5.5,XRP=6.3,BNB=2.5 --cvd-entry-mode pine-ltf --reverse-spike-min-ratio 1.005
```

Probe output:
- `events=250`
- `exits=64`
- Report: `Projects/Trading Value/MTS-V1/parity_reports/sol_diff_minratio_1005.md`

## Result
Compared with the official SOL baseline:
- Entry matches did not improve: official `40/69`, probe `40/71`.
- Exit timestamp matches did not improve: official `27/40`, probe `27/40`.
- Exit price <= `0.15` improved: official `33/40`, probe `35/40`.
- Average exit delta improved: official `0.094749`, probe `0.072249`.
- The largest threshold-edge drift pair moved from Python exit `2026-04-20T14:45:00Z` to `2026-04-20T23:00:00Z`, but TradingView exits at `2026-04-21T12:30:00Z`, so timing parity remains wrong.

## Promotion Decision
Do not promote `reverse_spike_min_ratio=1.005` into the accepted profile or official SOL artifact.

Reason:
- It improves price residuals but does not reduce SOL matched exit timing residual count.
- The remaining 4/20 residual is still reverse-spike sourced with ratio `1.1571`, so a small threshold-edge guard is not the main timing rule mismatch.
- Raising the guard further would no longer be a narrow edge guard and would risk broad reverse-spike behavior drift.

## Default Safety
Default replay was regenerated to `runs\mtsv1_tv_sol_15m_binanceusdm_profile\trades_default_minratio_probe.jsonl`.

Result:
- `events=253`
- `exits=65`
- byte-for-byte equal to official `runs\mtsv1_tv_sol_15m_binanceusdm_profile\trades.jsonl`

## Next Recommended Task
SOL reverse-spike confirmation/order timing experiment.

Focus on the 4/20 and 4/13 residuals by checking whether Pine sees the same reverse-spike pulse on the same calculation pass after State2 fill recognition. Do not tune the threshold upward further before isolating calculation-pass ordering.

No ETH/BNB expansion and no live-ready claim.
