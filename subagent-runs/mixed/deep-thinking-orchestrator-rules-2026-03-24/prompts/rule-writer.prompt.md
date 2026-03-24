You are the implementer for a `/submix` documentation-policy update in `C:\Users\haj\projects\subagent-orchestrator`.

Ownership / writable scope:
- `skills/claude-subagent-orchestrator/references/agent-contract.md`
- `skills/claude-subagent-orchestrator/references/sub-command-protocol.md`
- `skills/claude-subagent-orchestrator/references/orchestration-workflow.md`
- `skills/claude-subagent-orchestrator/assets/prompt-templates/pattern-a-solo.md`
- `skills/claude-subagent-orchestrator/assets/prompt-templates/pattern-b-implement-review.md`
- `skills/claude-subagent-orchestrator/assets/prompt-templates/pattern-d-plan-implement-review.md`

You are not alone in the codebase. Do not revert edits made by others. Only modify the files above.

Task:
Integrate the practical principles from `deep-thinking-tokens-guide.md` into the Claude subagent orchestrator docs/templates.

Desired outcome:
- Shared docs emphasize depth over length, decision-point focus, concise handling of obvious points, clear choice + justification, and stopping once confidence is sufficient.
- Overthinking is treated as a prompt-quality failure signal: repetition, uniformly long output, speculative option listing without decision.
- The docs must not imply numeric DTR measurement or unenforceable telemetry.
- Maintain single-source-of-truth discipline. Put most policy in shared references; templates should only add light role-specific shaping.

Implementation guidance:
- In `agent-contract.md`, add concise general reasoning-discipline rules and reflect them in return/stop expectations.
- In `sub-command-protocol.md`, codify economy/reasoning-depth policy for orchestration decisions.
- In `orchestration-workflow.md`, add minimal guidance on building/validating contracts so workers converge on decisions instead of verbose branching.
- In `pattern-a-solo.md` and `pattern-b-implement-review.md`, lightly tighten implementer/reviewer prompts.
- In `pattern-d-plan-implement-review.md`, ensure planner output converges on one recommended route with at most one fallback if materially needed.
- Avoid bloating templates or duplicating long policy blocks.

Validation:
- Keep wording concise and consistent.
- No mentions of measuring DTR/runtime internals.
- No files outside scope changed.

Return:
- Files changed with a short summary per file
- Key wording choices
- Any residual risk or ambiguity
- Explicitly list the file paths changed
