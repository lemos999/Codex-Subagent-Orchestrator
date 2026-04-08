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

## Read In This Order

- read `references/parent-session-workflow.md` for the phase model and operating rules
- read `references/phase-spec-format.md` for the manual run-kit format and starter files
- read `references/token-efficiency-playbook.md` when the request emphasizes minimum token use
- read `skills/agent-skills-integration/agent-skill-routing.md` when you need phase-by-phase routing into the vendored `agent-skills` pack

## Operating Rules

- do not launch external workers or helper scripts for this workflow
- keep the parent responsible for decomposition, edits, validation, and final acceptance
- treat subagent roles as short-lived parent phases, not new sessions
- use vendored `agent-skills` as the execution-discipline layer for the active phase; keep local parent-session rules authoritative for acceptance, scope, and repair-loop behavior
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
