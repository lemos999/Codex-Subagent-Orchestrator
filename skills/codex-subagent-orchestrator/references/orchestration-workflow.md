# Internal `/sub` Orchestration Workflow

This workflow treats `/sub` as an internal supervision mode, not as an external launcher.

Use `skills/agent-skills-integration/agent-skill-routing.md` whenever a worker or stage needs vendored execution-discipline skills from `vendor/agent-skills/`.

If the runtime cannot provide the required internal agent tools, do not invent worker launches. Fall back to a parent-only reasoning path under `skills/codex-parent-session-orchestrator/SKILL.md`, keep the same plan-first contract, and preserve `/sub`-style evidence on disk so the degradation is explicit and reviewable.

For any `/sub` coding request that could lead to implementation, treat the request as an explicit request for the shared plan-first flow. Use `skills/agent-skills-integration/agent-skill-routing.md` as the shared gate authority, `skills/karpathy-guidelines/SKILL.md` as the default local anti-overengineering overlay for coding stages and coding workers, `skills/plan-mode-default/SKILL.md` as the default workspace planning behavior surface, and `skills/plan-mode-default/references/coding-plan-prompt-en.md` as the detailed planning contract unless the user explicitly overrides the contract format. This plan-first gate is mandatory before any writable worker launch or implementation activity, the approved full PLAN should be written under repo-root `plan/` as a versioned living record, and any override must still preserve the understanding-report and explicit-approval gate.

## Core Loop

Use one of these two orders:

### Coding `/sub` requests that need a fresh approval gate

1. interpret the `/sub` request
2. scan the repository enough to understand the boundary
3. produce the short understanding report required by `skills/plan-mode-default/SKILL.md` and `skills/plan-mode-default/references/coding-plan-prompt-en.md`
4. wait for explicit user approval to proceed with coding
5. write or update the approved full PLAN under repo-root `plan/` in the primary workspace
6. finalize whether delegation is justified
7. finalize worker count, execution mode, and worker roles
8. write the orchestration plan on disk
9. launch bounded internal agents
10. keep status visible in chat and on disk
11. collect worker outputs
12. run review or validation at the planned gate
13. accept, repair, re-plan, or stop

If a later tiny follow-up edit, repair step, or similar writable coding action is already explicitly covered by the active approved plan record and does not materially change the approved direction, do not reopen a fresh understanding-report approval gate. Refresh the active approved plan file, keep `status.md` and `orchestration-plan.md` aligned with that same active plan, and continue through the remaining delegated execution steps under the existing approval.

### Non-coding `/sub` requests

1. interpret the `/sub` request
2. scan the repository enough to understand the boundary
3. decide whether delegation is justified
4. finalize worker count, execution mode, and worker roles
5. write the orchestration plan on disk
6. launch bounded internal agents
7. keep status visible in chat and on disk
8. collect worker outputs
9. run review or validation at the planned gate when needed
10. accept, repair, re-plan, or stop

## Parent Responsibilities

The parent owns:

- request interpretation
- task decomposition
- worker count
- execution mode: serial | parallel | mixed
- model selection
- reasoning selection
- review timing
- approved writable boundaries
- acceptance criteria
- final acceptance
- integrating accepted writable worker outputs into the primary workspace
- selecting the minimum imported vendor skills each stage or worker actually needs
- ensuring that coding stages and coding workers inherit `skills/karpathy-guidelines/SKILL.md` as the default local anti-overengineering overlay
- ensuring that planner-like workers on coding runs inherit `skills/plan-mode-default/SKILL.md` and `skills/plan-mode-default/references/coding-plan-prompt-en.md` as the default planning contract unless the user explicitly overrides it
- ensuring that coding `/sub` runs do not launch writable workers before the understanding-report approval gate is satisfied
- for coding runs, writing or updating the approved full PLAN under repo-root `plan/` in the primary workspace before writable worker launch
- for coding runs, keeping the active approved plan file updated with typed progress, completion state, blockers, next step, and version links as the run advances
- for coding runs, keeping the active plan file's `Scoreboard` section current and treating it as the authoritative score-history ledger for the run
- for coding runs, recording explicit user scores as authoritative and otherwise maintaining a conservative provisional score without blocking for feedback or using a fixed hardcoded fallback number, while keeping that provisional score at `50` or below
- for coding runs, keeping `orchestration-plan.md`, `status.md`, and the active plan file aligned on the same active path, version, current status, and current score state
- keeping `status.md` as the authoritative current orchestration-state ledger, the active file under `plan/` as the authoritative approved plan-history ledger for coding runs, and `orchestration-plan.md` as the authoritative record of the approved team shape and initial execution contract

