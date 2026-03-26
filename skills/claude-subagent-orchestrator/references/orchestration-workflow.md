# Orchestration Workflow

## Workflow Stages

### Stage 1: CLASSIFY

Determine before choosing any team shape:

- **Task type**: create, fix, refactor, review, analyze
- **Complexity**: low (boilerplate), medium (logic), high (architecture)
- **Parallelism**: are there independent subtasks with disjoint file scopes?
- **Review need**: does output persist? (if yes, review is required)

### 1.5 Ambiguity Gate

After classification, run the Ambiguity Gate (see sub-command-protocol.md § Ambiguity Gate). If the gate triggers, resolve ambiguity before proceeding to Stage 2 (team planning).

### Stage 2: CHOOSE TEAM

See `sub-command-protocol.md` for team sizing rules and model allocation. Choose the pattern:

| Pattern | Shape | When |
|---|---|---|
| **A: Solo** | 1 agent (implementer or reviewer) | Single bounded task: implementer for low-risk writes, reviewer for validation-only requests, Explore agent for research |
| **B: Implement + Review** | implementer -> reviewer | Standard deliverable (default) |
| **C: Parallel + Review** | N implementers -> reviewer | Independent outputs, disjoint scopes |
| **D: Plan + Implement + Review** | planner -> implementer -> reviewer | Complex task needing design first |
| **E: Full Loop** | implementer -> reviewer -> fixer -> reviewer | Known risk, expected repairs |

### Stage 3: INJECT SHARED DIRECTIVE

Every worker prompt must begin with the workspace operating contract from `AGENTS.md`.

**Injection protocol:**

```
# Injection modes (choose based on context):

REFERENCE MODE (default, saves tokens):
  "You operate under the shared contract in AGENTS.md at the workspace root.
   Read it before starting."

INLINE MODE (for critical workers or first run):
  Prepend the first paragraph of AGENTS.md directly into the worker prompt.
```

Use **reference mode** by default. Switch to **inline mode** when:
- The worker's task is high-risk or architectural
- The shared contract contains project-specific conventions the worker must follow precisely
- It is the first run in a new workspace and you want to ensure contract awareness

If `AGENTS.md` does not exist at the workspace root, skip shared directive injection entirely. Note this in the run manifest under `Errors / Notes`.

### Stage 4: BUILD CONTRACTS

Build a complete contract for each worker per the format in `agent-contract.md`.

Each contract includes:
- Task, inspect-first list, writable scope, validation, return contract, stop condition
- Shared directive (reference or inline, per Stage 3)
- Tool guidance (which tools the worker should or should not use)

For bounded tasks, keep the contract decision-oriented:
- ask for one chosen route with concrete justification when a real branch exists
- include alternatives only when they materially affect delivery
- tell the worker to stop once the answer is sufficiently supported instead of elaborating uniformly

### Stage 5: SELECT SETTINGS

Per worker:

| Setting | Decision |
|---|---|
| `engine` | Default is `claude` (Task tool). Override only when role fit or explicit user direction justifies `codex` or `gemini`. See `engine-adapters.md`. |
| `model` | See model allocation in `sub-command-protocol.md`. |
| `isolation` | Use `"worktree"` only when parallel writers could touch overlapping directories. |
| `run_in_background` | Use `true` only for truly independent long tasks. |
| `max_turns` | Set when the task is well-bounded and runaway work is a real risk. |

**Engine-role validation**: Check `engine-adapters.md` before dispatch. If the chosen engine-role combination is not valid, replace it or fail the run explicitly.

### Stage 6: CONFIRM

Before launching, present the execution plan to the user and wait for confirmation.

**Display format:**

