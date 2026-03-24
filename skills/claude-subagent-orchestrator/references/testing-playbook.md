# Testing Playbook

## Purpose

Validate that the Claude subagent orchestrator works correctly before trusting it with real work. Run these scenarios in order of increasing complexity.

## Test Scenarios

### Tier 1: Single Agent (Start Here)

#### Test 1A: Implement + Review — Minimal Write
```
/sub Create a file at tests/artifacts/hello.txt containing "Hello from sub-implementer"
```

**Expected**:
- Pattern B (implementer → reviewer) — file creation is a persistent deliverable, review required per Review Gate Rules
- Implementer model: haiku (trivial task)
- Reviewer model: haiku (routine check)
- File exists at `tests/artifacts/hello.txt` with correct content
- Reviewer verdict: ACCEPTED
- Evidence: full (manifest + summary + prompts + results)

#### Test 1B: Solo Reviewer — File Check
**Depends on**: Test 1A (requires `tests/artifacts/hello.txt` to exist)
```
/sub Review the file at tests/artifacts/hello.txt for correctness
```

**Expected**:
- Pattern A (solo reviewer)
- Model: haiku (routine check)
- Verdict: ACCEPTED
- No files modified

### Tier 2: Implementer + Reviewer (Default Pattern)

#### Test 2A: Standard Pair — Create and Validate
```
/sub Create a TypeScript utility function at tests/artifacts/format-date.ts that formats Date objects to ISO 8601 strings
```

**Expected**:
- Pattern B (implementer → reviewer)
- Implementer model: sonnet
- Reviewer model: haiku
- File created with correct exports
- Reviewer verdict: ACCEPTED
- Evidence: full manifest + summary + prompts + results

#### Test 2B: Standard Pair — Deliberate Issue
```
/sub Create a function at tests/artifacts/divide.ts that divides two numbers (intentionally skip division-by-zero handling)
```

**Expected**:
- Implementer creates function without zero check
- Reviewer flags MATERIAL_ISSUES (no zero division guard)
- Fixer adds the guard
- Re-reviewer ACCEPTS
- Evidence shows the full repair loop

### Tier 3: Parallel Execution

#### Test 3A: Two Independent Files
```
/sub Create two independent files: tests/artifacts/greet.ts (greeting function) and tests/artifacts/farewell.ts (farewell function)
```

**Expected**:
- Pattern C (parallel implementers → reviewer)
- Two implementers launch in single message (true parallelism)
- Reviewer checks both files
- Both files exist with correct content

### Tier 4: Complex Patterns

#### Test 4A: Plan + Implement + Review
```
/sub Design and implement a simple key-value store module at tests/artifacts/kv-store.ts with get, set, delete, and has operations
```

**Expected**:
- Pattern D (planner → implementer → reviewer)
- Planner outputs design, implementer follows plan
- OR pattern B if orchestrator judges planning unnecessary (acceptable)

#### Test 4B: Full Fix Loop
```
/sub Create a user validation function at tests/artifacts/validate-user.ts that validates email, name length (2-50 chars), and age (18+), but deliberately make the age check use > instead of >=
```

**Expected**:
- Implementer creates function with the > bug
- Reviewer catches the off-by-one (MATERIAL_ISSUES)
- Fixer corrects to >=
- Re-reviewer ACCEPTS
- Evidence documents the full cycle

### Tier 5: Watchdog Hook

#### Test 5A: Watchdog PASS — Goal-Aligned Output
```
/sub Create a greeting function at tests/artifacts/greet-watchdog.ts that takes a name and returns "Hello, {name}!" (enable watchdog)
```

**Expected**:
- Pattern B with watchdog enabled
- Implementer creates the function correctly
- Watchdog evaluates against original goal → PASS
- Reviewer confirms technical correctness → ACCEPTED
- Evidence includes watchdog prompt/result files

#### Test 5B: Watchdog SHORTFALL — Goal Misalignment
```
/sub Create a utility at tests/artifacts/math-utils.ts with add, subtract, multiply, divide functions. The divide function must handle division by zero. (enable watchdog, instruct implementer to skip divide-by-zero handling)
```

**Expected**:
- Implementer creates functions but skips divide-by-zero
- Watchdog catches SHORTFALL: "goal requires divide-by-zero handling but output lacks it"
- Leader evaluates → Accept (rational feedback)
- Fixer adds divide-by-zero handling
- Watchdog re-check → PASS
- Evidence documents the full watchdog cycle

#### Test 5C: Watchdog Reject — Unrealistic Feedback
```
Simulate: Watchdog reports SHORTFALL for a cosmetic concern not related to the goal
```

**Expected**:
- Leader evaluates → Reject (feedback disconnected from goal)
- Rejection reason logged in evidence
- Proceed with current output
- Reviewer still runs independently

#### Test 5D: Watchdog Escalate — Ambiguous Judgment
```
Simulate: Watchdog reports SHORTFALL but the finding has merit on both sides
```

**Expected**:
- Leader evaluates → Escalate
- User presented with output + watchdog findings
- User decides (proceed / fix / modify)

### Tier 6: Mixed Engine

