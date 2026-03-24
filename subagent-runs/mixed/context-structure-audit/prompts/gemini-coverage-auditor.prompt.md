# Task: Context Sharing Coverage Audit

You are auditing a multi-AI-engine project's context sharing structure. The project uses 3 AI engines (Claude, Codex/GPT, Gemini) and needs all of them to share the same project context.

## Current Context Sources (5)

1. **project-status/current.md** — Macro context (project status, components, next tasks, commands, rules). All engines should read this.
2. **WKI (.knowledge/)** — Micro context (semantic search, auto-injected into worker prompts). Only works via TS launcher (`/sub`, `/submix`).
3. **CLAUDE.md** — Auto-loaded by Claude Code at session start. References project-status.
4. **AGENTS.md** — Auto-loaded by Codex CLI. Also read by Gemini CLI. References project-status.
5. **.claude/memory/** — Claude-only persistent memory (user preferences, feedback, project notes).

## Your Analysis Tasks

For each execution path below, trace whether the engine gets macro context (project-status) and micro context (WKI):

| Path | Engine | Gets Macro? | Gets Micro? |
|------|--------|------------|------------|
| Normal chat | Claude | ? | ? |
| /sub worker | Claude | ? | ? |
| /submix worker | Claude | ? | ? |
| /submix worker | Codex | ? | ? |
| /submix worker | Gemini | ? | ? |
| /design (skill) | Claude | ? | ? |
| /gdd (skill) | Claude | ? | ? |
| /discuss | Claude+Codex+Gemini | ? | ? |
| TS launcher worker | Any engine | ? | ? |
| Standalone codex exec | Codex | ? | ? |
| Standalone gemini-cli | Gemini | ? | ? |

For each "?" answer YES/NO and explain HOW (auto-load, WKI inject, manual read, or N/A).

Then identify:
1. **Coverage gaps**: Paths where an engine misses context
2. **Redundancies**: Same info duplicated across sources
3. **Improvement suggestions**: Minimal changes for full coverage

Respond in Korean (한국어).
