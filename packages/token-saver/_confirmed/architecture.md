# CTS — Architecture

## 실행 파이프라인 (6단계 — RTK 참조, 개량)

```
1. Intercept   Claude Code hook이 도구 호출 감지
     ↓
2. Route       첫 토큰으로 명령 타입 식별 (git/vitest/ls/...)
     ↓
3. Exempt?     면제 리스트 확인 (tsc/eslint → 원본 통과)
     ↓
4. Execute     실제 명령 실행 (child_process)
     ↓
5. Compress    명령 타입별 압축기가 출력 변환
     ↓
6. Return      압축 결과 반환 + 원본 tee 저장 + 통계 기록
```

## 파일 구조

```
packages/token-saver/
├── src/
│   ├── index.ts              # CLI 진입점 (node cts.js <cmd>)
│   ├── router.ts             # C1: 첫 토큰 매칭 → 압축기 선택
│   ├── registry.ts           # C2: 명령→압축기 Map
│   ├── compressors/
│   │   ├── git.ts            # C3: git status/log/diff/show/push
│   │   ├── test.ts           # C4: vitest/jest/pytest
│   │   └── generic.ts        # S1: ls/find/cat 등
│   ├── exempt.ts             # S3: 면제 리스트
│   ├── tee.ts                # S2: 원본 보존
│   ├── stats.ts              # S4: 절감 통계
│   └── config.ts             # S5: YAML 로드
├── hook/
│   ├── pre-tool-use.sh       # C5: PreToolUse hook 스크립트
│   └── post-tool-use.sh      # C5: PostToolUse hook 스크립트 (S6 포함)
├── cts.config.yaml           # 기본 설정
├── package.json
├── tsconfig.json
└── _confirmed/               # 설계 문서 (이 디렉토리)
```

## Hook 연결 (C5)

### PreToolUse hook (bash 명령 리라이트)

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Bash",
      "hooks": [{
        "type": "command",
        "command": "node packages/token-saver/dist/hook/pre-tool-use.js",
        "timeout": 10
      }]
    }]
  }
}
```

hook이 받는 stdin:
```json
{
  "hook_event_name": "PreToolUse",
  "tool_name": "Bash",
  "tool_input": { "command": "git status" }
}
```

hook이 반환:
```json
{
  "updatedInput": {
    "command": "node packages/token-saver/dist/index.js exec git status"
  }
}
```

### PostToolUse hook (빌트인 도구 힌트)

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Read",
      "hooks": [{
        "type": "command",
        "command": "node packages/token-saver/dist/hook/post-tool-use.js",
        "timeout": 5
      }]
    }]
  }
}
```

Read 결과가 500줄 초과 시 `additionalContext`로 요약 힌트 추가.

## 데이터 흐름 상세

### bash 명령 (PreToolUse → CTS exec)

```
Claude: "git status 실행해줘"
  → PreToolUse hook
    → stdin: { tool_input: { command: "git status" } }
    → pre-tool-use.js: 면제 확인 → 면제 아님 → 리라이트
    → stdout: { updatedInput: { command: "node .../cts exec git status" } }
  → Claude Code: "node .../cts exec git status" 실행
    → cts exec:
      1. child_process.execSync("git status")
      2. router.route("git") → GitCompressor
      3. GitCompressor.compress(stdout) → compressed
      4. tee.save(stdout) → /tmp/cts-tee/...
      5. stats.record("git status", original, compressed)
      6. process.stdout.write(compressed)
  → Claude: 압축된 결과를 컨텍스트에 저장
```

### 빌트인 도구 (PostToolUse → 힌트)

```
Claude: Read("src/big-file.ts", { limit: 2000 })
  → Claude Code: 파일 읽기 실행 → 결과 2000줄
  → PostToolUse hook
    → stdin: { tool_name: "Read", tool_output: "..." }
    → post-tool-use.js: 줄 수 확인 → 500줄 초과
    → stdout: { additionalContext: "⚡ 2000줄 읽음. 필요한 부분만 offset/limit으로 재읽기 권장." }
  → Claude: 결과 + 힌트를 함께 받음
```

## 오버헤드 예산

| 단계 | 예산 |
|------|------|
| hook 스크립트 시작 | <3ms (Node.js 이미 로드 상태) |
| 면제 확인 | <1ms (배열 includes) |
| 명령 실행 | 원래 시간 (passthrough) |
| 압축 | <5ms (문자열 처리) |
| tee 저장 | <2ms (비동기 write) |
| **총 오버헤드** | **<10ms** (명령 실행 시간 제외) |

주의: Node.js 콜드스타트 (~100ms)는 PreToolUse hook에서 발생.
완화: hook command를 `node --require` 프리로드 또는 짧은 bash 스크립트로 래핑.
