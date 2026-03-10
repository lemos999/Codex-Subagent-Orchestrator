---
name: codex-parent-session-orchestrator
description: Run a structured scan/plan/implement/verify/review workflow inside the current parent Codex session without launching `codex exec` workers. Use when the user wants a single-session workflow, wants to avoid subagents, or wants lower token overhead with disk-backed checkpoints and compact handoff files.
---

# Codex Parent Session Orchestrator

## Overview

Use this skill when the parent Codex instance should keep execution inside the current session instead of delegating work to child runs.

The parent should:

- keep the whole task inside one Codex session
- preserve the good parts of subagent workflows as explicit phases
- keep state on disk so the chat does not carry full history
- reuse `AGENTS.md` by reference instead of restating it
- keep summaries compact and delta-oriented
- end writable work with a read-only review pass
- use a bounded fix then re-review loop when review finds a material issue

## Read In This Order

- Read `references/parent-session-workflow.md` for the phase model and operating rules.
- Read `references/phase-spec-format.md` when you need the JSON format for deterministic run scaffolding.
- Read `references/token-efficiency-playbook.md` when the request emphasizes minimum token use.
- Use `scripts/start-codex-parent-session.ps1` when you want a run directory with compact phase files, checkpoints, and a manifest.

## Operating Rules

- Do not launch `codex exec` workers for this workflow.
- Keep the parent responsible for decomposition, edits, validation, and final acceptance.
- Treat subagent roles as short-lived parent phases, not new sessions.
- Default phase order:
  - `scan`
  - `plan`
  - `implement`
  - `verify`
  - `review`
- Add `fix` and a second `review` only when a material issue is found.
- Keep context small:
  - use `AGENTS.md` by reference
  - read only the files needed for the current phase
  - update `session-summary.md` with deltas instead of retelling the full history
- Prefer compact outputs and short verification notes.
- Keep writable scope narrow even though the parent is doing the edit itself.
- If the session grows too large, write a fresh compact checkpoint and continue from that file in a new parent session.

## Phase Contract

Every phase should state:

- phase name
- role
- mode: `read-only` or `write`
- one concrete goal
- files to read first
- writable scope if any
- outputs to leave on disk
- validation checks
- stop condition

## When To Use

Use this skill when the user asks for:

- parent-only execution
- a single Codex session
- no subagents
- low-token workflows
- phase-based delivery with checkpoints

Do not use this skill when the user explicitly asks for `/sub` or for real child-worker execution. In those cases the subagent workflow remains the compatibility path.
