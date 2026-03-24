# Orchestration Summary

- workspace_root: `C:\Users\haj\projects\subagent-orchestrator`
- execution_mode: parallel
- workers_succeeded: 3/3
- shared_directive_mode: disabled
- shared_directive_chars: 0 -> 0
- live_usage_enabled: False
- total_prompt_chars: 4716
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
- manifest: `C:\Users\haj\projects\subagent-orchestrator\subagent-runs\mixed\tune-evidence\orchestration-manifest.json`

## Workers

- `codex-evidence`: ok; engine=codex; stage=1; kind=reviewer; read_only=True; full_auto=False; model=gpt-5.4; sandbox=; reasoning=; prompt_chars=1572; footer_tokens=n/a; workflow_mode=disabled
  preview: 원하면 다음 답변에서 이 규칙을 `체크리스트` 형태로 10줄 내로 압축해드리겠습니다.
- `claude-evidence`: ok; engine=claude; stage=1; kind=reviewer; read_only=True; full_auto=False; model=haiku; sandbox=; reasoning=; prompt_chars=1572; footer_tokens=n/a; workflow_mode=disabled
  preview: 이 프로젝트의 **워커 실행 후 증거 기록 규칙**을 정리하면:

## 디렉토리 구조
- `gemini-evidence`: ok; engine=gemini; stage=1; kind=reviewer; read_only=True; full_auto=False; model=gemini-2.5-flash; sandbox=; reasoning=; prompt_chars=1572; footer_tokens=n/a; workflow_mode=disabled
  preview: I will read the file `skills/claude-subagent-orchestrator/references/evidence-format.md` to understand the rules for recording evidence after a worker run.
Here are the rules for recording evidence af...
