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
- execution mode
- review timing or review policy
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

## `status.md`

Record:

- run id
- current stage
- active agents
- waiting agents
- completed agents
- failed agents
- current blocker, if any
- approved fix scope, if any
- next planned action

Update this file whenever the stage changes or a meaningful worker event occurs.

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
