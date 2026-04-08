# Token Efficiency Playbook

## Goal

Keep result quality high while minimizing repeated context.

## Primary Rules

- Keep one parent session active at a time.
- Move durable state to files, not chat.
- Reuse `AGENTS.md` by reference.
- Read only the current phase file plus the files listed under `Read first`.
- Use `session-summary.md` as the sole durable checkpoint.
- Treat the current phase file as the active instruction surface, not the durable state file.
- Prefer compact summaries over narrative retellings.

## Cheap Context Surfaces

Use these first:

- `active-context.md` for bootstrap context only
- `session-summary.md` for durable state
- current phase file
- targeted file reads
- short failing log excerpts

## Expensive Context Surfaces

Avoid these unless required:

- pasting full AGENTS text
- replaying prior chat history
- replaying full stdout or stderr
- pasting entire files after they are already on disk
- asking the model to regenerate a plan that is already accepted
- chaining repeated fix loops when the same root cause already proved the plan is wrong

## Summary Format

When updating `session-summary.md`, keep the shape stable:

- current status
- accepted facts
- approved fix scope when one is open
  defect, allowed file surface, rerun proof, assumed task boundary, do-not-cross boundary
- repair loop status when one is open
- touched files
- commands run
- failures or risks
- next step

## Review Loop

The cheapest safe quality loop is:

1. implement
2. verify
3. read-only review
4. bounded fix if needed
5. re-verify only what changed
6. re-review

Use these loop exits:

- if `verify` fails because of code or configuration inside the current approved design and writable scope, record an approved fix scope that names that defect and use `fix`
- if `verify` only exposed a wrong or insufficient check and no code change or plan change is needed, stay in `verify`
- if `re-verify` fails because of code or configuration inside the current approved design and writable scope, refresh the approved fix scope to name that remaining defect and use `fix` only when the remaining failure is not the same root cause that already survived this repair loop
- if `re-verify` only exposed a wrong or insufficient check and no code change or plan change is needed, stay in `re-verify`
- if `re-verify` shows the same root cause survived the just-completed bounded repair loop, return to `plan`
- if `verify` or `re-verify` shows the design is wrong, or shows a validation strategy defect, return to `plan`
- if `review`, `re-review`, or `re-verify` shows the next safe step would exceed the approved fix scope or cause a material plan change, return to `plan`
- if `verify` or `re-verify` shows the task boundary was misunderstood, return to `scan`
- if `re-review` still finds the same root-cause issue after one bounded repair loop, return to `plan` instead of chaining more fixes
- if `re-review` finds a remaining issue that can be repaired only through another bounded loop, require explicit user approval and a fresh approved fix scope naming that remaining defect before returning to `fix`
- if that user-approved next loop would still cause a material plan change or task-boundary change, return to `plan` or `scan` instead of direct `fix`
- treat `re-verify -> fix` as part of the same bounded repair loop; the user-approval gate applies only when `re-review` tries to start another loop

This is usually cheaper than restarting the whole task or maintaining separate worker sessions.
