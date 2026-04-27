# Plan Validation

## Result

Proceed with the candidate as a replay-only diagnostic, not as an accepted semantic change.

## Rationale

- Prior threshold/confirmation probes failed to improve timing safely.
- CVD input reconstruction showed later TV-exit bars can still have Python-formula pulses, so a pure threshold rule is unlikely to solve the residual.
- The current residual rows all have L2 filled, making an L2-recognition hold a bounded calculation-pass hypothesis.
- Default `0.0` avoids changing BTC/Core5 accepted artifacts while the candidate is evaluated.

## Watchdog Notes

- Do not overwrite official SOL/BTC artifacts during the probe.
- Reject if entry/cycle alignment regresses even when price residuals improve.
- No live-ready claim is allowed from this work.
