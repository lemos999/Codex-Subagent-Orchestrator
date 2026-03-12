# Codex Parent Session Orchestrator

This workspace now defaults to a parent-session-first workflow.

The main path keeps the task inside one Codex session and preserves subagent-style discipline through explicit phases, compact checkpoint files, and a final read-only review.

The older subagent launcher remains in the repository as a compatibility path for explicit `/sub` requests and real child-worker execution.

## What It Does

- keeps execution in the current parent Codex session
- preserves multi-role rigor as phase files instead of child sessions
- moves durable state out of chat and onto disk
- keeps prompts compact by referencing `AGENTS.md` instead of restating it
- supports a bounded `fix -> re-review` loop without separate workers
- keeps `/sub` available for explicit child-worker execution through either a one-off team launcher or a queue runner
- supports optional file-backed memory for `/sub` runs without changing the default parent-session path

## Choosing a Path

Use the repository in one of three ways:

- default parent-session workflow: one Codex session, explicit phases, disk-backed checkpoints, no child workers
- `/sub` team launcher: one-off bounded child-worker execution for explicit child isolation or parallel branches
- `/sub` queue runner: repeated backlog dispatch with one workspace per issue and preserved queue state

Rule of thumb:

- if the user did not explicitly ask for child workers, stay on the parent-session path
- if the user explicitly asks for `/sub`, real child-worker isolation, or parallel worker execution, use the team launcher
- if the user wants polling, repeated issue handling, or unattended dispatch, use the queue runner

## Parent-Session Workflow

The default phase loop is:

1. `scan`
2. `plan`
3. `implement`
4. `verify`
5. `review`
6. optional `fix -> review`

The parent session stays responsible for the whole task. The workflow relies on a run directory with compact files such as:

- `task-brief.md`
- `active-context.md`
- `phase-checklist.md`
- `session-summary.md`
- `phases/*.md`

These files keep token use down by replacing repeated chat retellings with stable disk-backed checkpoints.

## Repository Layout

```text
.
|-- AGENTS.md
|-- README.md
`-- skills/
    |-- codex-parent-session-orchestrator/
    |   |-- SKILL.md
    |   |-- assets/spec-templates/
    |   |-- references/
    |   `-- scripts/start-codex-parent-session.ps1
    `-- codex-subagent-orchestrator/
        |-- SKILL.md
        |-- agents/openai.yaml
        |-- assets/spec-templates/
        |-- references/
        `-- scripts/
            |-- codex-memory.ps1
            |-- start-codex-subagent-team.ps1
            `-- start-codex-subagent-queue.ps1
```

## Requirements

- a Codex workspace that supports local skills under `./skills`
- PowerShell

You do not need `codex exec` for the default parent-session workflow.

You still need `codex exec` on `PATH` if you want to use `/sub` team or queue workflows.

## Quick Start

### 1. Prepare a parent-session run scaffold

Copy the bundled template into the workspace root and run the parent-session preparation script:

```powershell
Copy-Item `
  ".\skills\codex-parent-session-orchestrator\assets\spec-templates\minimal-parent-session.template.json" `
  ".\minimal-parent-session.json"

& ".\skills\codex-parent-session-orchestrator\scripts\start-codex-parent-session.ps1" `
  -SpecPath ".\minimal-parent-session.json" `
  -AsJson
