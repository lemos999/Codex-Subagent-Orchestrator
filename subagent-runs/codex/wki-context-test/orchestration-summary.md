# Orchestration Summary

- workspace_root: `C:\Users\haj\projects\subagent-orchestrator`
- execution_mode: sequential
- workers_succeeded: 1/1
- shared_directive_mode: disabled
- shared_directive_chars: 0 -> 0
- live_usage_enabled: False
- total_prompt_chars: 1525
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
- manifest: `C:\Users\haj\projects\subagent-orchestrator\subagent-runs\codex\wki-context-test\orchestration-manifest.json`

## Workers

- `analyst`: ok; engine=codex; stage=1; kind=reviewer; read_only=True; full_auto=False; model=gpt-5.4; sandbox=; reasoning=; prompt_chars=1525; footer_tokens=n/a; workflow_mode=disabled
  preview: In short, Stage 9 is the acceptance/recovery checkpoint plus mandatory evidence persistence. The run is not considered reportable until that evidence package has been written.