#### Test 6A: Codex Implementer + Claude Reviewer
```
/sub Create a file at tests/artifacts/mixed-hello.txt containing "Hello from Codex" — use engine: codex for implementer
```

**Expected**:
- Pattern B (implementer → reviewer)
- Implementer engine: codex (codex exec)
- Reviewer engine: claude (Task tool, default)
- File exists with correct content
- Evidence: `subagent-runs/mixed/<run-name>/`

#### Test 6B: Gemini Analyzer + Claude Implementer
```
/sub Analyze the project structure and create a summary at tests/artifacts/project-summary.md — use engine: gemini for analysis
```

**Expected**:
- Pattern D (planner → implementer → reviewer) or B with gemini analysis first
- Analyzer engine: gemini
- Implementer engine: claude (default)
- Reviewer engine: claude (default)
- Evidence: `subagent-runs/mixed/<run-name>/`

#### Test 6C: Three-Way Mixed Engine
```
/sub Create a game design document: use gemini for concept analysis, codex for content generation, claude for review — output at tests/artifacts/game-concept.md
```

**Expected**:
- 3 different engines used across workers
- All produce coherent, related output
- Evidence in `subagent-runs/mixed/<run-name>/` with engines/ subdirectories

#### Test 6D: Engine Fallback — Default Behavior
```
/sub Create a file at tests/artifacts/default-engine.txt with "Hello" (no engine specified)
```

**Expected**:
- All workers use `claude` engine (default)
- Behavior identical to pre-mixed-engine system
- Evidence in `subagent-runs/claude/<run-name>/` (NOT mixed/)

## Validation Checklist

Run after each test scenario:

### Deliverable Checks
- [ ] Output file(s) exist at specified paths
- [ ] Output file(s) are non-empty
- [ ] Output file(s) contain expected content/exports
- [ ] No unauthorized files were created or modified

### Workflow Checks
- [ ] Correct pattern was chosen (matches task complexity)
- [ ] Correct models were allocated (matches complexity)
- [ ] Reviewer ran after implementer (not skipped)
- [ ] Reviewer was read-only (no files modified by reviewer)
- [ ] Fixer (if used) was scoped to reviewer findings only
- [ ] Re-review happened after fixer (if fixer was used)

### Contract Checks
- [ ] Each worker received an explicit contract with all required fields
- [ ] Workers stayed within writable scope
- [ ] Workers self-validated before returning
- [ ] Workers stopped instead of expanding scope

### Evidence Checks
- [ ] Evidence directory created at correct path (claude/, codex/, gemini/, or mixed/ depending on engines used)
- [ ] `run-manifest.md` exists and is well-formed
- [ ] `run-summary.md` exists with one line per agent
- [ ] `prompts/` directory has one file per worker
- [ ] `results/` directory has one file per worker
- [ ] Failed runs still have evidence documenting what went wrong

### Watchdog Checks (when enabled)
- [ ] Watchdog contract includes original goal verbatim
- [ ] Watchdog verdict is PASS or SHORTFALL (not ACCEPTED/MINOR/MATERIAL)
- [ ] Leader decision is logged (Accept/Reject/Escalate)
- [ ] Rejection includes specific reason
- [ ] Escalation presents both sides to user
- [ ] Watchdog evidence files exist in subagent-runs/claude/
- [ ] Watchdog cycle limit (1 per stage) respected

### Mixed Engine Checks
- [ ] Correct engine was used for each worker (verify CLI command in evidence)
- [ ] Engine-role compatibility respected (no claude --print for implementer)
- [ ] Mixed-engine evidence stored in `subagent-runs/mixed/`
- [ ] Single-engine runs still stored in respective engine directory
- [ ] Manifest includes engine field for each agent
- [ ] Summary table includes engine column

## Efficiency Checklist

| Metric | Target | Red Flag |
|---|---|---|
| Agents per deliverable | ≤ 2 | 3+ for a single file |
| Fix-review cycles | 0-1 | 2 cycles on a simple task |
| Model cost | Cheapest adequate | Opus for hello-world |
| Parent interventions | 0 | Parent editing deliverables |
| Scope compliance | 100% | Any unauthorized changes |
| Evidence completeness | All fields populated | Missing manifest or prompts |
| Engine selection | Cheapest adequate engine | Opus for tasks a cheaper engine handles |

## Failure Recovery Scenarios

### Scenario F1: Worker Returns Empty
- Re-launch with more specific contract
- If still empty: report to user, don't retry infinitely

### Scenario F2: Worker Exceeds Scope
- Discard result
- Re-launch with explicit warning: "Do NOT modify files outside: [list]"

### Scenario F3: Reviewer Always Rejects
- After 2 fix cycles: stop and escalate
- Write evidence of all cycles for user review

### Scenario F4: Task Tool Error
- Retry once with simplified prompt
- If still failing: report error to user, preserve any partial evidence

## Test Artifact Cleanup

All test artifacts go to `tests/artifacts/`. Clean up after testing:

```bash
rm -rf tests/artifacts/*
rm -rf subagent-runs/claude/test-*
rm -rf subagent-runs/mixed/test-*
rm -rf subagent-runs/gemini/test-*
```
