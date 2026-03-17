/**
 * Live usage monitor — polls worker stdout/session files for token usage events.
 * Accumulates token counts and writes snapshots to a status file.
 *
 * Zero additional API calls — reads from files the worker already writes.
 */

import * as fs from 'node:fs/promises';
import * as fsSync from 'node:fs';
import type { LiveUsageSpec } from '../types/spec.js';

// ============================================================
// Types
// ============================================================

export interface UsageSnapshot {
  updated_at_utc: string;
  workers: Record<string, WorkerUsage>;
  totals: TokenBreakdown;
}

export interface WorkerUsage {
  name: string;
  status: 'running' | 'completed' | 'failed';
  tokens: TokenBreakdown;
  last_update_utc: string;
}

export interface TokenBreakdown {
  input_tokens: number;
  output_tokens: number;
  cached_input_tokens: number;
  reasoning_output_tokens: number;
  total_tokens: number;
}

function emptyBreakdown(): TokenBreakdown {
  return {
    input_tokens: 0,
    output_tokens: 0,
    cached_input_tokens: 0,
    reasoning_output_tokens: 0,
    total_tokens: 0,
  };
}

// ============================================================
// File tail cursor
// ============================================================

interface FileCursor {
  offset: number;
  remainder: string;
}

function readAppendedLines(filePath: string, cursor: FileCursor): string[] {
  if (!filePath || !fsSync.existsSync(filePath)) return [];

  let fd: number | null = null;
  try {
    fd = fsSync.openSync(filePath, 'r');
    const stat = fsSync.fstatSync(fd);

    if (cursor.offset > stat.size) {
      cursor.offset = 0;
      cursor.remainder = '';
    }

    const buf = Buffer.alloc(stat.size - cursor.offset);
    const bytesRead = fsSync.readSync(fd, buf, 0, buf.length, cursor.offset);
    cursor.offset += bytesRead;

    const text = buf.toString('utf8', 0, bytesRead);
    if (!text) return [];

    const combined = cursor.remainder + text;
    const normalized = combined.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
    const parts = normalized.split('\n');

    if (normalized.endsWith('\n')) {
      cursor.remainder = '';
      // Remove trailing empty element
      if (parts.length > 0 && parts[parts.length - 1] === '') {
        parts.pop();
      }
    } else {
      cursor.remainder = parts.pop() ?? '';
    }

    return parts;
  } catch {
    return [];
  } finally {
    if (fd !== null) fsSync.closeSync(fd);
  }
}

// ============================================================
// Token extraction from JSON event lines
// ============================================================

function extractTokensFromLine(line: string): Partial<TokenBreakdown> | null {
  if (!line.trim()) return null;

  try {
    const entry = JSON.parse(line) as Record<string, unknown>;

    // Format 1: Codex session.jsonl event with usage object
    const usage = (entry['usage'] ?? entry['token_usage']) as Record<string, unknown> | undefined;
    if (usage) {
      return {
        total_tokens: asNum(usage['total_tokens'] ?? usage['totalTokens']),
        input_tokens: asNum(usage['input_tokens'] ?? usage['inputTokens']),
        output_tokens: asNum(usage['output_tokens'] ?? usage['outputTokens']),
        cached_input_tokens: asNum(usage['cached_input_tokens'] ?? usage['cachedInputTokens']),
        reasoning_output_tokens: asNum(usage['reasoning_output_tokens'] ?? usage['reasoningOutputTokens']),
      };
    }

    // Format 2: event_msg with token_count
    const eventMsg = entry['event_msg'] as Record<string, unknown> | undefined;
    if (eventMsg) {
      const tokenCount = asNum(eventMsg['token_count']);
      if (tokenCount > 0) {
        return { total_tokens: tokenCount };
      }
    }
  } catch {
    // Not JSON — skip
  }

  return null;
}

function asNum(v: unknown): number {
  if (typeof v === 'number') return v;
  if (typeof v === 'string') {
    const n = parseInt(v, 10);
    return isNaN(n) ? 0 : n;
  }
  return 0;
}

// ============================================================
// Usage monitor class
// ============================================================

export class UsageMonitor {
  private readonly config: LiveUsageSpec;
  private readonly statusFile: string | null;
  private readonly pollIntervalMs: number;
  private readonly workerFiles = new Map<string, { stdoutPath: string; cursor: FileCursor }>();
  private readonly workerUsages = new Map<string, WorkerUsage>();
  private timer: ReturnType<typeof setInterval> | null = null;
  private running = false;

