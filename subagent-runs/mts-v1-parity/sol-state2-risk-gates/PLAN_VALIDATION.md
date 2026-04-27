# Plan Validation

## Result
Approved with narrow scope.

## Rationale
- The SOL `reverse_spike_min_ratio=1.5` probe can be run without changing accepted replay defaults.
- Risk gate implementation is orthogonal to parity semantics and closes a previously documented local blocker.
- Strict risk gate mode is opt-in, so existing paper-only replay and tests can continue while live/promotion checks fail closed.

## Watchdog Notes
- Do not promote the ratio probe unless entry and exit parity improve without increasing missing cycles.
- Do not claim live-ready: MMR values in production must still come from exchange-published values, and daily PnL must be wired to live accounting before real orders.
