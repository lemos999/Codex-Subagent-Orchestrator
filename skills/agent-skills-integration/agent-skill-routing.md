# Agent Skills Routing

This workspace vendors the full upstream `addyosmani/agent-skills` repository under `vendor/agent-skills/`.

Use the vendor pack as an execution-discipline layer, not as a replacement for local orchestration.

Precedence order:

1. `AGENTS.md`
2. local parent or `/sub` orchestration rules
3. this routing file
4. vendored upstream skills, agents, references, and command files

If an upstream skill conflicts with local approval, writable-scope, parent-landing, or evidence rules, the local workspace rules win.

## Shared Turn Discipline

At the start of every turn, reread `AGENTS.md` before relying on remembered workspace state, applying local routing, or selecting vendored skills. Treat the fresh `AGENTS.md` read as mandatory on every follow-up turn, not just at session start.

Whenever this workflow needs the current time or writes a timestamp, use the user's timezone from the active session context as the authoritative reference. Apply that rule to plan files, scoreboards, score-history entries, status records, and any other durable or transient time handling. Do not fall back to agent-local, host-local, or system-default time when the user's timezone is available.

## Shared Mandatory Plan-First Contract

For this shared gate specifically, this routing file is the canonical local policy source. Parent-session and `/sub` skills should inherit and operationalize this gate, not replace it with a conflicting parallel authority.

For every new coding request, or any later coding request that is not already covered by the active approved plan record, require this order with no exceptions:

1. give a short natural-language understanding report
2. ask for explicit user approval to proceed
3. apply `skills/plan-mode-default/SKILL.md` and complete the planning contract from `skills/plan-mode-default/references/coding-plan-prompt-en.md`
4. write or update the approved full plan as a versioned Markdown record under `plan/`
5. only then begin implementation, fix work, or launch writable coding workers

This applies to new features, bug fixes, refactors, direct edit requests, "do it now" requests, urgent requests, tiny fixes, repair steps, and follow-up change requests whenever they are not already covered by the active approved plan record. In this workspace, treat every such coding request as an explicit request for the plan-first flow before implementation begins.

Do not treat blanket authority, urgency, "proceed immediately", or small scope as a waiver of this gate. No coding subtask, tiny follow-up edit, repair step, or seemingly trivial implementation action may proceed unless it is already covered by the active approved plan record or has been re-planned and approved. If a later tiny follow-up edit, repair step, or similar coding action is already explicitly covered by the active approved plan record and does not materially change the approved direction, continue under that plan by updating the active plan file instead of reopening a fresh approval gate.

The active plan file under `plan/` is a living delivery record, not a one-time dump. Use a time-sortable filename, clearly mark the plan type, version, status, and current progress, and keep that same document updated after every planning-turn change, every writable task step, and every status-changing verification, review, repair, or acceptance step so it always shows what is complete, incomplete, in progress, blocked, superseded, or next.

For any coding request, treat the local `plan` phase as mandatory before `implement`, `fix`, `/sub` implementer routing, or any writable execution. Do not let urgency, tiny scope, or direct implementation language bypass the local plan-first approval gate.

## Shared Score Tracking Contract

For every coding task that is tracked through the local planning workflow, keep a `Scoreboard` section in the active plan file under `plan/`.

Use that scoreboard as the authoritative local record for the current satisfaction score, score history, and score-maintenance actions. Always try to earn and maintain the highest possible user score while still staying inside the user's instructions, the local workflow rules, and normal correctness, safety, and rollback constraints.

The scoreboard should record at least:

- current score on a `0-100` scale
- score source: `user` or `provisional`
- last updated time
- score rationale
- what improved
- what remains unsatisfactory
- what should happen next to raise or maintain the score
- a chronological score-history log that preserves prior score states instead of overwriting them

All recorded times in the active plan file, its header fields, the `Scoreboard`, and score-history entries must use the user's timezone from the current session context.

If the user explicitly provides a score, record that score as authoritative. If the user does not provide a score yet, do not pause or wait for feedback. Continue the work and maintain a conservative provisional working score based on the current result quality and the available satisfaction signals, but do not set that provisional score above `50`. Do not use a fixed hardcoded fallback number for that provisional score.

Treat an unchanged score as the current overall result rating staying the same, not as zero new points being awarded. Update the scoreboard whenever explicit user feedback arrives or whenever planning, implementation, verification, review, repair, or acceptance materially changes the likely satisfaction state. Append a new history entry whenever the score value, score source, or score rationale materially changes, including when an explicit user score replaces a provisional score with the same numeric value.

