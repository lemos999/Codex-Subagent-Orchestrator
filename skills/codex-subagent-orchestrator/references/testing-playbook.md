# Testing Playbook

## Purpose

Use this playbook when you need to validate the launcher after edits or hand the skill to another session for replay.

## What Good Looks Like

A healthy launcher run should produce:

- the expected worker output files
- one `orchestration-manifest.json`
- one prompt file per worker
- one `last.txt` file per worker unless overridden
- stable absolute paths in stdout, stderr, and manifest entries
- a manifest `workspace_root` that still points at the real workspace root even when the spec file lives under `subagent-runs/...`

## Recommended Test Order

1. Run a single sequential write worker.
2. Run two independent workers in parallel.
3. Run two independent writers in parallel and a read-only reviewer in a later stage.
4. Run a nested-spec root-safety check where the spec file itself lives under `subagent-runs/...` but `cwd: "."` still resolves to the real workspace root.
5. Run a memory-enabled launcher spec and confirm `.codex-memory/runtime/worker-memory/*.md` plus manifest memory metrics are written.
6. Re-run at least one spec with `memory.enabled: false` and confirm prompt files and summaries still work without memory injection.
7. Re-run at least one spec with an absolute non-ASCII workspace path if you need portability confidence for extracted folders.
8. Only after those pass, test a full `/sub` request from chat.

## Template Specs

Use the bundled templates under `assets/spec-templates/`:

- `minimal-write.template.json`
- `parallel-two-files.template.json`
- `parallel-implementers-reviewer.template.json`
- `implementer-reviewer.template.json`
- `memory-enabled.template.json`
- `nested-root-safety.template.json`

The bundled templates now default to:

- `cwd: "."`
- `cwd_resolution: "invocation"`

That means you can usually copy them into the workspace root and run them without editing a path first.

Only use an explicit absolute `cwd` when you are intentionally testing deployment-specific portability. In that case, use forward slashes or escaped backslashes so the JSON stays valid.

If you are debugging the launcher itself, set:

- `timeout_seconds`
- `debug_log_file`

in the spec before running.

## Command Pattern

```powershell
& ".\\skills\\codex-subagent-orchestrator\\scripts\\start-codex-subagent-team.ps1" `
  -SpecPath ".\\your-spec.json" `
  -AsJson
```

## Validation Checklist

- The manifest `workspace_root` and worker `cwd` match the intended workspace.
- Parallel workers that should finish before review are in an earlier stage than the reviewer or validator.
- The manifest records `invocation_cwd`, `cwd_requested`, and `cwd_resolution_mode` so you can explain how the workspace root was chosen.
- Relative-path specs and any deployment-specific absolute-path specs both resolve to the same intended workspace when you test portability.
- Every worker has a `prompt.txt`.
- Every worker has a `last.txt` or an explicit override path.
- The run produces `orchestration-summary.md` unless `write_summary_file` was disabled.
- Requested versus actual model, sandbox, and reasoning fields make sense.
- Child session IDs are captured when stdout exposes them.
- No worker writes outside its declared scope.
- The manifest `stage_plan` matches the intended parallel grouping.
- If `debug_log_file` is enabled, the trace reaches `manifest_written`.
- If a recovery run creates a second delivery attempt, run a reviewer worker against the final successful artifact before accepting it.
- If memory is enabled, confirm the reviewer still runs with `read-only`, the runtime memory file exists only for non-`off` workers, and manifest `memory.*` fields match the run.

## Efficiency Checklist

- Use `low` reasoning for routine writer and reviewer workers.
- Default to `shared_directive_mode: "hybrid"` for mixed `/sub` teams so implementers/fixers keep the full contract while reviewers, validators, planners, and read-only custom workers stay compact.
- Prefer `shared_directive_mode: "reference"` only when you explicitly want workers to reopen the local directive file.
- Use `shared_directive_mode: "compact"` when you want a short inlined contract and do not want to rely on a file reference.
- Prefer compact response style and consume `orchestration-summary.md` before reading raw logs.
- On Windows PowerShell, treat `stderr` as diagnostic only; use `last.txt`, reviewer output, manifest metadata, and footer tokens as the primary truth sources when logs look mojibaked.
- Pass `-m` explicitly when you care about reproducibility.
- Avoid replaying full worker stdout into the parent context.
- Keep the team small unless the task has real parallel branches.

## Fallback Rule

If the launcher itself fails:

1. keep the failed spec file
2. keep the manifest or error output if any
3. record the failure reason
4. pivot to direct `codex exec` with explicit cost controls
5. do not pretend the launcher path worked

Recommended direct fallback pattern for a routine worker:

```powershell
Get-Content -Raw .\worker.prompt.txt | codex exec `
  -C . `
  --skip-git-repo-check `
  -m gpt-5.4 `
  -s workspace-write `
  -c 'model_reasoning_effort="low"' `
  -o .\subagent-runs\worker.last.txt `
  -
```
