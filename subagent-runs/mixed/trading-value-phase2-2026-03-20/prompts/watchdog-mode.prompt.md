## Watchdog Contract

**Original goal**: ModeSelector 구현 — coin_strategy_spec_v2.md §10 허용 전략 매트릭스 (11행 전부) + §12 신규 진입 금지 필터 (8가지 조건 전부). EngineState != READY 또는 RiskGate == BLOCK 시 MODE_NO_TRADE 강제.

**Worker stage**: Stage 2b (mode-selector / sub-implementer)
**Files produced**: Projects/Trading Value/src/trading_value/core/mode.py

**Your task**: Read mode.py and verify every matrix row and filter condition matches the spec exactly.

**Evaluation criteria**:
1. §10 Matrix (11 rows):
   - BULLISH + H1_BULLISH + M30_BULLISH → TREND_LONG
   - BULLISH + H1_BULLISH + M30_NEUTRAL → TREND_LONG (enhanced: vol>=1.5*sma5, RR>=2.0)
   - BULLISH + H1_BULLISH + M30_BEARISH → PULLBACK_LONG
   - BULLISH + H1_NEUTRAL + M30_BULLISH → TREND_LONG
   - BULLISH + H1_NEUTRAL + M30_NEUTRAL/BEARISH → PULLBACK_LONG
   - BULLISH + H1_BEARISH + M30_BEARISH → REBOUND_SHORT (reduced risk)
   - BULLISH + H1_BEARISH + M30_NEUTRAL/BULLISH → NO_TRADE
   - NEUTRAL + H1_BEARISH + M30_BEARISH → REBOUND_SHORT
   - NEUTRAL + other → NO_TRADE
   - BEARISH + any + M30_BEARISH/NEUTRAL → REBOUND_SHORT
   - BEARISH + any + M30_BULLISH → NO_TRADE
2. §12 Entry Filters (all 8):
   - box_center_30m, abnormal_volatility, RR<1.5, low volume, high_impact_event, existing position, total risk exposure, loss limits (consecutive 4, daily -3R, weekly)
3. Engine/RiskGate pre-checks force MODE_NO_TRADE
4. Enhanced conditions correctly recorded for BULLISH+H1_BULLISH+M30_NEUTRAL row

**Inspect**:
- Projects/Trading Value/src/trading_value/core/mode.py
- Projects/Trading Value/coin_strategy_spec_v2.md (§10, §12)

**Return**: Verdict: PASS or SHORTFALL. If SHORTFALL: specific missing rows or filters. Confidence: HIGH/MEDIUM/LOW.
**Stop condition**: Evaluation only. Do NOT edit files.