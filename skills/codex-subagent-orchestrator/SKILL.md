---
name: codex-subagent-orchestrator
description: Orchestrate one or more `codex exec` subagents for delegated implementation, review, analysis, or generation work. Use when Codex should act as a supervisor that decomposes a user request, autonomously decides team size and worker roles, assigns bounded tasks to child Codex runs, adjusts model, sandbox, and reasoning effort per worker, runs workers sequentially or in parallel, resumes workers as needed, and validates outputs before reporting back. Trigger when the user explicitly starts a request with `/sub`, or asks for subagents, worker teams, parallel Codex execution, delegated task execution, supervisory workflows, or multi-agent delivery inside a local workspace.
---

# Codex Subagent Orchestrator

## Overview

Use this skill when the parent Codex instance should supervise execution rather than perform the whole task directly.

The parent should:

- treat `/sub <request>` as an orchestration entrypoint
- classify the task
- decide whether `/sub` should resolve to a one-off team run or a queue run
- decide whether subagents are justified
- autonomously choose team size and team shape
- choose the smallest useful skill set
- choose team shape, sandbox, model, and reasoning per worker
- launch one or more bounded workers
- validate outputs
- resume or retry workers only when bounded follow-up is cleaner than a fresh run
- preserve worker evidence so later sessions can audit what actually happened

## Read In This Order

- Read `references/orchestration-workflow.md` for the operating model, prompt contract, team patterns, and supervision loop.
- Read `references/sub-command-protocol.md` when the user request starts with `/sub`.
- Read `references/spec-format.md` when you need the launcher input format or want to create a reusable worker-team spec.
- Read `references/testing-playbook.md` when you need to validate the launcher itself or prepare a reproducible handoff to another session.
- Read `references/queue-runner.md` when you need tracker polling, issue workspaces, or a Symphony-lite unattended supervisor loop.
- Use `scripts/start-codex-subagent-team.ps1` when you want deterministic local execution of one or more workers from a JSON spec.

## Operating Rules

- Keep the parent responsible for decomposition, acceptance criteria, and rollback thinking.
- Keep the parent out of requested deliverable-file edits whenever a bounded worker can do the work instead.
- Treat the text after `/sub` as the actual user request.
- Route `/sub` automatically:
  - choose the team launcher for finite work such as "fix this bug", "implement this file", "work this one ticket", or "review these changes"
  - choose the queue runner for ongoing work such as "keep processing queue.json", "watch the tasks folder", "run unattended", "poll for new issues", or "handle all matching tasks in the background"
- Keep each worker focused on one bounded deliverable.
- Use the workspace `AGENTS.md` as the primary shared operating contract when it exists.
- Inject the shared principal-engineer operating contract into every worker, but do not duplicate long instructions unless the worker genuinely needs them.
- Add a role-specific mission on top of the shared contract for each worker.
- For `custom` workers that launch nested teams, declare `required_paths` and preferably `required_non_empty_paths` so the launcher can reject false-success runs.
- Prefer `workspace-write` over `danger-full-access`.
- Use reasoning efficiently. Default to `low` for routine workers and raise it only when ambiguity or risk justifies it.
- Prefer `shared_directive_mode: "reference"` for routine workspace-local workers, and fall back to `"compact"` when you want a short inlined contract instead of the full directive.
- Use parallel workers only when tasks are independent enough that output merging remains clear.
- When parallel workers feed a final reviewer, put the parallel builders in the same stage and the reviewer in a later stage.
- Do not create large teams by default. Expand the team only when the decomposition really earns it.
- Treat skills as routing hints for workers, not as an excuse to bloat every worker prompt.
- Pass `-m` explicitly when model choice matters.
- Keep `last.txt`, prompt files, and the launcher manifest unless the user explicitly wants cleanup.
- Prefer the generated orchestration summary over raw stdout when bringing worker results back into parent context.
- Validate files and summaries before accepting a worker result.
- Evaluate efficiency structure-first: fewer parent interventions, fewer full reruns, bounded fixer loops, and clean reviewer coverage matter more than raw token totals alone.
- Default reviewers and validators to `read-only`. If they need write access, the parent should justify that deviation explicitly.
- If a reviewer or validator finds a material issue, launch a bounded fixer worker and then re-run review or validation on the repaired artifact before acceptance.
- When the launcher is used for deliverable work, prefer top-level policy fields `requested_deliverables`, `supervisor_only: true`, `require_final_read_only_review: true`, and `material_issue_strategy: "fixer_then_rereview"` so unsafe team shapes fail before execution.

## Worker Prompt Contract

Every worker prompt should explicitly state:

- the shared principal-engineer contract
- the worker role and mission
- the concrete task
- the files to inspect first
- the writable scope
- the output contract
- the validation steps
- any required skills
- a stop condition

Do not let workers expand scope or modify unrelated files.

## Team Patterns

Use a single worker when one bounded task is enough.

Use a small team by default:

- `1` worker for a narrow task
- `2` workers for implementer/verifier or two independent outputs
- `3` workers for planner/implementer/reviewer or similarly clean separation
- `4+` workers only when parallelism is real and merge cost stays controlled

Use parallel workers when:

- tasks are independent
- each worker has a clean output boundary
- the parent can merge or compare results deterministically

Use a staged team when:

- one worker produces a plan or artifact
- later workers consume that result
- the parent needs to gate each phase

## Launcher Guidance

Use `scripts/start-codex-subagent-team.ps1` with a JSON spec when:

- you want `/sub` requests translated into repeatable worker orchestration
- you want repeatable worker orchestration
- you want multiple workers launched in parallel
- you want per-worker reasoning, sandbox, or output control
- you want prompt files, `last.txt`, and a manifest for later supervision or forensics

If the request is simple enough, you may still invoke `codex exec` directly without the launcher.

Use `scripts/start-codex-subagent-queue.ps1` with a queue config when:

- the user wants one `/sub` request to keep processing multiple issues over time
- the user wants local backlog polling or background issue dispatch
- the work should continue unattended until the queue is drained or stopped
- each issue should get its own workspace and per-issue launcher evidence
