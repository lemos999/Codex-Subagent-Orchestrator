## Watchdog Contract
**Original goal**: RiskManager — RiskGate 평가 (ALLOW/REDUCE/BLOCK), §13.3 중단규칙 (연속4손실, 일일-3R, 주간한도, API오류3연속, 슬리피지2배), 거래결과 기록, 리셋, risk_pct 선택
**Files**: Projects/Trading Value/src/trading_value/core/risk.py
**Criteria**: 1) BLOCK conditions match §13.3 exactly? 2) REDUCE for counter-trend/volatility? 3) record_trade_result handles date/week rollover? 4) slippage monitoring rolling 20? 5) select_risk_pct: counter_trend=0.25%, BLOCK=0?
**Inspect**: risk.py + coin_strategy_spec_v2.md §13
**Return**: PASS or SHORTFALL. Confidence. Do NOT edit files.