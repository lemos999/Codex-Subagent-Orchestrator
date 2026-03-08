# Orchestration Workflow

## Purpose

This workflow is for a parent Codex instance that should act as a supervisor, not as the only implementer.

The parent should break work into bounded worker runs and use `codex exec` as the execution engine for those workers.

If the user starts with `/sub`, treat that as an explicit instruction to use this workflow.

## Parent-Worker Split

### Parent responsibilities

- classify the task
- decide whether to use one worker or a team
- choose skills for the workers
- define each worker boundary
- choose sandbox and reasoning effort per worker
- choose whether the team should run in parallel or sequentially
- capture outputs without dragging full raw transcripts back into parent context
- preserve a per-run archive with worker-specific evidence folders
- validate results
- resume, retry, or stop
- avoid direct edits to requested deliverable files when a bounded worker can perform the change

### Worker responsibilities

- execute one bounded task
- use the required skills
- stay within the writable scope
- return the requested output contract
- stop after validation

## Workflow Stages

### 1. Classify the request

Determine:

- whether the request entered through `/sub`
- whether `/sub` implies `team mode` or `queue mode`
- task type
- required files
- writable scope
- expected output
- risk level
- whether workers can run in parallel

Route to `queue mode` when the request implies repeated polling, background work, unattended local backlog execution, or unattended tracker execution. Otherwise route to `team mode`.

### 2. Choose the team shape

This stage applies only after the parent has chosen `team mode`.

Use one worker for:

- a single bounded edit or generation step

Use autonomous team sizing:

- `1` worker for narrow tasks
- `2` workers for implementer/verifier or two independent outputs
- `3` workers for planner/implementer/reviewer
- `4+` workers only when parallelism materially improves throughput and merge risk remains low

Use parallel workers for:

- independent tasks with clean output boundaries
- compare-and-choose tasks
- separate analysis and implementation tracks
- same-stage independent workers followed by a later review stage

Use staged workers for:

- planner -> implementer
- implementer -> reviewer
- extractor -> transformer -> verifier

### 3. Select skills

Choose the smallest useful skill set.

Recommended pattern:

- one primary workflow skill
- one secondary domain skill if needed

Avoid large skill bundles unless the task truly needs them.

### 4. Build each worker contract

A worker contract should include:

- task
- files to inspect first
- writable scope
- required skills
- output contract
- validation instructions
- stop condition
- success-proof paths when exit code alone is not enough

You can express that contract in two ways:

- a direct `prompt` string
- structured launcher fields such as `task`, `skills`, `read_first`, `writable_scope`, `validation`, `return_contract`, `required_paths`, and `required_non_empty_paths`

Prefer structured fields when the parent wants repeatable orchestration from JSON specs.

For `custom` workers that supervise nested teams, always add success-proof paths:

- `required_paths` for files that must exist
- `required_non_empty_paths` for files that must exist and contain real output

Use these for nested specs, nested summaries, reviews, and promised deliverables so a custom worker cannot be counted as successful while its nested team actually failed.

For `/sub` implementation specs, also set top-level policy fields so the launcher can reject unsafe team shapes before any worker starts:

- `requested_deliverables`
- `supervisor_only: true`
- `require_final_read_only_review: true`
- `material_issue_strategy: "fixer_then_rereview"`

When a workspace has an `AGENTS.md`, treat it as the shared worker contract by default. Add only the role-specific delta and bounded task details on top of it.

For routine workers, prefer a cheaper contract instead of inlining a long directive every time. Use:

- `shared_directive_mode: "reference"` when the worker can read the workspace `AGENTS.md` directly
- `shared_directive_mode: "compact"` when the worker should receive a short inlined contract
- `response_style: "compact"` when the worker should return a short verification summary
- the generated orchestration summary file instead of raw worker transcripts when updating the parent

Recommended prompt shape:

```text
Treat the following as mandatory operating instructions for this run.

You are a principal software engineer, reviewer, and production architect whose goal is to turn every request into code that improves code health, not merely code that runs once.

Role:
<worker role>

Mission:
<role-specific mission>

You are a bounded codex exec worker in the workspace root.

Task:
<one concrete task>

Use these skills if they trigger:
- <skill-name>

Read first:
- <file>

You may modify only:
- <file or directory>

Validation:
- <validation rule>

Return:
- <summary or structured output>

Do not ask questions. Do not expand scope.
```

### 5. Choose execution settings

Recommended default:

- sandbox: `workspace-write`
- reasoning: `low`
- execution mode: `parallel` only when file scopes are independent, otherwise `sequential`

Recommended reviewer default:

- sandbox: `read-only`
- reasoning: `low`
- response style: `compact`

Choose reasoning efficiently. Do not treat `/sub` as permission to overuse high reasoning.

Raise reasoning for ambiguity or high-risk edits.

If the parent chooses a model intentionally, pass `-m` explicitly. Do not rely on the current CLI default when reproducibility matters.

Use `danger-full-access` only when the worker cannot complete its task inside workspace limits.

### 6. Launch workers

Use direct `codex exec` for simple single-worker runs.

Use `scripts/start-codex-subagent-team.ps1` for:

- multiple workers
- repeatable orchestration
- per-worker logs and final-message capture
- prompt file retention
- a machine-readable manifest with requested versus actual runtime details
- a run archive with copied launcher files, deliverables, and per-worker evidence folders
- stage-based mixed parallel execution where workers in the same stage run together and later stages wait
- preflight validation that reviewers remain read-only and that the last writable worker is followed by a final read-only review when the spec requires it
- workflow-driven issue execution where `WORKFLOW.md` and `AGENTS.md` are auto-detected after a bootstrap hook creates the workspace

