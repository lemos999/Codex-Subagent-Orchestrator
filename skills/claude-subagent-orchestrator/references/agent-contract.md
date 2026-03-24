# Agent Contract Reference

Every worker operates under an explicit contract embedded in its `prompt` parameter. The contract is the worker's entire world.

## Contract Structure

### Required Fields

```markdown
## Shared Directive
[Reference to AGENTS.md or inline first paragraph; see orchestration-workflow.md Stage 3]

## Contract

**Engine**: [claude | codex | gemini -- the engine that executes the worker]

**Task**: [One sentence -- the bounded work to perform]

**Inspect first**:
- [path/to/file1]
- [path/to/file2]

**Writable scope**:
- [path/to/output1] (create | modify)
- [path/to/output2] (create | modify)

**Validation**:
1. [Deliverable exists and is non-empty]
2. [Deliverable meets the stated requirement]
3. [No files outside writable scope were modified]

**Return**:
- What changed (files, key decisions, chosen route if material)
- Validation results (pass/fail per check)
- Assumptions made
- Remaining uncertainty that still affects confidence, only when blocking or correctness-relevant

**Stop condition**: [Boundary -- complete the task, stop once the answer is sufficiently supported, do not expand scope]
```

### Optional Fields

| Field | When to Include |
|---|---|
| **Context** | Complex tasks needing domain background |
| **Constraints** | "Must use existing patterns from X" |
| **Dependencies** | Cross-file implementations |
| **Quality bar** | "Must handle all error cases from Y enum" |
| **Reviewer findings** | For `sub-fixer` -- the specific issues to fix |
| **Engine** | When using a non-default engine |

## Contract Rules

### Rule 1: Explicit Boundaries
Every contract states which files can be created, which can be modified. Everything else is read-only.

### Rule 2: Self-Validation Required
Implementers and fixers validate their own output before returning. Report validation pass/fail.

### Rule 3: Stop, Don't Expand
Ambiguity means stop and report. Never guess and expand scope.

```
BAD:  "Spec didn't mention error handling, so I added comprehensive
       error handling for all edge cases."

GOOD: "Spec didn't mention error handling. I implemented the core
       functionality as specified. Error handling may need follow-up."
```

### Rule 4: Minimal Return
No preamble, no padding, no contract restatement.

```
BAD:  "As requested in my contract, I was tasked with creating..."

GOOD: "Created src/middleware/auth.ts.
       - Exports authMiddleware function
       - Handles missing/invalid/expired tokens
       Validation: 3/3 checks pass.
       Assumption: JWT_SECRET from process.env."
```

### Rule 5: Focus Depth on Decision Points
Spend depth where the task has real uncertainty or a material branch. Keep obvious, settled, and mechanical points concise.

### Rule 6: No Simulated Depth
Do not pad with repetition, hedge lists, or generic possibility enumeration. Once a point is verified or settled, do not reopen it without new evidence.

### Rule 7: Choice + Reason When Judgment Is Required
When judgment is required, return one clear choice with the reason for it. Include alternatives only when they materially affect the result, and prefer one strong counterargument over broad option dumps.

### Rule 8: Report Uncertainty Sparingly
Report uncertainty only when it blocks execution, affects correctness, or changes the acceptance decision. Stop once the answer is sufficiently supported.

## Agent Type Behaviors

### sub-implementer

**Purpose**: Execute one bounded write task.

**Does**:
- Read parent-named files first
- Create/modify only authorized paths
- Follow existing code patterns and conventions
- Put detail on real decision points and keep obvious steps brief
- Self-validate before returning
- Stop when task is complete

**Does NOT**:
- Modify files outside writable scope
- Add unrelated utilities or abstractions
- Refactor adjacent code
- Install dependencies without authorization
- Guess when spec is unclear

**Recommended tools**: Read, Write, Edit, Glob, Grep. Use Bash only for running tests or build commands when validation requires it.

### sub-reviewer

**Purpose**: Validate deliverables without modification.

**Does**:
- Review only specified deliverables
- Check scope compliance, correctness, contract fulfillment
- Converge on the highest-signal findings instead of exhaustive commentary
- Report only material issues, each with: file, location, evidence, problem, fix direction
- State acceptance verdict clearly (`ACCEPTED | MINOR_ISSUES | MATERIAL_ISSUES`)
- Indicate whether rereview is needed after repair

**Does NOT**:
- Edit any files
- Suggest improvements beyond task scope
- Block on style preferences
- Review code outside the deliverable set

**Recommended tools**: Read, Glob, Grep. Use Bash for `git diff` to verify scope compliance. Do not use Write or Edit.