```markdown
## /sub Execution Plan

**Request**: [abbreviated original request]
**Pattern**: [pattern name -- e.g., "B: Implement + Review"]

| # | Agent | Role | Engine | Model | Reasoning | Goal |
|---|---|---|---|---|---|---|
| 1 | impl-name | implementer | codex | gpt-5.4 | medium | [one-line goal] |
| 2 | review-name | reviewer | claude | haiku | low | [one-line goal] |

When watchdog is enabled, add a `Watchdog` column to the execution plan.

**Estimated cost**: [low / medium / high based on model + agent count]

> **yes** -- proceed as planned
> **no** -- cancel this /sub
> **modify** -- tell me what to change
```

**User response handling:**

| Response | Action |
|---|---|
| **yes** | Proceed to Stage 7: LAUNCH |
| **no** | Abort. Write no evidence. Report cancellation to user. |
| **modify** | Apply requested changes, then re-display the updated plan and ask again. |

**Rules:**
- Always show the plan before first launch.
- After a `modify`, re-display the full updated table for re-confirmation.
- If the user modifies more than 3 times, suggest they describe the full shape they want instead of incremental changes.
- Skip confirmation only if the user already said "just do it" or equivalent in the same session.

### Stage 7: LAUNCH

Only proceed here after the user confirms with `yes`.

**Sequential** (implementer then reviewer):

```
Message 1: Task(subagent_type="sub-implementer", model="sonnet",
                description="Implement X", prompt="<contract>")
  -> wait for result
Message 2: Task(subagent_type="sub-reviewer", model="haiku",
                description="Review X", prompt="<contract>")
  -> wait for result
```

**Parallel** (independent writers, single message):

```
Message 1:
  Task(subagent_type="sub-implementer", description="Create file A", prompt="<contract A>")
  Task(subagent_type="sub-implementer", description="Create file B", prompt="<contract B>")
-> both run concurrently
```

**With worktree isolation** (parallel writers in the same directory):

```
Task(subagent_type="sub-implementer", isolation="worktree",
     description="Refactor module X", prompt="<contract>")
```

#### Engine Dispatch

The execution path depends on the selected engine:

**engine: `claude`** (default, Task tool):

```
Task(subagent_type="sub-implementer", model="sonnet",
     description="Implement X", prompt="<contract>")
```

**engine: `codex`** (shell -> `codex exec`):

```
1. Write prompt to a temporary file
2. Run: codex exec -m <model> -s <sandbox> "<prompt>"
3. Parse stdout
4. Record evidence
```

**engine: `gemini`** (shell -> Gemini CLI):

```
1. Write prompt to a temporary file
2. Run: npx @google/gemini-cli --prompt "<prompt>" --yolo [--model <model>]
3. Parse stdout
4. Record evidence
```

Mixed-engine runs can dispatch `claude`, `codex`, and `gemini` in the same stage when their scopes and dependencies allow it.

### Stage 7.5: WATCHDOG HOOK (Optional)

When the execution plan includes watchdog agents, run a watchdog check after each worker stage completes.

**Watchdog purpose**: Evaluate each worker's output against the original goal, not just technical correctness. A technically correct implementation that misses the goal is still a failure.

**Watchdog execution:**

1. After each worker returns, launch a watchdog agent (`sub-reviewer` with watchdog contract).
2. The watchdog evaluates whether the output advances the original goal and is complete enough for the next stage.
3. The watchdog returns `PASS` or `SHORTFALL` with specific findings.

**3-Choice Protocol (on SHORTFALL):**

| Choice | Condition | Action |
|---|---|---|
| **Accept** | Feedback is rational and actionable | Incorporate feedback. Launch `sub-fixer` or re-implement. Then re-run the watchdog. |
| **Reject** | Feedback is disconnected from the actual task or unrealistic | Log the rejection reason in evidence. Proceed with the current output. |
| **Escalate** | Judgment is ambiguous | Present both the output and the watchdog's findings to the user. |

**Decision criteria for the orchestrator:**
- Does the watchdog cite a specific gap between the output and the original goal?
- Is the suggested fix within the original scope and feasible?
- Does the feedback contradict the user's explicit requirements?

