## Watchdog Contract

**Original goal**: Trading Value 지표 엔진 구현 — coin_strategy_spec_v2.md §5의 모든 지표 규칙 (이치목 9/26/52, ATR 14, 고정윈도우 볼륨프로파일 POC/VAH/VAL, 스윙 left=2 right=2), §6 파생필드 (cloud_position, tk_state, profile_bias), §7 정량 보조 조건 (zone_width, upper_rejection, support_hold, maintain_above/below, box_center_30m, retracement, abnormal_volatility, hammer)

**Worker stage**: Stage 1 (indicator-engine / sub-implementer)
**Worker output summary**: indicators.py created with 19 pure functions covering all 8 function groups
**Files produced**: Projects/Trading Value/src/trading_value/core/indicators.py

**Your task**: Read the indicator implementation and the spec document. Evaluate whether the output covers ALL indicator rules from §5, §6, §7.

**Evaluation criteria**:
1. §5.2 Ichimoku: tenkan/kijun/senkou_a/senkou_b/cloud_top/cloud_bottom calculated correctly? cloud_top/bottom at CURRENT bar (not forward-shifted)?
2. §5.3 Volume Profile: fixed windows (30m=96, 1h=120, 4h=90)? POC/VAH/VAL with 70% value area? 15m/5m excluded?
3. §5.4 ATR: Wilder's smoothing, period=14?
4. §5.5 Swing: left=2, right=2 fractal, only confirmed (right bars completed)?
5. §6 Derived fields: cloud_position (above/in/below), tk_state (bullish/bearish), profile_bias (above_va/inside_va/below_va)?
6. §7.1 Zone width: max(price*0.0015, ATR_15m*0.25)?
7. §7.2 upper_rejection: high>=zone.high AND close<zone.mid AND upper_wick>=body?
8. §7.3 support_hold: low<zone.low AND close>zone.mid AND lower_wick>=body?
9. §7.4 maintain_above/below: 2 consecutive closes?
10. §7.5 box_center_30m: 48-bar range, 40-60%, distance>=0.5*ATR_30m?
11. §7.6 retracement: (close-swing_low)/(swing_high-swing_low)?
12. §7.7 abnormal_volatility: 15m>2.5*ATR or 30m>2.0*ATR?
13. §11.2 hammer candle: body<=35% total, lower_wick>=2*body, close>=open?

**Inspect**:
- Projects/Trading Value/src/trading_value/core/indicators.py
- Projects/Trading Value/coin_strategy_spec_v2.md (sections 5, 6, 7, 11.2)

**Return**:
- Verdict: PASS or SHORTFALL
- If SHORTFALL: specific findings (what spec requires vs what was delivered)
- Confidence: HIGH / MEDIUM / LOW

**Stop condition**: Evaluation only. Do NOT edit files. Do NOT suggest scope expansion.