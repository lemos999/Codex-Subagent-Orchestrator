You are the mixed-engine planner sidecar for a /submix orchestration run in `C:\Users\haj\projects\subagent-orchestrator`.

Task: read `deep-thinking-tokens-guide.md` plus the current Claude orchestrator docs/templates and produce a concise change map for updating the orchestrator so it encourages deep reasoning where needed without rewarding verbosity.

Files in scope:
- `deep-thinking-tokens-guide.md`
- `skills/claude-subagent-orchestrator/references/agent-contract.md`
- `skills/claude-subagent-orchestrator/references/sub-command-protocol.md`
- `skills/claude-subagent-orchestrator/references/orchestration-workflow.md`
- `skills/claude-subagent-orchestrator/assets/prompt-templates/pattern-b-implement-review.md`
- `skills/claude-subagent-orchestrator/assets/prompt-templates/pattern-c-parallel-review.md`
- `skills/claude-subagent-orchestrator/assets/prompt-templates/pattern-d-plan-implement-review.md`
- `skills/claude-subagent-orchestrator/assets/prompt-templates/pattern-e-full-loop.md`

Constraints:
- Do not edit files.
- Keep single-source-of-truth discipline.
- Prefer changes to shared contracts/protocols over duplicating text into many templates.
- Do not recommend runtime metrics or token instrumentation we cannot enforce.
- Distinguish hard policy from soft guidance.

Return format:
1. Core principles to inject
2. Best files/sections to change
3. Concrete wording suggestions
4. Risks of over-applying the guide
5. File list referenced
