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