Use `scripts/start-codex-subagent-queue.ps1` when:

- work should be pulled from a tracker instead of being launched manually one spec at a time
- the work source is a local `queue.json` or `tasks/` directory rather than a chat message
- you want one workspace per issue
- you want bounded concurrent issue dispatch over the existing launcher
- you want queue state, retries, and per-issue launcher evidence preserved on disk

If the launcher path fails and the parent pivots to direct `codex exec`, preserve the intended cost controls on the fallback path:

- keep the prompt file on disk
- pass `-m` explicitly when model choice matters
- pass `-c 'model_reasoning_effort="low"'` for routine workers unless the task risk justifies more
- keep `-o` enabled so the worker's final message is preserved

### 6A. Launch queue mode

Use `scripts/start-codex-subagent-queue.ps1` when the parent classified the request as ongoing tracker work.

Queue-mode parent responsibilities:

- build a queue config instead of a one-shot worker spec
- point tracker config at a local `queue.json`, local `tasks/` directory, or an optional external adapter
- set one workspace root for issue-specific workspaces
- set `hooks.after_create` for workspace bootstrap
- let the downstream launcher auto-detect `AGENTS.md` and `WORKFLOW.md` from the created workspace
- preserve queue state, queue report, and per-issue launcher outputs for audit

### 7. Validate results

The parent should check:

- expected files exist
- files are non-empty when required
- worker scope was respected
- output contract was satisfied
- follow-up work is actually needed
- if the parent had to recover from a wrong delivery path, wrong writable scope, or wrong workspace root, the final successful artifact is reviewed again by a reviewer or verifier worker before acceptance
- if a reviewer reported a material issue, the parent used a bounded fixer worker rather than patching the deliverable directly

### 7A. Measure efficiency correctly

Do not treat absolute token totals as the only efficiency metric.

Prefer a structure-first view:

- how much parent intervention was required
- whether the first accepted artifact came from the first clean launcher path or from a recovery path
- how many full reruns happened
- whether reviewer findings were handled by a bounded fixer loop instead of a full implementation rerun
- how many workers were used per requested deliverable
- whether read-only review coverage remained intact after the last writable worker

Use token totals as a secondary comparison signal after those structural indicators.

### 8. Resume or retry

Resume when prior worker context is valuable.

Retry fresh when:

- the prompt was wrong
- the scope was wrong
- the sandbox was wrong
- the worker drifted

When a recovery run changes the delivery location or corrects the workspace root, treat that recovery output as a fresh implementation candidate. Do not accept it only on implementer self-validation. Run a reviewer or verifier worker against the final accepted artifact.
When a reviewer finds a material issue in a deliverable, prefer a staged repair loop:

- reviewer reports the issue
- parent launches a bounded fixer worker
- reviewer or verifier runs again against the repaired artifact

Do not let the parent patch the deliverable directly unless the user explicitly asks for a manual parent-side intervention.

## Team Patterns

## Pattern A: Single worker

Use for one direct deliverable.

## Pattern B: Parallel independent workers

Use for independent tasks such as:

- one worker per file
- one worker per asset
- one worker per experiment branch

The parent should merge only after all workers finish and outputs are validated.

When you need a final reviewer, put the parallel builders in the same stage and place the reviewer or validator in a later stage.

## Pattern C: Planner plus implementers

Use when one worker first produces a bounded work plan or decomposition and later workers implement individual items.

The parent should approve the plan before launching the later workers.

## Pattern D: Implementer plus verifier

Use when the implementation is straightforward but correctness matters.

One worker edits. One worker reviews or verifies.

The parent decides whether to accept or re-run.

If the parent re-runs the implementer after a recovery step, the verifier should run again against the recovered final artifact.

## Pattern E: Implementer -> Reviewer -> Fixer -> Reviewer

Use when:

- the reviewer finds a bounded, repairable issue
- the parent wants to stay in supervisor mode
- the repaired artifact still needs an independent final check

Recommended roles:

- implementer: creates the initial artifact
- reviewer: identifies material issues without editing
- fixer: repairs only the reviewer-approved scope
- reviewer or verifier: re-checks the repaired final artifact

## Reasoning Policy

- `low`: routine file generation, narrow edits, straightforward implementation
- `medium`: mixed read/write tasks or moderate ambiguity
- `high`: complex refactors or tasks with tricky tradeoffs
- `xhigh`: rare deep-analysis cases

Default worker choice:

```text
model_reasoning_effort = "low"
```

Model selection should follow the same efficiency rule: use the cheapest model that safely fits the worker's task, unless the user explicitly requests a different model strategy.

Prompt selection should follow the same rule:

- `full`: only when the worker genuinely needs the whole directive inlined
- `compact`: default for routine writer, reviewer, and validation workers

## Output Policy

Use `-o` when the parent wants the final worker answer preserved on disk.

Use `--json` when another process or parent orchestration needs event-level visibility.

Use `--output-schema` when the parent requires deterministic structured output.

Do not immediately paste large child stdout logs into the parent conversation. Prefer one of:

- `last.txt`
- `orchestration-summary.md`
- a manifest entry
- a structured schema
- a short extracted summary

## Stop Rule

The parent should remain the final authority.

Workers do not own the whole request. They own bounded execution slices.