## Shared Default Anti-Overengineering Overlay

For coding work in this workspace, apply `skills/karpathy-guidelines/SKILL.md` as the default local behavioral overlay.

Use it to prefer the smallest complete design, explicit assumptions, surgical edits, and goal-driven verification without weakening:

- `AGENTS.md`
- the shared plan-first contract above
- the shared score-tracking contract above
- explicit user instructions
- phase-local or worker-local writable-scope and acceptance rules

## Vendored Source

- repository: `https://github.com/addyosmani/agent-skills`
- vendored root: `vendor/agent-skills/`
- upstream slash-command references:
  - `vendor/agent-skills/.claude/commands/spec.md`
  - `vendor/agent-skills/.claude/commands/plan.md`
  - `vendor/agent-skills/.claude/commands/build.md`
  - `vendor/agent-skills/.claude/commands/test.md`
  - `vendor/agent-skills/.claude/commands/review.md`
  - `vendor/agent-skills/.claude/commands/code-simplify.md`
  - `vendor/agent-skills/.claude/commands/ship.md`

## Parent-Session Phase Routing

### `scan`

Default:

- `skills/karpathy-guidelines/SKILL.md`
- `vendor/agent-skills/skills/using-agent-skills/SKILL.md`
- `vendor/agent-skills/skills/context-engineering/SKILL.md`

When the request is vague or still forming:

- `vendor/agent-skills/skills/idea-refine/SKILL.md`
- `vendor/agent-skills/skills/spec-driven-development/SKILL.md`

### `plan`

Default:

- `skills/karpathy-guidelines/SKILL.md`
- `skills/plan-mode-default/SKILL.md`
- `skills/plan-mode-default/references/coding-plan-prompt-en.md` when present; treat it as the local default planning contract unless the user explicitly overrides its format while preserving the understanding-report and explicit-approval gate
- `vendor/agent-skills/skills/planning-and-task-breakdown/SKILL.md`

Add when the plan needs explicit slice ordering or incremental rollout discipline:

- `vendor/agent-skills/skills/incremental-implementation/SKILL.md`

When interface, schema, or contract design matters:

- `vendor/agent-skills/skills/api-and-interface-design/SKILL.md`

When launch, migration, pipeline, or documentation work is part of the plan:

- `vendor/agent-skills/skills/ci-cd-and-automation/SKILL.md`
- `vendor/agent-skills/skills/deprecation-and-migration/SKILL.md`
- `vendor/agent-skills/skills/documentation-and-adrs/SKILL.md`
- `vendor/agent-skills/skills/shipping-and-launch/SKILL.md`

### `implement`

Use this phase only after the local plan-first approval gate has been satisfied.

Default:

- `skills/karpathy-guidelines/SKILL.md`
- `vendor/agent-skills/skills/incremental-implementation/SKILL.md`
- `vendor/agent-skills/skills/test-driven-development/SKILL.md`

Task-shaped add-ons:

- browser or app UI work:
  - `vendor/agent-skills/skills/frontend-ui-engineering/SKILL.md`
- boundary or API work:
  - `vendor/agent-skills/skills/api-and-interface-design/SKILL.md`
- workflow, git, or release-surface changes:
  - `vendor/agent-skills/skills/git-workflow-and-versioning/SKILL.md`
  - `vendor/agent-skills/skills/ci-cd-and-automation/SKILL.md`
- migration-heavy work:
  - `vendor/agent-skills/skills/deprecation-and-migration/SKILL.md`

### `verify`

Default:

- `skills/karpathy-guidelines/SKILL.md`
- `vendor/agent-skills/skills/debugging-and-error-recovery/SKILL.md`
- `vendor/agent-skills/skills/test-driven-development/SKILL.md`

Task-shaped add-ons:

- browser runtime validation:
  - `vendor/agent-skills/skills/browser-testing-with-devtools/SKILL.md`
- security-sensitive surfaces:
  - `vendor/agent-skills/skills/security-and-hardening/SKILL.md`
- performance-sensitive surfaces:
  - `vendor/agent-skills/skills/performance-optimization/SKILL.md`

### `review`

Default:

- `skills/karpathy-guidelines/SKILL.md`
- `vendor/agent-skills/skills/code-review-and-quality/SKILL.md`

Add as needed:

