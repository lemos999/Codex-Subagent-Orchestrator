/**
 * Queue compat — legacy PS config → canonical internal config.
 *
 * Handles:
 * - mock-json → local-json alias
 * - hooks.after_create (flat string) → hooks.after_create.command (nested object)
 * - after_create_sentinel_paths → hooks.after_create.sentinel_paths
 * - Unknown fields are silently ignored (passthrough)
 */

import * as path from 'node:path';
import type { CanonicalQueueConfig, TrackerConfig, PollingConfig, WorkspaceConfig, OutputConfig, HooksConfig, LauncherConfig, RetryConfig } from './queue-types.js';

// ============================================================
// Helpers
// ============================================================

function getOpt<T>(obj: Record<string, unknown>, key: string, fallback: T): T {
  const val = obj[key];
  return (val !== undefined && val !== null) ? val as T : fallback;
}

function getMap(obj: Record<string, unknown>, key: string): Record<string, unknown> {
  const val = obj[key];
  return (typeof val === 'object' && val !== null && !Array.isArray(val))
    ? val as Record<string, unknown>
    : {};
}

// ============================================================
// Normalize config
// ============================================================

export function normalizeQueueConfig(
  raw: Record<string, unknown>,
  configFilePath: string,
): CanonicalQueueConfig {
  const configDirectory = path.dirname(path.resolve(configFilePath));

  // Tracker
  const rawTracker = getMap(raw, 'tracker');
  let trackerKind = getOpt(rawTracker, 'kind', 'local-json') as string;
  if (trackerKind === 'mock-json') trackerKind = 'local-json'; // alias

  const tracker: TrackerConfig = {
    kind: trackerKind as 'local-json' | 'local-files' | 'linear',
    source_file: getOpt(rawTracker, 'source_file', undefined),
    source_dir: getOpt(rawTracker, 'source_dir', undefined),
    include_globs: getOpt(rawTracker, 'include_globs', ['*.md', '*.json']),
    recurse: getOpt(rawTracker, 'recurse', true),
    active_states: getOpt(rawTracker, 'active_states', ['Todo', 'In Progress']),
    terminal_states: getOpt(rawTracker, 'terminal_states', ['Done', 'Closed', 'Cancelled']),
    // Linear-specific
    project_slug: getOpt(rawTracker, 'project_slug', undefined),
    api_key_env: getOpt(rawTracker, 'api_key_env', 'LINEAR_API_KEY'),
    endpoint: getOpt(rawTracker, 'endpoint', 'https://api.linear.app/graphql'),
  };

  // Polling
  const rawPolling = getMap(raw, 'polling');
  const polling: PollingConfig = {
    interval_seconds: getOpt(rawPolling, 'interval_seconds', 5),
    max_polls: getOpt(rawPolling, 'max_polls', 0),
    drain_on_exit: getOpt(rawPolling, 'drain_on_exit', true),
  };

  // Workspace
  const rawWorkspace = getMap(raw, 'workspace');
  const workspace: WorkspaceConfig = {
    root: getOpt(rawWorkspace, 'root', 'workspaces'),
  };

  // Output
  const rawOutput = getMap(raw, 'output');
  const outputRoot = getOpt(rawOutput, 'root', 'queue-output');
  const output: OutputConfig = {
    root: outputRoot,
    state_file: getOpt(rawOutput, 'state_file', `${outputRoot}/queue-state.json`),
    report_file: getOpt(rawOutput, 'report_file', `${outputRoot}/queue-report.md`),
  };

  // Hooks — handle flat PS format → nested canonical format
  const rawHooks = getMap(raw, 'hooks');
  const hooks: HooksConfig = {};

  const afterCreateCmd = getOpt(rawHooks, 'after_create', undefined) as string | Record<string, unknown> | undefined;
  const afterCreateSentinels = getOpt(rawHooks, 'after_create_sentinel_paths', []) as string[];

  if (typeof afterCreateCmd === 'string') {
    // PS flat format: hooks.after_create is a command string
    hooks.after_create = {
      command: afterCreateCmd,
      sentinel_paths: afterCreateSentinels,
      // PS reads "after_create_if_workspace_empty" (flat key with prefix)
      if_workspace_empty: getOpt(rawHooks, 'after_create_if_workspace_empty',
        getOpt(rawHooks, 'if_workspace_empty', false)),
    };
  } else if (typeof afterCreateCmd === 'object' && afterCreateCmd !== null) {
    // TS nested format: hooks.after_create is already an object
    const cmd = afterCreateCmd as Record<string, unknown>;
    hooks.after_create = {
      command: getOpt(cmd, 'command', ''),
      sentinel_paths: getOpt(cmd, 'sentinel_paths', afterCreateSentinels),
      if_workspace_empty: getOpt(cmd, 'if_workspace_empty', false),
    };
  }

  // Launcher
  const rawLauncher = getMap(raw, 'launcher');
  const launcher: LauncherConfig = {
    max_concurrent_issues: getOpt(rawLauncher, 'max_concurrent_issues', 2),
    execution_mode: getOpt(rawLauncher, 'execution_mode', 'sequential'),
    shared_directive_mode: getOpt(rawLauncher, 'shared_directive_mode', undefined),
    write_prompt_files: getOpt(rawLauncher, 'write_prompt_files', true),
    write_summary_file: getOpt(rawLauncher, 'write_summary_file', true),
    supervisor_only: getOpt(rawLauncher, 'supervisor_only', undefined),
    require_final_read_only_review: getOpt(rawLauncher, 'require_final_read_only_review', undefined),
    material_issue_strategy: getOpt(rawLauncher, 'material_issue_strategy', undefined),
    agents_template: getOpt(rawLauncher, 'agents_template', undefined),
    defaults: getMap(rawLauncher, 'defaults'),
  };

  // Retry
  const rawRetry = getMap(raw, 'retry');
  const retry: RetryConfig = {
    base_backoff_seconds: getOpt(rawRetry, 'base_backoff_seconds', 30),
    max_backoff_seconds: getOpt(rawRetry, 'max_backoff_seconds', 300),
  };

  return {
    config_directory: configDirectory,
    tracker,
    polling,
    workspace,
    output,
    hooks,
    launcher,
    retry,
    workflow_file: getOpt(raw, 'workflow_file', undefined),
    workflow_prompt_mode: getOpt(raw, 'workflow_prompt_mode', undefined),
    workflow_render_strict: getOpt(raw, 'workflow_render_strict', undefined),
    workflow_auto_detect: getOpt(raw, 'workflow_auto_detect', undefined),
  };
}
