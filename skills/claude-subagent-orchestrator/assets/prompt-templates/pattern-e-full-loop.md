# Pattern E: Full Loop (Implement -> Review -> Fix -> Review)

Use when the task has known risk of issues requiring repair. Pre-plans the full repair cycle.

## Stage 1: Implementer

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
1. All deliverables exist and are non-empty
2. {{SPECIFIC_CHECKS}}
3. No files outside writable scope modified

**Return**: files changed, validation results, assumptions, blocking or correctness-relevant uncertainty only
**Stop condition**: Complete stated task only. Do not expand scope.
```

## Stage 2: Reviewer

```
You operate under the shared contract in AGENTS.md at the workspace root. Read it before starting.

## Review Contract

**Task**: Review {{DELIVERABLE_DESCRIPTION}}

**Files to review**:
{{#each DELIVERABLE_FILES}}
- {{this}}
{{/each}}

**Original task spec**: {{ORIGINAL_TASK}}

**Review criteria**:
1. Scope compliance
2. Correctness (especially: {{KNOWN_RISK_AREAS}})
3. Contract fulfillment
4. Security
5. If a counterargument matters, test the strongest one and resolve it instead of listing many

**Return**: verdict, material evidence-backed findings with one fix direction each, files checked, rereview required
**Stop condition**: Review only. Do not edit files. Resolve the verdict on the strongest remaining issue, not a broad option survey.
```

## Stage 3: Fixer (Conditional -- Only If MATERIAL_ISSUES)

```
You operate under the shared contract in AGENTS.md at the workspace root. Read it before starting.

## Fix Contract

**Task**: Fix the following reviewer findings

**Reviewer findings**:
{{#each REVIEWER_FINDINGS}}
{{this.number}}. {{this.file}}:{{this.location}} -- {{this.problem}} -- {{this.fix_direction}}
{{/each}}

**Inspect first**: {{AFFECTED_FILES}}

**Writable scope**: [same as original implementer]

**Validation**:
1. Each finding addressed
2. No new issues introduced
3. No files outside scope modified

**Return**: finding -> fix mapping, validation per fix, anything unresolvable
**Stop condition**: Fix only listed findings. Nothing else.
```

## Stage 4: Re-Reviewer (After Fixer)

```
You operate under the shared contract in AGENTS.md at the workspace root. Read it before starting.

## Re-Review Contract

**Task**: Re-review {{DELIVERABLE_DESCRIPTION}} after fixer repairs

**Files to review**: [same as Stage 2]

**Previous findings that were fixed**:
{{#each FIXED_FINDINGS}}
- {{this}}
{{/each}}

**Review criteria**:
1. Each previous finding is resolved
2. No new issues introduced by the fix
3. Overall deliverable still meets original spec

**Return**: verdict, any remaining or new material evidence-backed findings with one fix direction each, files checked
**Stop condition**: Review only. Do not edit files.
```

## Task Tool Invocation

```python
# Stage 1
impl_result = Task(subagent_type="sub-implementer", model="sonnet",
                   description="Implement {{SHORT}}", prompt=IMPL_PROMPT)

# Stage 2
review_result = Task(subagent_type="sub-reviewer", model="haiku",  # default; use sonnet for deep logic
                     description="Review {{SHORT}}", prompt=REVIEW_PROMPT)

# Stage 3 (conditional)
if review_result contains "MATERIAL_ISSUES":
    fix_result = Task(subagent_type="sub-fixer", model="sonnet",
                      description="Fix {{SHORT}}", prompt=FIX_PROMPT)

    # Stage 4
    rereview_result = Task(subagent_type="sub-reviewer", model="haiku",
                           description="Re-review {{SHORT}}", prompt=REREVIEW_PROMPT)

    if rereview_result contains "MATERIAL_ISSUES":
        # Max 2 cycles -> escalate to user
        report_failure_to_user()
```

## Cycle Limit

**Maximum 2 fix-review cycles.** After that:
1. Stop automation
2. Write full evidence (all cycles documented)
3. Report to user with all findings and fix attempts
4. Let user decide: manual fix, different approach, or accept as-is

## Watchdog Integration (Optional)

Pattern E already includes a fix-review cycle. Watchdog adds a goal-alignment layer on top.

**Typical flow with watchdog:**

```
Stage 1: Implementer
  -> Stage 1.5: Watchdog (goal check)
Stage 2: Reviewer
  -> If MATERIAL_ISSUES -> Stage 3: Fixer -> Stage 4: Re-Reviewer
Stage 4.5: Watchdog (final goal check on the fixed output)
```

**Note:** Watchdog runs after the implementer (Stage 1.5) and after the final accepted output (Stage 4.5 or after Stage 2 if no fix needed). This avoids redundant watchdog cycles during the fix loop.

**Watchdog cycle limit:** Maximum **1 watchdog-fix cycle per worker stage**. If re-fixed output still gets SHORTFALL, escalate to user.

**Watchdog prompt for Stage 1.5 (post-implementer):**

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
2. Is the implementation complete enough for the reviewer to validate?
3. Are there specific gaps between the goal and what was delivered?
4. If a counterargument matters, test the strongest one and resolve it

**Return**:
- Verdict: PASS or SHORTFALL
- If SHORTFALL: material findings with evidence and one fix direction
- Confidence: HIGH / MEDIUM / LOW

**Stop condition**: Evaluation only. No file edits. No scope expansion.
```

**Watchdog prompt for Stage 4.5 (post-fix/post-review final check):**

```
You operate under the shared contract in AGENTS.md at the workspace root.

## Watchdog Contract

**Original goal**: {{ORIGINAL_USER_REQUEST}}
**Worker stage**: Final output (after fix-review cycle or direct acceptance)
**Worker output summary**: {{FINAL_OUTPUT_SUMMARY}}
**Files produced**: {{FINAL_FILES}}
**Fix history**: {{FIX_CYCLES_SUMMARY_OR_NONE}}

**Your task**: Final goal-alignment check on the accepted output.

**Evaluation criteria**:
1. Does the final output fully satisfy the original goal?
2. If fixes were applied, did they resolve the issues without introducing goal drift?
3. Are there any remaining gaps between the goal and the final deliverable?
4. If a counterargument matters, test the strongest one and resolve it

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

# Stage 1.5: Watchdog (goal check)
wd1_result = Task(subagent_type="sub-reviewer", model="sonnet",
                  description="Watchdog: impl", prompt=WATCHDOG_1_PROMPT)

# If SHORTFALL -> leader evaluates:
#   Accept -> launch sub-fixer, re-run watchdog (max 1 cycle)
#   Reject -> log reason, proceed
#   Escalate -> present to user

# Stage 2: Reviewer
review_result = Task(subagent_type="sub-reviewer", model="haiku",
                     description="Review {{SHORT}}", prompt=REVIEW_PROMPT)

# Stage 3-4: Fix loop (if MATERIAL_ISSUES) -- no watchdog during fix loop

# Stage 4.5: Final watchdog (after acceptance)
wd2_result = Task(subagent_type="sub-reviewer", model="sonnet",
                  description="Watchdog: final", prompt=WATCHDOG_2_PROMPT)
```
