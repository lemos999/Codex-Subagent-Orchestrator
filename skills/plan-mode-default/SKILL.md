---
name: plan-mode-default
description: Hard plan-first contract for every coding request. Use when Codex must convert any coding request into a clarified, user-approved natural-language plan before implementation, including new features, bug fixes, refactors, direct edit requests, and follow-up changes across parent and /sub workflows.
---

# Plan Mode Default

Use this skill when any coding work should follow the workspace's mandatory plan-first contract instead of ad hoc planning or direct implementation. In this workspace, every coding request should be interpreted as an explicit request for this plan-first flow before implementation begins.

The shared plan-first gate is defined by `../agent-skills-integration/agent-skill-routing.md`. This skill is the execution layer for that gate and should be treated as the default planning behavior surface for both parent and `/sub` workflows.

## Workflow

- Apply the no-exception gate defined in `../agent-skills-integration/agent-skill-routing.md` before any implementation, fix work, or writable worker launch.
- Read `references/coding-plan-prompt-en.md` when you need the full contract text.
- Treat `../agent-skills-integration/agent-skill-routing.md` as the authority for when the plan-first gate is mandatory, and treat `references/coding-plan-prompt-en.md` as the authority for how the planning interaction and long-form approved plan should be produced.
- Keep the first response as a short understanding report in normal prose and ask for user approval before generating the full PLAN or beginning implementation.
- Do not treat "do it now", urgency, blanket authority, or tiny scope as a waiver of the approval gate.
- Do not treat minor subtasks, one-line fixes, tiny follow-up edits, or repair steps as exempt; they must either fit the active approved plan record or reopen planning.
- After approval, follow the contract exactly, including English output, persistence of the approved full PLAN under repo-root `plan/`, time-sortable versioned filenames, explicit plan-type markers, in-file status and progress tracking, an in-file `Scoreboard` section with score history, minimum PLAN length, natural-language directive style, hidden-rule surfacing, iterative refinement behavior, and re-gating when a later request materially changes the approved coding direction.
- Keep the `Scoreboard` section in the active plan file updated through the life of the task. Record explicit user scores as authoritative, and when the user gives no score yet, maintain a conservative provisional score based on the current evidence instead of stopping or inventing a fixed default number. Preserve prior score states by appending score-history entries instead of overwriting them.

## Resources

- `../agent-skills-integration/agent-skill-routing.md`: authoritative shared gate and routing-level policy
- `references/coding-plan-prompt-en.md`: authoritative plan-mode contract text
