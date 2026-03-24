# Task: /gdd Framework Deep Analysis

You are analyzing a Game Design Director (GDD) skill framework to determine how game-specific vs general-purpose it is.

## Context
We have a `/gdd` skill that produces game design documents through a phased pipeline (Phase 1-6). We want to create a **general-purpose planning/design skill** and need to know if `/gdd` can be adapted or if we should start fresh.

## Your Analysis Tasks

1. **Game-Specific Coupling Assessment**: Read the full framework below and categorize every major component as:
   - GAME-ONLY: Only makes sense for games (e.g., "fun 4-question test", game DNA, exploit detection)
   - DOMAIN-ADAPTABLE: Game-specific surface but generalizable pattern (e.g., "core loop" → "core workflow", "system priority" → "component priority")
   - GENERIC: Already domain-agnostic (e.g., phase gates, verification 4-steps structure, change management tiers)

2. **Coupling Ratio**: Estimate what % of the framework is GAME-ONLY vs DOMAIN-ADAPTABLE vs GENERIC

3. **Transformation Cost**: For DOMAIN-ADAPTABLE components, estimate how much rewriting is needed (low/medium/high)

4. **Recommendation**: Based on your analysis, recommend:
   - A) Modify /gdd → general-purpose (fork and abstract)
   - B) Extract generic skeleton → new skill (keep /gdd as-is, build new)
   - C) Build from scratch (if coupling is too deep)

## Framework to Analyze

The framework file follows after this line. Analyze the ENTIRE content:

---
