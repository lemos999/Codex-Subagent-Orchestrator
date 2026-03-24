# Python Logic Review: trading-quest mission system

You are reviewing 2 Python files for a trading quest mission system. Focus on:

## Files to review
1. `trading-quest/tq/journal/memory.py` — AI trading memory (save_best_params, record_mistake dedup)
2. `trading-quest/tq/web/routes.py` — Mission SSE endpoint (Phase 1 scan + Phase 2 optimize)

## Review checklist
1. **Phase 1 budget**: `phase1_budget = min(len(all_strategies), int(max_iterations * 0.4))` — Does this correctly limit phase 1? What if `result is None` (strategy fails)? The iteration counter increments but no scan_result is added. Could phase 1 end with 0 usable results?
2. **Phase 2 loop termination**: `while iteration < max_iterations and not mission_complete and len(exhausted_strategies) < len(top_strategies)` — Can this exit prematurely if all top strategies get exhausted before max_iterations? Is the random fallback sufficient to prevent exhaustion?
3. **Infinite loop risk**: In phase 2, if `_run_single_backtest` keeps returning None for a strategy, iteration doesn't increment but the loop continues. Is there a risk of spinning forever?
4. **`exhausted_strategies` logic**: When a strategy hits 3 consecutive 0-scores, it's added to exhausted. But `zero_score_count` is checked per strategy name — if the same strategy appears in scan_results with different params, does the counter work correctly?
5. **`save_best_params` tiebreaker**: Changed from `>=` to split `>` and `== with win_rate`. Is the logic correct? Edge case: what if score is equal and win_rate is also equal but trades count is higher?
6. **`record_mistake` dedup**: Uses `_params_hash` to check existing. But `_params_hash` loads the entire mistakes.json every time `record_mistake` is called. With many iterations, is this a perf concern?
7. **`import random` inside loop**: `import random` is inside the Phase 2 while loop body. Python caches imports but this is inside a generator function — any issue?
8. **`best_trades` variable**: Initialized to 0, updated in Phase 1 and Phase 2. But what if best_score never improves (stays at -inf)? Then `best_trades=0` is passed to `save_best_params` which is gated by score check anyway. OK?

## Output format
For each issue found, report:
- **Severity**: critical / medium / low
- **File**: filename:line (approximate)
- **Issue**: description
- **Fix suggestion**: what should change

If no issues found for a checklist item, say "OK" briefly.
