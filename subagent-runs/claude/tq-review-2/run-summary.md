# /sub Review: tq-review-2

## Agents
- backend-reviewer (sonnet): timeout → manual fallback
- sim-reviewer (sonnet): timeout → manual fallback
- integration-check (haiku): timeout → manual fallback

All 3 agents timed out. Review conducted manually by orchestrator.

## Findings & Fixes

### CRITICAL — Fixed

| # | File | Issue | Fix |
|---|------|-------|-----|
| C1 | order.py | 공매도 PnL `(exit-entry)*qty`는 롱 기준. 숏은 반대 | `is_short` 플래그 추가, 숏은 `(entry-exit)*qty`로 계산 |
| C2 | portfolio.py | 공매도 시 qty=0→음수→즉시 삭제, 포지션 유지 불가 | sell() 완전 재구현 + `buy_to_cover()` 추가 |
| C3 | routes.py | 분봉 `pd.concat()` 매 캔들 = O(n²) | `iloc[:i+1]` 슬라이싱으로 O(1) |

### MEDIUM — Fixed

| # | File | Issue | Fix |
|---|------|-------|-----|
| M2 | backtest.html | 무한모드 중단 불가 | "중단" 버튼 추가, reader.cancel()로 SSE 스트림 종료 |

### MEDIUM — Accepted

| # | Issue | Reason |
|---|-------|--------|
| M1 | compact()가 tried-params 삭제 → 재시도 가능 | 저점수 재시도는 학습에 해 없음 |
| M3 | 30m/1h/4h가 minute_ohlcv에서 로드 | 별도 테이블이지만 save_minute()로 저장됨 — 확인 필요 |
