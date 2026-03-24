# Pattern B: Implement + Review (Default)

The most common orchestration pattern. One implementer writes, one reviewer validates.

## Implementer Prompt Template

```
You operate under the shared contract in AGENTS.md at the workspace root. Read it before starting.

## Contract

**Task**: {{TASK_DESCRIPTION}}

**Inspect first**:
{{#each INSPECT_FILES}}
- {{this}}
{{/each}}

**Writable scope**:
{{#each WRITABLE_PATHS}}
- {{this.path}} ({{this.mode}})
{{/each}}

**Validation**:
1. All writable-scope files exist and are non-empty
2. {{SPECIFIC_VALIDATION_1}}
3. {{SPECIFIC_VALIDATION_2}}
4. No files outside writable scope were modified

**Return**:
- Files created/modified
- Critical decision and justification, if a real branch had to be resolved
- Validation results (pass/fail per check)
- Assumptions made (if any)
- Remaining uncertainty only when blocking or correctness-relevant

**Stop condition**: Complete the stated task. Do not expand scope, refactor adjacent code, or add features beyond the spec. Stop once the answer is sufficiently supported.
```

## Reviewer Prompt Template

```
You operate under the shared contract in AGENTS.md at the workspace root. Read it before starting.

## Review Contract

**Task**: Review the deliverables from the previous implementer

**Files to review**:
{{#each DELIVERABLE_FILES}}
- {{this}}
{{/each}}

**Original task spec**: {{ORIGINAL_TASK_DESCRIPTION}}

**Review criteria**:
1. Scope compliance -- only authorized paths were modified (verify with git diff or file inspection)
2. Correctness -- logic sound, edge cases handled
3. Contract fulfillment -- output matches the original task spec
4. Decision quality -- the output converges on a justified result without unnecessary repetition or speculative branch-listing
5. {{DOMAIN_SPECIFIC_CRITERION}}

**Return**:
- Verdict: ACCEPTED | MINOR_ISSUES | MATERIAL_ISSUES
- Findings: [file:location -- evidence -- problem -- fix direction] for each material issue
- Files checked: [list]
- Rereview required: YES | NO

**Stop condition**: Review only. Do not edit files. Do not suggest improvements beyond the task scope or pad the review once the verdict is supported.
```

## Task Tool Invocation

```python
# Stage 1: Implementer
Task(
    subagent_type="sub-implementer",
    model="sonnet",  # or haiku for simple, opus for complex
    description="Implement {{SHORT_DESCRIPTION}}",
    prompt=IMPLEMENTER_PROMPT
)

# Stage 2: Reviewer (after implementer completes)
Task(
    subagent_type="sub-reviewer",
    model="haiku",  # or sonnet for complex review
    description="Review {{SHORT_DESCRIPTION}}",
    prompt=REVIEWER_PROMPT
)
```

## Watchdog Integration (Optional)

When watchdog is enabled for this pattern, add a watchdog check after the implementer and optionally after the reviewer.

**Typical flow with watchdog:**

```
Stage 1: Implementer
  -> Stage 1.5: Watchdog (goal check on implementer output)
    -> If SHORTFALL -> Leader 3-choice protocol
Stage 2: Reviewer
```

**Watchdog prompt for Pattern B:**

```
You operate under the shared contract in AGENTS.md at the workspace root.

## Watchdog Contract

**Original goal**: {{ORIGINAL_USER_REQUEST}}
**Worker stage**: Implementation (sub-implementer)
**Worker output summary**: {{IMPLEMENTER_RETURN_SUMMARY}}
**Files produced**: {{IMPLEMENTER_FILES}}

**Your task**: Evaluate whether the implementer's output meaningfully advances the original goal.

**Evaluation criteria**:
1. Does the output address the core of the original goal?
2. Is the implementation complete enough for reviewer validation?
3. Are there specific gaps between the goal and what was delivered?
4. Does the output converge on a justified direction instead of repeating or branching without decision?

**Return**:
- Verdict: PASS or SHORTFALL
- If SHORTFALL: material findings with evidence and one fix direction
- Confidence: HIGH / MEDIUM / LOW

**Stop condition**: Evaluation only. No file edits. No scope expansion.
```

**Task invocation with watchdog:**

```python
# Stage 1: Implementer
impl_result = Task(subagent_type="sub-implementer", model="sonnet",
                   description="Implement {{SHORT}}", prompt=IMPL_PROMPT)

# Stage 1.5: Watchdog
wd_result = Task(subagent_type="sub-reviewer", model="sonnet",
                 description="Watchdog: {{SHORT}}", prompt=WATCHDOG_PROMPT)

# If SHORTFALL -> Leader evaluates:
#   Accept -> launch sub-fixer, then re-run watchdog (max 1 cycle)
#   Reject -> log reason, proceed to Stage 2
#   Escalate -> present to user, wait for decision

# Stage 2: Reviewer
review_result = Task(subagent_type="sub-reviewer", model="haiku",
                     description="Review {{SHORT}}", prompt=REVIEW_PROMPT)
```
