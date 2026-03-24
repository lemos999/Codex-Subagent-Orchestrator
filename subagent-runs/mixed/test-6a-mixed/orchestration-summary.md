# Orchestration Summary

- workspace_root: `C:\Users\haj\projects\subagent-orchestrator`
- execution_mode: parallel
- workers_succeeded: 2/2
- shared_directive_mode: disabled
- shared_directive_chars: 0 -> 0
- live_usage_enabled: False
- total_prompt_chars: 1009
- total_footer_tokens: 0
- supervisor_only: False
- require_final_read_only_review: False
- material_issue_strategy: none
- final_read_only_review_present: True
- efficiency_measurement: structure_first
- requested_deliverable_count: 0
- workers_per_deliverable: n/a
- writable_workers_per_deliverable: n/a
- worker_shape: writable=1, read_only=1, implementer=1, reviewer=1, validator=0, fixer=0
- full_auto_split: writable=1, read_only=0
- stage_shape: total=2, parallel_stages=0, max_parallel_workers_in_stage=1
- efficiency_note: Use reruns, parent burden, repair-loop shape, and worker-to-deliverable ratios as primary efficiency signals. Treat absolute token totals as secondary.
- manifest: `C:\Users\haj\projects\subagent-orchestrator\subagent-runs\mixed\test-6a-mixed\orchestration-manifest.json`

## Workers

- `codex-writer`: ok; engine=codex; stage=1; kind=implementer; read_only=False; full_auto=True; model=gpt-5.4; sandbox=; reasoning=low; prompt_chars=592; footer_tokens=n/a; workflow_mode=disabled
  preview: [tests/artifacts/mixed-hello.txt](/C:/Users/haj/projects/subagent-orchestrator/tests/artifacts/mixed-hello.txt) already contained the exact requested content, verified byte-for-byte as `Hello from Cod...
- `claude-reviewer`: ok; engine=claude; stage=2; kind=reviewer; read_only=True; full_auto=False; model=haiku; sandbox=; reasoning=low; prompt_chars=417; footer_tokens=n/a; workflow_mode=disabled
  preview: **ACCEPTED**

The file contains exactly "Hello from Codex engine" as expected.
