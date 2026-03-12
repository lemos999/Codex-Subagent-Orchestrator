# Launcher Spec Format

## Purpose

`scripts/start-codex-subagent-team.ps1` launches one or more `codex exec` workers from a JSON spec.

Use this format when you want repeatable worker orchestration with per-worker settings.

## Top-Level Shape

```json
{
  "cwd": "<WORKSPACE_ROOT>",
  "cwd_resolution": "invocation",
  "output_dir": "subagent-runs",
  "manifest_file": "subagent-runs/orchestration-manifest.json",
  "debug_log_file": "subagent-runs/launcher-debug.log",
  "summary_file": "subagent-runs/orchestration-summary.md",
  "archive_root": "subagent-records",
  "write_run_archive": true,
  "archive_run_label": "todo-app",
  "skip_git_repo_check": true,
  "execution_mode": "parallel",
  "timeout_seconds": 120,
  "write_prompt_files": true,
  "write_summary_file": true,
  "requested_deliverables": [
    "output.txt"
  ],
  "supervisor_only": true,
  "require_final_read_only_review": true,
  "material_issue_strategy": "fixer_then_rereview",
  "shared_directive_mode": "hybrid",
  "persona_guide_mode": "dynamic",
  "memory": {
    "enabled": true,
    "mode": "hybrid",
    "root": ".codex-memory"
  },
  "workflow_file": "WORKFLOW.md",
  "workflow_auto_detect": true,
  "workflow_prompt_mode": "prepend",
  "workflow_context": {
    "attempt": 1,
    "issue": {
      "identifier": "ABC-123",
      "title": "Fix flaky test",
      "description": "The CI test is intermittently failing."
    }
  },
  "workflow_render_strict": true,
  "hooks": {
    "after_create": "git clone --depth 1 https://github.com/your-org/your-repo.git .",
    "after_create_sentinel_paths": [
      ".git",
      "README.md"
    ]
  },
  "defaults": {
    "model": "gpt-5.4",
    "sandbox": "workspace-write",
    "reasoning_effort": "low",
    "prompt_profile": "compact",
    "response_style": "compact",
    "max_response_lines": 4,
    "json": false,
    "ephemeral": false
  },
  "agents": [
    {
      "name": "worker-a",
      "prompt": "Reply with exactly: A"
    }
  ]
}
```

## Top-Level Fields

