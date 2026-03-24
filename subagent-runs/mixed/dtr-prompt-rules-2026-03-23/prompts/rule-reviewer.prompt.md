You are the mixed-engine reviewer sidecar for a /submix orchestration run in `C:\Users\haj\projects\subagent-orchestrator`.

Task: review the current orchestrator docs/templates before edits and identify where prompt/contract quality is weak relative to these target principles from `deep-thinking-tokens-guide.md`:
- focus reasoning on real decision points
- avoid repetitive or uniformly long outputs
- require clear choice plus evidence/justification
- suppress ambiguous possibility-listing without decision
- stop once confidence is sufficient

Do not edit files.

Files in scope:
- `skills/claude-subagent-orchestrator/references/agent-contract.md`
- `skills/claude-subagent-orchestrator/references/sub-command-protocol.md`
- `skills/claude-subagent-orchestrator/references/orchestration-workflow.md`
- `skills/claude-subagent-orchestrator/assets/prompt-templates/pattern-a-solo.md`
- `skills/claude-subagent-orchestrator/assets/prompt-templates/pattern-b-implement-review.md`
- `skills/claude-subagent-orchestrator/assets/prompt-templates/pattern-c-parallel-review.md`
- `skills/claude-subagent-orchestrator/assets/prompt-templates/pattern-d-plan-implement-review.md`
- `skills/claude-subagent-orchestrator/assets/prompt-templates/pattern-e-full-loop.md`

Return:
1. Concise findings first, by file
2. Highest-risk wording gaps
3. Reviewer criteria suggestions that would catch overthinking or vague outputs
4. What should not be changed to avoid bloating prompts
5. File list referenced
