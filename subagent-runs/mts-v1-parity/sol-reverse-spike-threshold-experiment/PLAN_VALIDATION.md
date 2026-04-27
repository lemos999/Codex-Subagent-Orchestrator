# Plan Validation

## Lead Review
- The candidate is scoped to one signal family: reverse-spike threshold handling.
- The plan does not alter HTF cross, entry matching, order fill timing, HardSL, or sizing semantics.

## Watchdog Review
- No network dependency is required; use local cache and existing artifacts.
- Do not touch unrelated dirty workspace changes.
- Do not update live-readiness language.

## Result Reviewer Expectations
- A promoted change must preserve BTC protected metrics and SHA.
- If the threshold guard only improves one edge case but creates broader semantic drift, record it as rejected evidence rather than forcing promotion.
- If the guard stays experimental only, keep accepted profile defaults unchanged and record the blocker for the next task.
