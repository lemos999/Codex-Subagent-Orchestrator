# Parent Session Workflow

## Purpose

This workflow keeps execution inside one Codex parent session while preserving the useful discipline of a multi-role delivery process.

It replaces worker sessions with explicit parent phases and moves long-lived context out of chat and onto disk.

## Core Model

Use one parent session and a small set of phase files:

- `task-brief.md`
- `active-context.md`
- `phase-checklist.md`
- `session-summary.md`
- one file per phase under `phases/`

The chat should stay focused on the current phase only. Shared facts, constraints, and next steps should live in the run directory instead of being repeated in every turn.

When the active phase needs stronger execution discipline, route into `skills/agent-skills-integration/agent-skill-routing.md` and open only the vendored upstream skills needed for that phase.

Use these file-authority rules consistently:

- `session-summary.md` is the sole durable checkpoint for accepted facts, current status, failures, and next step.
- the current phase file is the active instruction surface for the current step.
- `active-context.md` is a bootstrap snapshot for the run and is not the live authority once work begins.
- `phase-checklist.md` is the ordered phase index and a manual progress aid, not the authoritative current-state record.
- `task-brief.md` records the task boundary and should change only when the boundary changes materially.

If you rename these files locally, keep the same authority rules and use the renamed paths consistently everywhere in the run kit.

## Default Runtime Path

### 1. Scan

Goal:

- understand the task boundary
- inspect only the first files needed
- identify likely touch points
- capture the repo map for this task

Outputs:

- update `task-brief.md`
- note likely touch points in `session-summary.md`

### 2. Plan

Goal:

- pick the smallest safe design
- decide edit order
- decide validation commands
- choose the minimum imported execution-discipline skills needed for the later phases

Outputs:

- update `session-summary.md` with the chosen plan

### 3. Implement

Goal:

- make the bounded edit
- keep scope aligned with the plan
- avoid decorative refactors

Outputs:

- code changes
- a short delta summary in `session-summary.md`

### 4. Verify

Goal:

- run the narrowest useful checks first
- capture failures as short deltas, not raw full logs

Outputs:

- update `session-summary.md` with pass or fail, commands run, and failure snippets if any

### 5. Review

Goal:

- perform a read-only senior review of the changed files
- look for regressions, missing tests, scope drift, and rollback risk

Outputs:

- accept the result, or
- define or confirm an approved fix scope and return to `fix`

### 6. Fix Then Re-Review

Use only when `verify` or `review` opens an approved fix scope.

Goal:

- repair the specific issue
- avoid expanding scope
- rerun the narrowest checks that prove the repair
- run review again on the repaired final state

The cheapest safe recovery path is:

1. `fix`
2. `re-verify`
3. `re-review`

## State Transition Rules

These rules decide the next phase. Do not improvise around them.

### Scan

- move to `plan` when the task boundary, likely touch points, and acceptance criteria are understood well enough to design safely
- stay in `scan` while you are still narrowing the same task boundary
- ask the user and pause when the task boundary or acceptance criteria cannot be recovered safely from local context

### Plan

- move to `implement` when the design, edit order, writable scope, and validation plan are explicit
- return to `scan` when planning reveals that the task boundary, requested deliverables, or acceptance criteria were misunderstood
- stay in `plan` while refining the same design and validation strategy
- ask the user and pause when multiple safe plans still remain after applying the least-change, least-risk default

### Implement

- move to `verify` when the planned edit is complete for the current approved scope
- return to `plan` before further editing when new evidence causes a material plan change
- return to `scan` before further editing when new evidence shows the task boundary was misunderstood

### Verify

- move to `review` when the chosen checks pass
- stay in `verify` when the chosen validation strategy is still correct, but the current check execution was wrong, omitted, or too narrow, and no code change is needed
- move to `fix` when a failure is caused by code or configuration inside the current approved design and writable scope, you record an approved fix scope in `session-summary.md` that names that defect, and the repair does not cause a material plan change
- return to `plan` when the failure shows the design is wrong, or when proving the change now requires a different validation strategy, command set, proof surface, or acceptance claim than the current plan records
- return to `scan` when the failure shows the task boundary or acceptance criteria were misunderstood

