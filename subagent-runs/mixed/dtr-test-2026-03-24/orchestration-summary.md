# Orchestration Summary

- workspace_root: `C:\Users\haj\projects\subagent-orchestrator`
- execution_mode: sequential
- workers_succeeded: 1/1
- shared_directive_mode: full
- shared_directive_chars: 39 -> 39
- live_usage_enabled: False
- total_prompt_chars: 1500
- total_footer_tokens: 0
- supervisor_only: False
- require_final_read_only_review: False
- material_issue_strategy: none
- final_read_only_review_present: True
- efficiency_measurement: structure_first
- requested_deliverable_count: 0
- workers_per_deliverable: n/a
- writable_workers_per_deliverable: n/a
- worker_shape: writable=0, read_only=1, implementer=0, reviewer=1, validator=0, fixer=0
- full_auto_split: writable=0, read_only=0
- stage_shape: total=1, parallel_stages=0, max_parallel_workers_in_stage=1
- efficiency_note: Use reruns, parent burden, repair-loop shape, and worker-to-deliverable ratios as primary efficiency signals. Treat absolute token totals as secondary.
- manifest: `C:\Users\haj\projects\subagent-orchestrator\subagent-runs\mixed\dtr-test-2026-03-24\orchestration-manifest.json`

## Workers

- `test-analyzer`: ok; engine=gemini; stage=1; kind=reviewer; read_only=True; full_auto=False; model=gemini-2.5-flash; sandbox=; reasoning=; prompt_chars=1500; footer_tokens=n/a; workflow_mode=disabled
  preview: I will read the file `packages/launcher/src/workers/spawn.ts` to understand the `spawnWorker` function.
The `spawnWorker` function in `packages/launcher/src/workers/spawn.ts` executes a specified comm...
