---
name: codex-subagent-orchestrator
description: Orchestrate one or more internal chat-session subagents for delegated implementation, review, analysis, or generation work. Use when Codex should act as a supervisor that decomposes a request, decides whether delegation is justified, chooses team size and worker roles, adapts model and reasoning per worker, runs workers serially or in parallel, preserves evidence on disk, and validates outputs before reporting back. Trigger when the user explicitly starts a request with /sub, or asks for subagents, worker teams, parallel help, delegated execution, supervisory workflows, or multi-agent delivery inside a local workspace.
---

# Codex Subagent Orchestrator

## Overview

Use this skill when the parent Codex session should supervise internal chat-session agents rather than do the whole task alone.

The parent should:

- treat `/sub <request>` as an orchestration entrypoint
- classify the task before any worker starts
- produce an orchestration plan before launch
- apply `skills/karpathy-guidelines/SKILL.md` as the default local anti-overengineering overlay for coding stages and coding worker roles so the run favors explicit assumptions, the smallest complete design, surgical edits, and goal-driven verification
- for coding requests, require the shared plan-first approval gate from `skills/agent-skills-integration/agent-skill-routing.md` before any writable worker launch or implementation activity; do not treat blanket authority or immediate-approval language as a waiver of that gate
- for coding requests, treat the approved full PLAN as a living disk artifact under repo-root `plan/`, not as a chat code block dump
- for coding `/sub` runs, keep score tracking in the active plan artifact and treat the parent as the owner of score updates, including explicit user scores and provisional score maintenance capped at `50` when the user gives no score yet
- decide whether delegation is justified and whether one worker or a team is warranted
- choose team size, worker roles, model, and reasoning per worker from the internal agent capabilities available in the active session
- decide whether execution should be serial, parallel, or mixed
- keep reviewers scarce, read-only, and late unless risk justifies something earlier
- preserve worker evidence on disk
- validate outputs before acceptance
- treat every `/sub` coding request as an explicit request for the shared plan-first flow and use `skills/plan-mode-default/SKILL.md` plus `skills/plan-mode-default/references/coding-plan-prompt-en.md` as the default planning contract before any implementation begins, unless the user explicitly overrides the contract format while preserving the understanding-report and explicit-approval gate

## Read In This Order

- read `skills/agent-skills-integration/agent-skill-routing.md` first for the shared plan-first authority and worker-routing rules
- classify whether the `/sub` request is coding or non-coding before loading coding-only overlays
- if the run is coding, read `skills/karpathy-guidelines/SKILL.md` next for the default local anti-overengineering posture on coding stages and workers
- if the run is coding, read `skills/plan-mode-default/SKILL.md` next for the default workspace planning behavior
- if the run is coding, read `skills/plan-mode-default/references/coding-plan-prompt-en.md` after that for the detailed planning contract text
- read `references/orchestration-workflow.md` for the internal operating model, supervision loop, and worker patterns
- read `references/sub-command-protocol.md` when the user request starts with `/sub`
- read `references/spec-format.md` when you need the on-disk run kit or worker brief format
- read `references/testing-playbook.md` when you need to validate the internal workflow itself
- read `references/queue-runner.md` when the user wants repeated backlog handling in the current live session
- read `references/subagent-persona-guide.md` when a worker needs a distilled expert overlay

## Operating Rules

- keep the parent responsible for decomposition, acceptance criteria, rollback thinking, and final acceptance
- use bounded internal workers to plan, draft, or review the change whenever that is cleaner than doing all reasoning in the parent, but remember that internal workers operate in forked workspaces and the parent must land accepted writable changes into the primary workspace
- treat the text after `/sub` as the actual user request
- do not launch any external runtime, wrapper command, detached terminal, or background watcher
- satisfy `/sub` only by using internal chat-session agents
- use vendored `agent-skills` as worker execution discipline; keep local `/sub` rules authoritative for approval, team shape, parent landing, status, and acceptance
- for coding stages and coding workers, treat `skills/karpathy-guidelines/SKILL.md` as the default local overlay for simplicity, surgical scope, and explicit assumption handling
- use `spawn_agent` for bounded worker execution
- use `send_input` only when reusing an existing worker is cleaner than replacing it
- use `wait_agent` sparingly and only when the parent is blocked on the next critical result
- use `close_agent` when the run ends or a worker is abandoned
- if the runtime cannot provide the required internal agent tools, do not fake multi-agent execution; state that `/sub` delegation is unavailable in this runtime and fall back to `skills/codex-parent-session-orchestrator/SKILL.md` while preserving the same plan-first contract and on-disk evidence discipline
- produce a pre-launch report before execution starts:
  - request summary
  - user constraints
  - delegation justification
  - approval status and reason
  - worker count
  - execution mode: serial | parallel | mixed
  - each worker id, role, mission, writable scope, model, reasoning effort, and stage
  - review timing or review policy
  - acceptance strategy
  - approved plan file path in `plan/` for coding runs
  - plan artifact type, version, and current status for coding runs
  - current score and score source from the active plan for coding runs
  - evidence file paths
