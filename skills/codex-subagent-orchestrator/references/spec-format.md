# Internal `/sub` Run Kit Format

The internal-only edition uses a Markdown run kit on disk instead of an external launcher JSON spec.

Recommended run directory:

```text
subagent-runs/<run-id>/
|-- orchestration-plan.md
|-- status.md
|-- worker-briefs/
|   |-- <worker>.md
|   `-- ...
|-- results/
|   |-- <worker>.md
|   `-- ...
|-- review-verdict.md
`-- acceptance.md
```

Use the templates under `skills/codex-subagent-orchestrator/assets/run-templates/` when you want a deterministic starting point.

## `orchestration-plan.md`

Record:

- request summary
- user constraints
- delegation justification
- approval status
- approval reason
- worker count
- execution mode: `serial | parallel | mixed`
- review timing or review policy
- approved plan file path in `plan/` for coding runs
- approved plan type, version, and current status for coding runs
- current score and score source from the active plan for coding runs
- for each worker:
  - worker id
  - role
  - mission
  - writable scope
  - model
  - reasoning effort
  - stage
- acceptance strategy
- evidence paths

Use `mixed` when the run has serial stages overall but one or more stages contain parallel branches.

Authority split for coding runs:

- `status.md` is the authoritative source for current orchestration state.
- the active file under `plan/` is the authoritative source for approved plan content, plan-progress history, and score history.
- `orchestration-plan.md` is the authoritative source for approved team shape and the initial execution contract.

## `status.md`

Record:

- run id
- current stage
- active plan file, if any
- active plan path verified on disk, if any
- orchestration/status/plan linkage check, if any
- active plan type, if any
- active plan version, if any
- active plan status, if any
- active plan progress state, if any
- current score, if any
- score source, if any
- score last updated, if any
- score maintenance focus, if any
- active agents
- waiting agents
- completed agents
- failed agents
- current blocker, if any
- approved fix scope, if any
- next planned action

Update this file whenever the stage changes and after every writable worker step or any verification, review, repair, or acceptance event that changes plan status, progress, blockers, next action, or score state.

## `worker-briefs/<worker>.md`

Each worker brief should contain:

- shared contract reference to `AGENTS.md`
- role
- mission
- concrete task
- read-first files
- writable scope
- required imported skill paths, if any
- validation steps
- return contract
- stop condition

If the worker is planning, refining a plan, or producing planner-like output, include `skills/plan-mode-default/SKILL.md` and `skills/plan-mode-default/references/coding-plan-prompt-en.md` in `read-first files` by default when those files exist, unless the user explicitly overrides the planning contract format while preserving the understanding-report and explicit-approval gate.
For coding runs, do not launch or record a writable worker stage until the run artifacts show that the understanding-report approval gate has been satisfied and name the approved plan file under `plan/`.
For coding runs, keep `status.md` and the active plan file aligned whenever plan status, progress state, blockers, next step, or score state change.
For coding runs, keep `orchestration-plan.md`, `status.md`, and the active file under `plan/` aligned on the same active path, version, current status, and current score state.

Keep one worker brief per worker.

## `results/<worker>.md`

Each result file should summarize:

- what the worker changed or verified
- whether the work happened in a forked workspace and what the parent still needs to land
- what checks the worker ran
- whether the worker claims success or failure
- any residual risks or blockers

Do not treat worker completion alone as acceptance. For write tasks, worker completion means a candidate change exists and the parent still has to land the accepted result in the primary workspace.

## `review-verdict.md`

Use this when the plan promised review or validation.

Capture:

- reviewer or validator identity
- scope reviewed
- verdict
- material findings
- required fixer scope if needed

Use this artifact to describe the proposed repair boundary, not the currently approved active fix scope.

## `acceptance.md`

This is the final supervisor verdict.

Capture:

- deliverables accepted
- landed changes in the primary workspace
- checks that passed
- review or validation evidence
- remaining risks
- cleanup decision

Do not use this artifact as the active fixer-scope ledger.

## In-Session Queue Extension

For queue mode, add:

```text
subagent-runs/<queue-id>/
|-- queue-state.md
`-- issues/
    `-- <issue-id>/
        |-- orchestration-plan.md
        |-- status.md
        |-- worker-briefs/
        |-- results/
        |-- review-verdict.md
        `-- acceptance.md
```

`queue-state.md` should track:

- backlog order
- current issue
- completed issues
- failed or deferred issues
- retry notes

Queue mode stays inside the current live session and must not be represented as detached background processing.
