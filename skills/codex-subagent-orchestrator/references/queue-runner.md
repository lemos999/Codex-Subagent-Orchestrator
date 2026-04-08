# In-Session `/sub` Queue Mode

The internal-only edition preserves queue semantics only while the current chat session remains alive.

## Use Queue Mode When

- the user wants repeated issue handling over one live session
- each issue can be planned, executed, reviewed, and accepted separately
- per-issue evidence should be preserved on disk

## Do Not Promise Queue Mode When

- the user expects detached unattended execution after the chat ends
- the user expects an OS-level background worker
- the user expects shell polling or external terminal status windows

If the user asks for those things, say the internal-only edition does not support them.

## Queue Structure

Use:

```text
subagent-runs/<queue-id>/
|-- queue-state.md
`-- issues/
    `-- <issue-id>/
        |-- orchestration-plan.md
        |-- status.md
        |-- worker-briefs/
        |-- results/
        |-- review-verdict.md
        `-- acceptance.md
```

## Queue Loop

For each issue:

1. read the issue brief
2. decide whether one worker or a small team is justified
3. write the issue plan
4. launch internal agents
5. review or validate
6. accept, defer, or record failure
7. update `queue-state.md`

## Retry Rules

Use retries only when:

- the issue failed for a bounded operational reason
- rerunning the same bounded plan is cleaner than replanning

Do not retry blindly when the issue needs a different design, different writable scope, or a changed acceptance strategy.

## Status Reporting

Keep the queue visible in chat:

- current issue
- remaining issue count
- current issue stage
- any blocked or deferred issue

Queue mode must remain visible and in-session. It is not a detached daemon.