| Field | Required | Meaning |
|---|---|---|
| `cwd` | yes | Workspace root for every worker unless overridden later |
| `cwd_resolution` | no | How to resolve a relative top-level `cwd`: `invocation` or `spec`; defaults to `invocation` |
| `output_dir` | no | Directory for stdout, stderr, and optional final-message files |
| `manifest_file` | no | Where the launcher writes its machine-readable manifest |
| `debug_log_file` | no | Optional debug trace file for launcher-stage diagnostics |
| `summary_file` | no | Optional compact summary file for parent-side handoff |
| `archive_root` | no | Root directory where the launcher stores per-run evidence copies; defaults to `subagent-records` under the workspace root |
| `write_run_archive` | no | When true, stores a per-run archive with copied launcher files, deliverables, and worker evidence |
| `archive_run_label` | no | Optional human-readable label used in the run-archive folder name |
| `skip_git_repo_check` | no | Adds `--skip-git-repo-check` to each worker |
| `execution_mode` | no | `parallel` or `sequential`; defaults to `parallel` |
| `timeout_seconds` | no | Optional launcher timeout for the whole run; `0` means no launcher timeout |
| `write_prompt_files` | no | When true, writes `<worker>.prompt.txt` for audit and replay |
| `write_summary_file` | no | When true, writes `orchestration-summary.md` for compact parent-side handoff |
| `requested_deliverables` | no | Paths the parent expects workers to create or repair under supervision |
| `supervisor_only` | no | When true, declares that the parent should stay out of deliverable-file edits for this workflow |
| `require_final_read_only_review` | no | When true, the launcher rejects specs that end without a final read-only reviewer or validator after the last writable worker |
| `material_issue_strategy` | no | `none` or `fixer_then_rereview`; the latter requires a final read-only reviewer after the last fixer |
| `shared_directive_file` | no | File to inject into every worker before role-specific instructions |
| `shared_directive_text` | no | Inline shared directive text when you do not want to use `AGENTS.md` |
| `inject_shared_directive` | no | Disable shared directive injection entirely when false |
| `shared_directive_mode` | no | `full`, `compact`, `reference`, `hybrid`, or `disabled`; defaults to `hybrid` |
| `persona_guide_file` | no | File containing a persona-design guide for `/sub` workers |
| `persona_guide_text` | no | Inline persona-design guide text when you do not want to use the built-in guide |
| `persona_guide_mode` | no | `dynamic`, `compact`, `reference`, or `disabled`; defaults to `dynamic` |
| `memory` | no | Optional file-backed memory config. Keep it disabled or absent unless you want `.codex-memory/` scaffolded and worker runtime memory files attached via `Read first`. |
| `workflow_file` | no | Optional `WORKFLOW.md`-style prompt template file to render into each worker prompt |
| `workflow_auto_detect` | no | When true, the launcher will also look for `WORKFLOW.md` in the workspace root after bootstrap; defaults to `true` |
| `workflow_prompt_mode` | no | `prepend`, `replace`, or `disabled`; controls how rendered workflow text combines with worker `prompt` or `task` |
| `workflow_context` | no | Inline JSON object exposed to the workflow template, typically with keys such as `issue` and `attempt` |
| `workflow_context_file` | no | Path to a JSON file merged into `workflow_context` before rendering |
| `workflow_render_strict` | no | When true, missing `{{ variable }}` references fail the run; defaults to `true` |
| `hooks` | no | Optional launcher-side hook object, currently supporting `after_create` bootstrap behavior |
| `defaults` | no | Default worker settings |
| `agents` | yes | Array of worker definitions |

## Defaults Object

Supported fields:

- `sandbox`
- `model`
- `reasoning_effort`
- `json`
- `output_schema`
- `ephemeral`
- `prompt_profile`
- `response_style`
- `max_response_lines`

Defaults are merged into each worker unless the worker overrides them.

## Workflow Fields

These fields let the launcher absorb the repo-owned workflow contract pattern from Symphony while keeping the existing launcher command.

- `workflow_file` loads a `WORKFLOW.md`-style file.
- When `workflow_file` is omitted and `workflow_auto_detect` is true, the launcher looks for `WORKFLOW.md` in the workspace root and then in the spec directory.
- The launcher ignores YAML front matter operationally, but preserves it in the manifest for audit.
- The Markdown body is treated as the prompt template.
- Supported template forms are:
  - `{{ issue.identifier }}`
  - `{{ attempt }}`
  - `{% if attempt %}...{% else %}...{% endif %}`
- `workflow_prompt_mode: "prepend"` keeps the worker's own `task` or `prompt` and adds the rendered workflow text above it.
- `workflow_prompt_mode: "replace"` uses the rendered workflow text as the task body for that worker.

Top-level `workflow_context` is merged first, then agent-level `workflow_context_file`, then agent-level `workflow_context`. The launcher also injects:

- `agent.name`
- `agent.kind`
- `agent.stage`
- `agent.cwd`
- `run.worker_name`
- `run.worker_kind`
- `run.stage`
- `run.worker_cwd`
- `run.workspace_root`

If you want to carry tracker payloads from another system, prefer writing them to a JSON file and pointing `workflow_context_file` at it.

## Hook Fields

The optional top-level `hooks` object currently supports a Symphony-style one-shot bootstrap:

- `after_create`: PowerShell command to run before workers when bootstrap is needed
- `after_create_sentinel_paths`: if any listed path is missing, the hook runs
- `after_create_if_workspace_empty`: when true, the hook also runs if the workspace root has no files
- `after_create_stdout_file`: optional path for captured stdout
- `after_create_stderr_file`: optional path for captured stderr

