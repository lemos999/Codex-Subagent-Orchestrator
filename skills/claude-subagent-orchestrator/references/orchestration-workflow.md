# Orchestration Workflow

## Workflow Stages

### Stage 1: CLASSIFY

Determine before choosing any team shape:

- **Task type**: create, fix, refactor, review, analyze
- **Complexity**: low (boilerplate), medium (logic), high (architecture)
- **Parallelism**: are there independent subtasks with disjoint file scopes?
- **Review need**: does output persist? (yes → review required)

### Stage 2: CHOOSE TEAM

See `sub-command-protocol.md` for team sizing rules and model allocation. Choose the pattern:

| Pattern | Shape | When |
|---|---|---|
| **A: Solo** | 1 agent (implementer OR reviewer) | Single bounded task: implementer for low-risk writes, reviewer for validation-only requests, Explore agent for research |
| **B: Implement + Review** | implementer → reviewer | Standard deliverable (**default**) |
| **C: Parallel + Review** | N implementers ∥ → reviewer | Independent outputs, disjoint scopes |
| **D: Plan + Implement + Review** | planner → implementer → reviewer | Complex task needing design first |
| **E: Full Loop** | implementer → reviewer → fixer → reviewer | Known risk, expected repairs |

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
- It's the first run in a new workspace and you want to ensure contract awareness

**If AGENTS.md does not exist** at the workspace root, skip shared directive injection entirely. Note this in the run manifest under Errors/Notes: "No AGENTS.md found — shared directive skipped."

### Stage 4: BUILD CONTRACTS

Build a complete contract for each worker per the format in `agent-contract.md`.

Each contract includes:
- Task, inspect-first list, writable scope, validation, return contract, stop condition
- Shared directive (reference or inline, per Stage 3)
- Tool guidance (which tools the worker should/should not use)

### Stage 5: SELECT SETTINGS

Per worker:

| Setting | Decision |
|---|---|
| `engine` | 기본값 `claude` (Task tool). 사용자가 지정하거나 역할-엔진 호환성에 따라 `codex` 또는 `gemini` 선택. `engine-adapters.md` 참조 |
| `model` | See model allocation in `sub-command-protocol.md` — engine별로 사용 가능한 모델이 다름 |
| `isolation` | `"worktree"` only when parallel writers could touch overlapping directories |
| `run_in_background` | `true` only for truly independent long tasks where you have other work to do |
| `max_turns` | Set to limit runaway agents (optional, use when task is well-bounded) |

**Engine-role validation**: engine 선택 후 `engine-adapters.md`의 호환성 매트릭스를 확인한다. 비호환 조합(예: `claude` CLI --print + implementer)은 자동으로 대체하거나 에러로 거부한다.

### Stage 6: CONFIRM

Before launching, present the execution plan to the user and wait for confirmation.

**Display format:**

```markdown
## /sub Execution Plan

**Request**: [abbreviated original request]
**Pattern**: [pattern name — e.g., "B: Implement + Review"]

| # | Agent | Role | Engine | Model | reasoning | Goal |
|---|-------|------|--------|-------|-----------|------|
| 1 | impl-name | implementer | codex | gpt-5.4 | medium | [one-line goal] |
| 2 | review-name | reviewer | claude | haiku | low | [one-line goal] |

When watchdog is enabled, add a "Watchdog" column to the execution plan:

| # | Agent | Role | Engine | Model | reasoning | Goal | Watchdog |
|---|-------|------|--------|-------|-----------|------|----------|
| 1 | impl-name | implementer | codex | gpt-5.4 | medium | [goal] | yes |
| 2 | review-name | reviewer | claude | haiku | low | [goal] | no |

**Estimated cost**: [low / medium / high based on model + agent count]

> **yes** — proceed as planned
> **no** — cancel this /sub
> **modify** — tell me what to change (e.g., "use opus for reviewer", "add a planner", "remove agent 2")
```

**User response handling:**

| Response | Action |
|---|---|
| **yes** | Proceed to Stage 7: LAUNCH |
| **no** | Abort. Write no evidence. Report cancellation to user. |
| **modify** | Apply requested changes (model swap, agent add/remove, role change), then re-display the updated plan and ask again. |

**Rules:**
- Always show the plan before first launch — no silent execution
- After a **modify**, re-display the full updated table for re-confirmation
- If the user modifies more than 3 times, suggest they describe the full shape they want instead of incremental changes
- The confirmation step is skipped only if the user previously said "just do it" or equivalent in the same session

### Stage 7: LAUNCH

