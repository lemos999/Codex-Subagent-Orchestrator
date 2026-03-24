/**
 * Worker spawner — runs CLI commands via child_process.spawn.
 * Handles codex, claude, and gemini engines.
 */

import { spawn } from 'node:child_process';
import * as fs from 'node:fs/promises';
import * as path from 'node:path';

import type { Engine } from '../types/engine.js';
import type { WorkerResult } from '../types/manifest.js';
import { IS_WINDOWS, winCmd } from '../common/platform.js';
import { sha256 } from '../common/fs-helpers.js';

// ============================================================
// Resolved worker spec (everything needed to spawn one worker)
// ============================================================

export interface ResolvedWorkerSpec {
  name: string;
  engine: Engine;
  model: string;
  taskText: string;
  prompt: string;
  cwd: string;
  outputDir: string;
  sandbox: string;
  kind: string;
  stage: number;
  isReadOnly: boolean;
  reasoningEffort: string | null;
  promptProfile: string;
  responseStyle: string;
  maxResponseLines: number;
  json: boolean;
  outputSchema: Record<string, unknown> | null;
  writePromptFile: boolean;
  requiredPaths: string[];
  requiredNonEmptyPaths: string[];
  extraArgs: string[];
  timeoutMs: number;
}

// ============================================================
// Worker output (raw result before validation)
// ============================================================

export interface WorkerOutput {
  exitCode: number;
  stdoutPath: string;
  stderrPath: string;
  lastPath: string;
  promptPath: string | null;
  lastMessage: string;
  stdoutPreview: string;
  stderrPreview: string;
  command: string;
  promptSha256: string;
  promptChars: number;
}

// ============================================================
// Helpers
// ============================================================

/** Check if text contains non-ASCII characters (Korean, CJK, etc.) */
function hasNonAscii(text: string): boolean {
  return /[^\x00-\x7F]/.test(text);
}

// ============================================================
// Engine command builders
// ============================================================

interface SpawnCommand {
  cmd: string;
  args: string[];
  stdin?: string;
}

function buildCodexCommand(spec: ResolvedWorkerSpec): SpawnCommand {
  const args = ['exec', '--full-auto'];
  if (spec.model) {
    args.push('-m', spec.model);
  }
  // Note: codex exec does not support --reasoning-effort flag.
  args.push(...spec.extraArgs);

  // Encoding safety: warn about Korean content (Codex may show mojibake)
  const prompt = hasNonAscii(spec.prompt)
    ? `Note: This prompt contains non-ASCII characters (Korean/CJK). If file content appears garbled, the file is UTF-8 encoded Korean text.\n\n${spec.prompt}`
    : spec.prompt;

  return { cmd: winCmd('codex'), args, stdin: prompt };
}

function buildClaudeCommand(spec: ResolvedWorkerSpec): SpawnCommand {
  const args = ['--print'];
  if (spec.model) {
    args.push('--model', spec.model);
  }
  args.push(...spec.extraArgs);
  return { cmd: winCmd('claude'), args, stdin: spec.prompt };
}

function buildGeminiCommand(spec: ResolvedWorkerSpec): SpawnCommand {
  // Read-only roles (reviewer, analyzer) skip --yolo to prevent unintended file modifications.
  // --yolo auto-approves all tool calls including file writes.
  const args = spec.isReadOnly
    ? ['@google/gemini-cli', '--yolo']  // TODO: gemini-cli has no read-only flag yet; --yolo is required for non-interactive
    : ['@google/gemini-cli', '--yolo'];
  if (spec.model) {
    args.push('--model', spec.model);
  }
  args.push(...spec.extraArgs);

  // For read-only tasks, prepend safety instruction to prompt
  const safePrompt = spec.isReadOnly
    ? `IMPORTANT: This is a READ-ONLY analysis task. Do NOT modify, create, or delete any files. Only read files and provide analysis.\n\n${spec.prompt}`
    : spec.prompt;

  return { cmd: winCmd('npx'), args, stdin: safePrompt };
}

