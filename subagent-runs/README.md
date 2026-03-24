# subagent-runs 저장 경로 규칙

> 최종 갱신: 2026-03-13

## 디렉토리 구조

```
subagent-runs/
├── claude/          ← Claude Code 세션에서 생성된 모든 데이터
│   └── <run-name>/
├── codex/           ← Codex CLI에서 생성된 모든 데이터
│   └── <run-name>/
├── gemini/          ← Gemini CLI 세션에서 생성된 모든 데이터
│   └── <run-name>/
└── mixed/           ← 하나의 run에서 여러 엔진을 함께 사용한 데이터
    └── <run-name>/
```

## 규칙

| 엔진 | 저장 경로 | 예시 |
|------|----------|------|
| Claude Code (기본) | `subagent-runs/claude/<run-name>/` | `subagent-runs/claude/gdd-tetris-pipeline/` |
| Codex CLI | `subagent-runs/codex/<run-name>/` | `subagent-runs/codex/build-review-2026-03-13/` |
| Gemini CLI | `subagent-runs/gemini/<run-name>/` | `subagent-runs/gemini/run-rps-rules-v2/` |
| Mixed engines | `subagent-runs/mixed/<run-name>/` | `subagent-runs/mixed/test-3way-final/` |

- `<run-name>` 형식: `<task-slug>-<YYYY-MM-DD>` (충돌 시 `-2`, `-3` 추가)
- 엔진 구분 없이 `subagent-runs/` 직하에 임의의 새 런 폴더를 생성하지 않는다
- 단일 엔진 실행은 해당 엔진 폴더에 저장하고, 한 run에서 둘 이상의 엔진이 참여하면 `mixed/`에 저장한다
- 각 엔진 폴더의 세부 증적 형식은 해당 오케스트레이터 계약을 따른다
