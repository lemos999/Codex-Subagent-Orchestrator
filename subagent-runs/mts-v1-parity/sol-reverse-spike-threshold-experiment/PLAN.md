# Plan

## Backlog
- Current item: SOL reverse-spike threshold/confirmation experiment.
- Later items: SOL semantic promotion decision, XRP semantic diagnosis, ETH/BNB expansion only after SOL/XRP gates improve.

## Selected Next Task
Test exactly one replay candidate: a threshold-edge guard for reverse-spike State2 aborts.

## Rationale
- The previous loop showed all seven Python-early SOL State2 residual rows are `reverse_spike`.
- The largest drift pair exits `1305m` early with ratio `1.0015`, which is close enough to the strict threshold that small OHLCV/CVD provider differences can flip the pulse.
- HTF cross has no matched timing residuals, so it remains out of scope.

## Implementation Intent
- Add a narrow replay parameter for minimum adverse reverse-spike ratio.
- Keep the default at the current strict behavior unless the experiment is explicitly promoted.
- Run a SOL probe first, compare against TradingView, and only then decide whether to replace the official SOL artifact.
- Regenerate Core5 reports only after BTC/XRP safety checks pass.

## Verification Gates
- Focused unit tests around the new guard.
- SOL replay probe and SOL diff report.
- BTC baseline gate, including SHA256.
- XRP/Core5 baseline report remains generated.
- Ruff and `py_compile` over touched files.

## Rollback
- Revert the new parameter and generated probe/report artifacts if BTC baseline regresses or SOL metrics degrade.
