# CTS — Component Map

## Core 컴포넌트 (구현 순서)

| # | 컴포넌트 | 역할 |
|---|---------|------|
| C5 | Hook Adapter | Claude Code PreToolUse/PostToolUse hook 연결 |
| C1 | Command Router | bash 명령 식별 → 적절한 압축기로 라우팅 |
| C2 | Compressor Registry | 명령 타입 → 압축기 매핑 (하드코딩 Map) |
| C3 | Git Compressor | git status/log/diff/show/push 압축 |
| C4 | Test Compressor | vitest/jest/pytest 요약 + 실패 상세 |

## Support 컴포넌트

| 컴포넌트 | 역할 |
|---------|------|
| S1 | Generic Compressor — ls/find/cat 등 범용 압축 |
| S2 | Tee Store — 원본 출력 임시 보존 |
| S3 | Exempt List — 압축 면제 명령 관리 |
| S4 | Stats Tracker — 절감 통계 기록 |
| S5 | Config Loader — YAML 규칙 파일 로드 |
| S6 | Builtin Adapter — Read/Grep 결과 additionalContext 힌트 |

## 의존성 맵

```
C5 (Hook Adapter)
 ├─→ C1 (Command Router)     [bash 명령 문자열]
 │    ├─→ S3 (Exempt List)   [면제 여부]
 │    ├─→ C2 (Registry)      [명령 타입]
 │    │    ├─→ C3 (Git)
 │    │    ├─→ C4 (Test)
 │    │    └─→ S1 (Generic)
 │    └─→ S2 (Tee Store)    [원본 보존]
 └─→ S6 (Builtin Adapter)   [Read/Grep 힌트]

S5 (Config) ─→ C2, S3
S4 (Stats)  ←─ C1
```

## 스코프: 린 (1인)
