## Watchdog Contract

**Original goal**: 이벤트 기반 백테스트 엔진 — §16.1 필수 조건 (슬리피지, 수수료, 부분 체결), OHLCV→BAR_CLOSED 이벤트 변환, §10 평가 우선순위 (EngineState→RiskGate→RegimeState/ModeState→Setup→Position), 심볼별 직렬 이벤트 루프, 가상 주문 체결, 멱등 이벤트, 로그/저널 (§15), 결과 집계 (PnL, 승률, 최대 낙폭, RR 분포)

**Files produced**: Projects/Trading Value/src/trading_value/adapters/backtest.py

**Evaluation criteria**:
1. §16.1: slippage, commission, partial fill support?
2. §10 evaluation priority: 4H→1H→30M→15M→5M bar close order? Exits before new entries?
3. §15 log fields present? (timestamp, symbol, event_type, regime_state, mode_state, setup_state, lifecycle_state, reason)
4. VirtualOrder with TTL (2x5m bars)?
5. BacktestResult has: win_rate, avg_rr, max_drawdown, max_consecutive_losses?
6. TradeRecord captures: strategy, entry/exit prices, pnl_r, exit_reason, regime_at_entry?
7. build_snapshots_at helper exists?
8. BacktestEngine.run() accepts dict[str, dict[Timeframe, DataFrame]]?

**Inspect**: Projects/Trading Value/src/trading_value/adapters/backtest.py

**Return**: Verdict: PASS or SHORTFALL. Confidence: HIGH/MEDIUM/LOW.
**Stop condition**: Evaluation only. Do NOT edit files.