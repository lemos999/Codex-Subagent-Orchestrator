# Subagent Orchestrator

`subagent-orchestrator` is a workspace-local skill for supervising one or more `codex exec` workers from a parent Codex session.

It is designed for tasks where the parent should stay in supervisor mode, split work into bounded worker runs, preserve execution evidence, and accept results only after validation.

## What It Does

- Interprets `/sub ...` requests as explicit delegation requests.
- Chooses a small worker team based on task shape.
- Supports sequential and parallel worker execution.
- Keeps worker prompts bounded with explicit writable scope and validation rules.
- Preserves prompt files, manifests, summaries, and per-run evidence for later review.
- Enforces safer delivery patterns such as read-only final review after writable work.

## Repository Layout

```text
.
|-- AGENTS.md
`-- skills/
    `-- codex-subagent-orchestrator/
        |-- SKILL.md
        |-- agents/openai.yaml
        |-- assets/spec-templates/
        |-- references/
        `-- scripts/start-codex-subagent-team.ps1
```

## Requirements

- A Codex environment with `codex exec` available on `PATH`
- PowerShell
- A workspace where local skills under `./skills` are supported

This repository is already arranged as a Codex workspace. The root `AGENTS.md` wires `/sub` requests to the local orchestrator skill.

## Quick Start

### 1. Clone the repository

```powershell
git clone <YOUR_REPO_URL>
cd Subagent-Orchestrator-main
```

### 2. Use the chat entrypoint

In Codex chat, start a request with `/sub`:

```text
/sub create a small CLI todo app with one implementer and one reviewer
```

The parent Codex session should:

- switch into supervisor mode
- form a bounded worker team
- run workers with `codex exec`
- validate the result before reporting back

### 3. Or run the launcher directly

Copy one of the bundled spec templates into the workspace root and execute it with the TS launcher:

```bash
cp skills/codex-subagent-orchestrator/assets/spec-templates/minimal-write.template.json minimal-write.json
node packages/launcher/dist/cli.js --spec minimal-write.json
```

**Legacy PS launcher (fallback):**

```powershell
Copy-Item `
  ".\skills\codex-subagent-orchestrator\assets\spec-templates\minimal-write.template.json" `
  ".\minimal-write.json"

& ".\skills\codex-subagent-orchestrator\scripts\start-codex-subagent-team.ps1" `
  -SpecPath ".\minimal-write.json" `
  -AsJson
```

The template uses:

- `cwd: "."`
- `cwd_resolution: "invocation"`

That means the launcher resolves the worker workspace from the directory where you run the command.

## Bundled Example Specs

The repository includes reusable JSON specs under `skills/codex-subagent-orchestrator/assets/spec-templates/`:

- `minimal-write.template.json`: one sequential writer that creates a bounded file
- `live-usage.template.json`: one sequential writer with real-time token usage display and a persisted usage snapshot
- `parallel-two-files.template.json`: two independent writers running in parallel
- `implementer-reviewer.template.json`: one implementer followed by a read-only reviewer
- `parallel-implementers-reviewer.template.json`: two parallel implementers followed by a read-only reviewer
- `nested-root-safety.template.json`: workspace root resolution and nested-run safety validation
- `workflow-issue.template.json`: a Symphony-style `WORKFLOW.md` issue run while keeping the existing launcher command
- `queue-local-json.template.json`: a local `queue.json` backlog for unattended `/sub` queue runs
- `queue-local-files.template.json`: a local `tasks/` directory queue for unattended `/sub` queue runs
- `queue-mock.template.json`: a local mock-tracker queue config for end-to-end Symphony-lite runs
- `queue-linear.template.json`: an optional Linear-backed queue config for unattended issue polling

These templates are intended as launcher and workflow examples, not domain examples such as crawlers or games.

## Launcher Command Pattern

### Primary — TS Launcher

Use the TypeScript launcher for repeatable worker orchestration from JSON (supports all engines):

```bash
node packages/launcher/dist/cli.js --spec your-spec.json
```

### Legacy — PS Launcher (Fallback)

The PowerShell launcher remains available as a fallback:

```powershell
& ".\skills\codex-subagent-orchestrator\scripts\start-codex-subagent-team.ps1" `
  -SpecPath ".\your-spec.json" `
  -AsJson