### Review

- accept and stop when no material issue remains
- move to `fix` when the issue is material, can be captured by an approved fix scope that names that defect, stays inside the allowed file surface and rerun proof, and does not cause a material plan change
- return to `plan` when the issue is material and would exceed the approved fix scope or cause a material plan change
- return to `scan` when the issue shows the task boundary, requested deliverables, or acceptance criteria were wrong
- ask the user and pause when review still leaves multiple safe resolutions after applying the least-change, least-risk default and choosing one would invent user intent; otherwise follow the deterministic `fix`, `plan`, or `scan` route above

### Fix

- move to `re-verify` when the approved repair is complete
- return to `plan` before further editing when the repair would exceed the approved fix scope
- return to `scan` before further editing when the repair shows the task boundary, requested deliverables, or acceptance criteria were misunderstood

### Re-Verify

- move to `re-review` when the chosen repair checks pass
- stay in `re-verify` when the chosen validation strategy is still correct, but the current check execution was wrong, omitted, or too narrow, and no code change is needed
- move to `fix` when the remaining failure is caused by code or configuration inside the current approved design and writable scope, you refresh the approved fix scope in `session-summary.md` to name that remaining defect, the remaining failure is not the same root cause that already survived this repair loop, and the repair still does not exceed the approved fix scope; this remains inside the current bounded repair loop and does not require a new user approval gate
- return to `plan` when the same root cause survives the just-completed bounded repair loop
- return to `plan` when the remaining failure shows the design is wrong, or when proving the repair now requires a different validation strategy, command set, proof surface, or acceptance claim than the current plan records
- return to `plan` when the remaining failure would exceed the current approved fix scope or cause a material plan change
- return to `scan` when the remaining failure shows the task boundary or acceptance criteria were misunderstood

### Re-Review

- skip this phase when no fix was performed
- accept and stop when no material issue remains
- move to `fix` only after the user explicitly approves another bounded repair loop, a fresh approved fix scope naming the specific remaining defect is recorded in `session-summary.md`, and that fresh scope still does not cause a material plan change or task-boundary change
- return to `plan` when the same root cause survives one bounded repair loop, when the remaining issue would exceed a fresh approved fix scope or cause a material plan change, or when the user declines another repair loop
- return to `scan` when the remaining issue shows the task boundary, requested deliverables, or acceptance criteria were misunderstood
- ask the user and pause before another repair loop when explicit approval is still pending or when re-review still leaves multiple safe resolutions after applying the least-change, least-risk default

### Repeated Repairs

- use one bounded `fix -> re-verify -> re-review` loop by default
- the first bounded repair loop starts when `verify` or `review` first records an approved fix scope and enters `fix`
- `re-verify -> fix` remains inside that same bounded repair loop while the current repair attempt is still being proved
- the first bounded repair loop ends only after `re-review` decides to accept, return to `plan` or `scan`, or pause for user input
- a second bounded repair loop can start only from `re-review` after explicit user approval and a fresh approved fix scope
- if the same root cause survives one bounded repair loop, return to `plan` instead of chaining open-ended fixes
- ask the user before starting another repair loop when explicit approval is still pending; if the user-approved next step would still cause a material plan change, return to `plan` instead of direct `fix`

## Defined Terms

