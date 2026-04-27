# Final Review

## Result Reviewer
- The new option is replay-only and defaults to the current behavior.
- SOL default replay is semantically unchanged after stripping telemetry.
- `confirm_bars=2` is a clear negative result and was not promoted.

## Watchdog
- Official BTC artifact was not regenerated.
- Core5 baseline gate still passes and BTC SHA remains `BE6FDFE9CD6A853D7983B51DCDA4D61DA41EEFE546FF8FCEDB84114630AFB41D`.
- Official SOL artifact changed only because additive telemetry fields were added.
- No live-readiness language was added.

## Residual Risk
- The confirmation option is useful as a probe but dangerous as a tuning knob; keep accepted profile at `1` until a direct TradingView/Python CVD input comparison justifies a semantic change.
