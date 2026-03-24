# /submix Run Summary: WKI Pipeline Analysis

## Results

| Agent | Engine | Status | Notes |
|-------|--------|--------|-------|
| search-analyzer | Claude Opus | pending | 에이전트 실행 중 (결과 대기) |
| fts-specialist | Gemini Pro | **failed** | 분석 대신 코드를 수정함 (YOLO 모드). 테스트 실패, regression 발생. 모든 변경 롤백 |
| architecture-critic | Codex GPT | **failed** | "Argument list too long" — 전체 소스 코드를 CLI 인수로 전달하여 셸 제한 초과 |

## Lessons Learned
- Gemini `--yolo` 모드는 읽기 전용 분석에 부적합 — 코드를 수정해버림
- Codex에 대용량 프롬프트 전달 시 파일 stdin pipe 사용 필요 (`codex exec` 인수 제한)
- 0.742 baseline이 Gemini의 변경으로 0.689까지 하락 → 완전 복원 완료