- `material issue`: anything that blocks confident acceptance, including correctness failures, broken contracts, security or data-loss risk, rollback hazards, material scope drift, or missing validation for risky changed behavior
- `approved fix scope`: a bounded repair scope recorded in `session-summary.md` immediately before `fix` begins; `verify` and `review` may open it for the first repair pass, `re-verify` may refresh it while staying inside the same bounded repair loop, and `re-review` may record a fresh one only after explicit user approval for another bounded repair loop; it must name the defect being repaired in operator-checkable terms, the allowed file surface, the proof to rerun, the task boundary it assumes, and the boundary the repair must not cross
- `fits approved fix scope`: the remaining repair still targets the named defect or a direct symptom of the same root cause already recorded in the approved fix scope, stays inside the explicitly named file surface, rerun proof, and task boundary, and does not introduce a dependency or alter the trust or rollback boundary
- `exceeds approved fix scope`: the remaining repair targets a different material issue than the defect named in the current approved fix scope, touches a file outside the named file surface, requires an additional proof obligation or different validation command, changes user-visible behavior or interfaces, introduces a dependency, alters the trust or rollback boundary, or changes the task boundary
- `material plan change`: any change that adds a file outside the planned edit surface, changes user-visible behavior or interfaces, changes the validation command set or proof surface, introduces a dependency, or alters the trust or rollback boundary
- `boundary-crossing change`: any change whose correctness depends on behavior across a module, package, process, API, storage, permission, or user-visible boundary, not just inside one local implementation surface
- `risky changed behavior`: any changed behavior involving persistence, authentication, authorization, money, external side effects, concurrency, retries, rollback, or public or user-visible contracts
- `narrowest useful checks`: the smallest set of checks that still proves the changed behavior for the touched surface; local changes require local proof, boundary-crossing changes require boundary-level proof, and missing automation requires explicit manual validation notes
- `wrong or insufficient check`: the chosen validation strategy is still correct, but a specific command, fixture, environment precondition, or manual step was wrong, omitted, or too narrow; no code change and no plan change are needed, so stay in `verify` or `re-verify`
- `validation strategy defect`: proving the change now requires a different command set, broader proof surface, or different acceptance claim than the current plan records; return to `plan`
- `accepted facts`: observed repository state, command output, explicit user direction, and completed phase outcomes or explicitly accepted decisions recorded in `session-summary.md`; keep open inferences and reviewer hypotheses under risks instead of freezing them as facts
- `same root cause`: the repaired path still fails for the same underlying defect category after one bounded repair loop, even if the visible symptom text changes; if the next repair would target the same defect locus or the same proof obligation named in the approved fix scope, treat it as the same root cause
- `least-change, least-risk default`: when exactly one safe path preserves accepted behavior, interfaces, validation strategy, and rollback boundary, take it locally instead of escalating

## Token Discipline

### Default rules

- Use `AGENTS.md` by reference when possible.
- Read only phase-listed files before broadening scope.
- Prefer line references and deltas over pasted full files.
- Store long logs on disk and carry only failure excerpts into chat.
- Update `session-summary.md` after each meaningful step.
- Keep parent summaries compact and decision-oriented.
- Treat the current phase file as active instructions and `session-summary.md` as the only durable checkpoint.

### What To Persist On Disk

- task and acceptance criteria
- touched files
- open risks
- failed commands and short failure reasons
- next phase and next command
- any return-to-`plan` or return-to-`scan` decision and why it was triggered

### What Not To Repeat In Chat

- full AGENTS text
- full diff output
- unchanged file content
- already accepted decisions
- raw test logs unless the exact failure lines matter

## Quality Rules

- End every writable sequence with a read-only review phase.
- Keep fixes bounded to an approved fix scope recorded in `session-summary.md`.
- Re-verify and re-review after every material fix.
- Prefer the smallest validation command that can prove correctness.
- If the plan changes materially, update `session-summary.md` before editing again.
- Stop writing before expanding scope beyond the current approved plan.

## Session Rollover

If the current chat grows too large:

1. update `session-summary.md`
2. keep only accepted facts, current status, touched files, open risks, and next step
3. continue from that file in a fresh parent session

This keeps the workflow parent-only while preventing context bloat from becoming the dominant token cost.
