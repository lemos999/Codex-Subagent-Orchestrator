# Queue Runner

## Purpose

`scripts/start-codex-subagent-queue.ps1` is a local-first queue runner that supervises repeated issue dispatch while preserving the existing launcher and `/sub`-style bounded worker model.

Use it when you want:

- polling against a local backlog instead of one-off manual specs
- one deterministic workspace per issue
- bootstrap hooks for new workspaces
- `WORKFLOW.md` and `AGENTS.md` auto-detected after bootstrap
- bounded concurrency over multiple issue runs
- queue state, retries, and per-issue launcher evidence on disk

## Command

```powershell
& ".\skills\codex-subagent-orchestrator\scripts\start-codex-subagent-queue.ps1" `
  -ConfigPath ".\queue-local-json.json" `
  -AsJson
```

Arguments:

- `-ConfigPath`: queue config JSON file
- `-LauncherPath`: optional override for the team launcher path
- `-CodexExecutable`: optional override for the worker executable; defaults to `codex`
- `-MaxPolls`: optional override for `polling.max_polls`
- `-AsJson`: emit machine-readable queue status instead of a table

## Config Shape

```json
{
  "tracker": {
    "kind": "local-json",
    "source_file": "tasks/queue.json",
    "active_states": ["Todo", "In Progress"],
    "terminal_states": ["Done", "Closed"]
  },
  "polling": {
    "interval_seconds": 5,
    "max_polls": 1,
    "drain_on_exit": true
  },
  "workspace": {
    "root": "workspaces"
  },
  "output": {
    "root": "queue-output",
    "report_file": "queue-output/queue-report.md"
  },
  "memory": {
    "enabled": true,
    "mode": "hybrid",
    "root": ".codex-memory"
  },
  "hooks": {
    "after_create": "git clone --depth 1 https://github.com/your-org/your-repo.git .",
    "after_create_sentinel_paths": [".git", "WORKFLOW.md", "AGENTS.md"]
  },
  "launcher": {
    "max_concurrent_issues": 2,
    "execution_mode": "sequential",
    "shared_directive_mode": "reference",
    "defaults": {
      "sandbox": "workspace-write",
      "reasoning_effort": "low",
      "prompt_profile": "compact",
      "response_style": "compact",
      "max_response_lines": 4
    }
  }
}
```

## Tracker Kinds

### `local-json`

Use this for a single local backlog file such as `tasks/queue.json`.

Required fields:

- `tracker.kind`
- `tracker.source_file`
- `tracker.active_states`
- `tracker.terminal_states`

The source file can be either:

- an array of issue objects
- an object with an `issues` array
- an object with a `tasks` array

Issue fields commonly used:

- `id`
- `identifier`
- `title`
- `description`
- `priority`
- `state`
- `labels`
- `blocked_by`
- `requested_deliverables`
- `auto_run`

The queue runner records the last successful fingerprint for each issue and skips redispatching unchanged completed tasks on later polls or later runs.

### `local-files`

Use this when you want one file per task under a directory such as `tasks/`.

Required fields:

- `tracker.kind`
- `tracker.source_dir`
- `tracker.active_states`
- `tracker.terminal_states`

Optional fields:

- `tracker.include_globs`: defaults to `["*.json", "*.md", "*.txt"]`
- `tracker.recurse`: defaults to `true`

Supported file formats:

- `*.json`: one issue object per file
- `*.md` and `*.txt`: optional front matter plus markdown/plain-text body

Markdown front matter example:

```md
---
identifier: LOCAL-42
state: Todo
priority: 1
labels:
  - backend
blocked_by:
  - LOCAL-41
requested_deliverables:
  - src/app.ts
---
# Fix the handler
Reproduce the bug and patch the handler without widening scope.
```

For `blocked_by`, local-files mode treats a blocker as satisfied once the blocker task has already completed successfully with the same task content, even if the source file still says `Todo`.

### `mock-json`

Compatibility alias for older local validation configs. Prefer `local-json` for new configs.

### `linear`

Optional adapter for unattended polling against Linear.

Required fields:

- `tracker.kind`
- `tracker.project_slug`
- `tracker.active_states`
- `tracker.terminal_states`

Optional fields:

- `tracker.endpoint`: defaults to `https://api.linear.app/graphql`
- `tracker.api_key_env`: defaults to `LINEAR_API_KEY`

The queue runner only reads tracker state. Ticket edits, state transitions, PR links, and comments should still be handled by the agent via the workflow prompt and tools.

## How It Works

1. Load queue config
2. Poll the configured tracker
3. Filter active, unblocked issues
4. Create or reuse one workspace per issue
5. Run `hooks.after_create` only when sentinel paths are missing
6. Generate one per-issue launcher spec
7. Launch `start-codex-subagent-team.ps1` with issue-specific workflow context
8. Track completion, backoff, and per-issue artifacts in `queue-state.json`
9. Write a human-readable `queue-report.md`
10. Skip redispatching unchanged completed task versions

## Memory Propagation

If the queue config includes a top-level `memory` block, the queue runner copies that block into every generated per-issue launcher spec. This keeps memory opt-in, preserves disabled behavior when the block is absent, and lets issue workspaces reuse the same `.codex-memory/` settings without expanding worker prompts inline.

## Auto-Detected Contracts

When the queue runner bootstraps a workspace, the downstream launcher automatically re-reads:

- `AGENTS.md`
- `WORKFLOW.md`

That means a fresh cloned workspace can provide its own shared contract and workflow prompt without having to hardcode their paths in the queue config.

## Output Files

The queue runner writes:

- `queue-state.json`
- `queue-report.md`
- `generated-specs/<issue>.json`
- `queue-logs/<issue>/launcher.stdout.log`
- `queue-logs/<issue>/launcher.stderr.log`
- `issue-runs/<issue>/<timestamp>/...`

The issue-run directories are the normal launcher outputs, including prompt files, manifests, summaries, and optional archives.
