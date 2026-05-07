---
name: karpathy-guidelines
description: Default local anti-overengineering overlay for coding work. Use to prefer the smallest complete design, surface assumptions, keep edits surgical, and define concrete verification goals without weakening local plan-first, score-tracking, or writable-scope rules.
---

# Karpathy Guidelines

Use this local skill as the default behavioral overlay for coding phases and coding worker roles in this workspace.

This skill complements but does not override:

- `AGENTS.md`
- `skills/agent-skills-integration/agent-skill-routing.md`
- `skills/plan-mode-default/SKILL.md`
- explicit user instructions
- phase-local acceptance, writable-scope, and review rules

If another local contract is stricter, follow the stricter local contract.

## 1. Think Before Coding

Do not assume silently.

- State the smallest safe assumption when details are missing.
- If the request can reasonably mean multiple things, surface the ambiguity instead of hiding it.
- If the problem boundary is unclear, narrow it before editing.
- If a simpler path exists, prefer it and say why.

## 2. Simplicity First

Use the smallest complete design that solves the stated problem.

- Do not add features, options, toggles, or abstractions that were not requested.
- Do not create single-use indirection just to look flexible.
- Prefer clear control flow over decorative architecture.
- Keep the number of touched files as low as correctness allows.

## 3. Surgical Changes

Change only what the active request and approved plan require.

- Do not clean up adjacent code unless the current change made it necessary.
- Remove only the unused code that your own change created.
- Match local naming, layout, and style when working in existing files.
- Keep every changed line traceable to the requested outcome, the approved plan, or the required validation path.

## 4. Goal-Driven Execution

Turn the work into explicit, checkable goals.

- Define what must be true when the task is done.
- Prefer validation that proves user-visible behavior.
- When the work has multiple steps, keep the order concrete and easy to verify.
- If review or verification finds a problem, fix the narrow issue and check again instead of widening scope by default.

## 5. Workspace Alignment

In this workspace, use these guidelines as a default overlay for coding work:

- during `plan`, keep the plan concrete but avoid speculative implementation detail
- during `implement`, prefer the smallest safe change that satisfies the approved plan
- during `verify`, check the behavior that proves the goal rather than collecting decorative evidence
- during `review`, flag unnecessary complexity, scope drift, and single-use abstraction
- during `fix`, preserve the bounded repair scope unless the user re-approves a wider plan

When this skill is used together with the local plan-first flow, the approved plan remains the authority for scope, ordering, and status, while this skill supplies the default simplicity and anti-overengineering posture.
