# /sub Command Protocol

This is the single source of truth for task classification, team sizing, and model allocation.

## Entry

1. Strip `/sub` prefix.
2. Classify the remaining text.
3. Enter supervisor mode.
4. Plan the team and present the execution plan to the user (`Stage 6: CONFIRM`).
5. Wait for user confirmation: `yes` / `no` / `modify`.
6. On `yes`: decompose, delegate, validate.
7. On `modify`: adjust plan per user feedback, re-present, and re-confirm.
8. On `no`: abort without execution.

## Task Classification

| Category | Indicators | Default Pattern |
|---|---|---|
| **Create** | "make", "create", "add", "write", "generate" | B: Implement + Review |
| **Fix** | "fix", "repair", "resolve", "debug" | B: Implement + Review |
| **Refactor** | "refactor", "reorganize", "restructure" | B: Implement + Review (`opus` implementer) |
| **Review** | "review", "check", "validate", "audit" | A: Solo reviewer |
| **Analyze** | "analyze", "investigate", "explore" | A: Solo (Explore or general-purpose agent) |
| **Multi-output** | "create X and Y", "both A and B" | C: Parallel + Review |

## Complexity Assessment

| Level | Signals | Default Model |
|---|---|---|
| **Low** | Single file, clear spec, boilerplate, repetitive | `haiku` |
| **Medium** | Multiple files, moderate logic, existing patterns to follow | `sonnet` |
| **High** | Architecture decisions, cross-cutting, nuanced trade-offs | `opus` |

## Team Sizing (Authoritative)

```
0 agents -- trivial, parent handles directly
           (single-line edit already known, no inspection needed, one Edit call suffices)
1 agent  -- bounded task, low risk, or ephemeral output (no review needed)
           (requires file inspection, multi-line generation, or tool use beyond quick Edit)
2 agents -- implementer -> reviewer (default for any persistent deliverable)
3 agents -- parallel implementers -> reviewer, or planner -> implementer -> reviewer
4 agents -- maximum per /sub request (only when parallelism saves wall-clock time)
```

**Escalation**: If the task requires 5+ agents, decompose it into multiple `/sub` calls.

## Watchdog Activation Rules

Watchdog hooks are optional and add one agent per watched stage. Enable when:

| Condition | Watchdog | Rationale |
|---|---|---|
| User explicitly requests watchdog or goal monitoring | YES | User directive |
| High complexity + persistent output | YES | Goal drift risk is high |
| Architecture/design tasks (Pattern D, E) | YES | Design decisions need goal alignment checks |
| Low complexity or ephemeral output | NO | Overhead exceeds benefit |
| Solo reviewer (Pattern A review-only) | NO | Already a validation task |

**Watchdog does not replace the reviewer.** Watchdog checks goal alignment; reviewer checks technical correctness and scope compliance. Both can run on the same output.

When watchdog is enabled, team size increases by the number of watched stages (typically +1 to +3 agents). The 4-agent-per-`/sub` limit applies to non-watchdog agents only.

## Engine & Model Allocation (Authoritative)

### Engine Allocation

| Role | Default Engine | Override When |
|---|---|---|
| Implementer | `claude` (Task tool) | The user explicitly requests `codex` or `gemini` |
| Reviewer | `claude` (Task tool) | The review is analysis-heavy and an external engine is a better fit |
| Fixer | `claude` (Task tool) | A different engine is explicitly justified |
| Planner | `claude` (Task tool) | The task benefits from `codex` or `gemini` strengths |
| Watchdog | `claude` (Task tool) | Another engine is explicitly justified |

If `engine` is omitted, default to `"claude"` (Task tool). See [engine-adapters.md](engine-adapters.md) for engine-specific constraints.

### Engine-Model Mapping

| Engine | Available Models | Default |
|---|---|---|
| `claude` | `haiku`, `sonnet`, `opus` | `sonnet` |
| `codex` | `gpt-5.4`, `o3`, `o4-mini` | `gpt-5.4` |
| `gemini` | `gemini-2.5-pro`, `gemini-2.5-flash` | `gemini-2.5-pro` |

### Model Allocation (`engine: "claude"` default path)

| Role | Default | Override When |
|---|---|---|
| Implementer | `sonnet` | `haiku` for boilerplate; `opus` for architecture or complex logic |
| Reviewer | `haiku` | `sonnet` for deep logic review; `opus` for security-critical review |
| Fixer | `sonnet` | `haiku` for trivial one-line fixes |
| Planner | `opus` | `sonnet` if planning is straightforward |
| Watchdog | `sonnet` | `haiku` for simple goal checks; `opus` for nuanced goal alignment |

**Economy rule**: Never use a more expensive model when a cheaper one produces equivalent results.

## Reasoning Discipline (Authoritative)

- Use the smallest reasoning depth that fully resolves the task.
- Spend deeper analysis only at genuine decision points: ambiguity, material trade-offs, root-cause analysis, architecture, or high-risk review.
- Keep routine implementation, boilerplate, and mechanical edits narrow and brief.
- Prefer outputs that converge on one recommendation with concrete justification over broad possibility lists.
- Analyze and explore routes must still end with a conclusion or recommended next step, not an open-ended survey.
- Treat repeated points, uniformly long explanations, and unresolved branching as prompt-quality failures, not signs of rigor.

## Parallel Execution Rules

Launch multiple `Task` calls in a single message only when all conditions are met:

1. **Disjoint file scopes** -- no overlapping writable paths.
2. **No data dependency** -- neither worker reads what the other writes.
3. **Deterministic merge** -- results combine without conflict.

If any condition fails, run sequentially.

Workers in the same stage run in parallel. Later-stage workers (reviewers) always wait for earlier-stage workers (implementers).

## Review Gate Rules

| Output Type | Review Required? |
|---|---|
| Committed code | YES -- mandatory |
| User-facing documents | YES -- mandatory |
| Config files | YES -- mandatory |
| Analysis/exploration results | NO -- ephemeral |
| One-time answers | NO -- ephemeral |
| Logs/debug output | NO -- ephemeral |

## Reporting Format

Every `/sub` completion uses this structure:

```markdown
## /sub Result

**Request**: [abbreviated original request]
**Route**: [pattern used -- e.g., "B: implementer (codex/gpt-5.4) -> reviewer (claude/haiku)"]
**Status**: DELIVERED | DELIVERED_WITH_NOTES | NEEDS_ATTENTION

### Changes
- [file]: [created | modified] -- [what changed]

### Review
- Verdict: [ACCEPTED | MINOR_ISSUES | MATERIAL_ISSUES]
- Findings: [list if any]
- Fix cycles: [0 | 1 | 2]

### Evidence
- `subagent-runs/claude/<run-name>/`

### Watchdog
- Stages watched: [list]
- Findings: [PASS / SHORTFALL per stage]
- Leader decisions: [Accept / Reject / Escalate per finding]

### Open Items
- [unresolved items, if any]
```
