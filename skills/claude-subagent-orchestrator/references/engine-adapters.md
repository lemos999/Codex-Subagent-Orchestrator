# Engine Adapters

`/sub` 오케스트레이터가 워커를 실행할 때 사용하는 엔진별 호출 사양을 정의한다.

## 엔진 식별자 체계

| Engine ID | CLI 명령어 | 인증 | 모델 파라미터 |
|---|---|---|---|
| `claude` | Claude Code Task tool (네이티브) 또는 `claude --print` (CLI) | 구독 | `haiku`, `sonnet`, `opus` |
| `codex` | `codex exec` | 구독 | `-m gpt-5.4` 등 |
| `gemini` | `npx @google/gemini-cli --prompt` | Google 계정 | `--model gemini-2.5-pro` 등 |

## 엔진-역할 호환성 매트릭스

| Engine | implementer | reviewer | fixer | planner | watchdog |
|---|---|---|---|---|---|
| `claude` (Task tool) | O | O | O | O | O |
| `claude` (CLI --print) | X (도구 사용 불가) | O (read-only) | X | O | O |
| `codex` (exec) | O | O | O | O | O |
| `gemini` (--yolo) | O | O | O | O | O |

**핵심 제약**: `claude` CLI `--print` 모드는 도구(Read, Write, Edit 등)에 접근할 수 없으므로, 파일 수정이 필요한 implementer 및 fixer 역할에 배정할 수 없다.

## CLI Adapter 추상 인터페이스

모든 CLI adapter의 입출력 계약:

- **입력**: `prompt`, `model`, `cwd`, `sandbox`, `options`
- **출력**: `exit_code`, `stdout`, `last_message`, `token_usage` (가능한 경우)

## 각 엔진별 CLI 호출 사양

### Claude (Task tool -- 기본)

- Claude Code 세션 내에서 Agent tool로 직접 호출
- `subagent_type`: `sub-implementer`, `sub-reviewer`, `sub-fixer`
- `model`: `haiku`, `sonnet`, `opus`
- 도구 접근: 전체 (Read, Write, Edit, Bash, Glob, Grep)

### Claude (CLI --print -- 외부 호출 시)

- 명령: `claude --print [--model <model>] "<prompt>"`
- stdout 전체가 응답 텍스트
- 도구 접근 불가 -- 분석/리뷰 전용
- exit code 0 = 성공
- token usage: CLI에서 제공하지 않으므로 `"unavailable"`

### Codex (exec)

- 명령: `cat prompt.md | codex exec --full-auto [-m <model>]`
- 프롬프트는 **반드시 stdin pipe로 전달** — 인자 방식(`"$(cat file)"`)은 긴 프롬프트에서 "Argument list too long" 에러
- **절대 금지**: stdin + 인자 동시 사용 (프롬프트 중복으로 에코만 반복)
- `--full-auto` 플래그로 비대화형 실행
- stdout에서 응답 추출
- token usage: stdout footer에서 파싱
- spawn.ts 구현: `{ cmd: 'codex', args: ['exec', '--full-auto'], stdin: prompt }`

### Gemini (CLI)

- 명령: `npx @google/gemini-cli --prompt "<prompt>" --yolo [--model <model>]`
- `--yolo`: 비대화형 자동 승인
- stdout에서 응답 추출
- token usage: CLI 출력에서 파싱 시도, 없으면 `"unavailable"`

## 엔진 선택 기본값

- Claude 오케스트레이터에서 `engine` 미지정 시: `"claude"` (Task tool)
- Codex 런처에서 `engine` 미지정 시: `"codex"` (기존 동작 호환)

## 에러 처리

| 조건 | 처리 방법 |
|---|---|
| CLI exit code != 0 | 재시도 1회, 실패 시 에러 마킹 |
| 인증 만료 | 에러 보고, 사용자 에스컬레이션 |
| 타임아웃 | 워커별 timeout 설정 존중 |
| 파싱 실패 | raw stdout 보존, 전체 텍스트 반환 |

## MCP 전환 경로

현재: `orchestrator -> Bash tool -> CLI 명령어`
향후: `orchestrator -> MCP tool -> MCP 서버 -> CLI 명령어`

engine 필드와 adapter 인터페이스가 동일하므로 호출 방법만 변경된다. 스펙 파일이나 증거 형식은 MCP 전환 시에도 동일하게 유지된다.