  constructor(config: LiveUsageSpec) {
    this.config = config;
    this.statusFile = config.status_file ?? null;
    this.pollIntervalMs = Math.max(config.poll_interval_ms ?? 500, 100);
  }

  get enabled(): boolean {
    return this.config.enabled !== false;
  }

  /** Register a worker for monitoring before it starts. */
  registerWorker(name: string, stdoutPath: string): void {
    this.workerFiles.set(name, {
      stdoutPath,
      cursor: { offset: 0, remainder: '' },
    });
    this.workerUsages.set(name, {
      name,
      status: 'running',
      tokens: emptyBreakdown(),
      last_update_utc: new Date().toISOString(),
    });
  }

  /** Mark a worker as completed/failed. */
  markWorkerDone(name: string, exitCode: number): void {
    const usage = this.workerUsages.get(name);
    if (usage) {
      usage.status = exitCode === 0 ? 'completed' : 'failed';
      usage.last_update_utc = new Date().toISOString();
    }
  }

  /** Start the polling loop. */
  start(): void {
    if (!this.enabled || this.running) return;
    this.running = true;

    this.timer = setInterval(() => {
      this.poll();
    }, this.pollIntervalMs);
  }

  /** Stop the polling loop and write final snapshot. */
  async stop(): Promise<UsageSnapshot> {
    this.running = false;
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }

    // Final poll to catch any remaining data
    this.poll();

    const snapshot = this.buildSnapshot();
    if (this.statusFile) {
      await fs.writeFile(this.statusFile, JSON.stringify(snapshot, null, 2), 'utf8');
    }
    return snapshot;
  }

  /** Single poll cycle — read new lines from all worker files. */
  private poll(): void {
    for (const [name, file] of this.workerFiles) {
      const lines = readAppendedLines(file.stdoutPath, file.cursor);
      const usage = this.workerUsages.get(name);
      if (!usage) continue;

      for (const line of lines) {
        const tokens = extractTokensFromLine(line);
        if (tokens) {
          // Accumulate (use latest total if provided, otherwise add incrementally)
          if (tokens.total_tokens && tokens.total_tokens > usage.tokens.total_tokens) {
            usage.tokens.total_tokens = tokens.total_tokens;
          }
          if (tokens.input_tokens && tokens.input_tokens > usage.tokens.input_tokens) {
            usage.tokens.input_tokens = tokens.input_tokens;
          }
          if (tokens.output_tokens && tokens.output_tokens > usage.tokens.output_tokens) {
            usage.tokens.output_tokens = tokens.output_tokens;
          }
          if (tokens.cached_input_tokens && tokens.cached_input_tokens > usage.tokens.cached_input_tokens) {
            usage.tokens.cached_input_tokens = tokens.cached_input_tokens;
          }
          if (tokens.reasoning_output_tokens && tokens.reasoning_output_tokens > usage.tokens.reasoning_output_tokens) {
            usage.tokens.reasoning_output_tokens = tokens.reasoning_output_tokens;
          }
          usage.last_update_utc = new Date().toISOString();
        }
      }
    }

    // Write snapshot to file (sync to avoid overlapping writes)
    if (this.statusFile) {
      try {
        const snapshot = this.buildSnapshot();
        fsSync.writeFileSync(this.statusFile, JSON.stringify(snapshot, null, 2), 'utf8');
      } catch {
        // Ignore write errors during polling
      }
    }
  }

  /** Build the current usage snapshot. */
  private buildSnapshot(): UsageSnapshot {
    const totals = emptyBreakdown();

    for (const usage of this.workerUsages.values()) {
      totals.input_tokens += usage.tokens.input_tokens;
      totals.output_tokens += usage.tokens.output_tokens;
      totals.cached_input_tokens += usage.tokens.cached_input_tokens;
      totals.reasoning_output_tokens += usage.tokens.reasoning_output_tokens;
      totals.total_tokens += usage.tokens.total_tokens;
    }

    const workers: Record<string, WorkerUsage> = {};
    for (const [name, usage] of this.workerUsages) {
      workers[name] = { ...usage, tokens: { ...usage.tokens } };
    }

    return {
      updated_at_utc: new Date().toISOString(),
      workers,
      totals,
    };
  }
}
