# Plan

## Goal
Continue the remaining `$vloop` steps after SOL CVD input parity:

1. Test one bounded SOL reverse-spike timing candidate.
2. Add local fail-closed risk gate coverage for MMR leverage cap and daily max-loss.
3. Preserve BTC/Core5 baseline and avoid live-ready claims.

## Constraints
- Do not overwrite official BTC/SOL accepted artifacts unless a candidate improves semantic parity and preserves BTC.
- Do not lower strict semantic targets.
- Treat direct TradingView CVD plot export as an external condition unless a local substitute is enough.
- Risk gates may be implemented locally, but live-readiness still requires production/exchange validation.

## Implementation
- Run a high-ratio SOL reverse-spike probe as a data-drift/timing candidate.
- Reject the candidate if it reduces common-window match quality or creates missing cycles.
- Add a reusable Python `risk_gate.py`.
- Add `--require-risk-ready` and `--daily-pnl-pct` to the MTS paper runner so strict mode blocks before replay.
- Add Pine MMR effective leverage cap formula to order sizing.
- Add focused unit/static tests and CLI evidence probes.

## Verification
- Focused tests for risk gate, MTS paper runner, Pine static checks, parity diff, and replay.
- Full MTS-V1 tests.
- Ruff and `py_compile`.
- Core5 baseline gate.
- Evidence self-check.

## Rollback
- Revert `risk_gate.py`, MTS paper runner strict gate changes, Pine leverage formula changes, tests, and generated probe artifacts.
