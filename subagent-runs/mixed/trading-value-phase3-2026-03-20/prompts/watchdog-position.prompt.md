## Watchdog Contract

**Original goal**: PositionManager — TradeLifecycleState 전이 (§9.3), 분할 진입 50/30/20, 분할 청산 30/30/40, 전략별 트레일링 스탑, 쿨다운 (정상 2봉/손절 4봉), 최대 보유 48봉, 포지션 사이징 §13.2, 불변조건 (stop_price 필수, 반대방향 금지)

**Files produced**: Projects/Trading Value/src/trading_value/core/position.py

**Evaluation criteria**:
1. §13.2 position sizing: TargetQty = (Balance * Risk%) / |Entry - Stop|, round down to min_qty?
2. Entry splits 50/30/20 correct?
3. Exit splits 30/30/40 correct?
4. §11.1 TREND_LONG trailing: 5m close < 5m Kijun → half, 15m close < 15m Tenkan → all?
5. §11.2 PULLBACK_LONG trailing: 15m close < 15m Kijun → half, 30m close < zone mid → all?
6. §11.3 REBOUND_SHORT trailing: 5m close > 5m Kijun → 30%, 15m close > 15m Tenkan → half, 15m close > 15m Kijun → all?
7. §13.5 cooldown: normal=2 bars (1h), stop_loss=4 bars (2h)?
8. §13.6 max hold: 48 bars, <0.5R → close, >=0.5R → tighten?
9. §9.3 lifecycle transitions complete? (FLAT→ENTRY_WORKING→OPEN_STAGE0→1→2→EXIT_WORKING→COOLDOWN→FLAT)
10. Invariants: OPEN states require stop_price, side matches lifecycle?

**Inspect**: Projects/Trading Value/src/trading_value/core/position.py and Projects/Trading Value/coin_strategy_spec_v2.md §11, §13, §14 and auto_trading_state_machine_design.md §9.3

**Return**: Verdict: PASS or SHORTFALL. Confidence: HIGH/MEDIUM/LOW.
**Stop condition**: Evaluation only. Do NOT edit files.