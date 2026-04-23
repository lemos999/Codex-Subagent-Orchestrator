<!--
  ARCHIVED (2026-04-22) — content merged into `CLAUDE.md`

  History
  -------
  CLAUDE_new.md originated as an English draft of "Agent Directives:
  Mechanical Overrides" holding Rules 1~10 (Pre-Work, Code Quality,
  Context Management, Edit Safety). It predated the current Korean
  CLAUDE.md, which now holds the full 20 rules plus the priority block
  and Root Cause First section.

  Reason for consolidation (2026-04-22)
  -------------------------------------
  - Duplicate intent existed in both files; maintaining two copies
    risked rule drift between Claude sessions and other engines.
  - Several CLAUDE_new.md rules were STALE after refinements that
    landed in CLAUDE.md on the same day:
      * Rule 2 (PHASED EXECUTION)   — approval gate is now
        Auto Mode-conditional, not unconditional.
      * Rule 3 (SENIOR DEV OVERRIDE) — now scoped to the current task;
        large out-of-scope refactors require proposal + approval first.
      * Rule 4 (FORCED VERIFICATION) — multi-language (TS / Python /
        Rust examples) instead of TS-only hard-coding.
      * Rule 5 (SUB-AGENT SWARMING) — conditional "권장" with 3 triggers
        (independence, file count, non-triviality) instead of "MUST".
      * Rule 6 (CONTEXT DECAY)       — conditional on 3 explicit
        triggers instead of unconditional re-read every 10 messages.
      * Rule 9 (EDIT INTEGRITY)      — post-edit re-read no longer
        mandatory (harness tracks state); pre-edit re-read tied to
        Rule 6 conditions.
  - Unique details from CLAUDE_new.md that WERE preserved by
    back-porting into CLAUDE.md:
      * Rule 1  — dead-code specifics (unused exports/imports/props,
                  debug logs) + rationale (context compaction).
      * Rule 5  — rationale ("각 에이전트는 독립 컨텍스트 창").
      * Rule 7  — warning ("단일 읽기로 전체를 봤다고 가정 금지").
      * Rule 8  — "suspiciously few results" trigger, narrower
                  re-search specifics, reporting duty on suspected
                  truncation.
      * Rule 10 — rationale ("grep은 있으나 AST는 없다") + warning
                  ("단일 grep이 모두 커버했다고 가정 금지").

  This file is retained only as a POINTER so external references
  (AGENTS.md, ./skills/, scripts, or user notes linking here) do not
  break. Do not add new rule content here — edit CLAUDE.md instead.

  For the live rules, see: CLAUDE.md §"Agent Directives".
-->

# Moved -> CLAUDE.md

The Agent Directives previously drafted in this file were consolidated
into [`CLAUDE.md`](./CLAUDE.md) on **2026-04-22**.

`CLAUDE.md` is the single source of truth for all agent rules
(Pre-Work, Code Quality, Context Management, Edit Safety, Breakthrough
Protocol, Root Cause First, and conflict-resolution priority).

> This file is kept only as a redirect. See the HTML comment above for
> full history and reasoning.