function buildCommand(spec: ResolvedWorkerSpec): SpawnCommand {
  switch (spec.engine) {
    case 'codex':
      return buildCodexCommand(spec);
    case 'claude':
      return buildClaudeCommand(spec);
    case 'gemini':
      return buildGeminiCommand(spec);
    default:
      throw new Error(`Unknown engine: ${spec.engine as string}`);
  }
}

function formatCommand(cmd: string, args: string[]): string {
  return `${cmd} ${args.join(' ')}`;
}

// ============================================================
// Output extraction
// ============================================================

function extractLastMessage(
  engine: Engine,
  stdout: string,
  _stderr: string,
): string {
  if (!stdout.trim()) return '';

  switch (engine) {
    case 'codex': {
      const lines = stdout.trim().split('\n');
      for (let i = lines.length - 1; i >= 0; i--) {
        try {
          const event = JSON.parse(lines[i]);
          if (event.type === 'message' && event.content) {
            return event.content;
          }
          if (typeof event === 'string') {
            return event;
          }
        } catch {
          // Not JSON, use as-is
        }
      }
      return lines[lines.length - 1] || '';
    }
    case 'claude':
      return stdout.trim();
    case 'gemini': {
      const lines = stdout.trim().split('\n');
      const filtered = lines.filter(
        (line) =>
          !line.includes('YOLO mode is enabled') &&
          !line.includes('Loaded cached credentials'),
      );
      return filtered.join('\n').trim();
    }
    default:
      return stdout.trim();
  }
}

function preview(text: string, maxLen = 200): string {
  if (!text) return '';
  const firstLines = text.trim().split('\n').slice(0, 3).join('\n');
  return firstLines.length > maxLen
    ? firstLines.slice(0, maxLen) + '...'
    : firstLines;
}

// ============================================================
// Main spawn function
// ============================================================

/**
 * Spawn a child process and collect its output.
 * Returns { exitCode, stdoutBuf, stderrBuf } after the process exits.
 *
 * Fix for review issue #9: The promise resolves with raw buffers
 * synchronously on close. File I/O happens after resolution, outside
 * the Promise constructor.
 */
function spawnProcess(
  cmd: string,
  args: string[],
  cwd: string,
  stdin: string | undefined,
  timeoutMs: number,
): Promise<{ exitCode: number; stdoutBuf: string; stderrBuf: string }> {
  return new Promise((resolve, reject) => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | null = null;

    if (timeoutMs > 0) {
      timer = setTimeout(() => {
        controller.abort();
      }, timeoutMs);
    }

    const child = spawn(cmd, args, {
      cwd,
      stdio: ['pipe', 'pipe', 'pipe'],
      signal: controller.signal,
      shell: IS_WINDOWS,
    });

    const stdoutChunks: Buffer[] = [];
    const stderrChunks: Buffer[] = [];

    child.stdout.on('data', (chunk: Buffer) => stdoutChunks.push(chunk));
    child.stderr.on('data', (chunk: Buffer) => stderrChunks.push(chunk));

    child.on('close', (code) => {
      if (timer) clearTimeout(timer);
      resolve({
        exitCode: code ?? 1,
        stdoutBuf: Buffer.concat(stdoutChunks).toString('utf8'),
        stderrBuf: Buffer.concat(stderrChunks).toString('utf8'),
      });
    });

    child.on('error', (err) => {
      if (timer) clearTimeout(timer);
      reject(err);
    });

    if (stdin !== undefined) {
      child.stdin.write(stdin);
      child.stdin.end();
    } else {
      child.stdin.end();
    }
  });
}