The parent should not satisfy requested deliverable edits directly when a bounded worker can do the work cleanly.

## Worker Responsibilities

Each worker owns one bounded job in its own forked workspace:

- one clear mission
- one writable surface
- one validation contract
- one stop condition

Workers should not infer broader scope, edit unrelated files, or silently change the team plan.
For write tasks, their result is a proposed change set until the parent lands the accepted change in the primary workspace.
For planning tasks on coding runs, workers should read `skills/plan-mode-default/SKILL.md` and `skills/plan-mode-default/references/coding-plan-prompt-en.md` first by default when those files exist and should follow that contract unless the user explicitly overrides it.
For coding tasks, no writable worker should launch until that contract has already produced the understanding report and the user has explicitly approved proceeding.

## Choosing Team Size

Start with the assumption that one implementer is enough.

Expand to multiple implementers only when all of the following are true:

- deliverables can be partitioned cleanly
- writable surfaces do not overlap
- outputs do not depend on each other in order-sensitive ways
- interface or contract merge risk is low enough to describe deterministically
- the parent can integrate the accepted branch outputs into the primary workspace without ambiguity
- one final read-only reviewer or validator can judge the merged result after integration

Keep one implementer when any of the following is true:

- files overlap or are nested
- one change depends on another change landing first
- one shared contract, config, or interface could be touched from multiple directions
- reconciliation would be harder than one bounded writer

## Choosing Serial Versus Parallel

Use serial stages when:

- later work consumes earlier output
- a reviewer must gate a risky transition
- the parent must integrate one worker's accepted output before another worker can proceed safely
- the task includes sequential proof obligations
- the writable surface is coupled

Use parallel stages when:

- workers are truly independent
- their writable surfaces are disjoint
- the merge story is obvious before launch

Use `mixed` execution mode when:

- the run contains serial stages overall
- one or more stages contain parallel workers
- reporting only `serial` or only `parallel` would hide important coordination behavior

## Model And Reasoning Selection

Choose model and reasoning only after the plan exists.

Evaluate:

- task ambiguity
- failure cost
- writable scope size
- dependency depth
- verification burden
- review burden

Use the lightest model and reasoning that can still execute the bounded task safely.

Do not hardcode model slug preference tables into repository instructions. Choose from the internal agent capabilities currently available in the active session. If the session cannot expose distinct choices clearly, report that limitation instead of pretending the choice was dynamic.

## Imported Skill Selection

Select imported vendor skills only after team shape and stage order are stable.

Apply this order:

1. write down the active judgment criteria for this stage or worker:
   - dominant surfaces
   - acceptance risks
   - verification burdens
   - review burdens
2. pick the role core from `skills/agent-skills-integration/agent-skill-routing.md`
3. add task-shaped skills only when the written criteria say the extra discipline is needed
4. add risk-shaped review skills only when acceptance depends on that risk lens
5. keep expanding only while each added imported skill changes behavior or checks in a way the parent can explain
6. stop when another imported skill would duplicate an already-selected behavior check

The parent should be able to justify every imported skill in one sentence.
If it cannot, the selection is too broad and should be reduced before launch.
Do not follow a rigid tiny cap when the task genuinely spans several surfaces. The rule is justified use, not arbitrary scarcity.

## Review Policy

Default to one late read-only reviewer or validator.

Move review earlier only when:

- a risky interface needs an explicit gate
- a parallel merge needs reconciliation before further work
- a bounded fixer loop is expected and cheaper than a larger rerun