If no sentinel paths are provided, `after_create` defaults to running only when the workspace is empty.
After `after_create` finishes, the launcher re-reads `AGENTS.md` and `WORKFLOW.md` from the workspace before composing worker prompts.

Recommended default split:

- implementers and fixers: `workspace-write`
- reviewers and validators: `read-only`

For `/sub` delivery work, prefer:

- `supervisor_only: true`
- `require_final_read_only_review: true`
- `material_issue_strategy: "fixer_then_rereview"`

## Agent Object

Required fields:

- `name`
- `prompt` or `task`

Optional fields:

- `mode`: `exec` or `resume`
- `kind`: `implementer`, `reviewer`, `validator`, `fixer`, `planner`, or `custom`
- `stage`: positive integer stage number; same-stage workers can run together when `execution_mode` is `parallel`
- `resume_last`: boolean
- `session_id`
- `cwd`
- `role`
- `mission`
- `success_criteria`
- `coordination_notes`
- `task`
- `skills`
- `read_first`
- `writable_scope`
- `requirements`
- `validation`
- `return_contract`
- `required_paths`
- `required_non_empty_paths`
- `sandbox`
- `model`
- `reasoning_effort`
- `json`
- `output_schema`
- `ephemeral`
- `prompt_profile`
- `response_style`
- `max_response_lines`
- `output_last_message_file`
- `memory_mode`
- `workflow_prompt_mode`
- `workflow_context`
- `workflow_context_file`
- `stop_when`
- `extra_args`

## Agent Modes

### `exec`

Starts a fresh worker:

```json
{
  "name": "builder",
  "mode": "exec",
  "prompt": "Create or replace output.txt with exactly HELLO."
}
```

Or use structured fields and let the launcher compose the prompt:

```json
{
  "name": "builder",
  "mode": "exec",
  "role": "implementer",
  "mission": "Create the target artifact while preserving local conventions and keeping scope narrow.",
  "task": "Create or replace output.txt with exactly HELLO.",
  "read_first": [
    "README.md"
  ],
  "writable_scope": [
    "output.txt"
  ],
  "validation": [
    "Ensure the file exists.",
    "Ensure it contains exactly HELLO."
  ],
  "success_criteria": [
    "The file exists.",
    "The file content is exactly HELLO."
  ],
  "return_contract": [
    "Brief summary only."
  ]
}
```

### `resume`

Resumes a previous worker session:

```json
{
  "name": "finisher",
  "mode": "resume",
  "resume_last": true,
  "prompt": "Continue from the previous state and finish validation."
}
```

Or:

```json
{
  "name": "finisher",
  "mode": "resume",
  "session_id": "019cc115-283d-7e82-a318-df785765562d",
  "prompt": "Continue from the previous state and finish validation."
}
```

## Parallel Team Example

```json
{
  "cwd": "<WORKSPACE_ROOT>",
  "output_dir": "subagent-runs",
  "skip_git_repo_check": true,
  "defaults": {
    "sandbox": "workspace-write",
    "reasoning_effort": "low"
  },
  "agents": [
    {
      "name": "asset-a",
      "role": "generator",
      "mission": "Produce the first independent output and stop after validating it.",
      "task": "Reply with exactly: ASSET-A",
      "skills": [
        "codex-subagent-orchestrator"
      ],
      "return_contract": [
        "Reply with exactly: ASSET-A"
      ]
    },
    {
      "name": "asset-b",
      "role": "generator",
      "mission": "Produce the second independent output and stop after validating it.",
      "task": "Reply with exactly: ASSET-B",
      "skills": [
        "codex-subagent-orchestrator"
      ],
      "return_contract": [
        "Reply with exactly: ASSET-B"
      ]
    }
  ]
}
```

## Stage-Based Parallel Pattern

