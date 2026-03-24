# Fix Material Issues in trading-quest

Working directory: C:\Users\haj\projects\subagent-orchestrator\trading-quest

## Issue 1 (CRITICAL): Engine data not sliced to simulation date
File: tq/quest/engine.py

The engine fetches data but always passes the FULL dataset to strategy.decide(). 
Strategy always sees the latest real row (2026-03-16) regardless of simulated day.
This means 0 trades are generated during backtesting.

FIX: In the method that passes data to strategy, slice the DataFrame so it only contains rows up to and including the current simulation date. Something like:
```python
history = data[data.index <= current_sim_date]
```
Find where strategy is called with history/data and add this slice.

## Issue 2 (CRITICAL): process_signals() SELL on symbols without position
File: tq/quest/engine.py

When a SELL signal is generated for one symbol, the engine attempts to sell ALL symbols. 
This produces "No position" errors.

FIX: Only submit orders for the specific symbol that generated the signal. Check if a position exists before attempting to sell.

## Issue 3 (MEDIUM): Missing Web API endpoints
File: tq/web/routes.py

These API endpoints are missing and must be added:
- GET /api/quests — list all active quests
- GET /api/quest/<quest_id>/trades — return trade_log from quest state
- GET /api/data/<symbol> — return OHLCV data with start/end params
- GET /api/data/<symbol>/indicators — compute and return SMA/BB indicators
- POST /api/compare — run strategy comparison

Add these endpoints. Use the existing DataCache, QuestState, and StrategyRanker classes.

## Issue 4 (MEDIUM): Phase transition min_score too high
File: tq/quest/phase.py

Phase 1→2 requires min_score=100 but scores start at 0 and stay there when no trades occur.

FIX: Either remove the min_score requirement (use day count instead) or lower it significantly. The original design used date-based transitions (current_date >= phase1_end_date), not score-based.

## Validation
After fixing, run:
1. py -m pytest tests/ -q
2. py -m tq quest start --market US --strategy macd --symbols "AAPL,MSFT,GOOGL"
   Then: py -m tq quest run --quest-id <id> --days 30
   Verify trades > 0 and score > 0
