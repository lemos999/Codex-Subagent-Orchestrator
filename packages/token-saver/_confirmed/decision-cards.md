# CTS — Decision Cards

## DC-1: C5 Hook Adapter — hook 연결 방식
**결정: PreToolUse 리라이트 + PostToolUse additionalContext**
- bash 명령: PreToolUse에서 `node cts.js <cmd>`로 리라이트
- 빌트인 도구: PostToolUse에서 additionalContext로 요약 힌트 추가
- Charter 대조: Differentiation "빌트인까지 커버" 부분 달성

## DC-2: C1 Command Router — 명령 매칭 방식
**결정: 첫 토큰 매칭**
- bash 명령의 첫 단어(git, npm, vitest)로 분기
- 서브커맨드는 압축기 내부에서 처리
- 매칭 실패 = 원본 그대로 통과 (fallback)
- 복합 명령(pipe/&&)은 v1 미지원, 원본 통과

## DC-3: C2 Compressor Registry — 등록 구조
**결정: 하드코딩 Map**
- `{ git: GitCompressor, vitest: TestCompressor, ... }`
- v1은 3개(git/test/generic)면 충분
- v2에서 플러그인화 검토

## DC-4: C3 Git Compressor — git 압축 전략
**결정: 최근 3개 full + 나머지 oneline**

| 서브커맨드 | 전략 | 압축 후 |
|-----------|------|---------|
| git status | short format + 파일 수 요약 | ~3,000 B |
| git log | 최근 3개 full format, 4번째부터 oneline | ~1,500 B |
| git diff | stat 요약 + 50줄 초과 시 truncate + tee | ~500 B |
| git show | stat + 제목+본문. diff truncate | ~800 B |
| git push/pull | "ok main" 1줄 요약 | ~20 B |

## DC-5: C4 Test Compressor — 테스트 압축 전략
**결정: 요약 + 실패 상세**
- 출력: `135 passed, 2 failed\n\nFAIL: test-name\n  Expected: X\n  Received: Y`
- 통과 수 보존 (RTK의 정보 손실 해결)
- 파싱 실패 시 원본 통과

## Exempt List (S3)
압축하지 않는 명령:
- `tsc` / `npx tsc` — 타입 체크 (CLAUDE.md 규칙4)
- `eslint` / `npx eslint` — 린팅 (CLAUDE.md 규칙4)
- `node workspace-knowledge-index` — WKI 명령
- `codex exec` — Codex 외부 엔진 호출
- `npx @google/gemini-cli` — Gemini 외부 엔진 호출

## Tee Store (S2)
- 모든 압축된 출력의 원본을 `/tmp/cts-tee/<timestamp>-<cmd>.txt`에 저장
- 최근 50개 유지, 오래된 것 자동 삭제
- AI가 "원본 보기"를 요청하면 tee 파일 경로 안내