- `vendor/agent-skills/skills/code-simplification/SKILL.md`
- `vendor/agent-skills/skills/security-and-hardening/SKILL.md`
- `vendor/agent-skills/skills/performance-optimization/SKILL.md`
- `vendor/agent-skills/skills/documentation-and-adrs/SKILL.md`
- `vendor/agent-skills/skills/git-workflow-and-versioning/SKILL.md`

### `fix`, `re-verify`, `re-review`

Default:

- `skills/karpathy-guidelines/SKILL.md`
- `vendor/agent-skills/skills/debugging-and-error-recovery/SKILL.md`
- `vendor/agent-skills/skills/test-driven-development/SKILL.md`
- `vendor/agent-skills/skills/code-review-and-quality/SKILL.md`

Add as needed:

- `vendor/agent-skills/skills/security-and-hardening/SKILL.md`
- `vendor/agent-skills/skills/performance-optimization/SKILL.md`
- `vendor/agent-skills/skills/code-simplification/SKILL.md`

## Release-Only Overlay

This is not part of the default parent phase checklist.

Use it only when the task genuinely includes release work or an explicit shipping step:

- `vendor/agent-skills/skills/git-workflow-and-versioning/SKILL.md`
- `vendor/agent-skills/skills/ci-cd-and-automation/SKILL.md`
- `vendor/agent-skills/skills/documentation-and-adrs/SKILL.md`
- `vendor/agent-skills/skills/shipping-and-launch/SKILL.md`
- `vendor/agent-skills/skills/deprecation-and-migration/SKILL.md`

## `/sub` Worker Routing

### Planner / Planner-Like

For coding planning workers, default:

- `skills/karpathy-guidelines/SKILL.md`
- `skills/plan-mode-default/SKILL.md`
- `skills/plan-mode-default/references/coding-plan-prompt-en.md` when present; treat it as the local default planning contract unless the user explicitly overrides its format while preserving the understanding-report and explicit-approval gate
- `vendor/agent-skills/skills/using-agent-skills/SKILL.md`
- `vendor/agent-skills/skills/planning-and-task-breakdown/SKILL.md`

For non-coding planning or analysis workers, default:

- `vendor/agent-skills/skills/using-agent-skills/SKILL.md`
- `vendor/agent-skills/skills/planning-and-task-breakdown/SKILL.md`

Add when relevant:

- `vendor/agent-skills/skills/context-engineering/SKILL.md`
- `vendor/agent-skills/skills/spec-driven-development/SKILL.md`
- `vendor/agent-skills/skills/api-and-interface-design/SKILL.md`
- `vendor/agent-skills/skills/deprecation-and-migration/SKILL.md`
- `vendor/agent-skills/skills/documentation-and-adrs/SKILL.md`
- `vendor/agent-skills/skills/shipping-and-launch/SKILL.md`

### Implementer

Use this worker role only after the local plan-first approval gate has been satisfied.

Default:

- `skills/karpathy-guidelines/SKILL.md`
- `vendor/agent-skills/skills/incremental-implementation/SKILL.md`
- `vendor/agent-skills/skills/test-driven-development/SKILL.md`

Task-shaped add-ons:

- `vendor/agent-skills/skills/frontend-ui-engineering/SKILL.md`
- `vendor/agent-skills/skills/api-and-interface-design/SKILL.md`
- `vendor/agent-skills/skills/ci-cd-and-automation/SKILL.md`
- `vendor/agent-skills/skills/git-workflow-and-versioning/SKILL.md`
- `vendor/agent-skills/skills/deprecation-and-migration/SKILL.md`

### Fixer

Default:

- `skills/karpathy-guidelines/SKILL.md`
- `vendor/agent-skills/skills/debugging-and-error-recovery/SKILL.md`
- `vendor/agent-skills/skills/test-driven-development/SKILL.md`

Add when relevant:

- `vendor/agent-skills/skills/incremental-implementation/SKILL.md`
- `vendor/agent-skills/skills/security-and-hardening/SKILL.md`
- `vendor/agent-skills/skills/performance-optimization/SKILL.md`
- `vendor/agent-skills/skills/code-simplification/SKILL.md`

### Reviewer

For coding review workers, default:

- `skills/karpathy-guidelines/SKILL.md`
- `vendor/agent-skills/skills/code-review-and-quality/SKILL.md`

For non-coding review workers, default:

- `vendor/agent-skills/skills/code-review-and-quality/SKILL.md`

Add when relevant:

- `vendor/agent-skills/skills/security-and-hardening/SKILL.md`
- `vendor/agent-skills/skills/performance-optimization/SKILL.md`
- `vendor/agent-skills/skills/code-simplification/SKILL.md`
- `vendor/agent-skills/skills/documentation-and-adrs/SKILL.md`
- `vendor/agent-skills/skills/git-workflow-and-versioning/SKILL.md`

### Validator

For coding validation workers, default:

- `skills/karpathy-guidelines/SKILL.md`
- `vendor/agent-skills/skills/test-driven-development/SKILL.md`
- `vendor/agent-skills/skills/debugging-and-error-recovery/SKILL.md`

For non-coding validation workers, default:

- `vendor/agent-skills/skills/test-driven-development/SKILL.md`
- `vendor/agent-skills/skills/debugging-and-error-recovery/SKILL.md`

Add when relevant:

- `vendor/agent-skills/skills/browser-testing-with-devtools/SKILL.md`
- `vendor/agent-skills/skills/security-and-hardening/SKILL.md`
- `vendor/agent-skills/skills/performance-optimization/SKILL.md`
- `vendor/agent-skills/skills/shipping-and-launch/SKILL.md`

### Specialist Overlays

Use these when a worker needs a stronger review posture:

- `vendor/agent-skills/agents/code-reviewer.md`
- `vendor/agent-skills/agents/test-engineer.md`
- `vendor/agent-skills/agents/security-auditor.md`

## Reference Checklists

Pull these only when the active task needs them:

- testing:
  - `vendor/agent-skills/references/testing-patterns.md`
- security:
  - `vendor/agent-skills/references/security-checklist.md`
- performance:
  - `vendor/agent-skills/references/performance-checklist.md`
- accessibility:
  - `vendor/agent-skills/references/accessibility-checklist.md`

## Integration Rules

- do not inline all 20 skills into one prompt
- select only the minimum set that materially sharpens the current phase or worker
- when multiple imported skills overlap, prefer the phase-appropriate core skill and add specialized ones only when the task surface justifies them
- use imported anti-rationalization and verification sections as execution discipline, but keep local approval, parent-landing, evidence, and bounded-fix-loop rules in charge

## Selection Algorithm

Use this deterministic selection order so the vendor pack stays meaningfully integrated without turning into prompt bloat.

1. write the active judgment criteria first:
   - dominant technical surfaces
   - acceptance risks
   - verification burdens
   - review burdens
2. start with the role or phase default skill set from this file
3. add task-shaped implementation skills only when one of those criteria says the extra discipline is needed
4. add specialist overlays or checklists only when the acceptance risk genuinely requires that extra lens
5. do not attach launch, migration, CI, browser, security, performance, or documentation skills unless the task actually touches that surface
6. keep expanding only while each added imported skill changes behavior, validation, or acceptance in a way the parent can explain
7. if two imported skills say nearly the same thing, keep the one that matches the current phase or worker role more directly
8. stop when the next imported skill adds breadth but not meaningful signal

Quick defaults:

- parent `plan` phase: `skills/karpathy-guidelines/SKILL.md` + `skills/plan-mode-default/SKILL.md` + `skills/plan-mode-default/references/coding-plan-prompt-en.md` + `planning-and-task-breakdown`; add `incremental-implementation` only when slice ordering or rollout discipline matters
- planner-like `/sub` worker: `skills/karpathy-guidelines/SKILL.md` + `skills/plan-mode-default/SKILL.md` + `skills/plan-mode-default/references/coding-plan-prompt-en.md` + `using-agent-skills` + `planning-and-task-breakdown`; add `context-engineering` when repo context selection matters and `spec-driven-development` when the task boundary or contract is still forming
- implementer: `skills/karpathy-guidelines/SKILL.md` + `incremental-implementation` + `test-driven-development`; add exactly one surface skill for UI, API, CI, git, or migration when needed
- fixer: `skills/karpathy-guidelines/SKILL.md` + `debugging-and-error-recovery` + `test-driven-development`; add `incremental-implementation` only when the repair needs staged rewrite discipline, then add one specialist skill only when the finding is clearly security, performance, or simplification related
- reviewer: `skills/karpathy-guidelines/SKILL.md` + `code-review-and-quality`; add one specialist overlay or checklist only when the requested acceptance bar explicitly includes it
- validator: `skills/karpathy-guidelines/SKILL.md` + `test-driven-development` + `debugging-and-error-recovery`; add one runtime or specialist verification skill only when the task surface requires it