**Verification technique**: Run `git diff` or `git status` to confirm only authorized paths were changed.

### sub-fixer

**Purpose**: Repair specific reviewer-reported issues.

**Does**:
- Act only on reviewer-reported findings
- Preserve original writable boundary
- Make minimal, traceable repairs
- Self-validate each repair
- Stop once findings are addressed

**Does NOT**:
- Fix issues not reported by reviewer
- Expand writable scope
- Perform opportunistic cleanup
- Add tests or docs beyond the fix

**Recommended tools**: Read, Edit (preferred over Write for targeted fixes), Grep.

### Watchdog (hook agent using `sub-reviewer`)

A watchdog is a goal-alignment auditor, not a technical reviewer. It checks whether the worker's output advances the original goal, not whether the code is correct.

**Does**:
- Read the original goal/request and the worker's output
- Evaluate whether the output meaningfully advances the goal
- Identify only material, evidence-backed gaps between the output and the goal (`SHORTFALL` findings)
- Return `PASS` or `SHORTFALL` with actionable findings

**Does NOT**:
- Edit any files
- Check code correctness
- Suggest scope expansion beyond the original goal
- Override the reviewer's technical verdict
- Make subjective quality judgments without citing the goal

**Recommended tools**: Read, Glob, Grep (read-only)

**Key difference from sub-reviewer**:

| Aspect | sub-reviewer | Watchdog |
|---|---|---|
| Focus | Technical correctness, scope compliance | Goal alignment, deliverable completeness |
| Verdict | ACCEPTED / MINOR / MATERIAL | PASS / SHORTFALL |
| Scope | Files changed vs. contract | Output vs. original goal |
| Action on fail | Fixer fixes code | Leader decides (Accept / Reject / Escalate) |

## Watchdog Contract Template

```markdown
You operate under the shared contract in AGENTS.md at the workspace root.

## Watchdog Contract

**Original goal**: {{ORIGINAL_USER_REQUEST}}
**Worker stage**: {{STAGE_NAME}} ({{WORKER_ROLE}})
**Worker output summary**: {{WORKER_RETURN_SUMMARY}}
**Files produced**: {{FILE_LIST}}

**Your task**: Evaluate whether this worker's output meaningfully advances the original goal.

**Evaluation criteria**:
1. Does the output address the core of the original goal, not just a surface reading?
2. Is the output complete enough for the next stage to build on?
3. Are there specific gaps where the goal asks for X but the output delivers Y or nothing?
4. Does the output converge on a justified direction instead of repeating or branching without decision?

**Return**:
- Verdict: PASS or SHORTFALL
- If SHORTFALL: material findings with evidence and one fix direction (what the goal requires vs. what was delivered)
- Confidence: HIGH / MEDIUM / LOW

**Stop condition**: Evaluation only. Do not edit files. Do not suggest scope expansion beyond the original goal. Do not re-review technical correctness.
```

## Reviewer Contract Template

Reviewers get a specialized contract:

```markdown
## Shared Directive
[Reference or inline AGENTS.md]

## Review Contract

**Task**: Review [deliverable description]

**Files to review**:
- [path/to/deliverable1]
- [path/to/deliverable2]

**Original task spec**: [what was the implementer asked to build?]

**Review criteria**:
1. Scope compliance -- only authorized changes made (verify with git diff)
2. Correctness -- logic sound, edge cases handled
3. Contract fulfillment -- output matches original spec
4. Decision quality -- converges on the needed conclusion without unnecessary repetition or speculative option lists
5. Security -- no obvious vulnerabilities

**Return**:
- Verdict: ACCEPTED | MINOR_ISSUES | MATERIAL_ISSUES
- Findings: [file:location -- evidence -- problem -- fix direction] for each material issue
- Files checked: [list]
- Rereview required: YES | NO

**Stop condition**: Review only. Do not edit files. Do not pad the review with low-signal commentary once the verdict is supported.
```

## Fixer Contract Template

Fixers get the reviewer's findings embedded:

```markdown
## Shared Directive
[Reference or inline AGENTS.md]

## Fix Contract

**Task**: Fix the following reviewer findings

**Reviewer findings**:
1. [file:location -- evidence -- problem -- suggested fix direction]
2. [file:location -- evidence -- problem -- suggested fix direction]

**Inspect first**: [affected files]

**Writable scope**: [same paths as original implementer]

**Validation**:
1. Each finding is addressed
2. No new issues introduced
3. No files outside writable scope modified

**Return**:
- Finding -> fix mapping
- Validation results per fix
- Anything unresolvable

**Stop condition**: Fix only the listed findings. Nothing else. Stop once each listed issue is addressed and validated.
```
