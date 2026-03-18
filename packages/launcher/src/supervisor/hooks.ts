/**
 * Hook execution — runs spec-defined hooks at specific lifecycle points.
 *
 * Currently supported:
 * - after_create: runs after workspace directory is created/verified
 */

import { spawn } from 'node:child_process';
import * as fs from 'node:fs/promises';
import * as fsSync from 'node:fs';
import * as path from 'node:path';

import type { HooksSpec } from '../types/spec.js';

export interface HookResult {
  ran: boolean;
  trigger: string | null;
  exitCode: number | null;
  stdout: string | null;
  stderr: string | null;
  missingPaths: string[];
  workspaceWasEmpty: boolean;
}

function emptyResult(): HookResult {
  return {
    ran: false,
    trigger: null,
    exitCode: null,
    stdout: null,
    stderr: null,
    missingPaths: [],
    workspaceWasEmpty: false,
  };
}

/**
 * Run the after_create hook if conditions are met.
 */
export async function runAfterCreateHook(
  hooks: HooksSpec | undefined,
  workspaceRoot: string,
): Promise<HookResult> {
  if (!hooks?.after_create) return emptyResult();

  const hook = hooks.after_create;
  const result = emptyResult();

  // Check workspace empty
  try {
    const entries = await fs.readdir(workspaceRoot);
    result.workspaceWasEmpty = entries.length === 0;
  } catch {
    result.workspaceWasEmpty = true;
  }

  // Check sentinel paths
  if (hook.sentinel_paths) {
    for (const p of hook.sentinel_paths) {
      const fullPath = path.resolve(workspaceRoot, p);
      if (!fsSync.existsSync(fullPath)) {
        result.missingPaths.push(p);
      }
    }
  }

  // Determine if hook should run
  const shouldRun =
    (hook.if_workspace_empty && result.workspaceWasEmpty) ||
    result.missingPaths.length > 0;

  if (!shouldRun) return result;

  result.trigger = result.workspaceWasEmpty
    ? 'workspace_empty'
    : 'missing_sentinel';

  // Execute hook command
  try {
    const { exitCode, stdout, stderr } = await executeCommand(
      hook.command,
      workspaceRoot,
    );
    result.ran = true;
    result.exitCode = exitCode;
    result.stdout = stdout;
    result.stderr = stderr;

    // Write stdout/stderr files if configured (with error handling)
    if (hook.stdout_file && stdout) {
      try {
        await fs.writeFile(hook.stdout_file, stdout, 'utf8');
      } catch {
        /* ignore write error for hook output files */
      }
    }
    if (hook.stderr_file && stderr) {
      try {
        await fs.writeFile(hook.stderr_file, stderr, 'utf8');
      } catch {
        /* ignore write error for hook output files */
      }
    }
  } catch (err) {
    result.ran = true;
    result.exitCode = -1;
    result.stderr = err instanceof Error ? err.message : String(err);
  }

  return result;
}

function executeCommand(
  command: string,
  cwd: string,
): Promise<{ exitCode: number; stdout: string; stderr: string }> {
  return new Promise((resolve, reject) => {
    const child = spawn(command, [], {
      cwd,
      shell: true,
      stdio: ['ignore', 'pipe', 'pipe'],
    });

    const stdoutChunks: Buffer[] = [];
    const stderrChunks: Buffer[] = [];

    child.stdout.on('data', (chunk: Buffer) => stdoutChunks.push(chunk));
    child.stderr.on('data', (chunk: Buffer) => stderrChunks.push(chunk));

    child.on('error', reject);
    child.on('close', (code) => {
      resolve({
        exitCode: code ?? 1,
        stdout: Buffer.concat(stdoutChunks).toString('utf8'),
        stderr: Buffer.concat(stderrChunks).toString('utf8'),
      });
    });
  });
}