```

This writes a compact run scaffold under `parent-session-runs/` by default.

### 2. Work from the generated files

Use:

- `active-context.md` as the compact current-task context
- `phase-checklist.md` as the execution loop
- `session-summary.md` as the only durable checkpoint file
- `phases/*.md` as phase-specific instructions

The current Codex parent session should read the current phase file, do the work, update `session-summary.md`, and move to the next phase.

### 3. Roll over when the chat grows too large

When the parent chat becomes expensive, compress the current state into `session-summary.md` and continue from that file in a fresh parent session.

This keeps the workflow parent-only while avoiding runaway context cost.

## Optional `/sub` Quick Start

Use `/sub` only when you actually want child workers instead of the default parent-session path.

### 1. Run a one-off child-worker team

Copy a bundled team template into the workspace root and launch it:

```powershell
Copy-Item `
  ".\skills\codex-subagent-orchestrator\assets\spec-templates\implementer-reviewer.template.json" `
  ".\implementer-reviewer.json"

& ".\skills\codex-subagent-orchestrator\scripts\start-codex-subagent-team.ps1" `
  -SpecPath ".\implementer-reviewer.json" `
  -AsJson
```

This writes launcher output under `subagent-runs/` and optional archives under `subagent-records/`.

### 2. Run repeated issue dispatch with the queue runner

Copy a bundled queue template into the workspace root and launch it:

```powershell
Copy-Item `
  ".\skills\codex-subagent-orchestrator\assets\spec-templates\queue-local-json.template.json" `
  ".\queue-local-json.json"

& ".\skills\codex-subagent-orchestrator\scripts\start-codex-subagent-queue.ps1" `
  -ConfigPath ".\queue-local-json.json" `
  -AsJson
```

The queue runner keeps issue workspaces, generated specs, queue state, and per-issue launcher evidence on disk.

## Bundled Parent-Session Templates

The repository includes reusable JSON specs under `skills/codex-parent-session-orchestrator/assets/spec-templates/`:

- `minimal-parent-session.template.json`
- `implement-review.template.json`

## Bundled `/sub` Templates

The repository also includes reusable `/sub` team and queue templates under `skills/codex-subagent-orchestrator/assets/spec-templates/`.

Common starting points:

- `implementer-reviewer.template.json`
- `parallel-implementers-reviewer.template.json`
- `memory-enabled.template.json`
- `queue-local-json.template.json`
- `queue-local-files.template.json`
- `queue-linear.template.json`

## Parent-Session Spec Model

The preparation script takes a JSON spec with top-level fields such as:

- `cwd`
- `output_dir`
- `task`
- `context`
- `constraints`
- `acceptance_criteria`
- `requested_deliverables`
- `shared_directive_mode`
- `defaults`
- `phases`

Key design choice:

- phases describe what the parent should do next
- the script does not launch child workers
- the run directory is the handoff surface

## Token Strategy

The repository now optimizes for repeated-context reduction rather than worker-prompt reduction.

Use these defaults:

- keep one parent session active at a time
- keep `AGENTS.md` referenced, not repeated
- read only the files needed for the current phase
- store long logs on disk and carry only short excerpts into chat
- use `session-summary.md` as the single durable checkpoint
- end every writable sequence with a read-only review

## `/sub` Child-Worker Workflow

The explicit child-worker path lives under `skills/codex-subagent-orchestrator/`.

It has two entrypoints:

- `start-codex-subagent-team.ps1` for one-off bounded worker teams
- `start-codex-subagent-queue.ps1` for repeated tracker or backlog dispatch

Use `/sub` only when:

- the user explicitly asks for `/sub`
- real child-worker isolation is required
- parallel child execution materially helps throughput
- repeated tracker-driven or queue-driven dispatch is needed

The team launcher command is:

```powershell
& ".\skills\codex-subagent-orchestrator\scripts\start-codex-subagent-team.ps1" `
  -SpecPath ".\your-spec.json" `
  -AsJson
```

The queue runner command is:

```powershell
& ".\skills\codex-subagent-orchestrator\scripts\start-codex-subagent-queue.ps1" `
  -ConfigPath ".\your-queue.json" `
  -AsJson
```

When a `/sub` spec omits `shared_directive_mode`, the launcher now defaults to a hybrid policy:

- `implementer` and `fixer` workers get the full shared directive
- `reviewer`, `validator`, `planner`, and read-only `custom` workers get the compact shared directive

`/sub` also supports a distilled persona layer. `persona_guide_mode: "dynamic"` now compiles a task-specific zero-shot working persona from the built-in guide, so workers infer the smallest fitting expert blend from the request instead of replaying large persona source files. Use `compact` when you want the raw guide injected as-is, `reference` when you want workers to reopen the guide file themselves, and `disabled` when you want no persona overlay.

## Guardrails

Use the guardrails below to avoid the mistakes that showed up during optimization and benchmarking:

- do not package `tests/`, `subagent-runs/`, `subagent-records/`, `benchmark-output/`, or other local run artifacts into deployment zips
- keep `/sub` benchmarks rooted at the real repo workspace; the benchmark runner now refuses to run if `AGENTS.md` or `./skills` are missing
- score worker quality from `last.txt`, reviewer JSON, manifest metadata, and footer tokens first
- treat Windows PowerShell `stderr` as diagnostic only, because encoding can be lossy even when the worker run is valid

## Documentation Map

Parent-session workflow:

- `skills/codex-parent-session-orchestrator/SKILL.md`
- `skills/codex-parent-session-orchestrator/references/parent-session-workflow.md`
- `skills/codex-parent-session-orchestrator/references/phase-spec-format.md`
- `skills/codex-parent-session-orchestrator/references/token-efficiency-playbook.md`

Legacy subagent workflow:

- `skills/codex-subagent-orchestrator/SKILL.md`
- `skills/codex-subagent-orchestrator/references/orchestration-workflow.md`
- `skills/codex-subagent-orchestrator/references/queue-runner.md`
- `skills/codex-subagent-orchestrator/references/spec-format.md`
- `skills/codex-subagent-orchestrator/references/sub-command-protocol.md`
- `skills/codex-subagent-orchestrator/references/testing-playbook.md`

## Optional `/sub` Memory

The `/sub` team launcher and queue-generated issue specs now support opt-in file-backed memory under `.codex-memory/`.

- keep the `memory` block absent, or set `memory.enabled: false`, to preserve the old launcher behavior
- when enabled, Markdown files under `.codex-memory/` remain the source of truth and `index/memory-index.json` is rebuilt from them
- worker prompts get a short memory policy and a generated runtime memory file path instead of large inline memory text
- reviewers and validators stay read-only; with `memory.mode: "hybrid"` they default to core memory while implementers and fixers default to retrieval
- queue configs can declare one top-level `memory` block and the queue runner will copy it into every generated per-issue launcher spec
- memory is supporting context only: current task, repository files, validation output, and reviewer findings override it
- retention is guarded: secrets, instruction-like text, large raw logs, and failed review notes are excluded

Runnable example:

- `skills/codex-subagent-orchestrator/assets/spec-templates/memory-enabled.template.json`

Minimal example:

```json
{
  "memory": {
    "enabled": true,
    "mode": "hybrid",
    "root": ".codex-memory"
  }
}
```

Supported modes:

- `off`
- `reference`
- `core`
- `retrieval`
- `hybrid`

## Notes

- The default workflow is now parent-session-first.
- The run scaffold is intentionally compact and file-backed.
- `/sub` remains explicit and opt-in for true child-worker execution.
- `/sub` memory is also opt-in and does not change the default parent-session path.
