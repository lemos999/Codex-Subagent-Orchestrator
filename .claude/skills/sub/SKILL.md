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

Delegation is not trust — it is a **verifiable contract**. Both the orchestrator and every worker MUST follow this discipline.

### Pre-Work: Clean Before You Build

- When a worker must refactor a file >300 LOC, **remove dead code in a separate commit first**. Do not build on rubble.
- No single worker touches more than 5 files. When exceeded, the orchestrator **splits workers** — this is the essence of swarming.

### Quality: Good Enough Is Not Enough

- Workers write code that **passes senior review**, not code that merely runs. Actively fix architectural flaws, duplicated state, and inconsistent patterns.
- **Workers MUST run `tsc --noEmit` + `eslint` before declaring completion** and fix all errors. If no type-checker is configured, state that fact explicitly. Completion without verification is a false report.

### Context: Do Not Trust Your Memory

- Worker context is finite. **Re-read the target file before every edit** — even if you read it before.
- Files >500 LOC: **read in chunks with offset/limit**. Never assume a single read captured the entire file.
- If search results look suspiciously sparse, **re-run with narrower scope**. Truncation happens silently.

### Edit Safety: Did the Fix Actually Land?

- Edit tool fails silently. **Re-read the file after editing to confirm the change applied**. Verification read every 3 edits.
- When renaming, a single grep is never enough: direct calls, type references, string literals, dynamic imports, re-exports, tests/mocks — **search each of the 6 patterns separately**.

### Breakthrough Protocol: When a Worker Is Stuck

The most dangerous moment in orchestration is when a worker reports "can't be done." Accepting that report at face value halts the entire run.

- **Repetition detection**: If a worker has tried 3+ times in the same dimension (tweaking params, not structure), the orchestrator intervenes. Change the structure — not the parameters.
- **Premise inversion**: When a worker reports failure, the orchestrator asks: "What premises were you operating under?" List 3 premises and try the opposite of each. The premise itself may be the constraint.
- **Failure is data**: No worker result ends at "FAIL." Every failure MUST be annotated with **"This tells us:"** — the search space just narrowed.
- **"Impossible" is a forbidden word**: Neither workers nor the orchestrator may use "impossible" or "unrealistic" as final conclusions. Replace with **"not yet solved with this approach"** and propose the next dimension.
- **No binary thinking**: "Do it or don't" is a false dichotomy. Partial execution at reduced confidence beats zero execution waiting for perfect conditions.
