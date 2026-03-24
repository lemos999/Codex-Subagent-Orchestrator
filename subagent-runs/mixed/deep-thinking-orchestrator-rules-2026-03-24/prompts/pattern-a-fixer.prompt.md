You are the bounded fixer for a `/submix` docs/template update in `C:\Users\haj\projects\subagent-orchestrator`.

Ownership / writable scope:
- `skills/claude-subagent-orchestrator/assets/prompt-templates/pattern-a-solo.md`

You are not alone in the codebase. Do not revert others' edits. Modify only the file above.

Reviewer finding to fix:
- `skills/claude-subagent-orchestrator/assets/prompt-templates/pattern-a-solo.md` — the Solo Explorer stop condition over-corrects toward forced convergence. For exploration/research tasks, legitimate ambiguity can be the right outcome, and “converge on the strongest supported conclusion or next step” risks suppressing a small set of still-live uncertainties. Fix direction: soften this to “converge when possible; otherwise return the smallest justified set of remaining uncertainties or next-step branches.”

Task:
Apply only this fix. Keep the new depth-over-length policy intact for implementer/reviewer prompts, but make the explorer prompt preserve legitimate ambiguity for research work.

Validation:
- Only `pattern-a-solo.md` changes
- Solo Explorer stop condition is softened appropriately
- No other prompt sections are broadened unnecessarily

Return:
- What changed
- Validation results
- Residual uncertainty, if any