Only proceed here after user confirms with **yes** in Stage 6.

**Sequential** (implementer then reviewer):
```
Message 1: Task(subagent_type="sub-implementer", model="sonnet",
                description="Implement X", prompt="<contract>")
  → Wait for result
Message 2: Task(subagent_type="sub-reviewer", model="haiku",
                description="Review X", prompt="<contract>")
  → Wait for result
```

**Parallel** (independent writers — single message):
```
Message 1:
  Task(subagent_type="sub-implementer", description="Create file A", prompt="<contract A>")
  Task(subagent_type="sub-implementer", description="Create file B", prompt="<contract B>")
→ Both run concurrently, results arrive together
```

**With worktree isolation** (parallel writers in same directory):
```
Task(subagent_type="sub-implementer", isolation="worktree",
     description="Refactor module X", prompt="<contract>")
```

#### Engine Dispatch

engine 필드에 따라 워커 실행 방식이 달라진다:

**engine: "claude" (기본 -- Task tool 네이티브)**:
기존과 동일. Agent tool로 직접 호출.
```
Task(subagent_type="sub-implementer", model="sonnet",
     description="Implement X", prompt="<contract>")
```

**engine: "codex" (Bash -> codex exec)**:
Bash tool로 `codex exec` 호출. 프롬프트는 파일로 저장 후 전달.
```
1. Write prompt to temporary file
2. Bash: codex exec -m <model> -s <sandbox> "$(cat prompt-file)"
3. Parse stdout for response
4. Record in evidence
```

**engine: "gemini" (Bash -> gemini CLI)**:
Bash tool로 Gemini CLI 호출.
```
1. Write prompt to temporary file
2. Bash: npx @google/gemini-cli --prompt "$(cat prompt-file)" --yolo [--model <model>]
3. Parse stdout for response
4. Record in evidence
```

**혼합 엔진 병렬 실행**:
같은 스테이지에서 서로 다른 엔진의 워커가 병렬 실행 가능. Claude 워커는 Agent tool, 외부 엔진 워커는 Bash tool로 동시 호출.
```
Message 1:
  Agent(subagent_type="sub-implementer", prompt="<claude contract>")
  Bash("codex exec -m gpt-5.4 '<codex contract>'")
-> Both run concurrently
```

### Stage 7.5: WATCHDOG HOOK (Optional)

When the execution plan includes watchdog agents (see `sub-command-protocol.md` for when to enable), run a watchdog check after each worker stage completes.

**Watchdog purpose:** Evaluate each worker's output against the **original goal**, not just technical correctness. A technically correct implementation that misses the goal is still a failure.

**Watchdog execution:**

1. After each worker returns, launch a watchdog agent (sub-reviewer with watchdog contract)
2. Watchdog evaluates: "Does this output advance the original goal? Is the quality sufficient?"
3. Watchdog returns one of: PASS / SHORTFALL (with specific findings)

**3-Choice Protocol (on SHORTFALL):**

When a watchdog reports SHORTFALL, the orchestrator acts as **기획 리더 (Planning Leader)** and evaluates the watchdog's feedback:

| Choice | Condition | Action |
|--------|-----------|--------|
| **Accept** | Feedback is rational and actionable | Incorporate feedback. Launch `sub-fixer` or re-implement. Then re-run watchdog on the fixed output. |
| **Reject** | Feedback is disconnected from the actual task, unrealistic, or based on misunderstanding | Log rejection reason in evidence. Proceed with current output. |
| **Escalate** | Judgment is ambiguous — both the output and the feedback have merit | Present both the output and the watchdog's findings to the user. Wait for user decision. |

**Decision criteria for the orchestrator:**
- Does the watchdog's finding cite a specific gap between the output and the original goal?
- Is the suggested fix within the original scope and feasible?
- Does the feedback contradict the user's explicit requirements?

**Watchdog cycle limit:** Maximum **1 watchdog-fix cycle per worker stage**. If the re-fixed output still gets SHORTFALL, escalate to user.

**Integration with existing stages:**
- Stage 7.5 runs between Stage 7 (LAUNCH) and Stage 8 (VALIDATE)
- If all watchdogs PASS, proceed to Stage 8 normally
- Stage 8 (VALIDATE) still runs — watchdog checks goal alignment, Stage 8 checks deliverable completeness
- Stage 9 (RECOVER) handles reviewer findings, which are separate from watchdog findings

### Stage 8: VALIDATE

After each worker returns:

1. **Check deliverables**: Use Glob to verify output files exist
2. **Read content**: Use Read to verify files are non-empty and reasonable
3. **Parse worker summary**: Check what changed, validation results, uncertainties
4. **Parse reviewer verdict**: ACCEPTED / MINOR_ISSUES / MATERIAL_ISSUES

### Stage 9: EVIDENCE + RECOVER or ACCEPT

> ⚠️ **BLOCKING STAGE**: 이 단계를 완료하지 않으면 사용자에게 결과를 보고할 수 없다. Evidence 작성은 결과 보고의 **전제 조건**이다.

**If ACCEPTED or MINOR_ISSUES:**

**Critical rule**: Evidence writing is mandatory and non-delegatable. The orchestrator writes it using the Write tool directly — never a worker, never skipped.

**Evidence directory selection**:
- 모든 워커가 동일 엔진: `subagent-runs/<engine>/<run-name>/`
- 복수 엔진 사용: `subagent-runs/mixed/<run-name>/`

1. Name the run: `<task-slug>-<YYYY-MM-DD>` (append `-2`, `-3` on collision)
2. Create the run directory: `subagent-runs/<engine>/<run-name>/` (single engine) or `subagent-runs/mixed/<run-name>/` (multiple engines)
3. Write `subagent-runs/<engine>/<run-name>/run-manifest.md` — authoritative structured record
4. Write `subagent-runs/<engine>/<run-name>/run-summary.md` — compact one-liner-per-agent table
5. Write `subagent-runs/<engine>/<run-name>/prompts/<role>.prompt.md` for each worker — exact prompt text sent
6. Write `subagent-runs/<engine>/<run-name>/results/<role>.result.md` for each worker — full return text
7. Report to user, including the run directory path

Use the evidence level appropriate to the run shape (see evidence level table in `evidence-format.md`): full, standard, or light. When in doubt, write more, not less.

When watchdog was enabled, include watchdog results in the evidence: stages watched, PASS/SHORTFALL verdicts per stage, and the orchestrator's Accept/Reject/Escalate decision for each SHORTFALL finding.

**If MATERIAL_ISSUES:**
1. Extract reviewer's specific findings
2. Launch `sub-fixer` with:
   - Only the reviewer's findings as task input
   - Original writable scope (not broader)
   - Reference to the reviewer's finding text
3. After fixer returns, launch `sub-reviewer` again
4. Maximum **2 fix-review cycles**
5. If still failing after 2 cycles: stop, write evidence, escalate to user

## Fallback Protocol

When the orchestration path fails:

| Failure | Response |
|---|---|
| Task tool returns error | Retry once with simplified prompt. If still failing, report to user. |
| Worker exceeds writable scope | Discard result. Re-launch with explicit warning in contract. |
| Worker returns empty/incomplete | Check if task was too vague. Re-launch with more specific contract. |
| Worker times out | Read partial results (resume with agent ID if useful). Otherwise re-launch. |
| Review-fix loop exceeds 2 cycles | Stop automation. Write evidence of what happened. Report to user. |
| Workspace in bad state (merge conflicts, etc.) | Do not proceed. Report state to user. |
| One parallel worker succeeds, another fails | Preserve the successful output. Retry the failed worker. If retry fails, report partial success to user with evidence. |

**Critical rule**: Never pretend evidence or artifacts were produced when they weren't. If the orchestration fails partway, document exactly what succeeded and what didn't.

## Evidence Writing Mechanism

Evidence files are written by the orchestrator (parent) using the **Write** tool. This applies to every completed run — successful, failed, or aborted.

The file templates and field definitions are in `evidence-format.md`. Key points:

- **Failed/aborted runs** get full evidence. Document exactly which agents completed, which failed, and why.
- **Evidence level** depends on run shape — see the evidence level table in `evidence-format.md`. Pattern B and above produce full evidence by default.
- **Timing**: write evidence after the final verdict is known, before reporting to the user.

See Stage 9 for the mandatory per-file write sequence.

## Efficiency Signals

Measure orchestration quality by:

| Signal | Good | Bad |
|---|---|---|
| Agents per deliverable | ≤ 2 | 4+ per deliverable |
| Fix-review cycles | 0-1 | 2+ |
| Parent interventions | 0 | Multiple manual patches |
| Final read-only review | Always present | Skipped |
| Model selection | Cheapest adequate | Opus everywhere |
| Scope compliance | 100% within boundary | Unauthorized changes |
| Watchdog cycles | 0-1 per stage | 2+ per stage |
| Watchdog accept/reject ratio | Mostly accept | Mostly reject (watchdog may be miscalibrated) |
