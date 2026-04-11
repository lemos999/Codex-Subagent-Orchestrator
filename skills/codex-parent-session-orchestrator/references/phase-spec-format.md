# Parent-Session Run Kit Format

The parent-session workflow uses a manual Markdown run kit instead of an external scaffolding script.

Recommended directory:

```text
parent-session-runs/<run-id>/
|-- task-brief.md
|-- active-context.md
|-- phase-checklist.md
|-- session-summary.md
`-- phases/
    |-- scan.md
    |-- plan.md
    |-- implement.md
    |-- verify.md
    `-- review.md
```

Add `fix.md`, `re-verify.md`, and `re-review.md` only when a material issue opens a bounded repair loop.

## `task-brief.md`

Capture:

- request summary
- constraints
- acceptance criteria
- known files or touch points
- risks worth tracking from the start

## `active-context.md`

Capture:

- current repository facts that matter right now
- open assumptions
- current target files
- current validation plan

Treat this as a bootstrap snapshot, not as the authoritative long-lived checkpoint once work begins.

## `phase-checklist.md`

Capture:

- ordered phases
- completion marks
- pause points
- any explicit return edges already known
- optional repair-loop phases only when a bounded repair loop is actually open

This is the ordered phase index, not the durable current-state ledger.

## `session-summary.md`

Capture:

- current status
- accepted facts
- approved fix scope when one is open
- repair loop status when one is open
- touched files
- commands run
- failures or risks
- next step

This is the durable current-state authority.

## `phases/*.md`

Each phase file should contain:

- phase name
- role
- mode
- goal
- files to read first
- writable scope
- outputs to update on disk
- success criteria
- validation checks when needed
- stop condition
- selected imported skill paths when the phase needs vendored execution discipline

For the `plan` phase, include `skills/agent-skills-integration/agent-skill-routing.md`, `skills/karpathy-guidelines/SKILL.md`, `skills/plan-mode-default/SKILL.md`, and `skills/plan-mode-default/references/coding-plan-prompt-en.md` in `files to read first` by default when those files exist, unless the user explicitly asks for a different planning contract format that still preserves the understanding-report and explicit-approval gate.
For coding runs, use the `plan` phase to write or update the approved full PLAN under repo-root `plan/` as a versioned, time-sortable Markdown record with typed status, progress, and scoreboard fields, and record that file path in `session-summary.md`.
For coding runs, do not activate `implement.md` until `session-summary.md` records that the plan-first approval gate has been satisfied and names the approved plan file under `plan/`.
For coding runs, any later phase that materially changes progress, blockers, completion state, next step, or score state should list the active plan file under `plan/` in `outputs to update on disk`.

## Templates

Use the files under `skills/codex-parent-session-orchestrator/assets/run-templates/` when you want a deterministic starting point without any helper script.
