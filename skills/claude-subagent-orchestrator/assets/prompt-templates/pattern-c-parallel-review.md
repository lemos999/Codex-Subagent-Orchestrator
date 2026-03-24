# Pattern C: Parallel Implementers + Review

Multiple independent implementers run in parallel, followed by a single reviewer.

## Prerequisites

Before using this pattern, verify:
- [ ] All implementers have **disjoint writable scopes** (no overlapping files)
- [ ] No data dependency between implementers (neither reads what the other writes)
- [ ] Results combine without conflict

If any condition fails, use sequential Pattern B instead.

## Implementer Prompts (One Per Worker)

Each implementer gets its own contract targeting its specific files:

```
You operate under the shared contract in AGENTS.md at the workspace root. Read it before starting.

## Contract

**Task**: {{TASK_FOR_THIS_WORKER}}

**Inspect first**:
- {{SHARED_CONTEXT_FILES}}
- {{WORKER_SPECIFIC_FILES}}

**Writable scope**:
- {{WORKER_SPECIFIC_OUTPUT}} (create | modify)

**Validation**:
1. Output file exists and is non-empty
2. {{WORKER_SPECIFIC_CHECK}}
3. No files outside writable scope modified

**Return**:
- What was created/modified
- Validation results
- Assumptions and blocking or correctness-relevant uncertainty only

**Stop condition**: Complete only your assigned output. Do not touch files assigned to other workers.
```

## Reviewer Prompt (Covers All Outputs)

```
You operate under the shared contract in AGENTS.md at the workspace root. Read it before starting.

## Review Contract

**Task**: Review all deliverables from the parallel implementation stage

**Files to review**:
{{#each ALL_DELIVERABLE_FILES}}
- {{this}}
{{/each}}

**Original task specs**:
- Worker 1: {{TASK_1_DESCRIPTION}}
- Worker 2: {{TASK_2_DESCRIPTION}}

**Review criteria**:
1. Scope compliance per worker -- each worker only modified its authorized paths
2. Correctness -- logic sound in each deliverable
3. Consistency -- deliverables are compatible with each other (no conflicts)
4. Contract fulfillment -- each output matches its task spec

**Return**:
- Verdict: ACCEPTED | MINOR_ISSUES | MATERIAL_ISSUES
- Per-worker material findings with evidence and one fix direction (if any)
- Cross-worker consistency check result
- Files checked
- Rereview required: YES | NO

**Stop condition**: Review only. Do not edit files.
```

## Task Tool Invocation

```python
# Stage 1: Parallel implementers (single message -- both Task calls together)
Task(
    subagent_type="sub-implementer",
    model="sonnet",
    description="Create {{OUTPUT_1}}",
    prompt=IMPLEMENTER_1_PROMPT
)
Task(
    subagent_type="sub-implementer",
    model="sonnet",
    description="Create {{OUTPUT_2}}",
    prompt=IMPLEMENTER_2_PROMPT
)
# Both run concurrently

# Stage 2: Reviewer (after BOTH implementers complete)
Task(
    subagent_type="sub-reviewer",
    model="haiku",  # default haiku; upgrade to sonnet if files have complex logic
    description="Review all deliverables",
    prompt=REVIEWER_PROMPT
)
```

## With Worktree Isolation

If parallel workers need to touch files in the same directory (rare):

```python
Task(
    subagent_type="sub-implementer",
    model="sonnet",
    isolation="worktree",
    description="Create {{OUTPUT_1}}",
    prompt=IMPLEMENTER_1_PROMPT
)
```

Note: Worktree isolation creates a temporary git branch. Changes must be merged manually.

## Watchdog Integration (Optional)

For parallel implementations, watchdog can run on each worker's output independently.

**Typical flow with watchdog:**

```
Stage 1a: Implementer 1 -> Stage 1b: Implementer 2 (parallel)
  -> Stage 1.5a: Watchdog (worker 1 output)
  -> Stage 1.5b: Watchdog (worker 2 output) (parallel)
Stage 2: Reviewer (all outputs)
```

**Note:** Parallel watchdogs follow the same rules as parallel implementers -- they have disjoint evaluation scopes (each watches one worker's output) and can run in a single message.

**Watchdog cycle limit:** Maximum **1 watchdog-fix cycle per worker stage**. If re-fixed output still gets SHORTFALL, escalate to user.

**Watchdog prompt for Pattern C (per worker):**

```
You operate under the shared contract in AGENTS.md at the workspace root.

## Watchdog Contract

**Original goal**: {{ORIGINAL_USER_REQUEST}}
**Worker stage**: Parallel implementation -- Worker {{WORKER_NUMBER}} (sub-implementer)
**Worker output summary**: {{WORKER_RETURN_SUMMARY}}
**Files produced**: {{WORKER_FILES}}

**Your task**: Evaluate whether this worker's output meaningfully advances its portion of the original goal.

**Evaluation criteria**:
1. Does the output address the core of this worker's assigned portion of the goal?
2. Is the implementation complete enough for the reviewer to validate?
3. Are there specific gaps between the goal and what was delivered?
4. Does the output stay within this worker's scope (no cross-contamination with other workers)?

**Return**:
- Verdict: PASS or SHORTFALL
- If SHORTFALL: material findings with evidence and one fix direction
- Confidence: HIGH / MEDIUM / LOW

**Stop condition**: Evaluation only. No file edits. No scope expansion.
```

**Task invocation with watchdog:**

```python
# Stage 1a/1b: Parallel implementers (single message)
impl1_result = Task(subagent_type="sub-implementer", model="sonnet",
                    description="Create {{OUTPUT_1}}", prompt=IMPL_1_PROMPT)
impl2_result = Task(subagent_type="sub-implementer", model="sonnet",
                    description="Create {{OUTPUT_2}}", prompt=IMPL_2_PROMPT)

# Stage 1.5a/1.5b: Parallel watchdogs (single message)
wd1_result = Task(subagent_type="sub-reviewer", model="sonnet",
                  description="Watchdog: worker 1", prompt=WATCHDOG_1_PROMPT)
wd2_result = Task(subagent_type="sub-reviewer", model="sonnet",
                  description="Watchdog: worker 2", prompt=WATCHDOG_2_PROMPT)

# If SHORTFALL -- leader evaluates per worker:
#   Accept -> launch sub-fixer for that worker, re-run watchdog (max 1 cycle)
#   Reject -> log reason, proceed
#   Escalate -> present to user

# Stage 2: Reviewer (all outputs)
review_result = Task(subagent_type="sub-reviewer", model="haiku",
                     description="Review all deliverables", prompt=REVIEW_PROMPT)
```
