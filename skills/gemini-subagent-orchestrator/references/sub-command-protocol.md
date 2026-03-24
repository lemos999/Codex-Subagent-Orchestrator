# `/sub` Command Protocol (Gemini)

## Trigger Rule

When the user message begins with `/sub`, treat it as an explicit request to enter **supervisor mode** using the external launcher.

## The Parent's Responsibilities

1.  **Strip the prefix:** Treat the text after `/sub` as the actual user request.
2.  **Choose the team shape:** Decide whether the run is Gemini-only or mixed-engine.
3.  **Generate Spec:** Write a bounded JSON spec file for the worker team.
4.  **Execute Runner:** Run `start-codex-subagent-team.ps1` with that spec.
5.  **No Launcher Bypass:** Do not shortcut `/sub` by directly calling `generalist` or `codebase_investigator`.

## Sizing the Team

-   `1` worker: narrow generation or extraction
-   `2` workers: default `implementer + reviewer`
-   `3` workers: `planner + implementer + reviewer` or a mixed-engine split
-   `4+` workers: only when parallelism is genuine and output boundaries stay clear

## Evidence Rules

- Single-engine Gemini runs: `subagent-runs/gemini/<run-name>/`
- Mixed-engine runs: `subagent-runs/mixed/<run-name>/`
- The launcher is responsible for writing `orchestration-summary.md`, `orchestration-manifest.json`, prompt files, and worker outputs.

## Validation

- Always trust the read-only reviewer over the implementer.
- If a reviewer finds a material issue, launch a bounded fixer spec instead of patching the deliverable directly.
