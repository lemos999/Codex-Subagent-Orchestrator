## Watchdog Contract

**Original goal**: SetupTracker — SetupState 전이 관리, 전략별 감시 존 선택 (§11.1 TREND_LONG, §11.2 PULLBACK_LONG, §11.3 REBOUND_SHORT), 존 터치 감지, 트리거 확인, 무효화 조건, 손절/목표가 계산, RR 검증

**Files produced**: Projects/Trading Value/src/trading_value/core/setup.py

**Evaluation criteria**:
1. §11.1 TREND_LONG zones: 30m Tenkan, 1h Tenkan?
2. §11.2 PULLBACK_LONG zones: priority 30m Kijun→1h Kijun→30m POC→30m VAL→1h POC→1h VAL→4h Kijun?
3. §11.3 REBOUND_SHORT zones: 15m Kijun→30m Tenkan→30m Kijun→30m VAH→30m POC→1h Tenkan?
4. §11.1 TREND_LONG trigger: 5m wick + 5m high break + 15m close >= zone.mid + 30m close > zone.low + volume?
5. §11.2 PULLBACK_LONG trigger: 15m support_hold/hammer + 5m close > max 3 highs + 15m vol > prev + 30m close >= zone.mid?
6. §11.3 REBOUND_SHORT trigger: prior decline check + 5m upper_rejection + 5m low break + 15m close < zone.mid + decline vol > bounce vol?
7. Stop/target calculations match spec exactly?
8. Invalidation conditions complete per §11?
9. SetupState transitions match §9.2?
10. RR check: tp1 RR < 1.5 blocks ENTRY_READY?

**Inspect**: Projects/Trading Value/src/trading_value/core/setup.py and Projects/Trading Value/coin_strategy_spec_v2.md §11

**Return**: Verdict: PASS or SHORTFALL. Confidence: HIGH/MEDIUM/LOW.
**Stop condition**: Evaluation only. Do NOT edit files.