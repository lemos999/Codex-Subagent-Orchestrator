# /submix Review: trading-quest mission system

## Engines Used
- **Gemini (gemini-2.5-pro)**: Python logic review — completed
- **Codex (gpt-5.4)**: Frontend review — no output (timeout/failure, fallback to manual)
- **Claude (haiku)**: Integration watchdog — no output (timeout, fallback to manual)

## Consolidated Findings

### CRITICAL (must fix)

| # | File | Issue |
|---|------|-------|
| C1 | routes.py:738 | Phase 1: `iteration` increments even for failed strategies (result=None). If many strategies fail, Phase 1 wastes budget and `scan_results` can be empty → Phase 2 has nothing to optimize |
| C2 | routes.py:768 | `win_rate < 0.2` records mistake for 0-trade results (win_rate=0.0, trades=0). A strategy with no trades isn't a "mistake" — it just didn't trigger signals |
| C3 | backtest.html | `/api/mission` fetch has no `resp.ok` check — non-200 responses are processed as SSE stream, causing silent failures |

### MEDIUM (should fix)

| # | File | Issue |
|---|------|-------|
| M1 | memory.py | `record_mistake` dedup scans all existing mistakes and re-hashes params every call → O(N²) as file grows |
| M2 | routes.py | `import random` inside generator body — non-idiomatic, should be at module level |
| M3 | routes.py | Phase 2 `top_strategies` is limited to 5. Once all 5 exhausted, loop ends even if budget remains. Could try strategies ranked 6+ |
| M4 | memory.py:87 | Tiebreaker: same score+win_rate but more trades → more statistically significant, should prefer |

### LOW (nice to have)

| # | File | Issue |
|---|------|-------|
| L1 | memory.py | Extreme disk I/O — every `has_tried`/`record_trial` reads+writes JSON files |
| L2 | routes.py | `_generate_param_variations` has limited factor list, Phase 2 may exhaust candidates quickly |
| L3 | backtest.html | `drawLineChart` color fill regex `replace(")", ",0.1)")` works for rgb() but would break for hex colors — current usage is OK |

## Frontend Review (manual)
- SSE event fields: all consumed correctly
- Chart data uses `{iter, value}` → `drawLineChart` uses index-based x, works fine
- Symbol autocomplete init is in sync with hidden input
- Benchmark section uses `/api/backtest/stream` which is still defined in routes.py — OK
- `lightweight-charts` removed correctly — benchmark doesn't use it
