# Agent Skills Routing

This workspace vendors the full upstream `addyosmani/agent-skills` repository under `vendor/agent-skills/`.

Use the vendor pack as an execution-discipline layer, not as a replacement for local orchestration.

Precedence order:

1. `AGENTS.md`
2. local parent or `/sub` orchestration rules
3. this routing file
4. vendored upstream skills, agents, references, and command files

If an upstream skill conflicts with local approval, writable-scope, parent-landing, or evidence rules, the local workspace rules win.

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

- `vendor/agent-skills/skills/using-agent-skills/SKILL.md`
- `vendor/agent-skills/skills/context-engineering/SKILL.md`

When the request is vague or still forming:

- `vendor/agent-skills/skills/idea-refine/SKILL.md`
- `vendor/agent-skills/skills/spec-driven-development/SKILL.md`

### `plan`

Default:

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

Default:

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

- `vendor/agent-skills/skills/code-review-and-quality/SKILL.md`

Add as needed:

- `vendor/agent-skills/skills/code-simplification/SKILL.md`
- `vendor/agent-skills/skills/security-and-hardening/SKILL.md`
- `vendor/agent-skills/skills/performance-optimization/SKILL.md`
- `vendor/agent-skills/skills/documentation-and-adrs/SKILL.md`
- `vendor/agent-skills/skills/git-workflow-and-versioning/SKILL.md`

### `fix`, `re-verify`, `re-review`

Default:

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

### Planner

Default:

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

Default:

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

- `vendor/agent-skills/skills/debugging-and-error-recovery/SKILL.md`
- `vendor/agent-skills/skills/test-driven-development/SKILL.md`

Add when relevant:

- `vendor/agent-skills/skills/incremental-implementation/SKILL.md`
- `vendor/agent-skills/skills/security-and-hardening/SKILL.md`
- `vendor/agent-skills/skills/performance-optimization/SKILL.md`
- `vendor/agent-skills/skills/code-simplification/SKILL.md`

### Reviewer

Default:

- `vendor/agent-skills/skills/code-review-and-quality/SKILL.md`

Add when relevant:

- `vendor/agent-skills/skills/security-and-hardening/SKILL.md`
- `vendor/agent-skills/skills/performance-optimization/SKILL.md`
- `vendor/agent-skills/skills/code-simplification/SKILL.md`
- `vendor/agent-skills/skills/documentation-and-adrs/SKILL.md`
- `vendor/agent-skills/skills/git-workflow-and-versioning/SKILL.md`

### Validator

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

- planner: `using-agent-skills` + `planning-and-task-breakdown`; add `context-engineering` when repo context selection matters and `spec-driven-development` when the task boundary or contract is still forming
- implementer: `incremental-implementation` + `test-driven-development`; add exactly one surface skill for UI, API, CI, git, or migration when needed
- fixer: `debugging-and-error-recovery` + `test-driven-development`; add `incremental-implementation` only when the repair needs staged rewrite discipline, then add one specialist skill only when the finding is clearly security, performance, or simplification related
- reviewer: `code-review-and-quality`; add one specialist overlay or checklist only when the requested acceptance bar explicitly includes it
- validator: `test-driven-development` + `debugging-and-error-recovery`; add one runtime or specialist verification skill only when the task surface requires it