```

Top-level fields commonly used in a spec:

- `cwd`
- `output_dir`
- `manifest_file`
- `execution_mode`
- `requested_deliverables`
- `supervisor_only`
- `require_final_read_only_review`
- `material_issue_strategy`
- `live_usage`
- `defaults`
- `agents`

Symphony-inspired workflow fields are also supported:

- `workflow_file`
- `workflow_prompt_mode`
- `workflow_context`
- `workflow_context_file`
- `workflow_render_strict`
- `hooks.after_create`

For deliverable-oriented `/sub` workflows, prefer:

- `supervisor_only: true`
- `require_final_read_only_review: true`
- `material_issue_strategy: "fixer_then_rereview"`

## Minimal Spec Example

```json
{
  "cwd": ".",
  "cwd_resolution": "invocation",
  "output_dir": "subagent-runs/codex/minimal-write",
  "skip_git_repo_check": true,
  "execution_mode": "sequential",
  "write_prompt_files": true,
  "write_summary_file": true,
  "shared_directive_mode": "reference",
  "defaults": {
    "model": "gpt-5.4",
    "sandbox": "workspace-write",
    "reasoning_effort": "low"
  },
  "agents": [
    {
      "name": "probe-writer",
      "task": "Create or replace launcher-probe.txt in the working directory containing exactly the text OK.",
      "writable_scope": ["launcher-probe.txt"],
      "validation": [
        "Ensure launcher-probe.txt exists.",
        "Ensure the file content is exactly OK."
      ]
    }
  ]
}
```

## Output Artifacts

A healthy run typically produces:

- worker stdout and stderr files
- one prompt file per worker
- one `last.txt` file per worker unless overridden
- `orchestration-manifest.json`
- `orchestration-summary.md`
- `run-manifest.md`
- `run-summary.md`
- `prompts/*.prompt.md` with the exact parent-written worker prompts
- `results/*.result.md` with the preserved worker return text
- `engines/<engine>/*.raw.txt` for mixed-engine runs
- `orchestration-usage.json` when `live_usage.enabled` is true and `display_mode` includes `file`
- an optional per-run archive with copied deliverables and worker evidence

By default, Codex launcher examples write outputs under `subagent-runs/codex/`.

## Live Usage Monitoring

If you want Codex usage to stay visible while workers are running, enable the top-level `live_usage` block in the launcher spec.

```json
"live_usage": {
  "enabled": true,
  "display_mode": "both",
  "status_file": "subagent-runs/codex/live-usage/orchestration-usage.json",
  "poll_interval_ms": 500
}
```

What this does:

- forces worker `codex exec` runs into `--json` mode so token events can be parsed during execution
- updates a single-line PowerShell progress display when `display_mode` is `progress` or `both`
- writes a machine-readable live snapshot when `display_mode` is `file` or `both`
- stays compatible with both the legacy `event_msg/token_count` footer event and the newer `thread/tokenUsage/updated` event shape

Quick start:

```powershell
Copy-Item `
  ".\skills\codex-subagent-orchestrator\assets\spec-templates\live-usage.template.json" `
  ".\live-usage.json"

& ".\skills\codex-subagent-orchestrator\scripts\start-codex-subagent-team.ps1" `
  -SpecPath ".\live-usage.json" `
  -CodexExecutable "codex.cmd" `
  -AsJson
```

On Windows, prefer `-CodexExecutable "codex.cmd"` if PowerShell execution policy blocks `codex.ps1`.

If you just want a short command to inspect the latest live snapshot, use the root helper:

```powershell
.\usage.cmd
```

Useful variants:

- `.\usage.cmd -Once`: print the latest snapshot once and exit
- `.\usage.cmd -StatusFile .\subagent-runs\codex\live-usage\orchestration-usage.json`: target a specific run

## Symphony Compatibility

The launcher can now absorb the repo-owned workflow contract idea from `openai/symphony` without changing the user-facing command shape.

- Keep using `/sub` in chat and `start-codex-subagent-team.ps1 -SpecPath ...` in PowerShell.
- Point `workflow_file` at a `WORKFLOW.md` file and pass issue data through `workflow_context` or `workflow_context_file`.
- The launcher renders `{{ issue.* }}` variables and `{% if attempt %}...{% endif %}` blocks before composing each worker prompt.
- Use `hooks.after_create` plus sentinel paths when you want a one-shot workspace bootstrap similar to Symphony's workspace creation hook.

This is intentionally not a long-running tracker poller. It imports the in-repo workflow contract and bootstrap pattern while keeping the current supervisor/worker model.

## Symphony-Lite Queue Runner

The repository now also includes a queue runner for unattended issue dispatch:

```powershell
& ".\skills\codex-subagent-orchestrator\scripts\start-codex-subagent-queue.ps1" `
  -ConfigPath ".\queue-local-json.json" `
  -AsJson
```

What it does:

- polls a local `queue.json`, a local `tasks/` directory, or an optional external tracker adapter
- creates one workspace per issue
- uses `hooks.after_create` to bootstrap missing workspaces
- auto-detects `AGENTS.md` and `WORKFLOW.md` after bootstrap
- generates one launcher spec per issue
- launches the existing team runner with bounded concurrency
- writes `queue-state.json`, `queue-report.md`, per-issue manifests, summaries, and worker evidence
- skips redispatching unchanged tasks that already completed successfully

This still keeps the current command family. The queue runner is a thin supervisor above the existing launcher, not a separate orchestration stack.

## `/sub` Routing

`/sub` is intended to stay the only chat command.

From the skill contract:

- if the request is a one-off bounded task, `/sub` should route to the team launcher path
- if the request means "keep watching", "run unattended", "drain queue.json", "watch a tasks folder", or "handle tracker work over time", `/sub` should route to the queue runner path

That means the user should not need separate chat commands such as `/sub-team` or `/sub-queue`. The parent Codex instance is expected to decide automatically from context.

## How the Skill Is Intended to Work

Parent Codex responsibilities:

- classify the request
- decide team size and worker roles
- choose model, sandbox, and reasoning effort
- keep worker boundaries narrow
- validate outputs
- rerun review after any bounded fix

Worker responsibilities:

- complete one bounded task
- stay within writable scope
- validate their own result
- return a compact summary
- stop after success criteria are met

## Documentation Map

- `skills/codex-subagent-orchestrator/SKILL.md`: skill overview and operating rules
- `skills/codex-subagent-orchestrator/references/orchestration-workflow.md`: parent/worker workflow and team patterns
- `skills/codex-subagent-orchestrator/references/sub-command-protocol.md`: `/sub` behavior contract
- `skills/codex-subagent-orchestrator/references/spec-format.md`: JSON launcher spec format
- `skills/codex-subagent-orchestrator/references/testing-playbook.md`: recommended test order and validation checklist

## Typical Use Cases

- delegate a bounded implementation task to one worker
- run multiple independent workers in parallel
- separate implementation from review
- preserve reproducible evidence for delivery and audit
- recover with a bounded fixer and re-review instead of rerunning a whole team

## Notes

- This repository ships orchestration examples, not full product examples.
- Reviewers and validators should default to `read-only`.
- `danger-full-access` should be reserved for cases where workspace-write is genuinely insufficient.
- If the launcher path fails, keep the failed spec and pivot to direct `codex exec` with explicit model and reasoning settings.
