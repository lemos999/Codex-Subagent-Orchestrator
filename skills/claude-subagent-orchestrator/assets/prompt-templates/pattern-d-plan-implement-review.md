# Pattern D: Plan + Implement + Review

Use when the task is complex enough to benefit from a design phase before implementation.

## When to Use

- Architecture decisions needed before writing code
- Multiple viable approaches and the orchestrator needs structured analysis
- Large scope where a plan reduces implementer ambiguity

## Stage 1: Planner

Uses a `general-purpose` or `Plan` agent to produce a concrete plan.

```
You operate under the shared contract in AGENTS.md at the workspace root. Read it before starting.

## Planning Contract

**Task**: Design the implementation approach for: {{TASK_DESCRIPTION}}

**Inspect first**:
{{#each CONTEXT_FILES}}
- {{this}}
{{/each}}

**Deliverable**: A concrete implementation plan including:
1. One recommended implementation route
2. Files to create or modify (with paths)
3. Key design decisions and rationale
4. Interface definitions (function signatures, types)
5. Edge cases to handle
6. Validation criteria

Include one fallback only if it is materially needed to deliver the task.

**Constraints**:
- {{PROJECT_CONSTRAINTS}}
- Follow existing patterns from the inspected files
- Compress the task to the key decision points first; analyze those, not every plausible option
- Prefer one chosen approach with brief rationale, plus at most one strong alternative or counterargument when it materially affects the plan

**Return**: The implementation plan as structured markdown, centered on the recommended route.

**Stop condition**: Plan only. Do not write any implementation code. Do not create files. Converge on one recommended route instead of enumerating broad option lists.
```

### Task Invocation

```python
Task(
    subagent_type="Plan",  # or "general-purpose"
    model="opus",          # planning benefits from strong reasoning
    description="Plan {{SHORT_DESCRIPTION}}",
    prompt=PLANNER_PROMPT
)
```

## Stage 2: Implementer

Follows the planner's output as its spec.

```
You operate under the shared contract in AGENTS.md at the workspace root. Read it before starting.

## Contract

**Task**: Implement the following plan:

{{PLANNER_OUTPUT}}

**Inspect first**:
{{#each PLAN_REFERENCED_FILES}}
- {{this}}
{{/each}}

**Writable scope**:
{{#each PLAN_OUTPUT_FILES}}
- {{this.path}} ({{this.mode}})
{{/each}}

**Validation**:
1. All files from the plan exist and are non-empty
2. Interfaces match the plan's definitions
3. Edge cases from the plan are handled
4. No files outside writable scope modified

**Return**: files created/modified, validation results, any deviations from plan, key decision if the plan left a material branch open, blocking or correctness-relevant uncertainty only
**Stop condition**: Implement the plan. Do not redesign or expand scope. If the plan leaves options open, choose the narrowest route that satisfies it and state the choice.
```

### Task Invocation

```python
Task(
    subagent_type="sub-implementer",
    model="sonnet",
    description="Implement {{SHORT_DESCRIPTION}}",
    prompt=IMPLEMENTER_PROMPT  # includes planner output
)
```

## Stage 3: Reviewer

Reviews deliverables against both the original task and the plan.

```
You operate under the shared contract in AGENTS.md at the workspace root. Read it before starting.

## Review Contract

**Task**: Review implementation against plan and original task

**Original task**: {{ORIGINAL_TASK_DESCRIPTION}}

**Implementation plan**: {{PLANNER_OUTPUT_SUMMARY}}

**Files to review**:
{{#each DELIVERABLE_FILES}}
- {{this}}
{{/each}}

**Review criteria**:
1. Scope compliance -- only planned files were created or modified
2. Plan adherence -- implementation matches the plan's interfaces and design
3. Correctness -- logic sound, edge cases from plan handled
4. Contract fulfillment -- output satisfies the original task
5. Decision quality -- remaining branch points are either resolved or explicitly justified as still open
6. If a counterargument matters, test the strongest one and resolve it instead of listing many

**Return**: verdict, material evidence-backed findings with one fix direction, files checked, rereview required
**Stop condition**: Review only. Do not edit files.
```

