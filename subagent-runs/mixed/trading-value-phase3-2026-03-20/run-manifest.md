# Run Manifest: trading-value-phase3-2026-03-20

## Request
- **Original**: Trading Value 3단계 — SetupTracker + PositionManager + BacktestAdapter + 테스트. Watchdog GPT-5.4, position-manager는 GPT-5.4 xhigh (codex fallback → claude opus).
- **Classification**: create
- **Complexity**: high

## Team
- **Pattern**: C — Multi-stage with mixed engine watchdogs
- **Agent count**: 5 workers + 3 fixers + 3 watchdogs = 11
- **Shared directive**: reference (AGENTS.md)

## Agents

### Agent 1: setup-tracker (claude/opus) — completed
- SetupContext, zone selection, triggers, stop/target, invalidation, transitions
- Fixer: invalidation wiring added (InvalidationInput dataclass, evaluate_setup_transition calls invalidation checks)

### Agent 2: position-manager (codex/gpt-5.4 → fallback claude/opus) — completed
- Position sizing, splits, trailing, cooldown, max_hold, lifecycle transitions, risk, invariants
- Fixer: EXIT_WORKING transitions, STOP_ORDER_ATTACHED gate, expanded invariant validation

### Agent 3: backtest-adapter (claude/opus) — completed
- BacktestEngine, VirtualOrder, simulate_fill, TradeRecord, DecisionLog, BacktestResult
- Fixer: exit order routing, BarClosedEvent OHLCV

### Agent 4: test-writer (claude/sonnet) — completed
- 62 tests: test_setup (22), test_position (27), test_backtest (13)

### Agent 5: reviewer (claude/sonnet) — completed
- Verdict: MINOR_ISSUES (process_lifecycle_event gate untested in backtest path)

## Watchdog (codex/gpt-5.4)

| Stage | Verdict | Accepted Fixes | Rejected |
|-------|---------|---------------|----------|
| setup-tracker | SHORTFALL | invalidation wiring | tp sort, 5m sequencing |
| position-manager | SHORTFALL | EXIT_WORKING, STOP gate, invariants | — |
| backtest-adapter | SHORTFALL | exit routing, OHLC | partial fill, engine state |

## Deliverables
- `setup.py`: SetupContext + 18 functions (zones, triggers, stops, invalidation, transitions)
- `position.py`: 9 function groups (sizing, splits, trailing, cooldown, lifecycle, risk, invariants)
- `backtest.py`: BacktestEngine + 7 classes + 16 functions (event loop, virtual orders, metrics)
- `test_setup.py`: 22 tests
- `test_position.py`: 27 tests
- `test_backtest.py`: 13 tests

## Metrics
- **Total tests**: 62 passed (Phase 3) + 158 passed (Phase 1+2) = 220 total
- **Fix cycles**: 3 (all watchdog-driven)
- **GPT-5.4 watchdog value**: caught EXIT_WORKING skip, STOP_ORDER_ATTACHED gate, exit routing bug

## Timeline
- **Started**: 2026-03-20
- **Completed**: 2026-03-20

## Notes
- Codex GPT-5.4 position-manager failed (hung on WKI indexing). Fallback to Claude opus.
- Backtest adapter is 1136 lines (exceeded 500 target) but covers full event loop.
- Reviewer noted backtest adapter bypasses STOP_ORDER_ATTACHED gate — acceptable for simulation but noted for future paper/live adapter.
