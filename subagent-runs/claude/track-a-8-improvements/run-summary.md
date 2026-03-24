# Run Summary: track-a-8-improvements

## Items Implemented

1. **Zone merge limit**: 존 폭 > ATR*2.0 시 가장 가까운 좁은 존만 사용
2. **InvalidationInput 연결**: _process_bar Step 4에서 구성, evaluate_setup_transition에 전달
3. **5m swing cache**: _swing_cache_5m 추가, M5 detect_swings 실행, stop/TP에 실제 스윙 사용
4. **Split entry 50/30/20**: market 50% + limit 30% + limit 20%
5. **Daily loss limit**: _daily_pnl 추적, -3R 이하 시 당일 차단
6. **M5 primary tick**: _detect_bar_closes에서 M5 반환 지원
7. **Fib extensions**: compute_fib_extensions() 함수 + TREND_LONG TP2에 사용
8. **Risk budget check**: 총 리스크 1.0% 초과 시 진입 차단

## Validation
- Import check: PASS
- compute_fib_extensions(100, 200) = [261.8, 300.0, 361.8]: PASS
- Backward compatibility (use_full_triggers=False): PASS

## Review
- Verdict: ACCEPTED
- Fix cycles: 0
