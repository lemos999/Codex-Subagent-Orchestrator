/**
 * Queue runner types — shared across all queue modules.
 */

// ============================================================
// Raw issue (from trackers, before normalization)
// ============================================================

export interface RawIssue {
  [key: string]: unknown;
}

// ============================================================
// Blocker (string or object)
// ============================================================

export interface BlockerObject {
  identifier?: string;
  id?: string;
  key?: string;
  state?: string;
}

export type Blocker = string | BlockerObject;

// ============================================================
// Normalized issue (after normalization)
// ============================================================

export interface NormalizedIssue {
  id: string;
  identifier: string;
  title: string;
  description: string;
  state: string;
  priority: number | null;  // PS preserves original; 999 only at sort time
  labels: string[];
  blocked_by: Blocker[];
  requested_deliverables: string[];
  auto_run: boolean;
  source_path: string;
  source_kind: string;
  branch_name: string;
  url: string;
  created_at: string;
  updated_at: string;
  mode_hint: string;
}

// ============================================================
// Issue state record (17 fields — matches PS queue-state.json)
// ============================================================

export interface IssueStateRecord {
  issue_key: string;
  status: 'idle' | 'running' | 'completed' | 'failed' | 'stopped';
  dispatch_count: number;
  consecutive_failures: number;
  next_eligible_at_utc: string | null;
  workspace_path: string | null;
  last_state: string | null;
  last_manifest: string | null;
  last_summary: string | null;
  last_stdout: string | null;
  last_stderr: string | null;
  last_exit_code: number | null;
  last_started_at_utc: string | null;
  last_finished_at_utc: string | null;
  last_seen_at_utc: string | null;
  last_issue_fingerprint: string | null;
  last_success_fingerprint: string | null;
  last_success_at_utc: string | null;
  source_path: string | null;
  stop_reason: string | null;
}

// ============================================================
// Queue state (persisted to queue-state.json)
// ============================================================

export interface QueueState {
  schema_version: 1;
  updated_at_utc: string;
  issues: Record<string, IssueStateRecord>;
}

// ============================================================
// Canonical queue config (after compat normalization)
// ============================================================

export interface TrackerConfig {
  kind: 'local-json' | 'local-files' | 'linear';
  source_file?: string;
  source_dir?: string;
  include_globs?: string[];
  recurse?: boolean;
  active_states: string[];
  terminal_states: string[];
  // Linear-specific
  project_slug?: string;
  api_key_env?: string;
  endpoint?: string;
}

export interface PollingConfig {
  interval_seconds: number;
  max_polls: number;
  drain_on_exit: boolean;
}

export interface WorkspaceConfig {
  root: string;
}

export interface OutputConfig {
  root: string;
  state_file?: string;
  report_file?: string;
}

export interface HooksConfig {
  after_create?: {
    command: string;
    sentinel_paths: string[];
    if_workspace_empty: boolean;
  };
}

export interface LauncherConfig {
  max_concurrent_issues: number;
  execution_mode: string;
  shared_directive_mode?: string;
  write_prompt_files?: boolean;
  write_summary_file?: boolean;
  supervisor_only?: boolean;
  require_final_read_only_review?: boolean;
  material_issue_strategy?: string;
  agents_template?: unknown[];
  defaults?: Record<string, unknown>;
}

export interface RetryConfig {
  base_backoff_seconds: number;
  max_backoff_seconds: number;
}

export interface CanonicalQueueConfig {
  config_directory: string;
  tracker: TrackerConfig;
  polling: PollingConfig;
  workspace: WorkspaceConfig;
  output: OutputConfig;
  hooks: HooksConfig;
  launcher: LauncherConfig;
  retry: RetryConfig;
  workflow_file?: string;
  workflow_prompt_mode?: string;
  workflow_render_strict?: boolean;
  workflow_auto_detect?: boolean;
}

// ============================================================
// Running process handle
// ============================================================

export interface RunningProcess {
  issueKey: string;
  pid: number;
  specPath: string;
  stdoutPath: string;
  stderrPath: string;
  startedAt: string;
  kill: () => void;
}

// ============================================================
// Launcher result (parsed from --json output or manifest)
// ============================================================

export interface LauncherResult {
  manifest: string | null;
  summary: string | null;
  exitCode: number;
}
