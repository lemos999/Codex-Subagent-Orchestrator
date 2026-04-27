# Plan Validation

## Result
PASS.

## Validation Notes
- Pine and Python both use strict adverse `delta_bar` against `active_rsm * sma(abs(delta_bar), 20)`.
- Existing reports identified reverse-spike as the source but lacked pulse strength details.
- The safe next step is telemetry and report exposure, not a replay rule change.
- BTC artifact must not be regenerated because the release gate pins its SHA.
- SOL artifact promotion is acceptable only after stripping `state2_*` fields proves row equivalence.

## Watchdog Notes
- No live-ready language is allowed.
- Do not expand to ETH/BNB before SOL reverse-spike timing is understood.
- Do not alter Pine or `strategy.py` semantics in this diagnostic task.
