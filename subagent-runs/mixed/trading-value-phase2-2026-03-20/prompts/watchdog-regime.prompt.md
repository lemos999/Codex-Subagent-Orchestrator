## Watchdog Contract

**Original goal**: RegimeClassifier 구현 — coin_strategy_spec_v2.md §8의 모든 타임프레임 상태 분류. HTF_BULLISH/NEUTRAL/BEARISH (§8.1), H1_BULLISH/NEUTRAL/BEARISH (§8.2), M30_BULLISH/NEUTRAL/BEARISH (§8.3). 각 판정 조건의 비교 연산자(> vs >=)가 정확히 spec과 일치해야 함.

**Worker stage**: Stage 2a (regime-classifier / sub-implementer)
**Files produced**: Projects/Trading Value/src/trading_value/core/regime.py

**Your task**: Read regime.py and spec §8. Verify EVERY condition's operator matches exactly.

**Evaluation criteria**:
1. §8.1 HTF_BULLISH: close > cloud_top (strict), tenkan > kijun (strict), profile_bias != below_va
2. §8.1 HTF_BEARISH: close < cloud_bottom (strict), tenkan < kijun (strict), profile_bias == below_va
3. §8.2 H1_BULLISH: close > cloud_top (strict), tenkan >= kijun, close >= kijun, profile_bias != below_va
4. §8.2 H1_BEARISH: close < cloud_bottom (strict), tenkan <= kijun, close <= kijun, profile_bias == below_va
5. §8.3 M30_BULLISH: close > cloud_top (strict), tenkan > kijun (strict), close >= kijun
6. §8.3 M30_BEARISH: close < cloud_bottom (strict), tenkan < kijun (strict), close <= kijun
7. NEUTRAL is the fallback for each when neither BULLISH nor BEARISH conditions are met
8. RegimeSnapshot combines all three levels
9. classify_regime requires H4, H1, M30 snapshots

**Inspect**:
- Projects/Trading Value/src/trading_value/core/regime.py
- Projects/Trading Value/coin_strategy_spec_v2.md (§8 only)

**Return**: Verdict: PASS or SHORTFALL. If SHORTFALL: specific operator mismatches. Confidence: HIGH/MEDIUM/LOW.
**Stop condition**: Evaluation only. Do NOT edit files.