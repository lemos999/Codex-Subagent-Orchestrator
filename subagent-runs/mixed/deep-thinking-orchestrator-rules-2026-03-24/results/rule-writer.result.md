Updated the documentation-policy layer to encode "depth over length" without inventing any DTR/runtime enforcement.

Files changed:
- `skills/claude-subagent-orchestrator/references/agent-contract.md`
- `skills/claude-subagent-orchestrator/references/sub-command-protocol.md`
- `skills/claude-subagent-orchestrator/references/orchestration-workflow.md`
- `skills/claude-subagent-orchestrator/assets/prompt-templates/pattern-a-solo.md`
- `skills/claude-subagent-orchestrator/assets/prompt-templates/pattern-b-implement-review.md`
- `skills/claude-subagent-orchestrator/assets/prompt-templates/pattern-d-plan-implement-review.md`

Per-file summary:
- `agent-contract.md`: added centralized reasoning-discipline rules, tightened return/stop expectations, and updated reviewer/watchdog/fixer contract language to prefer decisive, evidence-backed outputs over repetitive or speculative ones.
- `sub-command-protocol.md`: added an authoritative reasoning-discipline section tying orchestration economy to real decision points instead of raw output length.
- `orchestration-workflow.md`: added contract-building and validation guidance so supervisors ask for one chosen route when needed and treat repetition/open-ended branching as contract-quality issues.
- `pattern-a-solo.md`: lightly tightened solo implementer/reviewer prompts around key decision reporting and verdict convergence.
- `pattern-b-implement-review.md`: added decision-quality review criteria, made findings higher-signal, and tightened implementer/watchdog return/stop rules.
- `pattern-d-plan-implement-review.md`: made the planner converge on one recommended route with at most one material fallback, and pushed implementer/reviewer/watchdog language to resolve material branches instead of carrying them forward.

Key wording choices:
- Used "decision points", "one chosen route", "stop once sufficiently supported", and "high-signal findings" as the recurring vocabulary.
- Explicitly treated repetition, uniformly long explanation, and speculative branch-listing without decision as quality failures.
- Kept DTR out of the operational docs entirely; no telemetry, thresholds, or hidden-runtime claims.

Residual risk / ambiguity:
- Five of the target files are currently untracked in this repo, so they show up as new files rather than modified tracked files. I did not touch anything outside the authorized scope.
- I rewrote the affected markdown files cleanly instead of doing tiny line edits because the originals had mojibake/encoding-noisy text that made precise patching unreliable.
- No tests were run; this was a docs/template-only change.
