You are the implementer worker for a /submix orchestration run in `C:\Users\haj\projects\subagent-orchestrator`.

Task: update the Claude orchestrator docs/templates so they reflect the principles from `deep-thinking-tokens-guide.md` without bloating prompts or duplicating policy across files.

Inspect first:
- `deep-thinking-tokens-guide.md`
- `skills/claude-subagent-orchestrator/references/agent-contract.md`
- `skills/claude-subagent-orchestrator/references/sub-command-protocol.md`
- `skills/claude-subagent-orchestrator/references/orchestration-workflow.md`
- `skills/claude-subagent-orchestrator/assets/prompt-templates/pattern-a-solo.md`
- `skills/claude-subagent-orchestrator/assets/prompt-templates/pattern-b-implement-review.md`
- `skills/claude-subagent-orchestrator/assets/prompt-templates/pattern-c-parallel-review.md`
- `skills/claude-subagent-orchestrator/assets/prompt-templates/pattern-d-plan-implement-review.md`
- `skills/claude-subagent-orchestrator/assets/prompt-templates/pattern-e-full-loop.md`
- `subagent-runs/mixed/dtr-prompt-rules-2026-03-23/engines/codex/policy-mapper.raw.txt`
- `subagent-runs/mixed/dtr-prompt-rules-2026-03-23/engines/codex/rule-reviewer.raw.txt`

Writable scope:
- `skills/claude-subagent-orchestrator/references/agent-contract.md` (modify)
- `skills/claude-subagent-orchestrator/references/sub-command-protocol.md` (modify)
- `skills/claude-subagent-orchestrator/references/orchestration-workflow.md` (modify)
- `skills/claude-subagent-orchestrator/assets/prompt-templates/pattern-a-solo.md` (modify)
- `skills/claude-subagent-orchestrator/assets/prompt-templates/pattern-b-implement-review.md` (modify)
- `skills/claude-subagent-orchestrator/assets/prompt-templates/pattern-c-parallel-review.md` (modify)
- `skills/claude-subagent-orchestrator/assets/prompt-templates/pattern-d-plan-implement-review.md` (modify)
- `skills/claude-subagent-orchestrator/assets/prompt-templates/pattern-e-full-loop.md` (modify)

Required changes:
1. Add shared reasoning-discipline rules in `agent-contract.md` that encode:
   - focus depth on actual decision points
   - keep obvious or settled points brief
   - do not pad with repetition, hedge lists, or generic possibility enumeration
   - when judgment is required, return a clear choice plus reason
   - any remaining uncertainty should be reported only when blocking or correctness-relevant
2. Add policy-level reasoning calibration in `sub-command-protocol.md`:
   - deep reasoning is for ambiguity, tradeoffs, root-cause analysis, architecture, and high-risk review
   - routine implementation and mechanical edits should stay narrow and brief
   - analyze/explore routes should still converge to a conclusion or recommended next step, not an open-ended option survey
3. Update `orchestration-workflow.md` so contract-building and validation explicitly check for decisive, non-bloated outputs where appropriate, without inventing token metrics.
4. Update prompt templates only where needed to stay consistent with shared policy:
   - remove or narrow wording that rewards open-ended uncertainty dumps
   - require reviewer findings to be material, evidence-backed, and paired with one fix direction
   - make planner/reviewer/watchdog prompts in higher-risk patterns prefer 1 strong alternative or counterargument over broad option dumps
   - keep templates lean; do not copy long doctrine into every file

Constraints:
- Preserve existing single-source-of-truth structure.
- Do not add unenforceable runtime measurements or token-based rules.
- Do not weaken writable-scope, self-validation, reviewer, fixer, or rereview safeguards.
- Keep wording crisp and operational.

Validation:
1. The shared rules in `agent-contract.md` are enough to carry most of the new doctrine.
2. Pattern templates remain aligned with the shared rules and do not contradict them.
3. Reviewer/watchdog templates now require evidence-backed, material findings.
4. No files outside writable scope are modified.

Return:
- Files changed with a one-line summary each
- Key policy decisions
- Validation results
- Any blocking or correctness-relevant uncertainty only
