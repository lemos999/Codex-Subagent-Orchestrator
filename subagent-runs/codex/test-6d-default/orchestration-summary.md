# Orchestration Summary

- workspace_root: `C:\Users\haj\projects\subagent-orchestrator`
- execution_mode: sequential
- workers_succeeded: 1/1
- shared_directive_mode: disabled
- shared_directive_chars: 0 -> 0
- live_usage_enabled: False
- total_prompt_chars: 811
- total_footer_tokens: 0
- supervisor_only: False
- require_final_read_only_review: False
- material_issue_strategy: none
- final_read_only_review_present: False
- efficiency_measurement: structure_first
- requested_deliverable_count: 0
- workers_per_deliverable: n/a
- writable_workers_per_deliverable: n/a
- worker_shape: writable=1, read_only=0, implementer=1, reviewer=0, validator=0, fixer=0
- full_auto_split: writable=1, read_only=0
- stage_shape: total=1, parallel_stages=0, max_parallel_workers_in_stage=1
- efficiency_note: Use reruns, parent burden, repair-loop shape, and worker-to-deliverable ratios as primary efficiency signals. Treat absolute token totals as secondary.
- manifest: `C:\Users\haj\projects\subagent-orchestrator\subagent-runs\codex\test-6d-default\orchestration-manifest.json`

## Workers

- `writer`: ok; engine=codex; stage=1; kind=implementer; read_only=False; full_auto=True; model=gpt-5.4; sandbox=; reasoning=low; prompt_chars=811; footer_tokens=n/a; workflow_mode=disabled
  preview: [tests/artifacts/default-engine.txt](C:/Users/haj/projects/subagent-orchestrator/tests/artifacts/default-engine.txt) already contained exactly `Hello from default engine` with no trailing newline, so ...
