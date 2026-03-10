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

## Default Phase Loop

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
- define a bounded fix scope and return to `fix`

### 6. Fix Then Re-Review

Use only when the review finds a material issue.

Goal:

- repair the specific issue
- avoid expanding scope
- rerun the narrowest checks that prove the repair
- run review again on the repaired final state

## Token Discipline

### Default rules

- Use `AGENTS.md` by reference when possible.
- Read only phase-listed files before broadening scope.
- Prefer line references and deltas over pasted full files.
- Store long logs on disk and carry only failure excerpts into chat.
- Update `session-summary.md` after each meaningful step.
- Keep parent summaries compact and decision-oriented.

### What To Persist On Disk

- task and acceptance criteria
- touched files
- open risks
- failed commands and short failure reasons
- next phase and next command

### What Not To Repeat In Chat

- full AGENTS text
- full diff output
- unchanged file content
- already accepted decisions
- raw test logs unless the exact failure lines matter

## Quality Rules

- End every writable sequence with a read-only review phase.
- Keep fixes bounded to reviewer-approved scope.
- Re-review after every material fix.
- Prefer the smallest validation command that can prove correctness.
- If the plan changes materially, update `session-summary.md` before editing again.

## Session Rollover

If the current chat grows too large:

1. update `session-summary.md`
2. keep only accepted facts, current status, touched files, open risks, and next step
3. continue from that file in a fresh parent session

This keeps the workflow parent-only while preventing context bloat from becoming the dominant token cost.
