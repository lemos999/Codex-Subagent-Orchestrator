# Plan Artifacts

Approved long-form coding plans belong in this directory.

Rules:

- Write approved full plans here as Markdown files.
- Keep the plan body in the file instead of dumping the full document into chat.
- Use a time-sortable filename: `YYYYMMDD-HHMMSS--<plan-type>--<slug>--vNN.md`.
- Mark the plan type clearly, for example `draft-plan`, `revision-plan`, or `work-plan`.
- Keep the directory naturally ordered by timestamp and version so newer artifacts sort after older ones.
- Start every plan file with a compact record header that states plan type, workstream, version, status, created time, updated time, related or superseded plan if any, current completion state, completed work, remaining work, blockers, and next step.
- Keep a `Scoreboard` section in the active plan file that records the current score on a `0-100` scale, the score source (`user` or `provisional`), the last update time, the score rationale, what improved, what remains unsatisfactory, the next actions required to raise or maintain the score, and a chronological score-history log.
- Write the approved plan document itself in English.
- Treat the active plan file as a living delivery record and update it after every planning-turn change, every writable task step, and every verification, review, repair, or acceptance step that changes status, progress, blockers, next action, or likely satisfaction state, including tiny follow-up edits and one-line fixes.
- Record explicit user scores as authoritative when provided. When no explicit score has been provided yet, continue the work and maintain a conservative provisional score based on the current evidence instead of waiting or using a fixed hardcoded fallback number, but do not set that provisional score above `50`.
- Treat an unchanged score as the current overall result rating staying the same, not as zero new points being awarded.
- Preserve prior score states in the score-history log when the score value, score source, or score rationale materially changes. Do not overwrite the previous score record, and do append a history entry when an explicit user score replaces a provisional score with the same numeric value.
- Create a new versioned plan file when the approved direction or plan type changes materially; otherwise refresh the current active plan file and its progress and scoreboard fields.
- When a new versioned plan file becomes active, rewrite the prior active plan file so its status is clearly `Superseded` and it points to the new active plan as the replacement or successor.
