# Strategy Spec Review: coin_strategy_spec_v2.md

You are reviewing a crypto trading strategy specification for ETHUSDT/BTCUSDT Perp. Focus on **deterministic completeness** — can a machine execute these rules without human interpretation?

## Review Checklist

### 1. Ambiguous conditions
Find any rule that a programmer would need to "interpret" rather than code directly. Examples:
- "강한 상위 추세" — what exactly is "강한"?
- "급락 후 기술적 반등" — how many bars? how much drop?
- "핵심 지지 존에 도달" — tolerance? exact touch vs zone entry?

### 2. Allowed strategy matrix gaps
The matrix in section 10 maps (HTF, H1, M30) → allowed strategies. Check:
- Are there (HTF, H1, M30) combinations not covered?
- HTF_BULLISH + H1_BULLISH + M30_BEARISH → what happens?
- HTF_BULLISH + H1_BULLISH + M30_NEUTRAL → what happens?
- HTF_BEARISH + H1_BULLISH + any → what happens?

### 3. Entry sequence completeness
For each of the 3 strategies (TREND_LONG, PULLBACK_LONG, REBOUND_SHORT):
- Are all entry conditions fully quantified?
- Is the order of condition evaluation specified?
- What happens if conditions are met on different bars (e.g., zone touch on bar N, trigger on bar N+5)?
- Is there a timeout for waiting?

### 4. Target price selection
- "진입가보다 위에 있는 값만 유효" — what if ALL candidates are below entry? Entry blocked?
- Fib extensions (2.5/3.618/4.0) — extension from what base? (swing low to swing high? which ones?)
- What if tp1 and tp2 are the same level?

### 5. Multi-symbol gaps
- The spec now covers ETHUSDT + BTCUSDT. Are the indicator parameters (Ichimoku 9/26/52, ATR 14, etc.) appropriate for both?
- BTC has different volatility characteristics. Should zone_width or ATR multipliers differ?
- Volume profile windows (96/120/90 bars) — same for both symbols?

### 6. Risk management completeness
- "총자산의 0.35%" — is this account equity or margin balance?
- Position sizing formula is missing — how to convert risk% to contract size given leverage?
- "심볼당 최대 위험 노출 0.5%" + "합산 1.0%" — if both at 0.5%, sum is 1.0%. Is this correct edge case?

Output: For each finding, state Severity (critical/medium/low), Section reference, Issue description, Suggested fix.
