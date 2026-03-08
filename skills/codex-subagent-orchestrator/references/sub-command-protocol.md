# `/sub` Command Protocol

## Purpose

This protocol defines how the parent Codex instance should interpret requests that begin with `/sub`.

## Trigger Rule

When the user message begins with `/sub`, treat it as an explicit request to enter supervisor mode and delegate execution to one or more `codex exec` workers.

Interpret:

```text
/sub <request>
```

as:

- orchestration is required
- direct parent-only execution is not the preferred path
- the parent should choose and supervise the correct orchestration shape

The parent must route `/sub` to one of two execution paths:

- `team mode`: one-off bounded work using `start-codex-subagent-team.ps1`
- `queue mode`: unattended tracker-driven work using `start-codex-subagent-queue.ps1`

Default routing:

- choose `team mode` for finite requests such as:
  - fix or implement a specific task
  - work one ticket or one deliverable
  - review or verify a bounded artifact
  - generate one bounded output
- choose `queue mode` for ongoing requests such as:
  - watch a local queue file
  - watch a local tasks folder
  - keep processing tickets as they arrive
  - run unattended in the background
  - handle multiple tracker issues over time
  - maintain one workspace per issue automatically

## Parent Actions

When `/sub` is used, the parent should:

1. strip the `/sub` prefix
2. interpret the remaining text as the true task request
3. decide whether the request should run in `team mode` or `queue mode`
4. if `team mode`, decide whether the task needs one worker or a team
5. choose worker roles autonomously
6. choose model, sandbox, and reasoning per worker
7. launch and supervise the workers or the queue runner
8. validate outputs before reporting back
9. preserve enough evidence for later review: manifest, prompt files, worker summaries, queue state, and per-run archives
10. if the parent recovers from a wrong delivery path or wrong workspace root, run the reviewer or verifier again against the final successful artifact before accepting it
11. if a reviewer finds a material issue, launch a bounded fixer worker instead of patching the deliverable directly in the parent
12. when building a launcher spec for deliverable work, include `requested_deliverables`, `supervisor_only: true`, `require_final_read_only_review: true`, and `material_issue_strategy: "fixer_then_rereview"` so unsafe team shapes fail fast
13. when building a queue config, prefer one workspace per issue, `hooks.after_create`, and auto-detected `AGENTS.md`/`WORKFLOW.md`

## Team Sizing Rule

This section applies after `/sub` has already resolved to `team mode`.

The team should be chosen autonomously.

Use:

- `1` worker when one bounded worker can finish the task cleanly
- `2` workers when one worker should implement and one should verify, or when two outputs are cleanly independent
- `3` workers when planning, implementation, and review should be separated
- `4+` workers only when the work is truly parallelizable and file-level merge risk remains manageable

Do not add workers just because `/sub` was used. Add workers only when team structure improves execution quality or throughput.

## Worker Contract Rule

Every worker should receive:

- the shared operating contract from workspace `AGENTS.md` when available
- a role-specific mission from the parent
- a bounded task definition
- explicit writable scope
- validation instructions
- a return contract

Reviewers and validators should default to `read-only` unless a narrower exception is explicitly justified.

## Efficiency Rule

`/sub` does not mean "use maximum reasoning everywhere."

The parent should adjust reasoning efficiently:

- `low` for routine execution workers
- `medium` for moderate ambiguity
- `high` only when the worker's decision burden is genuinely complex
- `xhigh` only for exceptional cases

The same rule applies to model choice. Use the cheapest model that still safely fits the worker's task.

Do not evaluate orchestration quality by absolute token totals alone.

Prefer structure-first efficiency signals:

- keep parent intervention small
- avoid unnecessary full reruns
- prefer reviewer -> fixer -> reviewer loops over rerunning the whole team
- keep worker count proportional to requested deliverables
- use token totals only as a secondary comparison signal

If the parent intentionally chooses a model, it should pass `-m` explicitly so the run is reproducible.

## Parallel Rule

Run workers in parallel only when:

- they are independent
- they do not compete for the same writable scope
- the parent can merge results deterministically

When the launcher is used, prefer same-stage parallel workers plus a later-stage reviewer or validator instead of putting writers and reviewers in the same stage.

If those conditions are not met, use staged execution instead.

## Queue Rule

Choose `queue mode` when the request implies repetition, monitoring, or unattended tracker work.

In `queue mode`, the parent should:

- prepare a queue config instead of a one-off team spec
- prefer local `tracker.kind = "local-json"` or `tracker.kind = "local-files"` when the user did not explicitly ask for an external tracker
- use one workspace per issue
- prefer `hooks.after_create` for workspace bootstrap
- let the downstream launcher auto-detect `AGENTS.md` and `WORKFLOW.md` after bootstrap
- preserve `queue-state.json`, `queue-report.md`, per-issue generated specs, per-issue logs, and per-issue launcher outputs

Do not use `queue mode` for a single bounded request unless the user explicitly wants polling or repeated dispatch.

## Reporting Rule

The parent remains the final reporting authority.

Workers produce bounded outputs. The parent integrates, validates, and reports the final result.

When the launcher path fails, preserve the failed spec and fallback reason, then pivot cleanly to direct `codex exec` rather than silently switching behavior.

If the parent pivots to direct `codex exec`, it should preserve the intended worker settings explicitly:

- pass `-m` when the model choice matters
- pass `-c 'model_reasoning_effort="low"'` for routine workers unless the task risk justifies more
- keep `-o` so the final worker message is preserved on disk