When `execution_mode` is `parallel`, workers are grouped by `stage`:

- workers in the same stage run in parallel
- later stages wait for earlier stages to finish

Use this when you want independent implementers first and a final read-only review after they finish.

```json
{
  "cwd": ".",
  "cwd_resolution": "invocation",
  "output_dir": "subagent-runs/parallel-build-review",
  "skip_git_repo_check": true,
  "execution_mode": "parallel",
  "requested_deliverables": [
    "alpha.txt",
    "beta.txt"
  ],
  "supervisor_only": true,
  "require_final_read_only_review": true,
  "material_issue_strategy": "fixer_then_rereview",
  "shared_directive_mode": "hybrid",
  "defaults": {
    "model": "gpt-5.4",
    "sandbox": "workspace-write",
    "reasoning_effort": "low",
    "prompt_profile": "compact",
    "response_style": "compact",
    "max_response_lines": 3
  },
  "agents": [
    {
      "name": "alpha-builder",
      "kind": "implementer",
      "stage": 1,
      "task": "Create or replace alpha.txt with exactly ALPHA.",
      "writable_scope": [
        "alpha.txt"
      ],
      "validation": [
        "Ensure alpha.txt exists.",
        "Ensure alpha.txt contains exactly ALPHA."
      ]
    },
    {
      "name": "beta-builder",
      "kind": "implementer",
      "stage": 1,
      "task": "Create or replace beta.txt with exactly BETA.",
      "writable_scope": [
        "beta.txt"
      ],
      "validation": [
        "Ensure beta.txt exists.",
        "Ensure beta.txt contains exactly BETA."
      ]
    },
    {
      "name": "parallel-reviewer",
      "kind": "reviewer",
      "stage": 2,
      "sandbox": "read-only",
      "task": "Review alpha.txt and beta.txt for correctness and scope compliance.",
      "read_first": [
        "alpha.txt",
        "beta.txt"
      ],
      "validation": [
        "Check both files exist.",
        "Check alpha.txt contains exactly ALPHA.",
        "Check beta.txt contains exactly BETA."
      ]
    }
  ]
}
```

## Output Files

For each worker, the launcher writes:

- `<name>.stdout.log`
- `<name>.stderr.log`
- `<name>.prompt.txt` when `write_prompt_files` is true

If `output_last_message_file` is omitted, the launcher also writes:

- `<name>.last.txt`

inside the `output_dir`.

The launcher also writes one manifest file that records:

- the resolved spec path
- the resolved workspace root
- the execution mode
- the stage plan and which workers ran together
- requested versus actual model, sandbox, and reasoning settings
- child session IDs when recoverable
- prompt hashes and prompt file paths
- last-message previews and stderr previews
- structure-first efficiency signals such as worker counts, worker-to-deliverable ratios, and writable/read-only split
- stage counts and max parallel workers per stage
- supervisor-policy evaluation, including whether a final read-only review was present
- worker-level validation failures such as missing required paths or empty required artifacts

When `write_summary_file` is true, the launcher also writes one compact summary file that records:

- worker success or failure
- total prompt characters
- total footer-token counts when recoverable
- structure-first efficiency signals such as workers-per-deliverable and bounded-repair coverage
- stage counts and max parallel workers per stage
- shared directive compression details
- workflow template metadata and rendered context inputs
- workspace bootstrap hook decisions and exit status
- one short line per worker for parent-side handoff
- memory enablement, runtime-file counts, retain/optimize counts, and index chunk totals when a `memory` block is configured

## Memory Block

When the optional top-level `memory` object is present:

- `memory.enabled: false` preserves old behavior and does not scaffold `.codex-memory/`
- `memory.mode` supports `off`, `reference`, `core`, `retrieval`, and `hybrid`
- the launcher writes `.codex-memory/` Markdown files as the source of truth and `index/memory-index.json` as a rebuildable derived index
- worker prompts get a short memory policy plus a generated runtime file path under `.codex-memory/runtime/worker-memory/`
- reviewer and validator workers stay read-only; with `memory.mode: "hybrid"` they default to `core` memory while implementers, fixers, and planners default to `retrieval`

