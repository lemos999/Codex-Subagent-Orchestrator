# Token Efficiency Playbook

## Goal

Keep result quality high while minimizing repeated context.

## Primary Rules

- Keep one parent session active at a time.
- Move durable state to files, not chat.
- Reuse `AGENTS.md` by reference.
- Read only the current phase file plus the files listed under `Read first`.
- Prefer compact summaries over narrative retellings.

## Cheap Context Surfaces

Use these first:

- `active-context.md`
- `session-summary.md`
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

## Summary Format

When updating `session-summary.md`, keep the shape stable:

- current status
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

This is usually cheaper than restarting the whole task or maintaining separate worker sessions.
