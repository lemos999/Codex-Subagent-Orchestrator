# Task: Context Architecture Critique

You are an independent architecture critic reviewing a multi-AI-engine project's context sharing design.

## Current Architecture

```
Context Sources:
┌─────────────────────────────────────────────────┐
│ project-status/current.md (macro: project state)│ ← All engines should read
├─────────────────────────────────────────────────┤
│ WKI .knowledge/ (micro: semantic code search)   │ ← TS launcher only
├─────────────────────────────────────────────────┤
│ CLAUDE.md (Claude auto-load)                    │ ← Says "read project-status"
├─────────────────────────────────────────────────┤
│ AGENTS.md (Codex/Gemini auto-load)              │ ← Says "read project-status"
├─────────────────────────────────────────────────┤
│ .claude/memory/ (Claude-only persistent)        │ ← User prefs, feedback
└─────────────────────────────────────────────────┘

Execution Paths:
- Claude native (chat, /design, /gdd): reads CLAUDE.md → knows project-status
- Codex standalone (codex exec): reads AGENTS.md → knows project-status
- Gemini standalone (gemini-cli): reads AGENTS.md → knows project-status
- TS launcher workers (/sub, /submix): WKI auto-injects relevant context
- /discuss (3-engine debate): Claude orchestrates, constructs prompts for Codex/Gemini
```

## Critique Questions

1. **Is this architecture over-engineered?** 5 context sources for 3 engines — could it be simpler?
2. **Single source of truth?** project-status/current.md is referenced by both CLAUDE.md and AGENTS.md. Is this indirection necessary, or should the content just be in AGENTS.md directly?
3. **WKI gap**: WKI only works via TS launcher. Skills (/design, /gdd, /discuss) bypass the launcher. Is this a real problem or acceptable?
4. **Memory asymmetry**: .claude/memory/ is Claude-only. Codex/Gemini have no equivalent. Does this create bias?
5. **Maintenance burden**: How many files need updating when project state changes?
6. **Propose a simpler alternative** if one exists (fewer files, less indirection, same coverage).

Respond in Korean (한국어).
