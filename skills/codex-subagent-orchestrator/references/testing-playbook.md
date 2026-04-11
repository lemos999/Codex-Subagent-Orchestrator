# Internal `/sub` Testing Playbook

Test the internal-only edition with internal chat-session agents, not with shell launchers.

## Required Regression Matrix

Run these checks before claiming the workflow is stable.

Before runtime tests, verify the imported vendor pack is intact:

- `vendor/agent-skills/skills/` contains all 20 upstream skills
- `vendor/agent-skills/agents/` contains all 3 specialist personas
- `vendor/agent-skills/references/` contains all 4 upstream checklists
- `skills/agent-skills-integration/agent-skill-routing.md` references every imported skill at least once

### 0. Hard plan-first gate

Prove that every coding request triggers the understanding report and explicit approval gate before implementation, even when the request is tiny, urgent, or explicitly says to code immediately.

Check:

- no code, patch, or code-level implementation guidance appears before approval
- no writable worker launches before approval
- "do it now", blanket authority, or tiny scope do not bypass the gate
- tiny follow-up edits and repair steps do not bypass the gate or escape the active approved plan record
- follow-up material change requests reopen the gate before implementation resumes
- the approved full PLAN is written under repo-root `plan/`
- the full approved PLAN is not dumped into chat as a Markdown code block by default
- the active plan file uses a time-sortable versioned filename with an explicit plan-type marker
- the active plan file records status, completion state, completed work, remaining work, blockers, and next step
- later implementation or review progress updates refresh the active plan file instead of leaving the plan stale
- `orchestration-plan.md`, `status.md`, and the active file under `plan/` all point to the same active plan artifact
- the recorded active plan path exists on disk during the run
- when a material plan revision creates a new version, the new version becomes the active artifact and the prior version is marked clearly as related or superseded

### 1. Single bounded implementer

Prove that a narrow task stays on one implementer and reaches acceptance without unnecessary extra roles.

Check:

- one implementer chosen
- no redundant reviewer attached
- acceptance recorded

### 2. Parallel independent implementers

Prove that two independent writable scopes can run in parallel and still converge cleanly through parent integration.

Check:

- two implementers launched in the same stage
- writable scopes are disjoint
- the parent lands the accepted changes into the primary workspace
- one late reviewer or validator accepts the merged result in the primary workspace
- status reporting names both active workers while they run

### 3. Shared-state serialization

Prove that overlapping, nested, or order-dependent work does not fan out by mistake.

Check:

- one implementer is kept
- the parent can explain why parallelism was rejected

### 4. Reviewer throttling

Prove that the plan does not attach one reviewer after every writer by default.

Check:

- review is late by default
- redundant final reviewers are suppressed
- early review happens only with a clear justification

### 5. Bounded fixer loop

Prove that a material review finding triggers one bounded fixer and then re-review or re-validation.

Check:

- fixer scope is named explicitly
- the fix does not silently expand the writable surface
- acceptance happens only after the repaired artifact is rechecked
- the active plan artifact is refreshed before writable repair work begins
- `status.md` and the active plan file stay aligned on version, status, and next step after the repair path advances
- the active plan artifact's scoreboard is refreshed when the repair path changes likely satisfaction state

### 6. Approval gate

Prove that the pre-launch report appears before worker launch and that coding runs still pause for the mandatory plan-first gate.

Check:

- worker count reported
- execution mode reported as `serial`, `parallel`, or `mixed`
- per-worker model and reasoning reported
- review timing reported
- launch is skipped until the understanding-report approval gate is satisfied
- the pre-launch evidence names the current score state for coding runs

### 6.5 Scoreboard continuity

Prove that the active plan artifact keeps a usable score log through normal execution and `/sub` delegation.

Check:

- the active plan artifact contains a `Scoreboard` section
- an explicit user score is recorded as authoritative when one is given
- when the user gives no score, the workflow continues with a conservative provisional score instead of blocking
- no fixed hardcoded fallback number is required by the docs
- unchanged score is treated as the current overall rating staying the same, not as zero new points
- when an explicit user score replaces a provisional score with the same numeric value, the score-history log still preserves both states
- `orchestration-plan.md`, `status.md`, and the active plan artifact stay aligned on the current score state during delegated runs

### 7. Queue mode

Prove that backlog handling remains in-session and evidence is preserved per issue.

Check:

- `queue-state.md` exists
- each issue gets its own evidence folder
- the workflow does not claim detached unattended processing

## Auditing For Regressions

After rewriting the workflow, audit the repository for:

- `codex exec`
- external shell wrappers
- Python launch instructions
- PowerShell launcher instructions
- detached watcher or background-run claims

Any remaining mention of those as the primary `/sub` path is a regression.

Also audit for integration regressions:

- imported vendor skills exist on disk
- parent and `/sub` docs both reference `skills/agent-skills-integration/agent-skill-routing.md`
- that routing file is the only canonical imported-skill mapping and local orchestrator docs do not maintain divergent default tables
- the local orchestrators still keep approval, evidence, and parent-landing authority instead of outsourcing those concerns to upstream skill prose
- worker briefs and parent phases still force imported-skill selection to stay minimal and justified instead of loading the full vendor pack by habit

## Minimum-Set Discipline Checks

When validating active use of `agent-skills`, verify all of the following:

- the parent or worker selected a bounded imported skill set instead of attaching many plausible skills
- the parent or worker wrote the judgment criteria first instead of starting from a hardcoded fixed stack
- the selected imported skills match the active role or phase core first
- task-shaped or risk-shaped add-ons were added only when the task surface or acceptance bar truly required them
- every selected imported skill has a short rationale that says what behavior or check it changes
- imported skill count is judged by justification quality, not by a rigid ceiling; a larger set is acceptable when the written criteria prove it is necessary

## Suggested Internal-Agent Validation Pattern

Use internal agents to validate the workflow itself:

- one explorer to audit for leftover external-process guidance
- one explorer to audit whether approval, visibility, adaptive sizing, and reviewer throttling are all still specified
- one or more worker agents to produce bounded change proposals in forks, followed by parent landing and final review in the primary workspace

Preserve the audit notes under `subagent-runs/<test-run-id>/`.