**Watchdog cycle limit**: Maximum 1 watchdog-fix cycle per worker stage. If the re-fixed output still gets `SHORTFALL`, escalate to the user.

### Stage 8: VALIDATE

After each worker returns:

1. **Check deliverables**: verify output files exist.
2. **Read content**: verify files are non-empty and reasonable.
3. **Parse worker summary**: check what changed, validation results, and remaining uncertainty.
4. **Parse reviewer verdict**: `ACCEPTED | MINOR_ISSUES | MATERIAL_ISSUES`.
5. **Check convergence**: if output or review is repetitive, uniformly long, or stuck in open-ended option listing, treat that as a contract-quality issue and tighten the next contract or rerun scope.
6. **Check decisiveness by role**: planner, analyzer, reviewer, and watchdog outputs should converge on a clear recommendation or verdict; reviewer and watchdog findings should stay material, evidence-backed, and paired with one fix direction.

### Stage 9: EVIDENCE + RECOVER or ACCEPT

This is a blocking stage. Do not report success to the user before evidence is written.

**If `ACCEPTED` or `MINOR_ISSUES`:**

Evidence writing is mandatory and non-delegatable. The orchestrator writes it directly.

**Evidence directory selection**:
- Single engine: `subagent-runs/<engine>/<run-name>/`
- Mixed engine: `subagent-runs/mixed/<run-name>/`

1. Name the run: `<task-slug>-<YYYY-MM-DD>` (append `-2`, `-3` on collision).
2. Create the run directory.
3. Write `run-manifest.md`.
4. Write `run-summary.md`.
5. Write `prompts/<role>.prompt.md` for each worker.
6. Write `results/<role>.result.md` for each worker.
7. Report to the user, including the run directory path.

Use the evidence level appropriate to the run shape (see `evidence-format.md`). When in doubt, write more, not less.

When watchdog was enabled, include watchdog results in the evidence.

**If `MATERIAL_ISSUES`:**

1. Extract the reviewer's specific findings.
2. Launch `sub-fixer` with only those findings and the original writable scope.
3. After fixer returns, launch `sub-reviewer` again.
4. Maximum 2 fix-review cycles.
5. If still failing after 2 cycles: stop, write evidence, escalate to the user.

## Fallback Protocol

When the orchestration path fails:

| Failure | Response |
|---|---|
| Task tool returns error | Retry once with a simplified prompt. If it still fails, report to the user. |
| Worker exceeds writable scope | Discard the result. Re-launch with an explicit warning in the contract. |
| Worker returns empty or incomplete | Check whether the task was too vague. Re-launch with a more specific contract. |
| Worker times out | Read partial results if useful; otherwise re-launch. |
| Review-fix loop exceeds 2 cycles | Stop automation. Write evidence and report to the user. |
| Workspace in a bad state | Do not proceed. Report the state to the user. |
| One parallel worker succeeds, another fails | Preserve the successful output. Retry the failed worker, then report partial success if needed. |

Never pretend evidence or artifacts were produced when they were not.

## Evidence Writing Mechanism

Evidence files are written by the orchestrator using the Write tool. This applies to every completed run: successful, failed, or aborted.

Key points:
- Failed or aborted runs still get full evidence.
- Evidence level depends on run shape; Pattern B and above produce full evidence by default.
- Write evidence after the final verdict is known and before reporting to the user.

## Efficiency Signals

Measure orchestration quality by:

| Signal | Good | Bad |
|---|---|---|
| Agents per deliverable | <= 2 | 4+ per deliverable |
| Fix-review cycles | 0-1 | 2+ |
| Parent interventions | 0 | Multiple manual patches |
| Final read-only review | Always present | Skipped |
| Model selection | Cheapest adequate | Opus everywhere |
| Scope compliance | 100% within boundary | Unauthorized changes |
| Watchdog cycles | 0-1 per stage | 2+ per stage |
| Watchdog accept/reject ratio | Mostly accept | Mostly reject |
