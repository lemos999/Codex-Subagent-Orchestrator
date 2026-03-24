# Task: General-Purpose Planning Skill Architecture Design

You are a software architect advising on how to build a general-purpose "planning director" AI skill.

## Current State
We have a Game Design Director (`/gdd`) skill with this structure:
- Entry point: `.claude/skills/gdd/SKILL.md` (routing + help)
- Core skill: `skills/game-design-director/SKILL.md` (350 lines, phases + rules)
- Phase agents: `skills/game-design-director/agents/phase{1-6}.agent.md` (7 agents)
- Templates: `skills/game-design-director/templates/*.md` (3 templates)
- Sub-agent specs: `skills/game-design-director/specs/*.claude.json`
- Framework reference: `game-design-director/game-design-director-integrated.md` (2269 lines)

The /gdd pipeline:
- Phase 1: Define project DNA (identity/vision) via interview
- Phase 2: List & prioritize systems/components
- Phase 3: Deep-dive interview per component (quantify decisions)
- Phase 3.5: Cross-component validation (shared variables, contradictions)
- Phase 4: Recursive verification (4-step: errors → contradictions → context → implementation)
- Phase 5: Document generation (confirmed specs, dependency maps)
- Phase 6: Change management (tier-based impact analysis)

Plus Mode B: Analyze existing documents (diagnose → evaluate → compare → report)

## Design Question
We want a `/plan` or `/director` skill that works for ANY domain:
- Software architecture planning
- Business strategy documents
- Product requirement documents (PRD)
- Marketing campaign plans
- Research project designs
- Event planning
- etc.

## Your Task
Recommend the best architecture pattern. Consider these options and pick the best (or propose your own):

### Option A: Base + Domain Plugin
```
/director (base skill)
  ├── core/ (generic phases, gates, verification)
  ├── domains/
  │   ├── game/ (current /gdd content)
  │   ├── software/
  │   ├── business/
  │   └── ...
  └── templates/ (domain-specific templates)
```

### Option B: Abstract Factory
- Define abstract interfaces (DNA → Vision, System → Component, etc.)
- Each domain implements the interfaces
- Single orchestrator uses the interfaces

### Option C: Template-Driven
- One generic skill with configurable templates
- Domain knowledge lives entirely in template files
- The skill itself is 100% generic

### Option D: Your recommendation

For your chosen approach, provide:
1. Directory structure
2. What stays generic vs what gets parameterized
3. How domain-specific knowledge (like game's "fun 4-question test") maps to generic concepts
4. Migration path from current /gdd
5. Estimated effort (files to create/modify)

Respond in Korean (한국어).