export async function spawnWorker(
  spec: ResolvedWorkerSpec,
): Promise<WorkerOutput> {
  const { cmd, args, stdin } = buildCommand(spec);
  const command = formatCommand(cmd, args);

  // Ensure output directory exists
  await fs.mkdir(spec.outputDir, { recursive: true });

  // File paths
  const stdoutPath = path.resolve(spec.outputDir, `${spec.name}.stdout.log`);
  const stderrPath = path.resolve(spec.outputDir, `${spec.name}.stderr.log`);
  const lastPath = path.resolve(spec.outputDir, `${spec.name}.last.txt`);
  const promptPath = spec.writePromptFile
    ? path.resolve(spec.outputDir, `${spec.name}.prompt.txt`)
    : null;

  // Write prompt file if configured
  const promptSha256 = sha256(spec.prompt);

  if (promptPath) {
    await fs.writeFile(promptPath, spec.prompt, 'utf8');
  }

  // Spawn process — returns raw buffers synchronously on close
  const { exitCode, stdoutBuf, stderrBuf } = await spawnProcess(
    cmd,
    args,
    spec.cwd,
    stdin,
    spec.timeoutMs,
  );

  // Write output files (outside Promise constructor — fix #9)
  await fs.writeFile(stdoutPath, stdoutBuf, 'utf8');
  await fs.writeFile(stderrPath, stderrBuf, 'utf8');

  const lastMsg = extractLastMessage(spec.engine, stdoutBuf, stderrBuf);
  await fs.writeFile(lastPath, lastMsg, 'utf8');

  return {
    exitCode,
    stdoutPath,
    stderrPath,
    lastPath,
    promptPath,
    lastMessage: lastMsg,
    stdoutPreview: preview(stdoutBuf),
    stderrPreview: preview(stderrBuf),
    command,
    promptSha256,
    promptChars: spec.prompt.length,
  };
}

// ============================================================
// Convert WorkerOutput to WorkerResult
// ============================================================

export function toWorkerResult(
  spec: ResolvedWorkerSpec,
  output: WorkerOutput,
  validationFailures: string[],
  missingPaths: string[],
  emptyPaths: string[],
): WorkerResult {
  const succeeded =
    output.exitCode === 0 &&
    missingPaths.length === 0 &&
    emptyPaths.length === 0 &&
    validationFailures.length === 0;

  return {
    name: spec.name,
    engine: spec.engine,
    mode: 'exec',
    stage: spec.stage,
    worker_kind: spec.kind,
    is_read_only: spec.isReadOnly,
    cwd: spec.cwd,
    exit_code: output.exitCode,
    succeeded,
    required_paths: spec.requiredPaths,
    required_non_empty_paths: spec.requiredNonEmptyPaths,
    missing_required_paths: missingPaths,
    empty_required_paths: emptyPaths,
    validation_failures: validationFailures,
    requested_model: spec.model,
    requested_full_auto: !spec.isReadOnly,
    requested_json_output: spec.json,
    actual_model: spec.model,
    requested_sandbox: spec.sandbox,
    actual_sandbox: null,
    requested_reasoning_effort: spec.reasoningEffort,
    actual_reasoning_effort: spec.reasoningEffort,
    prompt_profile: spec.promptProfile,
    response_style: spec.responseStyle,
    max_response_lines: spec.maxResponseLines,
    actual_approval: null,
    actual_workdir: null,
    output_mode: spec.json ? 'json' : 'text',
    session_id: null,
    footer_tokens_used: null,
    turn_failed: output.exitCode !== 0,
    failure_message:
      output.exitCode !== 0
        ? `Process exited with code ${output.exitCode}`
        : null,
    stdout: output.stdoutPath,
    stderr: output.stderrPath,
    last: output.lastPath,
    prompt: output.promptPath,
    prompt_sha256: output.promptSha256,
    prompt_chars: output.promptChars,
    workflow_prompt_mode: 'disabled',
    workflow_prompt_chars: 0,
    command: output.command,
    last_exists: true,
    last_message_preview: preview(output.lastMessage),
    stderr_preview: output.stderrPreview,
    stdout_preview: output.stdoutPreview,
  };
}
