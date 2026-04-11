---
name: codex-parent-session-orchestrator
description: Run a structured scan/plan/implement/verify/review workflow inside the current parent Codex session without launching external workers or helper scripts. Use when the user wants a single-session workflow, wants to avoid subagents, or wants lower token overhead with disk-backed checkpoints and compact handoff files.
---

# Codex Parent Session Orchestrator

## Overview

Use this skill when the parent Codex instance should keep execution inside the current session instead of delegating work to internal subagents.

The parent should:

- keep the whole task inside one Codex session
- preserve the good parts of subagent workflows as explicit phases
- keep state on disk so the chat does not carry full history
- reuse `AGENTS.md` by reference instead of restating it
- keep summaries compact and delta-oriented
- end writable work with a read-only review pass
- use a bounded `fix -> re-verify -> re-review` loop when `verify` or `review` opens an approved fix scope
- apply `skills/karpathy-guidelines/SKILL.md` as the default local anti-overengineering overlay for coding phases so the parent favors explicit assumptions, the smallest complete design, surgical edits, and goal-driven verification
- inherit the shared mandatory plan-first gate from `skills/agent-skills-integration/agent-skill-routing.md` and use `skills/plan-mode-default/SKILL.md` plus `skills/plan-mode-default/references/coding-plan-prompt-en.md` as the default planning contract before any implementation begins, unless the user explicitly overrides the contract format while preserving the understanding-report and explicit-approval gate
- treat the approved full PLAN as a living disk artifact under repo-root `plan/`, not as a chat code block dump
- keep score tracking in the active plan artifact and update it through the task, using explicit user scores when given and a conservative provisional score capped at `50` when the user has not scored yet

## Read In This Order

- read `skills/agent-skills-integration/agent-skill-routing.md` first for the shared plan-first authority and vendored routing rules
- read `skills/karpathy-guidelines/SKILL.md` next for the default local anti-overengineering posture on coding phases
- read `skills/plan-mode-default/SKILL.md` next for the default workspace planning behavior
- read `skills/plan-mode-default/references/coding-plan-prompt-en.md` after that for the detailed planning contract text
- read `references/parent-session-workflow.md` for the phase model and operating rules
- read `references/phase-spec-format.md` for the manual run-kit format and starter files
- read `references/token-efficiency-playbook.md` when the request emphasizes minimum token use

## Operating Rules

- do not launch external workers or helper scripts for this workflow
- keep the parent responsible for decomposition, edits, validation, and final acceptance
- treat subagent roles as short-lived parent phases, not new sessions
- use vendored `agent-skills` as the execution-discipline layer for the active phase; keep local parent-session rules authoritative for acceptance, scope, and repair-loop behavior
- for coding phases, treat `skills/karpathy-guidelines/SKILL.md` as the default local overlay for simplicity, surgical scope, and explicit assumption handling
- for every coding request, satisfy the shared gate from `skills/agent-skills-integration/agent-skill-routing.md` before entering `implement` or making writable changes
- do not treat urgency, tiny scope, direct edit language, or "just do it now" requests as a waiver of the plan-first gate
- do not treat minor subtasks, one-line fixes, tiny follow-up edits, or repair steps as exempt; every writable coding action must already fit the active approved plan record or reopen planning first
- write or update the approved full PLAN under repo-root `plan/` before `implement` begins
- keep the active approved plan file versioned, time-sortable, clearly typed, and updated with progress, completion state, blockers, next step, and scoreboard state as work advances
- record explicit user scores as authoritative when available and otherwise maintain a conservative provisional score capped at `50` instead of blocking for feedback or using a fixed default number
- default runtime path:
  - `scan`
  - `plan`
  - `implement`
  - `verify`
  - `review`
- add `fix`, `re-verify`, and `re-review` only when a material issue is found
- use `session-summary.md` as the durable checkpoint for accepted facts, current status, approved fix scope, and next step
- treat the current phase file as the active instruction surface for the current step
- treat `active-context.md` as a bootstrap snapshot, not the long-lived run ledger
- treat `phase-checklist.md` as the ordered phase index and manual progress aid, not the durable current-state record
- keep context small:
  - use `AGENTS.md` by reference
  - read only the files needed for the current phase
  - update `session-summary.md` with deltas instead of retelling the full history
- if the session grows too large, refresh the on-disk checkpoint and continue from that file in a new parent session
- do not load all vendored skills at once; route only the minimum set needed for the current phase through `skills/agent-skills-integration/agent-skill-routing.md`
- every selected imported skill should have a short phase-local justification; if the parent cannot explain what a selected imported skill changes about the current phase, remove it
- for the `plan` phase, treat `skills/plan-mode-default/SKILL.md` and `skills/plan-mode-default/references/coding-plan-prompt-en.md` as the default behavior contract for planning output in this workspace unless the user explicitly asks for a different planning contract format; any override must still preserve the understanding-report and explicit-approval gate
- for coding work, treat the `plan` phase as mandatory before `implement`; direct implementation is not an allowed starting phase
- keep chat summaries short after plan approval and point to the saved plan file instead of pasting the full plan body

## Run Kit

The default run kit lives under `parent-session-runs/<run-id>/`.

Recommended files:

- `task-brief.md`
- `active-context.md`
- `phase-checklist.md`
- `session-summary.md`
- `phases/*.md`

Use the templates under `skills/codex-parent-session-orchestrator/assets/run-templates/` when you want a consistent starting point.

## Phase Contract

Every phase should state:

- phase name
- role
- mode: `read-only` or `write`
- one concrete goal
- files to read first when phase-local inputs matter
- writable scope if any
- outputs to leave on disk when the phase updates run artifacts
- success criteria
- validation checks when the phase needs observable proof beyond the stop rule
- stop condition

## When To Use

Use this skill when the user asks for:

- parent-only execution
- a single Codex session
- no subagents
- low-token workflows
- phase-based delivery with checkpoints

Do not use this skill when the user explicitly asks for `/sub` or for internal worker-team execution. In those cases use the subagent workflow.

## Imported Discipline

The canonical imported-skill mapping lives in `skills/agent-skills-integration/agent-skill-routing.md`.

Use that file as the only source of truth for:

- phase defaults
- optional task-shaped add-ons
- specialist overlays and checklists
- release-only overlays that are not part of the default parent phase checklist

Do not restate a separate default mapping here.
