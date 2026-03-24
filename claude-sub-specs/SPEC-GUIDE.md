# Claude Sub-Specs Guide

Claude 출처의 개선된 런처 spec 템플릿 모음.

## 파일 구조

```
claude-sub-specs/
├── SPEC-GUIDE.md                              ← 이 문서
├── minimal-write.claude.json                  ← Pattern A: 최소 검증
├── implementer-reviewer.claude.json           ← Pattern B: 구현 + 리뷰 (기본)
├── parallel-implementers-reviewer.claude.json ← Pattern C: 병렬 구현 + 리뷰
├── plan-implement-review.claude.json          ← Pattern D: 설계 → 구현 → 리뷰 (신규)
├── full-loop.claude.json                      ← Pattern E: 구현 → 리뷰 → 수정 → 재리뷰 (신규)
├── workflow-issue.claude.json                 ← 이슈 트래커 연동
└── queue-local-json.claude.json               ← 로컬 큐 러너
```

## 출력 경로 규칙

| 경로 | 용도 |
|---|---|
| `claude-sub-runs/` | 실행 로그, 매니페스트, 프롬프트 |
| `claude-sub-records/` | 아카이브 (per-run 증거 사본) |

기존 Codex 출력(`subagent-runs/`, `subagent-records/`)과 분리되어 출처 구분 가능.

## 기존 대비 개선 요약

### 1) 품질 (Quality)

| 개선 | 기존 | 개선 후 |
|---|---|---|
| 모델 차등 배정 | 전부 동일 모델 | 역할별 최적 모델 |
| `success_criteria` | 미사용 | 명시적 합격 기준 |
| `coordination_notes` | 미사용 | 병렬 워커 충돌 방지 |
| 구조화된 `return_contract` | 자유 형식 | 머신 파싱 가능 형식 |
| Pattern D (Plan) | 없음 | 복잡 작업용 설계 단계 추가 |
| Pattern E (Full Loop) | 없음 | 사전 계획된 수정-재검증 사이클 |

### 2) 최적화 (Optimization)

| 개선 | 기존 | 개선 후 |
|---|---|---|
| `reasoning_effort` 차등 | 전부 `low` | 역할별: planner=high, impl=medium, review=low |
| `live_usage` | 미사용 | 팀 템플릿에 기본 활성화 |
| `timeout_seconds` | 미설정 | 패턴별 적정 타임아웃 |
| `shared_directive_mode` | `reference` | `compact` (인라인 축약 = 파일 읽기 1회 절감) |
| 아카이브 | 미사용 | `write_run_archive: true` |

### 3) 토큰 절약 (Token Saving)

| 개선 | 기존 | 개선 후 |
|---|---|---|
| `max_response_lines` | 3-4 (획일) | 역할별: probe=3, impl=6-12, review=8-10, planner=30 |
| Reviewer 모델 | implementer와 동일 | 더 가벼운 모델 가능 |
| `stop_when` | 일부만 | 전체 에이전트에 명시 (scope creep 방지) |
| Fixer 컨텍스트 | 전체 태스크 반복 | 리뷰어 findings만 전달 |
| Re-reviewer 범위 | 전체 리뷰 반복 | 수정된 findings + 회귀만 확인 |

## 감시 감독관 (Watchdog) 지원

Pattern B/C/D/E 템플릿에 `watchdog` 필드가 추가되었습니다.

```json
"watchdog": {
  "enabled": false,
  "stages_to_watch": ["implementer"],
  "model": "gpt-5.4",
  "reasoning_effort": "medium",
  "verdict_format": "PASS | SHORTFALL",
  "on_shortfall": "3-choice: Accept (fix) | Reject (log + proceed) | Escalate (ask user)",
  "max_cycles_per_stage": 1
}
```

| 필드 | 설명 |
|---|---|
| `enabled` | `true`로 설정 시 watchdog 활성화 (기본: `false`) |
| `stages_to_watch` | 감시할 에이전트 이름 목록 |
| `parallel_watchdogs` | Pattern C 전용 — 병렬 watchdog 실행 여부 |
| `final_watchdog_after` | Pattern E 전용 — 최종 watchdog 시점 (`"acceptance"`) |
| `skip_during_fix_loop` | Pattern E 전용 — fix-review 루프 중 watchdog 생략 |
| `verdict_format` | `PASS` (목표 정렬) / `SHORTFALL` (미달) |
| `on_shortfall` | 3-선택지 프로토콜: Accept / Reject / Escalate |
| `max_cycles_per_stage` | 스테이지당 최대 watchdog-fix 사이클 (기본: 1) |

Pattern A (Solo)는 watchdog 대상이 아닙니다 — 단일 작업에는 목표 이탈 위험이 낮습니다.

## 모델 배정 전략

```
역할               reasoning_effort    비고
─────────────────  ─────────────────   ─────────────
planner            high                설계 판단 필요
implementer        medium              균형 (쓰기 + 검증)
reviewer (초기)    low                 빠른 게이트
fixer              medium              정확한 수정 필요
re-reviewer        medium              수정 검증 + 회귀 확인
watchdog           medium              목표 정렬 판단
probe              low                 연기 테스트
```

## 사용법

```powershell
# 1) 템플릿을 복사하고 실제 값으로 수정
Copy-Item ".\claude-sub-specs\implementer-reviewer.claude.json" ".\my-task.json"

# 2) 런처로 실행
& ".\skills\codex-subagent-orchestrator\scripts\start-codex-subagent-team.ps1" `
  -SpecPath ".\my-task.json" -AsJson
```

## _meta 필드

각 템플릿에 `_meta` 객체가 포함되어 있습니다:

```json
{
  "_meta": {
    "origin": "claude",
    "pattern": "B-implement-review",
    "version": "2.0",
    "purpose": "...",
    "model_strategy": {
      "quality": "...",
      "optimization": "...",
      "token_saving": "..."
    },
    "improvements": [...]
  }
}
```

런처는 `_meta`를 무시합니다. 사람이 읽기 위한 메타데이터입니다.
