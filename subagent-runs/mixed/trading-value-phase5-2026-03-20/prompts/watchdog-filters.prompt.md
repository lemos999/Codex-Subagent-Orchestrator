## Watchdog: filters.py
**Goal**: 매매 기록 패턴 분석 + 진입 금지 필터 생성 — 시간대/요일/전략/레짐/연속손실별 승률 분석, 유의성 판단 (sample>=20, win_rate<35%), 필터 적용 함수
**Criteria**: 1) classify_session 시간대 정확? 2) analyze_trades가 모든 조건 그룹을 커버? 3) generate_filters 임계값이 합리적 (소표본 방지)? 4) check_conditional_filters가 실시간 적용 가능한 구조? 5) 리포트 포맷이 읽기 쉬운가?
**Inspect**: Projects/Trading Value/src/trading_value/core/filters.py
**Return**: PASS or SHORTFALL. Do NOT edit.