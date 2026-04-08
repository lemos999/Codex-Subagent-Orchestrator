# Internal `/sub` Testing Playbook

Test the internal-only edition with internal chat-session agents, not with shell launchers.

## Required Regression Matrix

Run these checks before claiming the workflow is stable.

Before runtime tests, verify the imported vendor pack is intact:

- `vendor/agent-skills/skills/` contains all 20 upstream skills
- `vendor/agent-skills/agents/` contains all 3 specialist personas
- `vendor/agent-skills/references/` contains all 4 upstream checklists
- `skills/agent-skills-integration/agent-skill-routing.md` references every imported skill at least once

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

### 6. Approval gate

Prove that the pre-launch report appears before worker launch and that the run pauses unless blanket authority exists.

Check:

- worker count reported
- serial versus parallel plan reported
- per-worker model and reasoning reported
- review timing reported
- launch is skipped until approval unless authority already exists

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