If `debug_log_file` is set, the launcher also writes a lightweight trace of parent-side orchestration events such as process start, timeout, result collection, and manifest write.

When `write_run_archive` is true, the launcher also creates a per-run archive under `archive_root` with this shape:

- `launcher/`
  - spec copy
  - manifest copy
  - summary copy
  - debug-log copy
- `deliverables/`
  - copied requested deliverable files
- `workers/<kind>__<name>/`
  - `worker-metadata.json`
  - `prompt.txt`
  - `stdout.log`
  - `stderr.log`
  - `last.txt`
  - `session.jsonl` when recoverable
- `supervisor/`
  - workspace `AGENTS.md`
  - shared directive source copy when applicable

## Practical Guidance

- Use `/sub` as the user-facing trigger for this orchestration model.
- Use `workflow_file` when you want the repository to version the ticket-handling prompt in `WORKFLOW.md`.
- Keep tracker-derived issue data outside the prompt text itself; pass it through `workflow_context` or `workflow_context_file`.
- Use `workflow_prompt_mode: "prepend"` for implementers and reviewers that still need worker-local constraints such as writable scope and validation.
- Use `hooks.after_create` only for idempotent bootstrap steps such as `git clone ... .` or dependency fetches.
- For mixed parallel-and-review teams, put independent builders in the same `stage` and put the reviewer or validator in a later stage.
- The top-level `cwd` resolves relative to the launcher's current working directory by default. This keeps `cwd: "."` portable even when the spec file itself lives under `subagent-runs/...`.
- Set `cwd_resolution: "spec"` only when you intentionally want the top-level `cwd` to resolve relative to the spec file directory.
- Prefer relative top-level paths such as `cwd: "."` and `output_dir: "subagent-runs"` when you want the spec to stay portable across extracted workspaces.
- Absolute paths are allowed, but they should be treated as deployment-specific rather than reusable defaults.
- Keep worker prompts narrow.
- Use `read-only` for reviewers and validators unless they truly need write access.
- Default to `shared_directive_mode: "hybrid"` when you want full instructions on implementers/fixers but compact instructions on reviewers, validators, planners, and read-only custom workers.
- Prefer `shared_directive_mode: "reference"` only when you intentionally want workers to reopen a local directive file instead of receiving inline instructions.
- Use `shared_directive_mode: "compact"` when you want a short inlined contract instead of a file reference.
- Prefer `response_style: "compact"` plus a small `max_response_lines` value for routine workers.
- For `/sub` implementation work, set `requested_deliverables`, enable `supervisor_only`, and keep `require_final_read_only_review` enabled.
- For `custom` or nested-orchestrator workers, set `required_paths` and preferably `required_non_empty_paths` to the files that prove the nested team actually succeeded.
- Use `required_paths` when a worker exiting with code `0` is not enough to prove success.
- Keep `write_run_archive: true` for work you may need to audit later.
- Let the parent choose team size autonomously.
- Give each worker a unique `name`.
- Use `workspace-write` unless broader access is genuinely needed.
- Use `resume` only when the prior session context is worth preserving.
- Prefer the parent agent to merge results rather than asking workers to merge each other.
- Keep the manifest and `last.txt` files unless the user explicitly wants a cleanup pass.
- If you store generated specs under `subagent-runs/...`, keep `cwd: "."` and launch from the workspace root so the manifest still points to the real workspace root.
- If a reviewer finds a material issue, create a bounded fixer worker and then re-run review on the repaired artifact instead of patching deliverables directly in the parent.
- If you must bypass the launcher and call `codex exec` directly, keep cost controls explicit: pass `-m` when model choice matters and pass `-c 'model_reasoning_effort="low"'` for routine workers unless task risk justifies more.