Do not attach a reviewer after every writer.

If multiple final reviewers or validators do the same acceptance job, keep one and suppress the redundant ones.

## Approval Gate

Before launch, the parent must report:

- request summary
- user constraints
- delegation justification
- approval status and reason
- worker count
- execution mode: serial | parallel | mixed
- each worker id, role, mission, writable scope, model, reasoning effort, and stage
- review timing or review policy
- acceptance strategy
- approved plan file path in `plan/` for coding runs
- plan artifact type, version, and current status for coding runs
- current score and score source from the active plan for coding runs
- evidence file locations

For coding runs, treat delegation justification, worker count, execution mode, and per-worker assignments as provisional before approval and finalize them only after the understanding report and coding direction have been explicitly approved.

For any new coding request, or any later coding request that is not already covered by the active approved plan record, always pause for explicit approval of the understanding report before any writable worker launch. Blanket authority or explicit proceed-now language do not waive this plan-first gate.
If a later tiny follow-up edit, repair step, or similar writable coding action is already explicitly covered by the active approved plan record and does not materially change the approved direction, continue under that plan by refreshing the active plan file instead of reopening a fresh approval gate.

## Status Reporting

While workers run, the parent must continue reporting in chat.

Every meaningful status snapshot should include:

- current stage
- active agents
- waiting agents
- completed agents
- failed agents
- a short description of what each active agent is doing
- whether the run is blocked on approval, review, or verification
- current score state when it changed or when that state matters to the next action; missing score feedback alone must not block the run

The parent should not disappear behind a frozen shell command because the internal-only edition has no long-running shell launcher in the intended `/sub` path.

## Edge Cases

Handle these explicitly:

- do not skip the plan-first approval gate for coding requests, even with true blanket authority or an explicit proceed-now instruction
- if multiple safe plans remain after least-change reasoning, pause and ask instead of inventing user intent
- multiple deliverables do not automatically justify multiple implementers; keep one implementer when writable paths overlap, are nested, or depend on shared contracts
- if parallel workers could touch the same interface, config, or merge boundary, force serial execution or insert a reconciliation review stage
- if the active session cannot truly distinguish model or reasoning choices across workers, say so in the pre-launch report instead of pretending the choice was dynamic
- if a workspace path, deliverable path, or target branch is corrected mid-run, rerun final review or validation on the corrected final artifact before acceptance
- if a reviewer finding exceeds the approved fix scope, re-plan or re-approve instead of silently widening the fixer
- final acceptance comes from verified artifacts and reviewer or validator verdicts, not from a worker merely finishing without error

## Evidence Preservation

Preserve these files by default:

- `orchestration-plan.md`
- `status.md`
- `worker-briefs/*.md`
- `results/*.md`
- `review-verdict.md`
- `acceptance.md`

Cleanup is a separate phase. Do not destroy evidence unless the user explicitly asks for it.

## Bounded Fixer Loop

If review finds a material issue:

1. decide whether the issue fits a bounded fix scope
2. if yes, write the required fixer scope into `review-verdict.md` and the active approved fix scope into `status.md`
3. launch one bounded fixer
4. land the accepted repair in the primary workspace if the fixer worked in a fork
5. rerun review or validation on the repaired artifact in the primary workspace

Re-plan or re-approve instead of widening the repair when:

- the issue exceeds the approved fix scope
- the task boundary changed
- the same root cause already survived one bounded repair loop

Use this material-issue threshold:

- requested deliverable incorrect or missing
- promised check failed
- reviewer or validator cannot accept
- approved writable scope would need to widen
- merge behavior is no longer deterministic
- security, rollback, or contract risk changes acceptance

Cosmetic observations that do not change acceptance should not trigger a fixer loop by default.

## Queue Mode

Queue mode remains available only as an in-session loop.

For each issue:

1. derive one bounded orchestration plan
2. run it to acceptance or bounded stop
3. record outcome
4. move to the next issue

Detached unattended execution is intentionally unsupported in this internal-only edition.
