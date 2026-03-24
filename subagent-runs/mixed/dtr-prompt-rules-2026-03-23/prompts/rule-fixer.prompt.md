You are the scoped fixer for a /submix orchestration run in `C:\Users\haj\projects\subagent-orchestrator`.

Task: fix only the reviewer-reported issues below in the authorized files. Do not touch any other file and do not broaden scope.

Reviewer findings to fix:
1. `skills/claude-subagent-orchestrator/assets/prompt-templates/pattern-c-parallel-review.md`
   - Corrupted separators/text appear in reviewer and watchdog sections (examples: `??`, broken arrows, malformed worker-stage labels).
   - Fix direction: normalize those lines into plain, unambiguous English using normal ASCII separators such as `->` or `--`.
2. `skills/claude-subagent-orchestrator/assets/prompt-templates/pattern-e-full-loop.md`
   - Corrupted separators/text appear in the title, fixer contract, and watchdog flow/comments.
   - Fix direction: normalize those lines into plain, unambiguous English; preserve the actual workflow semantics.
3. `skills/claude-subagent-orchestrator/assets/prompt-templates/pattern-a-solo.md`
   - The Solo Explorer prompt omits the shared directive opener used by other templates.
   - Fix direction: prepend the same shared-directive opener pattern used by the other prompt templates, unless the file already contains an explicit exception.

Inspect first:
- `skills/claude-subagent-orchestrator/assets/prompt-templates/pattern-a-solo.md`
- `skills/claude-subagent-orchestrator/assets/prompt-templates/pattern-c-parallel-review.md`
- `skills/claude-subagent-orchestrator/assets/prompt-templates/pattern-e-full-loop.md`
- `subagent-runs/mixed/dtr-prompt-rules-2026-03-23/engines/codex/final-reviewer.raw.txt`

Writable scope:
- `skills/claude-subagent-orchestrator/assets/prompt-templates/pattern-a-solo.md` (modify)
- `skills/claude-subagent-orchestrator/assets/prompt-templates/pattern-c-parallel-review.md` (modify)
- `skills/claude-subagent-orchestrator/assets/prompt-templates/pattern-e-full-loop.md` (modify)

Validation:
1. No malformed separator artifacts remain in the edited sections.
2. `pattern-a-solo.md` explorer prompt now begins with the shared-directive opener.
3. No files outside writable scope are modified.

Return:
- Finding -> fix mapping
- Validation results
- Any blocking or correctness-relevant uncertainty only
