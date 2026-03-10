# Parent Session Phase Spec Format

## Purpose

`scripts/start-codex-parent-session.ps1` prepares a parent-session run directory from a JSON spec.

The script does not launch child workers. It writes compact phase files, a manifest, and checkpoint templates so the parent session can execute the workflow with minimal repeated context.

## Top-Level Shape

```json
{
  "cwd": ".",
  "cwd_resolution": "invocation",
  "output_dir": "parent-session-runs/refactor-parent-only",
  "task": "Replace the current subagent-first workflow with a parent-session-first workflow.",
  "context": [
    "Keep the existing subagent path only as a compatibility path.",
    "The parent-only workflow should become the documented default."
  ],
  "constraints": [
    "Do not launch codex exec workers for the new default workflow.",
    "Keep prompts and summaries compact."
  ],
  "acceptance_criteria": [
    "Add a parent-session local skill.",
    "Add a parent-session preparation script.",
    "Update root docs to make the parent-only path the default."
  ],
  "requested_deliverables": [
    "README.md",
    "AGENTS.md",
    "skills/codex-parent-session-orchestrator/"
  ],
  "shared_directive_mode": "reference",
  "defaults": {
    "reasoning_effort": "low",
    "response_style": "compact",
    "max_response_lines": 6
  },
  "phases": [
    {
      "name": "scan",
      "role": "planner",
      "mode": "read-only",
      "goal": "Inspect the repo shape and identify the smallest safe refactor surface.",
      "read_first": [
        "README.md",
        "AGENTS.md"
      ],
      "outputs": [
        "task-brief.md",
        "session-summary.md"
      ],
      "validation": [
        "List the files that define the current workflow.",
        "Capture any compatibility constraints."
      ]
    }
  ]
}
```

## Top-Level Fields

| Field | Required | Meaning |
|---|---|---|
| `cwd` | yes | Workspace root for the run |
| `cwd_resolution` | no | `invocation` or `spec`; defaults to `invocation` |
| `output_dir` | no | Directory where the script writes the run scaffold |
| `manifest_file` | no | Optional override for the manifest path |
| `task_brief_file` | no | Optional override for `task-brief.md` |
| `active_context_file` | no | Optional override for `active-context.md` |
| `checkpoint_file` | no | Optional override for `session-summary.md` |
| `phase_checklist_file` | no | Optional override for `phase-checklist.md` |
| `phase_directory` | no | Optional override for the per-phase file directory |
| `task` | yes | Concrete task statement for the run |
| `context` | no | Short background facts worth keeping |
| `constraints` | no | Hard boundaries or non-goals |
| `acceptance_criteria` | no | Observable success rules |
| `requested_deliverables` | no | Files or directories expected to change or be created |
| `shared_directive_file` | no | Shared directive file to reference or inline |
| `shared_directive_text` | no | Inline shared directive text |
| `inject_shared_directive` | no | Disable shared directive injection when false |
| `shared_directive_mode` | no | `full`, `compact`, `reference`, or `disabled`; defaults to `reference` |
| `defaults` | no | Default phase settings |
| `phases` | yes | Ordered phase definitions |

## Defaults Object

Supported fields:

- `reasoning_effort`
- `response_style`
- `max_response_lines`
- `mode`

These are inherited by phases unless the phase overrides them.

## Phase Object

Required fields:

- `name`
- `goal` or `task`

Optional fields:

- `role`
- `mode`
- `mission`
- `read_first`
- `focus_paths`
- `writable_scope`
- `outputs`
- `validation`
- `success_criteria`
- `stop_when`
- `reasoning_effort`
- `response_style`
- `max_response_lines`

## Generated Files

The script writes:

- `task-brief.md`
- `active-context.md`
- `phase-checklist.md`
- `session-summary.md`
- `parent-session-manifest.json`
- one phase file per entry under `phases/`

## Practical Guidance

- Keep phases small and ordered.
- Use `read-only` for `scan`, `plan`, `verify`, and `review`.
- Use `write` only for `implement` and bounded `fix` phases.
- Prefer one compact validation list per phase.
- Treat `session-summary.md` as the only long-lived handoff file.
