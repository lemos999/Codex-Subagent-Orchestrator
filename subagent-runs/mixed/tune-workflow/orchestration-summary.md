# Orchestration Summary

- workspace_root: `C:\Users\haj\projects\subagent-orchestrator`
- execution_mode: parallel
- workers_succeeded: 3/3
- shared_directive_mode: disabled
- shared_directive_chars: 0 -> 0
- live_usage_enabled: False
- total_prompt_chars: 3348
- total_footer_tokens: 0
- supervisor_only: False
- require_final_read_only_review: False
- material_issue_strategy: none
- final_read_only_review_present: True
- efficiency_measurement: structure_first
- requested_deliverable_count: 0
- workers_per_deliverable: n/a
- writable_workers_per_deliverable: n/a
- worker_shape: writable=0, read_only=3, implementer=0, reviewer=3, validator=0, fixer=0
- full_auto_split: writable=0, read_only=0
- stage_shape: total=1, parallel_stages=1, max_parallel_workers_in_stage=3
- efficiency_note: Use reruns, parent burden, repair-loop shape, and worker-to-deliverable ratios as primary efficiency signals. Treat absolute token totals as secondary.
- manifest: `C:\Users\haj\projects\subagent-orchestrator\subagent-runs\mixed\tune-workflow\orchestration-manifest.json`

## Workers

- `codex-workflow`: ok; engine=codex; stage=1; kind=reviewer; read_only=True; full_auto=False; model=gpt-5.4; sandbox=; reasoning=; prompt_chars=1116; footer_tokens=n/a; workflow_mode=disabled
  preview: 원하면 다음 답변에서 이걸 `실제 /sub 실행 예시` 기준으로 한 번 더 풀어서 보여드릴게요.
- `claude-workflow`: ok; engine=claude; stage=1; kind=reviewer; read_only=True; full_auto=False; model=haiku; sandbox=; reasoning=; prompt_chars=1116; footer_tokens=n/a; workflow_mode=disabled
  preview: # 오케스트레이션 워크플로우 단계별 흐름

오케스트레이션은 **9개 단계**로 구성됩니다:
- `gemini-workflow`: ok; engine=gemini; stage=1; kind=reviewer; read_only=True; full_auto=False; model=gemini-2.5-flash; sandbox=; reasoning=; prompt_chars=1116; footer_tokens=n/a; workflow_mode=disabled
  preview: I need to understand the orchestration workflow. I will start by reading the referenced `orchestration-workflow.md` file within the `claude-subagent-orchestrator` skill.
Here is a step-by-step explana...
