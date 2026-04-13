/**
 * Launcher spec JSON schema — frozen contract v1.
 * Matches the input format consumed by start-codex-subagent-team.ps1.
 */

import type {
  Engine,
  ExecutionMode,
  ReasoningEffort,
  Sandbox,
  WorkerKind,
} from './engine.js';

// ============================================================
// Top-level spec
// ============================================================

export interface LauncherSpec {
  // --- Required ---
  cwd: string;
  agents: AgentSpec[];

  // --- Optional (with defaults) ---
  cwd_resolution?: 'invocation' | 'spec';
  output_dir?: string;
  manifest_file?: string;
  debug_log_file?: string | null;
  summary_file?: string;
  archive_root?: string;
  write_run_archive?: boolean;
  archive_run_label?: string | null;
  skip_git_repo_check?: boolean;
  execution_mode?: ExecutionMode;
  timeout_seconds?: number;
  write_prompt_files?: boolean;
  write_summary_file?: boolean;
  requested_deliverables?: string[];
  supervisor_only?: boolean;
  require_final_read_only_review?: boolean;
  material_issue_strategy?: 'none' | 'fixer_then_rereview';
  shared_directive_file?: string | null;
  shared_directive_text?: string | null;
  inject_shared_directive?: boolean;
  shared_directive_mode?: 'full' | 'compact' | 'reference' | 'disabled';
  workflow_file?: string | null;
  workflow_auto_detect?: boolean;
  workflow_prompt_mode?: 'prepend' | 'replace' | 'disabled';
  workflow_context?: Record<string, unknown>;
  workflow_context_file?: string | null;
  workflow_render_strict?: boolean;
  hooks?: HooksSpec;
  live_usage?: LiveUsageSpec;
  defaults?: DefaultsSpec;
}

// ============================================================
// Defaults
// ============================================================

export interface DefaultsSpec {
  engine?: Engine;
  model?: string;
  sandbox?: Sandbox;
  reasoning_effort?: ReasoningEffort;
  json?: boolean;
  output_schema?: Record<string, unknown> | null;
  ephemeral?: boolean;
  prompt_profile?: 'full' | 'compact';
  response_style?: 'standard' | 'compact';
  max_response_lines?: number;
}

// ============================================================
// Agent spec
// ============================================================

export interface AgentSpec {
  // --- Required ---
  name: string;

  // --- Prompt (one of these) ---
  prompt?: string;
  task?: string;

  // --- Agent registry (optional, harness mode) ---
  agent_id?: string;
  agent_version?: number;

  // --- Optional ---
  engine?: Engine;
  mode?: 'exec' | 'resume';
  kind?: WorkerKind;
  stage?: number;
  resume_last?: boolean;
  session_id?: string | null;
  cwd?: string;
  role?: string;
  mission?: string;
  success_criteria?: string[];
  coordination_notes?: string | null;
  skills?: string[];
  read_first?: string[];
  writable_scope?: string[];
  requirements?: string[];
  validation?: string[];
  return_contract?: string[];
  required_paths?: string[];
  required_non_empty_paths?: string[];
  sandbox?: Sandbox;
  model?: string;
  reasoning_effort?: ReasoningEffort;
  json?: boolean;
  output_schema?: Record<string, unknown> | null;
  ephemeral?: boolean;
  prompt_profile?: 'full' | 'compact';
  response_style?: 'standard' | 'compact';
  max_response_lines?: number;
  output_last_message_file?: string;
  workflow_prompt_mode?: 'prepend' | 'replace' | 'disabled';
  workflow_context?: Record<string, unknown>;
  workflow_context_file?: string | null;
  stop_when?: string | null;
  extra_args?: string[];
}

// ============================================================
// Hooks
// ============================================================

export interface HooksSpec {
  after_create?: {
    command: string;
    sentinel_paths?: string[];
    if_workspace_empty?: boolean;
    stdout_file?: string | null;
    stderr_file?: string | null;
  };
}

// ============================================================
// Live usage
// ============================================================

export interface LiveUsageSpec {
  enabled?: boolean;
  display_mode?: 'none' | 'progress' | 'file' | 'both';
  status_file?: string | null;
  poll_interval_ms?: number;
}
