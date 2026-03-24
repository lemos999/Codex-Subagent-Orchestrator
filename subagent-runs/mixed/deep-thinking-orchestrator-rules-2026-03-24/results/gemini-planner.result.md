### 1. Core Principles to Inject

The central idea is to shift agent behavior from prioritizing output length to prioritizing reasoning depth.

- **Depth over Length**: Focus cognitive effort on critical, non-obvious decision points. State self-evident facts or boilerplate code concisely without elaboration.
- **Decisive Reasoning**: Avoid hedging, listing endless possibilities without commitment, or repeating the same point in different words. Make a choice and justify it.
- **Front-loaded Quality**: The initial approach and problem framing are the most critical. A strong start is a better indicator of success than a long, meandering process.
- **Targeted Elaboration**: Output length should be non-uniform. Be brief for simple parts and detailed only for complex, high-uncertainty sections of the task.

### 2. Best Files/Sections to Change

1. `skills/claude-subagent-orchestrator/references/agent-contract.md`
2. `skills/claude-subagent-orchestrator/assets/prompt-templates/pattern-b-implement-review.md`
3. Other templates only for light reinforcement, not policy duplication

### 3. Specific Wording Suggestions

- Add a shared reasoning-discipline rule so workers stop after the answer is sufficiently supported.
- Prefer a single decision with one or two concrete reasons over broad possibility lists.
- Add review checks for repeated points, open-ended branching, and failure to converge on a justified decision.

### 4. Risks of Over-Applying the Guide

- False conciseness that cuts substance instead of fluff
- Inhibiting exploration on legitimately ambiguous tasks
- Pretending DTR-like telemetry can be measured in runtime
- Over-duplicating the same policy into every template
