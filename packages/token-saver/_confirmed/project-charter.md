# Claude Token Saver (CTS) — Project Charter

## Primary Outcome
AI 코딩 세션의 토큰 효율을 극대화하여, 동일한 컨텍스트 윈도우로 더 많은 작업을 수행한다.

## Operating Loop
- **마이크로**: 명령 실행 → 출력 가로챔 → 압축 전략 적용 → 압축 결과 반환 (원본 tee 보존)
- **미들**: 세션 시작 → hook 활성화 → 자동 절감 → 세션 종료 시 통계
- **매크로**: 통계 축적 → 규칙 튜닝 → 커버리지 확장

## Baseline Expectations
1. 작업 결과물 품질 동일
2. 기존 인프라 무파괴 (WKI, 스킬, 페르소나, 런처)
3. 검증 명령 면제 (tsc, eslint)
4. 원본 복구 가능 (tee)
5. 설치/제거 간단 (hook ON/OFF)
6. 커밋/세션/맥락 이해 동일
7. Windows 안정 작동

## Differentiation
> "토큰 절감 도구인데, 빌트인 도구까지 커버하고 검증 명령은 면제하기 때문에, RTK보다 더 넓은 범위에서 더 안전하게 절감한다."

## Target Audience
- 대상: 이 워크스페이스의 모든 AI 엔진 (Claude, Codex, Gemini)
- 환경: Windows 11 + bash, Claude Code CLI, 1M 컨텍스트
- 복잡도: 낮음 (hook 설정 + YAML)
- 빈도: 매 세션 자동 (수십~수백 회/세션)
- 제약: <10ms 오버헤드, 5가지 조건 충족 필수
