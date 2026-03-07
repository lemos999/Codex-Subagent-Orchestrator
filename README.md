# Codex Subagent Orchestrator

This workspace-local skill helps a parent Codex instance supervise one or more `codex exec` workers. You can use it through `/sub` requests inside Codex, or run the PowerShell launcher directly with a JSON spec for repeatable orchestration.

This repository is not a typical application. It provides two things:

- a local Codex skill definition
- a PowerShell launcher for multi-worker execution, validation, and evidence capture

## Features

- Routes `/sub` requests into a worker-based execution flow
- Supports `parallel` and `sequential` execution modes with stage-based grouping
- Separates roles such as `implementer`, `reviewer`, `validator`, `fixer`, `planner`, and `custom`
- Reuses `AGENTS.md` as a shared operating contract with `full`, `compact`, and `reference` modes
- Writes worker-level `prompt`, `stdout`, `stderr`, `last.txt`, manifest, and summary artifacts
- Validates policies such as `requested_deliverables`, `supervisor_only`, and final read-only review coverage
- Archives deliverables, worker logs, and run evidence under `subagent-records/`

## Directory Layout

```text
.
|-- AGENTS.md
|-- README.md
`-- skills/
    `-- codex-subagent-orchestrator/
        |-- SKILL.md
        |-- agents/
        |   `-- openai.yaml
        |-- assets/
        |   `-- spec-templates/
        |-- references/
        `-- scripts/
            `-- start-codex-subagent-team.ps1
```

## Requirements

- `codex` CLI installed and available on `PATH`
- Windows PowerShell
- `AGENTS.md` present at the workspace root
- A Git repository is not strictly required, but the bundled templates assume `skip_git_repo_check: true`

## Quick Start

### 1. Use it through `/sub`

Open this workspace in Codex and start a request like:

```text
/sub update the auth flow under src and finish with a read-only review
```

### 2. Run the launcher directly

Copy one of the bundled templates, then run the launcher with that spec:

```powershell
Copy-Item `
  ".\skills\codex-subagent-orchestrator\assets\spec-templates\minimal-write.template.json" `
  ".\subagent-spec.json"

& ".\skills\codex-subagent-orchestrator\scripts\start-codex-subagent-team.ps1" `
  -SpecPath ".\subagent-spec.json" `
  -AsJson
```

By default, a relative top-level `cwd` is resolved from the directory where you launch the script, not from the spec file location. That makes `cwd: "."` portable for most workspace-local runs.

## Included Templates

- `minimal-write.template.json`: validates a single write worker
- `parallel-two-files.template.json`: runs two independent workers in parallel
- `parallel-implementers-reviewer.template.json`: runs parallel implementers followed by a later review stage
- `implementer-reviewer.template.json`: sequential implementer plus read-only reviewer example
- `nested-root-safety.template.json`: verifies workspace-root resolution when the spec file lives under a generated run directory

## Example Spec

```json
{
  "cwd": ".",
  "cwd_resolution": "invocation",
  "output_dir": "subagent-runs/minimal-write",
  "skip_git_repo_check": true,
  "execution_mode": "sequential",
  "shared_directive_mode": "reference",
  "defaults": {
    "sandbox": "workspace-write",
    "reasoning_effort": "low",
    "prompt_profile": "compact",
    "response_style": "compact",
    "max_response_lines": 4
  },
  "agents": [
    {
      "name": "probe-writer",
      "task": "Create or replace launcher-probe.txt in the working directory containing exactly the text OK.",
      "writable_scope": [
        "launcher-probe.txt"
      ],
      "required_non_empty_paths": [
        "launcher-probe.txt"
      ]
    }
  ]
}
```

## Output Artifacts

A typical run produces:

- `subagent-runs/<run>/orchestration-manifest.json`
- `subagent-runs/<run>/orchestration-summary.md`
- worker-level `*.stdout.log`, `*.stderr.log`, `*.prompt.txt`, and `*.last.txt`
- a per-run archive under `subagent-records/<timestamp>-<label>/`

The manifest records execution mode, stage plan, requested versus actual model and sandbox settings, validation results, session IDs, prompt hashes, and other trace data.

## Design Principles

- Keep the parent in supervisor mode whenever a bounded worker can make the deliverable change.
- Default reviewers and validators to `read-only`.
- Use parallelism only when output boundaries are independent and merge cost stays low.
- Prefer manifest, summary, and `last.txt` artifacts over copying large raw logs into parent context.
- If a reviewer finds a material issue, prefer a bounded fixer followed by re-review instead of patching the deliverable directly in the parent.

## Key Files

- `skills/codex-subagent-orchestrator/SKILL.md`: entry rules and operating model
- `skills/codex-subagent-orchestrator/scripts/start-codex-subagent-team.ps1`: launcher implementation
- `skills/codex-subagent-orchestrator/references/spec-format.md`: JSON spec format
- `skills/codex-subagent-orchestrator/references/orchestration-workflow.md`: parent-worker workflow
- `skills/codex-subagent-orchestrator/references/testing-playbook.md`: validation and testing guidance

## Recommended Usage

- Use a single worker or direct `codex exec` for small one-off tasks.
- Use the launcher when you need repeatable runs, parallel workers, late-stage review, or durable execution evidence.
- If you publish this on GitHub, keep `skills/`, `AGENTS.md`, the templates, and the reference docs together so the repository stays self-explanatory.