- for coding runs, treat delegation justification, worker count, execution mode, and per-worker assignments as provisional before approval and finalize them only after the understanding report and coding direction have been explicitly approved
- for coding requests, the shared understanding-report approval gate is mandatory and cannot be skipped; blanket authority or "proceed immediately" may only affect later execution pacing after that gate has been satisfied
- for coding requests, minor subtasks, one-line fixes, tiny follow-up edits, or repair steps are not exempt; every writable coding action must already fit the active approved plan record or reopen planning first
- for coding requests, write or update the approved full PLAN under repo-root `plan/` before any writable worker launch
- for coding requests, keep the active approved plan file versioned, time-sortable, clearly typed, and updated with progress, completion state, blockers, next step, and scoreboard state as the run advances
- for coding requests, record explicit user scores as authoritative and otherwise keep a conservative provisional score capped at `50` in the active plan instead of waiting for feedback or using a fixed fallback number
- choose model dynamically from the models currently available to internal agents in the active session; if you cannot distinguish the available options safely, say so instead of inventing a model catalog
- choose reasoning dynamically from task risk, ambiguity, writable scope, dependency depth, verification burden, and review burden
- default reviewers and validators to read-only
- default `review_policy` to one late read-only acceptance pass; add earlier review only when risk, reconciliation cost, or a bounded fixer gate justifies it
- do not attach a reviewer after every writer
- suppress redundant final reviewers or validators when one acceptance pass is enough
- retime a final reviewer behind the last writable stage unless there is a concrete reason to review earlier
- keep one implementer when work is narrow, sequential, shared-state, structurally overlapping, or merge-sensitive
- expand to multiple implementers only when deliverables are independently writable and merge behavior remains deterministic
- treat writable worker output as a proposal until the parent integrates the accepted change into the primary workspace
- when a reviewer or validator finds a material issue, prefer a bounded fixer followed by re-review or re-validation instead of rerunning the whole team by default
- if a finding exceeds the approved fix scope, re-plan or re-approve instead of silently widening the repair
- keep status visible in chat while agents work:
  - current stage
  - active agent count
  - waiting agents
  - completed agents
  - failed agents
  - what each active agent is doing
  - current score state when it changed or when it matters to the next action
- keep evidence on disk under `subagent-runs/<run-id>/` unless the user explicitly wants cleanup
- do not attach all vendored skills to every worker; route the minimum set that materially sharpens that worker's role through `skills/agent-skills-integration/agent-skill-routing.md`
- every selected imported skill must have a short justification tied to the worker's mission, risk, or acceptance bar; if the parent cannot explain why a selected imported skill changes behavior, remove it
- store required fixer scope in `review-verdict.md`, keep the active approved fix scope in `status.md`, and keep `acceptance.md` for the final supervisor verdict only
- for planner workers and for the mandatory first-stage planning gate on any coding `/sub` run, treat `skills/plan-mode-default/SKILL.md` and `skills/plan-mode-default/references/coding-plan-prompt-en.md` as the default planning contract unless the user explicitly asks for a different contract format that still preserves the understanding-report and explicit-approval gate

## Worker Prompt Contract

Every worker brief should explicitly state:

- the shared principal-engineer contract from `AGENTS.md`
- the worker role and mission
- the concrete task
- the files to read first
- the writable scope
- the output contract
- the validation steps
- any required skills
- the stop condition

When a worker's job is planning or plan refinement for coding work, its `files to read first` should include `skills/plan-mode-default/SKILL.md` and `skills/plan-mode-default/references/coding-plan-prompt-en.md` by default when those files exist, unless the user explicitly overrides the planning contract format while preserving the understanding-report and explicit-approval gate.
Do not launch implementer or fixer workers for coding work until a planner-like stage has produced the required understanding report and the user has explicitly approved proceeding.
When the parent materializes an approved full PLAN for coding work, it should save that artifact under repo-root `plan/` in the primary workspace, keep it updated as the run progresses, and keep chat output brief.

Do not let workers expand scope or modify unrelated files.
For write tasks, ask workers to leave a merge-ready explanation of what changed so the parent can land the accepted result in the primary workspace.
When imported `agent-skills` are selected, list their exact vendor paths in the worker brief so the worker can reopen only what it needs.

## Team Patterns

Use a single worker when one bounded task is enough.

Use a small team by default:

- `1` worker for a narrow or tightly coupled task
- `2` workers for implementer plus reviewer, or for two truly independent outputs
- `3` workers for two parallel implementers plus one final reviewer, or planner plus implementer plus reviewer when the split is materially cleaner
- `4+` workers only when parallelism is real, writable scope is disjoint, and merge cost stays controlled

Use parallel workers only when:

- tasks are independent enough to merge deterministically
- each worker has a clear writable boundary
- the parent can explain why one worker would be slower or riskier than a small fanout

Use `mixed` execution mode when:

- the overall run is staged serially
- at least one stage contains parallel workers
- the parent needs to report both the serial stage order and the parallel branch fanout explicitly

Use staged teams when:

- one worker produces a plan or artifact that later workers consume
- the review must gate a risky handoff
- a bounded fixer loop is safer than a broad rerun

## In-Session Queue Guidance

Use queue mode only inside the current live session.

Queue mode is appropriate when:

- the user wants repeated issue handling in one active session
- each issue can be planned and accepted separately
- per-issue evidence should live on disk

Queue mode is not detached background execution. If the user asks for unattended work after the session ends, say that the internal-only edition does not support it.

## Evidence

The default run directory is:

```text
subagent-runs/<run-id>/
|-- orchestration-plan.md
|-- status.md
|-- worker-briefs/
|-- results/
|-- review-verdict.md
`-- acceptance.md
```

Use the templates under `skills/codex-subagent-orchestrator/assets/run-templates/` when you want a consistent structure.

## Imported Discipline

The canonical imported-skill mapping lives in `skills/agent-skills-integration/agent-skill-routing.md`.

Use that file as the only source of truth for:

- planner, implementer, fixer, reviewer, and validator defaults
- task-shaped and risk-shaped add-ons
- specialist overlays and checklists
- release-only overlays that are not part of the default worker plan unless the task explicitly needs them

Do not restate a separate default mapping here.
