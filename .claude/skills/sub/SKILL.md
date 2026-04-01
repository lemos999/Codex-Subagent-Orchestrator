---
name: sub
description: Claude 단독 서브에이전트 오케스트레이션. `/sub <request>`로 Claude 워커(haiku/sonnet/opus)를 조합하여 감독 실행.
---

# /sub

Claude 단독 서브에이전트 오케스트레이션. 모든 워커가 Claude 엔진만 사용.

> **3개 AI 혼합 사용**: `/submix` 사용 (Claude + Codex/GPT + Gemini 자동 분담)

## Entry Protocol

1. Strip the `/sub` prefix
2. Route to `subagent-orchestrator` as the named supervisor subagent
3. The orchestrator reads `./skills/claude-subagent-orchestrator/SKILL.md` and handles everything

## Engine

**Claude 단독**. 모든 워커는 Claude Task tool로 실행.
- 모델: `haiku` (경량) / `sonnet` (기본) / `opus` (고급)
- Evidence: `subagent-runs/claude/<run-name>/`

## Invariants

- Parent stays supervisor — no direct deliverable edits
- Persistent deliverables require read-only review
- Material issues → bounded fixer → re-review (not full rerun)
- **Evidence는 필수이며 생략 불가** — 사용자 보고 전에 반드시 `subagent-runs/claude/<run-name>/`에 기록
- Watchdog hooks are optional goal-alignment auditors — on shortfall, orchestrator applies 3-choice protocol (Accept/Reject/Escalate)

## Evidence Reminder

모든 `/sub` 실행 후 **결과 보고 전에** evidence를 기록해야 한다:
1. `subagent-runs/claude/<run-name>/run-manifest.md`
2. `subagent-runs/claude/<run-name>/run-summary.md`
3. `subagent-runs/claude/<run-name>/prompts/*.prompt.md`
4. `subagent-runs/claude/<run-name>/results/*.result.md`

실패/중단 run도 기록한다. 상세 형식은 `evidence-format.md` 참조.

## Orchestrator & Worker Discipline

`/sub`는 위임의 기술이다. 위임은 신뢰가 아니라 **검증 가능한 계약**이다. 오케스트레이터와 모든 워커는 아래 규율을 따른다.

### 착수 전: 정리 먼저

- 워커가 300LOC 초과 파일을 리팩터해야 한다면, **dead code 제거를 별도 커밋**으로 먼저 수행한다. 잔해 위에 짓지 않는다.
- 하나의 워커가 5파일을 초과하여 수정하지 않는다. 초과 시 오케스트레이터가 **워커를 분할**한다 — 이것이 swarming의 본질이다.

### 품질: 적당히가 아니라 제대로

- 워커는 "돌아가는 코드"가 아니라 **시니어 리뷰를 통과할 코드**를 작성한다. 아키텍처 결함, 상태 중복, 패턴 불일치를 발견하면 적극 수정한다.
- **워커는 완료를 선언하기 전에 반드시 `tsc --noEmit` + `eslint`를 실행**하고 모든 에러를 수정한다. 타입체커 미설정 시 그 사실을 명시한다. 검증 없는 완료 보고는 거짓 보고다.

### 컨텍스트: 기억을 믿지 마라

- 워커 컨텍스트는 유한하다. **편집 전 반드시 대상 파일을 재읽기**한다 — 이전에 읽었더라도.
- 500LOC 초과 파일은 **offset/limit으로 분할 읽기**. 한 번에 전체를 봤다고 착각하지 않는다.
- 검색 결과가 의심스럽게 적으면 **범위를 좁혀 재실행**한다. Truncation은 침묵 속에 일어난다.

### 편집: 고친 게 진짜 고쳐졌는가

- Edit tool은 silent failure한다. **편집 후 파일을 다시 읽어 변경이 반영됐는지 확인**한다. 3회 편집마다 검증 읽기.
- 이름 변경 시 단일 grep으로 끝내지 않는다: 직접 호출, 타입 참조, 문자열 리터럴, 동적 import, re-export, 테스트/mock — **6가지 패턴을 각각 별도 검색**한다.
