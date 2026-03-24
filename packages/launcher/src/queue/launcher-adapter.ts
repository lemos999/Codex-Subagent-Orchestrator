/**
 * Launcher adapter — encapsulates launcher execution.
 *
 * Handles:
 * - Absolute launcher path resolution (config dir based)
 * - cwd separation (launcher runs from config dir, spec.cwd = workspace)
 * - spawn / kill semantics
 * - stdout/stderr capture
 * - Result parsing (--json mode or manifest file)
 */

import * as fs from 'node:fs/promises';
import * as path from 'node:path';
import { spawn, type ChildProcess } from 'node:child_process';
import type { NormalizedIssue, CanonicalQueueConfig, RunningProcess, LauncherResult } from './queue-types.js';

const IS_WINDOWS = process.platform === 'win32';

// ============================================================
// Generate launcher spec from issue + queue config
// ============================================================

export function generateLauncherSpec(
  issue: NormalizedIssue,
  config: CanonicalQueueConfig,
  workspacePath: string,
  runOutputDir: string,
  attempt: number,
): Record<string, unknown> {
  const spec: Record<string, unknown> = {
    cwd: workspacePath,
    output_dir: runOutputDir,
    execution_mode: config.launcher.execution_mode,
    skip_git_repo_check: true,
    write_prompt_files: config.launcher.write_prompt_files ?? true,
    write_summary_file: config.launcher.write_summary_file ?? true,
    workflow_context: {
      issue: {
        id: issue.id,
        identifier: issue.identifier,
        title: issue.title,
        description: issue.description,
        priority: issue.priority,
        state: issue.state,
        labels: issue.labels,
        blocked_by: issue.blocked_by,
        requested_deliverables: issue.requested_deliverables,
        source_path: issue.source_path,
        branch_name: issue.branch_name,
        url: issue.url,
      },
      attempt,
    },
    defaults: config.launcher.defaults ?? {},
    agents: config.launcher.agents_template ?? [],
  };

  if (issue.requested_deliverables.length > 0) {
    spec.requested_deliverables = issue.requested_deliverables;
  }
  if (config.launcher.shared_directive_mode) {
    spec.shared_directive_mode = config.launcher.shared_directive_mode;
  }
  if (config.launcher.supervisor_only) {
    spec.supervisor_only = config.launcher.supervisor_only;
  }
  if (config.launcher.require_final_read_only_review) {
    spec.require_final_read_only_review = config.launcher.require_final_read_only_review;
  }
  if (config.launcher.material_issue_strategy) {
    spec.material_issue_strategy = config.launcher.material_issue_strategy;
  }
  if (config.workflow_file) spec.workflow_file = config.workflow_file;
  if (config.workflow_prompt_mode) spec.workflow_prompt_mode = config.workflow_prompt_mode;
  if (config.workflow_render_strict !== undefined) spec.workflow_render_strict = config.workflow_render_strict;
  if (config.workflow_auto_detect !== undefined) spec.workflow_auto_detect = config.workflow_auto_detect;

  // Convert hooks to TS launcher format
  if (config.hooks.after_create) {
    spec.hooks = {
      after_create: {
        command: config.hooks.after_create.command,
        sentinel_paths: config.hooks.after_create.sentinel_paths,
        if_workspace_empty: config.hooks.after_create.if_workspace_empty,
      },
    };
  }

  return spec;
}

// ============================================================
// Spawn launcher process
// ============================================================

export async function spawnLauncher(
  issueKey: string,
  specPath: string,
  config: CanonicalQueueConfig,
  logsDir: string,
): Promise<RunningProcess> {
  const stdoutPath = path.join(logsDir, `${issueKey}.stdout.log`);
  const stderrPath = path.join(logsDir, `${issueKey}.stderr.log`);
  await fs.mkdir(logsDir, { recursive: true });

  // Resolve launcher path — relative to config directory
  const launcherPath = path.resolve(config.config_directory, 'packages/launcher/dist/cli.js');

  const child = spawn('node', [launcherPath, '--spec', specPath, '--json'], {
    cwd: config.config_directory,
    stdio: ['ignore', 'pipe', 'pipe'],
    shell: IS_WINDOWS,
  });

  // Capture stdout/stderr to files
  const stdoutStream = await fs.open(stdoutPath, 'w');
  const stderrStream = await fs.open(stderrPath, 'w');

  child.stdout?.on('data', (chunk: Buffer) => {
    stdoutStream.write(chunk);
  });
  child.stderr?.on('data', (chunk: Buffer) => {
    stderrStream.write(chunk);
  });

  // Clean up file handles on exit
  child.on('exit', () => {
    stdoutStream.close();
    stderrStream.close();
  });

  return {
    issueKey,
    pid: child.pid ?? -1,
    specPath,
    stdoutPath,
    stderrPath,
    startedAt: new Date().toISOString(),
    kill: () => {
      try { child.kill('SIGTERM'); } catch { /* already dead */ }
    },
  };
}

// ============================================================
// Wait for launcher and parse result
// ============================================================

export function waitForProcess(child: ChildProcess): Promise<number> {
  return new Promise((resolve) => {
    child.on('exit', (code) => resolve(code ?? 1));
    child.on('error', () => resolve(1));
  });
}

export async function parseLauncherResult(
  stdoutPath: string,
  exitCode: number,
): Promise<LauncherResult> {
  try {
    const raw = await fs.readFile(stdoutPath, 'utf8');
    // Try to find JSON output (last JSON object in stdout)
    const jsonMatch = raw.match(/\{[\s\S]*"manifest"[\s\S]*\}/);
    if (jsonMatch) {
      const parsed = JSON.parse(jsonMatch[0]) as Record<string, unknown>;
      return {
        manifest: (parsed.manifest as string) ?? null,
        summary: (parsed.summary as string) ?? null,
        exitCode,
      };
    }
  } catch {
    // Fall through to default
  }

  return { manifest: null, summary: null, exitCode };
}
