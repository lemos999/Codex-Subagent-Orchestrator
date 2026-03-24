/**
 * Queue state — persistent state management.
 *
 * - 17-field IssueStateRecord (PS-compatible)
 * - Atomic save (write to .tmp then rename)
 * - Schema version for forward compatibility
 */

import * as fs from 'node:fs/promises';
import * as path from 'node:path';
import type { QueueState, IssueStateRecord } from './queue-types.js';

// ============================================================
// Create / Load
// ============================================================

export function createEmptyState(): QueueState {
  return {
    schema_version: 1,
    updated_at_utc: new Date().toISOString(),
    issues: {},
  };
}

export async function loadState(statePath: string): Promise<QueueState> {
  try {
    const raw = await fs.readFile(statePath, 'utf8');
    const parsed = JSON.parse(raw) as QueueState;
    // Accept any schema version — forward compatible
    if (!parsed.issues || typeof parsed.issues !== 'object') {
      return createEmptyState();
    }
    return parsed;
  } catch {
    return createEmptyState();
  }
}

// ============================================================
// Save (atomic: write .tmp then rename)
// ============================================================

export async function saveState(statePath: string, state: QueueState): Promise<void> {
  state.updated_at_utc = new Date().toISOString();
  const dir = path.dirname(statePath);
  await fs.mkdir(dir, { recursive: true });
  const tmp = statePath + '.tmp';
  await fs.writeFile(tmp, JSON.stringify(state, null, 2), 'utf8');
  await fs.rename(tmp, statePath);
}

// ============================================================
// Get / create issue state record
// ============================================================

export function getIssueRecord(state: QueueState, issueKey: string): IssueStateRecord {
  if (!state.issues[issueKey]) {
    state.issues[issueKey] = createEmptyRecord(issueKey);
  }
  return state.issues[issueKey]!;
}

function createEmptyRecord(issueKey: string): IssueStateRecord {
  return {
    issue_key: issueKey,
    status: 'idle',
    dispatch_count: 0,
    consecutive_failures: 0,
    next_eligible_at_utc: null,
    workspace_path: null,
    last_state: null,
    last_manifest: null,
    last_summary: null,
    last_stdout: null,
    last_stderr: null,
    last_exit_code: null,
    last_started_at_utc: null,
    last_finished_at_utc: null,
    last_seen_at_utc: null,
    last_issue_fingerprint: null,
    last_success_fingerprint: null,
    last_success_at_utc: null,
    source_path: null,
    stop_reason: null,
  };
}

// ============================================================
// Backoff calculation (PS-compatible: 2^(failures-1) * base)
// ============================================================

export function getBackoffSeconds(
  consecutiveFailures: number,
  baseBackoff: number,
  maxBackoff: number,
): number {
  if (consecutiveFailures <= 0) return 0;
  const backoff = Math.pow(2, consecutiveFailures - 1) * baseBackoff;
  return Math.min(backoff, maxBackoff);
}

export function isEligibleNow(record: IssueStateRecord): boolean {
  if (!record.next_eligible_at_utc) return true;
  // PS-compatible: if parse fails, return true (eligible)
  const parsed = new Date(record.next_eligible_at_utc);
  if (isNaN(parsed.getTime())) return true;
  return new Date() >= parsed;
}