### Task Invocation

```python
Task(
    subagent_type="sub-reviewer",
    model="sonnet",  # sonnet because reviewing plan adherence requires deeper analysis
    description="Review {{SHORT_DESCRIPTION}}",
    prompt=REVIEWER_PROMPT
)
```

## Notes

- The planner's output is passed as text into the implementer's contract.
- If the plan is very long, summarize the key decisions and reference the full plan file.
- Keep the plan centered on one route. Include one fallback only when it changes delivery risk materially.
- The reviewer checks against both the plan and the original task (catching plan errors too).
- If the plan itself is flawed, the reviewer should flag this as a `MATERIAL_ISSUE`.

## Watchdog Integration (Optional)

Pattern D benefits most from watchdog hooks because design decisions can drift from the original goal.

**Typical flow with watchdog:**

```
Stage 1: Planner
  -> Stage 1.5: Watchdog (does the plan align with the goal?)
    -> If SHORTFALL -> Leader 3-choice protocol
Stage 2: Implementer
  -> Stage 2.5: Watchdog (does the implementation match goal + plan?)
    -> If SHORTFALL -> Leader 3-choice protocol
Stage 3: Reviewer
```

**Watchdog prompt for planner stage:**

```
You operate under the shared contract in AGENTS.md at the workspace root.

## Watchdog Contract

**Original goal**: {{ORIGINAL_USER_REQUEST}}
**Worker stage**: Planning (Plan agent)
**Worker output summary**: {{PLANNER_OUTPUT_SUMMARY}}

**Your task**: Evaluate whether the plan advances the original goal.

**Evaluation criteria**:
1. Does the plan's scope match the original goal (not narrower, not broader)?
2. Are the design decisions justified by the goal, not by general best practices?
3. Will the plan, if implemented as-is, produce an output that satisfies the goal?
4. Does the plan converge on a recommended route instead of staying in broad option exploration?
5. If an alternative matters, compare only the strongest one and resolve it

**Return**:
- Verdict: PASS or SHORTFALL
- If SHORTFALL: material plan-vs-goal gaps with evidence and one fix direction
- Confidence: HIGH / MEDIUM / LOW

**Stop condition**: Evaluation only. No file edits. No scope expansion.
```

**Watchdog prompt for implementer stage (Stage 2.5):**

```
You operate under the shared contract in AGENTS.md at the workspace root.

## Watchdog Contract

**Original goal**: {{ORIGINAL_USER_REQUEST}}
**Worker stage**: Implementation (sub-implementer, following plan)
**Worker output summary**: {{IMPLEMENTER_RETURN_SUMMARY}}
**Files produced**: {{IMPLEMENTER_FILES}}
**Plan summary**: {{PLANNER_OUTPUT_SUMMARY}}

**Your task**: Evaluate whether the implementation meaningfully advances the original goal and follows the approved plan.

**Evaluation criteria**:
1. Does the implementation address the core of the original goal (not just the plan)?
2. Does the implementation follow the plan's design decisions and interfaces?
3. Is the output complete enough for the reviewer to validate?
4. Are there gaps where the goal or plan requires X but the output delivers Y or nothing?
5. Does the implementation resolve material branches instead of carrying them forward without decision?
6. If a counterargument matters, test the strongest one and resolve it

**Return**:
- Verdict: PASS or SHORTFALL
- If SHORTFALL: material findings with evidence and one fix direction (distinguish goal gaps from plan deviations)
- Confidence: HIGH / MEDIUM / LOW

**Stop condition**: Evaluation only. No file edits. No scope expansion.
```

**Watchdog cycle limit:** Maximum 1 watchdog-fix cycle per worker stage. If the re-fixed output still gets `SHORTFALL`, escalate to the user.
