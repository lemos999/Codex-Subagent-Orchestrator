# Frontend Review: trading-quest backtest.html

You are reviewing `trading-quest/tq/web/templates/backtest.html` — a single-page HTML with inline JS for a trading mission system.

## Review checklist
1. **SSE event processing**: The `processMissionEvent(evt)` function handles iteration events and `done` events. Check if all fields from the server (`iteration`, `max_iterations`, `strategy`, `params`, `params_summary`, `trades`, `wins`, `losses`, `win_rate`, `return_pct`, `score`, `objectives_met`, `status`, `best_so_far`) are properly consumed. Any missing field handling?
2. **Chart data accumulation**: `msState.scoreHistory` uses `{iter, value}` but `drawLineChart` expects `{time?, value}` — the function accesses `data[i].value` which works, but the x-axis uses index-based positioning. Is this correct?
3. **Symbol autocomplete**:
   - `onSymbolInput()` uses debounce 150ms — OK?
   - `_selectedSymbols` is initialized as `["AAPL", "TSLA", "META"]` and `renderSymbolTags()` is called on init. But `ms-symbols` hidden input is also pre-set. Are they in sync?
   - When clicking outside dropdown, does the close handler work?
   - Does `onMissionMarketChange()` need to clear selected symbols or just close dropdown?
4. **Memory leak / event listener**: `document.addEventListener("click", ...)` is added at module level — this is fine for a single page. Any resize handler issues?
5. **Benchmark section**: Still references `/api/backtest/stream` — is this endpoint still available after removing the backtest IIFE? (The endpoint is in routes.py, not in the removed JS)
6. **Missing `lightweight-charts` import**: The old page imported `lightweight-charts` for candlestick. The new page removed it. But does the benchmark section use it? Check all references.
7. **`drawLineChart` color fill**: `color.replace(")", ",0.1)").replace("rgb", "rgba")` — does this work for all color formats passed? Check: `"rgb(245,158,11)"` → `"rgb(245,158,11,0.1)"` → `"rgba(245,158,11,0.1)"`. Is this correct?
8. **Error handling**: If `/api/mission` returns non-200, the fetch `.then()` will still execute. Is there a check for `resp.ok`?

## Output format
For each issue: **Severity** (critical/medium/low), **Location**, **Issue**, **Fix suggestion**.
