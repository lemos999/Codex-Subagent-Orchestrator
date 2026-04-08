# `/sub` Command Protocol

Treat `/sub` as a request for supervised internal delegation.

## Parse

- strip the `/sub` prefix
- treat the remaining text as the actual task request
- keep any explicit user constraints, deadlines, review requirements, or tool limitations

## Plan First

Before any worker starts, the parent must decide:

- whether one worker is enough or whether a team is justified
- whether execution should be serial or parallel
- whether the work should stay inside one issue-sized run or become an in-session queue
- which workers need write access
- where review belongs
- which imported vendor skills each phase or worker actually needs

## Mandatory Pre-Launch Report

Report this to the user before launch:

- request summary
- user constraints
- delegation justification
- approval status and reason
- planned worker count
- serial versus parallel layout
- each worker id, role, mission, writable scope, model, reasoning effort, and stage
- reviewer or validator timing or policy
- acceptance strategy
- evidence paths on disk

Unless the user already granted blanket authority or explicitly said to proceed immediately, pause here for approval.

## Approval Skip Conditions

Skip the pause only when one of these is true:

- the user clearly delegated blanket authority for the run
- the user explicitly said to proceed immediately

Ambiguous urgency is not enough.

## Adaptive Team Rules

Use one implementer when:

- the task is narrow
- the writable surface is shared or nested
- one change depends on another
- a single contract is likely to be touched from multiple sides

Use multiple implementers only when:

- writable surfaces are independent
- outputs can merge without negotiation
- the parent can land accepted changes into the primary workspace without ambiguity
- final acceptance can still be handled by one read-only reviewer or validator

## Adaptive Review Rules

Default to one late read-only reviewer or validator.

Move review earlier only when:

- risk justifies an intermediate gate
- a parallel branch merge needs reconciliation
- a bounded fixer gate is cheaper than a broad rerun

Do not add a reviewer after every writer.

Suppress redundant final reviewers and validators when one acceptance pass is enough.

## Model And Reasoning Rules

Choose model and reasoning only after the plan exists.

Base the choice on:

- ambiguity
- failure cost
- writable scope
- dependency depth
- verification burden
- review burden

Choose from the internal agent capabilities available in the active session. Do not rely on repository-local hardcoded model catalogs or fallback priority lists.

## Imported Skill Selection Rules

Choose imported vendor skills only after role, writable scope, and review timing are fixed.

Use this adaptive algorithm:

1. write down the active judgment criteria first:
   - dominant technical surfaces
   - acceptance risks
   - verification burdens
   - review burdens
2. start with the role core from `skills/agent-skills-integration/agent-skill-routing.md`
3. add task-shaped skills only when one of the written criteria says the worker needs that extra discipline
4. add risk-shaped skills only when acceptance genuinely depends on that extra risk lens
5. keep expanding only while each added imported skill changes behavior, validation, or acceptance in a way the parent can explain
6. stop when the next imported skill would only restate an already-covered behavior or check

Do not attach every plausible imported skill by habit.
Do not enforce a rigid small cap either. Use as many imported skills as the active criteria justify, and no more.
If the parent cannot explain why a selected imported skill changes the worker's behavior or acceptance bar, remove it.

## Status Rules

The parent must keep reporting during execution.

Each status update should say:

- current stage
- active agents
- waiting agents
- completed agents
- failed agents
- what active agents are working on
- whether the run is blocked on approval, verification, or review

## Acceptance Rules

Accept only when:

- requested deliverables are present
- accepted writable worker outputs have been landed in the primary workspace
- promised checks have passed
- promised reviewer or validator verdicts have been captured
- evidence files are updated

If a review finding exceeds the current bounded repair plan, re-plan or re-approve instead of silently widening the fix.

## Material Issue Threshold

Treat a finding as material when any of the following is true:

- a requested deliverable is missing or incorrect
- a promised check failed
- a reviewer or validator cannot accept the artifact
- the repair would cross the approved writable scope
- parallel branch outputs cannot be merged deterministically
- the finding introduces security, rollback, or contract risk that changes acceptance

Do not burn a fixer loop on cosmetic-only observations that do not affect acceptance.
