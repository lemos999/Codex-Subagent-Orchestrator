# CTS — Development Plan

## 테스트 계획 (3단계 비교)

### Phase T1: 현재 상태 baseline 측정
1. 일반 작업 세션 수행 (파일 수정, git 작업, 테스트 실행)
2. `/cost` 명령으로 세션 토큰 사용량 기록
3. bash 명령별 출력 크기 수집 (git status, git log, vitest 등)
4. **측정 기준**: 총 input 토큰, bash 출력 토큰, 세션 시간

### Phase T2: RTK 설치 + 측정
1. `cargo install --git https://github.com/rtk-ai/rtk` 또는 pre-built binary
2. `rtk init -g` → PreToolUse hook 설치
3. 동일 작업 세션 수행
4. `rtk gain` 으로 RTK 절감 통계 수집
5. `/cost` 로 총 세션 토큰 비교
6. **측정 후 제거**: `rtk init -g --uninstall && cargo uninstall rtk`

### Phase T3: CTS 설치 + 측정
1. `cd packages/token-saver && npm run build`
2. settings.local.json에 hook 추가
3. 동일 작업 세션 수행
4. CTS 절감 통계 확인
5. `/cost` 로 총 세션 토큰 비교

### 비교 표 (채울 것)

| 지표 | 현재 | RTK | CTS |
|------|------|-----|-----|
| 세션 총 input 토큰 | | | |
| bash 출력 토큰 | | | |
| git status 크기 | | | |
| git log 크기 | | | |
| vitest 크기 | | | |
| 검증(tsc) 출력 보존 | O | ? | O |
| 커밋 스타일 보존 | O | X | O |
| 빌트인 도구 커버 | X | X | O(힌트) |
| 설치 복잡도 | 없음 | 중간 | 낮음 |

---

## 구현 계획 (4 Sprint)

### Sprint 1: 코어 파이프라인 (C5→C1→C2→S3)
**목표**: hook으로 bash 명령을 가로채서 라우팅하는 기본 골격

파일:
- `src/index.ts` — CLI 진입점 (`cts exec <cmd>`)
- `src/router.ts` — 첫 토큰 매칭
- `src/registry.ts` — 압축기 Map
- `src/exempt.ts` — 면제 리스트
- `hook/pre-tool-use.js` — PreToolUse hook
- `package.json`, `tsconfig.json`

검증:
- `npx tsc --noEmit` PASS
- `cts exec "echo hello"` → "hello" (passthrough)
- `cts exec "tsc --noEmit"` → 원본 통과 (면제)
- PreToolUse hook 연결 → git status가 CTS를 통과하는지 확인

### Sprint 2: Git + Test 압축기 (C3, C4)
**목표**: 핵심 절감 달성

파일:
- `src/compressors/git.ts` — 서브커맨드별 압축
- `src/compressors/test.ts` — 요약 + 실패 상세
- `src/compressors/generic.ts` — 줄 수 제한, 그룹화

검증:
- `cts exec "git status"` → short format 출력
- `cts exec "git log -10"` → 최근 3개 full + 나머지 oneline
- `cts exec "npx vitest run"` → "135 passed, 2 failed" + 실패 상세
- 기존 nDCG eval 통과 (WKI 무영향 확인)

### Sprint 3: Tee + Stats + Builtin (S2, S4, S6)
**목표**: 안전장치 + 통계 + 빌트인 힌트

파일:
- `src/tee.ts` — 원본 보존
- `src/stats.ts` — SQLite 통계 (RTK의 history.db 참조)
- `hook/post-tool-use.js` — Read/Grep additionalContext

검증:
- tee 파일 생성 확인
- `cts stats` → 세션별 절감 통계 출력
- PostToolUse hook → Read 500줄 초과 시 힌트 추가

### Sprint 4: 비교 테스트
**목표**: 현재 vs RTK vs CTS 실측 비교

1. Phase T1 실행 (현재 baseline)
2. Phase T2 실행 (RTK)
3. Phase T3 실행 (CTS)
4. 비교 표 작성 + 결론

---

## 예상 일정

| Sprint | 예상 규모 | 파일 수 |
|--------|---------|---------|
| Sprint 1 | 6파일, 코어 골격 | ~300 LOC |
| Sprint 2 | 3파일, 압축기 | ~400 LOC |
| Sprint 3 | 3파일, 부가 기능 | ~200 LOC |
| Sprint 4 | 테스트 실행 | 코드 없음 |
| **총** | **~900 LOC** | |
