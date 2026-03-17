/**
 * Orchestration manifest output schema — frozen contract v1.
 * Matches the output format produced by start-codex-subagent-team.ps1.
 */

import type { Engine, ExecutionMode } from './engine.js';

// ============================================================
// Top-level manifest
// ============================================================

export interface Manifest {
  created_at_utc: string;
  launcher_version: string;
  launcher_script: string;
  spec_path: string;
  spec_directory: string;
  spec_sha256: string;
  codex_executable: string;
  claude_executable: string;
  gemini_executable: string;
  invocation_cwd: string;
  cwd_requested: string;
  cwd_resolution_mode: string;
  cwd_resolution_base: string;
  workspace_root: string;
  output_dir: string;
  debug_log: string | null;
  summary_file: string | null;
  live_usage: ManifestLiveUsage;
  archive: ManifestArchive;
  execution_mode: ExecutionMode;
  skip_git_repo_check: boolean;
  shared_directive: ManifestSharedDirective;
  workflow: ManifestWorkflow;
  hooks: ManifestHooks;
  policy: ManifestPolicy;
  efficiency_signals: ManifestEfficiencySignals;
  stage_plan: StagePlan[];
  defaults: Record<string, unknown>;
  results: WorkerResult[];
}

// ============================================================
// Sub-structures
// ============================================================

export interface ManifestLiveUsage {
  enabled: boolean;
  display_mode: string;
  poll_interval_ms: number;
  status_file: string | null;
  json_output_forced: boolean;
}

export interface ManifestArchive {
  enabled: boolean;
  root: string | null;
  run_label: string | null;
  run_directory: string | null;
  launcher_directory: string | null;
  deliverables_directory: string | null;
  workers_directory: string | null;
  supervisor_directory: string | null;
}

export interface ManifestSharedDirective {
  source: string | null;
  requested_mode: string;
  effective_mode: string;
  sha256: string | null;
  char_count: number;
  original_char_count: number;
  effective_char_count: number;
}

export interface ManifestWorkflow {
  enabled: boolean;
  source: string | null;
  prompt_mode: string;
  strict_render: boolean;
  auto_detected: boolean;
  front_matter_text: string | null;
  prompt_template_sha256: string | null;
  prompt_template_chars: number;
  context: Record<string, unknown>;
}

export interface ManifestHooks {
  after_create: {
    enabled: boolean;
    ran: boolean;
    trigger: string | null;
    exit_code: number | null;
    missing_sentinel_paths: string[];
    workspace_was_empty: boolean;
    stdout: string | null;
    stderr: string | null;
  };
}

export interface ManifestPolicy {
  execution_mode: ExecutionMode;
  supervisor_only: boolean;
  require_final_read_only_review: boolean;
  material_issue_strategy: string;
  requested_deliverables: string[];
  writable_worker_names: string[];
  read_only_reviewer_names: string[];
  final_read_only_reviewer_names: string[];
  final_read_only_review_present: boolean;
  last_writable_stage: number;
}

export interface ManifestEfficiencySignals {
  measurement_mode: string;
  note: string;
  execution_mode: ExecutionMode;
  total_workers: number;
  succeeded_workers: number;
  failed_workers: number;
  requested_deliverable_count: number;
  workers_per_deliverable: number | null;
  writable_workers_per_deliverable: number | null;
  writable_workers: number;
  read_only_workers: number;
  implementer_workers: number;
  reviewer_workers: number;
  validator_workers: number;
  fixer_workers: number;
  full_auto_writable_workers: number;
  full_auto_read_only_workers: number;
  stage_count: number;
  parallel_stage_count: number;
  max_parallel_workers_in_stage: number;
  uses_parallel_execution: boolean;
  uses_supervisor_only_policy: boolean;
  uses_bounded_repair_policy: boolean;
  final_read_only_review_present: boolean;
  total_prompt_chars: number;
  total_footer_tokens: number;
}

export interface StagePlan {
  stage: number;
  worker_count: number;
  worker_names: string[];
  worker_kinds: string[];
  read_only_workers: string[];
  writable_workers: string[];
}

// ============================================================
// Worker result
// ============================================================

export interface WorkerResult {
  name: string;
  engine: Engine;
  mode: string;
  stage: number;
  worker_kind: string;
  is_read_only: boolean;
  cwd: string;
  exit_code: number;
  succeeded: boolean;
  required_paths: string[];
  required_non_empty_paths: string[];
  missing_required_paths: string[];
  empty_required_paths: string[];
  validation_failures: string[];
  requested_model: string;
  requested_full_auto: boolean;
  requested_json_output: boolean;
  actual_model: string;
  requested_sandbox: string;
  actual_sandbox: string | null;
  requested_reasoning_effort: string | null;
  actual_reasoning_effort: string | null;
  prompt_profile: string;
  response_style: string;
  max_response_lines: number;
  actual_approval: boolean | null;
  actual_workdir: string | null;
  output_mode: string;
  session_id: string | null;
  footer_tokens_used: number | null;
  turn_failed: boolean;
  failure_message: string | null;
  stdout: string;
  stderr: string;
  last: string;
  prompt: string | null;
  prompt_sha256: string;
  prompt_chars: number;
  workflow_prompt_mode: string;
  workflow_prompt_chars: number;
  command: string;
  last_exists: boolean;
  last_message_preview: string;
  stderr_preview: string;
  stdout_preview: string;
}
