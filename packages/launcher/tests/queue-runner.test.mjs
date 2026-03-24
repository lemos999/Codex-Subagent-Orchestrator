/**
 * Queue runner golden tests — PS behavior fixtures.
 *
 * Tests: config compat, issue normalization, fingerprint,
 * blocked_by, backoff, state, sort order.
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

import { normalizeQueueConfig } from '../dist/queue/queue-compat.js';
import { normalizeIssue, computeFingerprint, isBlocked, compareIssues } from '../dist/queue/issue-normalizer.js';
import { createEmptyState, getIssueRecord, getBackoffSeconds, isEligibleNow } from '../dist/queue/queue-state.js';

// ============================================================
// 1. Config compat
// ============================================================

describe('queue-compat', () => {
  it('normalizes mock-json to local-json', () => {
    const cfg = normalizeQueueConfig(
      { tracker: { kind: 'mock-json', source_file: 'issues.json' }, workspace: { root: 'ws' }, output: { root: 'out' } },
      '/tmp/queue.json',
    );
    assert.equal(cfg.tracker.kind, 'local-json');
  });

  it('converts flat hooks to nested format', () => {
    const cfg = normalizeQueueConfig(
      {
        tracker: { kind: 'local-json', source_file: 'q.json' },
        workspace: { root: 'ws' },
        output: { root: 'out' },
        hooks: {
          after_create: 'git clone repo .',
          after_create_sentinel_paths: ['.git', 'AGENTS.md'],
        },
      },
      '/tmp/queue.json',
    );
    assert.equal(cfg.hooks.after_create.command, 'git clone repo .');
    assert.deepEqual(cfg.hooks.after_create.sentinel_paths, ['.git', 'AGENTS.md']);
  });

  it('handles nested hooks format', () => {
    const cfg = normalizeQueueConfig(
      {
        tracker: { kind: 'local-json', source_file: 'q.json' },
        workspace: { root: 'ws' },
        output: { root: 'out' },
        hooks: {
          after_create: { command: 'echo hi', sentinel_paths: ['a.txt'] },
        },
      },
      '/tmp/queue.json',
    );
    assert.equal(cfg.hooks.after_create.command, 'echo hi');
    assert.deepEqual(cfg.hooks.after_create.sentinel_paths, ['a.txt']);
  });

  it('uses default retry values (30s/300s)', () => {
    const cfg = normalizeQueueConfig(
      { tracker: { kind: 'local-json', source_file: 'q.json' }, workspace: { root: 'ws' }, output: { root: 'out' } },
      '/tmp/queue.json',
    );
    assert.equal(cfg.retry.base_backoff_seconds, 30);
    assert.equal(cfg.retry.max_backoff_seconds, 300);
  });

  it('parses linear tracker config', () => {
    const cfg = normalizeQueueConfig(
      {
        tracker: {
          kind: 'linear',
          project_slug: 'my-project',
          api_key_env: 'MY_LINEAR_KEY',
          active_states: ['Todo', 'In Progress', 'Rework'],
          terminal_states: ['Done', 'Cancelled'],
        },
        workspace: { root: 'ws' },
        output: { root: 'out' },
      },
      '/tmp/queue.json',
    );
    assert.equal(cfg.tracker.kind, 'linear');
    assert.equal(cfg.tracker.project_slug, 'my-project');
    assert.equal(cfg.tracker.api_key_env, 'MY_LINEAR_KEY');
    assert.equal(cfg.tracker.endpoint, 'https://api.linear.app/graphql');
    assert.deepEqual(cfg.tracker.active_states, ['Todo', 'In Progress', 'Rework']);
  });

  it('defaults linear endpoint and api_key_env', () => {
    const cfg = normalizeQueueConfig(
      {
        tracker: { kind: 'linear', project_slug: 'test' },
        workspace: { root: 'ws' },
        output: { root: 'out' },
      },
      '/tmp/queue.json',
    );
    assert.equal(cfg.tracker.api_key_env, 'LINEAR_API_KEY');
    assert.equal(cfg.tracker.endpoint, 'https://api.linear.app/graphql');
  });

  it('ignores unknown fields (passthrough)', () => {
    const cfg = normalizeQueueConfig(
      {
        tracker: { kind: 'local-json', source_file: 'q.json' },
        workspace: { root: 'ws' },
        output: { root: 'out' },
        unknown_field: 'should not crash',
        launcher: { max_concurrent_issues: 3, timeout_seconds: 999 },
      },
      '/tmp/queue.json',
    );
    assert.equal(cfg.launcher.max_concurrent_issues, 3);
    // No crash = pass
  });
});

// ============================================================
// 2. Issue normalization
// ============================================================

describe('issue-normalizer', () => {
  it('resolves id/identifier/key aliases', () => {
    const issue = normalizeIssue({ key: 'ABC-1', name: 'Title', body: 'Desc' });
    assert.equal(issue.identifier, 'ABC-1');
    assert.equal(issue.title, 'Title');
    assert.equal(issue.description, 'Desc');
  });

  it('defaults state to Todo', () => {
    const issue = normalizeIssue({ identifier: 'X', title: 'T' });
    assert.equal(issue.state, 'Todo');
  });

  it('preserves null priority (PS-compatible: cast only at sort)', () => {
    const issue = normalizeIssue({ identifier: 'X', title: 'T' });
    assert.equal(issue.priority, null);
  });

  it('parses numeric priority', () => {
    const issue = normalizeIssue({ identifier: 'X', title: 'T', priority: 3 });
    assert.equal(issue.priority, 3);
  });

  it('parses string priority to number', () => {
    const issue = normalizeIssue({ identifier: 'X', title: 'T', priority: '3' });
    assert.equal(issue.priority, 3);
  });

  it('handles blocked_by as string array', () => {
    const issue = normalizeIssue({ identifier: 'X', title: 'T', blocked_by: ['A', 'B'] });
    assert.deepEqual(issue.blocked_by, ['A', 'B']);
  });

  it('handles blocked_by as object array', () => {
    const issue = normalizeIssue({
      identifier: 'X', title: 'T',
      blocked_by: [{ identifier: 'A' }, { id: 'B' }],
    });
    assert.equal(issue.blocked_by.length, 2);
  });
});

// ============================================================
// 3. Fingerprint (PS-compatible: no sorting)
// ============================================================

describe('fingerprint', () => {
  it('produces stable JSON string', () => {
    const issue = normalizeIssue({ identifier: 'X', title: 'T', description: 'D', state: 'Todo' });
    const fp1 = computeFingerprint(issue);
    const fp2 = computeFingerprint(issue);
    assert.equal(fp1, fp2);
  });

  it('preserves original order (no sorting)', () => {
    const issue = normalizeIssue({
      identifier: 'X', title: 'T',
      labels: ['z', 'a', 'm'],
      requested_deliverables: ['c', 'a', 'b'],
    });
    const fp = computeFingerprint(issue);
    const parsed = JSON.parse(fp);
    // Order preserved, not sorted
    assert.deepEqual(parsed.labels, ['z', 'a', 'm']);
    assert.deepEqual(parsed.requested_deliverables, ['c', 'a', 'b']);
  });

  it('deduplicates labels', () => {
    const issue = normalizeIssue({
      identifier: 'X', title: 'T',
      labels: ['a', 'b', 'a'],
    });
    const fp = computeFingerprint(issue);
    const parsed = JSON.parse(fp);
    assert.deepEqual(parsed.labels, ['a', 'b']);
  });
});

// ============================================================
// 4. blocked_by resolution
// ============================================================

describe('blocked_by', () => {
  it('blocks when blocker is in active state', () => {
    const issue = normalizeIssue({ identifier: 'A', title: 'A', blocked_by: ['B'] });
    const blockerB = normalizeIssue({ identifier: 'B', title: 'B', state: 'Todo' });
    const issueMap = new Map([['B', blockerB]]);
    const state = {};

    assert.equal(isBlocked(issue, ['Todo', 'In Progress'], issueMap, state), true);
  });

  it('resolves when blocker is not in active state (e.g. Done)', () => {
    const issue = normalizeIssue({ identifier: 'A', title: 'A', blocked_by: ['B'] });
    const blockerB = normalizeIssue({ identifier: 'B', title: 'B', state: 'Done' });
    const issueMap = new Map([['B', blockerB]]);
    const state = {};

    assert.equal(isBlocked(issue, ['Todo', 'In Progress'], issueMap, state), false);
  });

  it('resolves when blocker has matching success fingerprint', () => {
    const issue = normalizeIssue({ identifier: 'A', title: 'A', blocked_by: ['B'] });
    const blockerB = normalizeIssue({ identifier: 'B', title: 'B', state: 'In Progress' });
    const fp = computeFingerprint(blockerB);
    const issueMap = new Map([['B', blockerB]]);
    const state = { B: { last_success_fingerprint: fp } };

    assert.equal(isBlocked(issue, ['Todo', 'In Progress'], issueMap, state), false);
  });

  it('resolves when blocker is missing but status=completed', () => {
    const issue = normalizeIssue({ identifier: 'A', title: 'A', blocked_by: ['GONE'] });
    const issueMap = new Map(); // GONE not in tracker
    const state = { GONE: { status: 'completed', last_success_fingerprint: null } };

    assert.equal(isBlocked(issue, ['Todo', 'In Progress'], issueMap, state), false);
  });

  it('does NOT block when string blocker is missing and no record (PS-compatible)', () => {
    const issue = normalizeIssue({ identifier: 'A', title: 'A', blocked_by: ['MISSING'] });
    const issueMap = new Map();
    const state = {};

    assert.equal(isBlocked(issue, ['Todo', 'In Progress'], issueMap, state), false);
  });

  it('blocks when object blocker has active state but is missing from tracker', () => {
    const issue = normalizeIssue({
      identifier: 'A', title: 'A',
      blocked_by: [{ identifier: 'B', state: 'Todo' }],
    });
    const issueMap = new Map();
    const state = {};

    assert.equal(isBlocked(issue, ['Todo', 'In Progress'], issueMap, state), true);
  });
});

// ============================================================
// 5. Backoff
// ============================================================

describe('backoff', () => {
  it('returns 0 for no failures', () => {
    assert.equal(getBackoffSeconds(0, 30, 300), 0);
  });

  it('calculates 2^(n-1) * base', () => {
    assert.equal(getBackoffSeconds(1, 30, 300), 30);   // 2^0 * 30
    assert.equal(getBackoffSeconds(2, 30, 300), 60);   // 2^1 * 30
    assert.equal(getBackoffSeconds(3, 30, 300), 120);  // 2^2 * 30
    assert.equal(getBackoffSeconds(4, 30, 300), 240);  // 2^3 * 30
  });

  it('caps at max', () => {
    assert.equal(getBackoffSeconds(5, 30, 300), 300);  // 2^4 * 30 = 480 → capped 300
    assert.equal(getBackoffSeconds(10, 30, 300), 300);
  });
});

// ============================================================
// 6. State
// ============================================================

describe('state', () => {
  it('creates empty state with schema_version', () => {
    const state = createEmptyState();
    assert.equal(state.schema_version, 1);
    assert.deepEqual(state.issues, {});
  });

  it('creates issue record with 20 fields', () => {
    const state = createEmptyState();
    const record = getIssueRecord(state, 'ISSUE-1');
    assert.equal(Object.keys(record).length, 20);
    assert.equal(record.issue_key, 'ISSUE-1');
    assert.equal(record.status, 'idle');
    assert.equal(record.dispatch_count, 0);
  });

  it('returns existing record on second call', () => {
    const state = createEmptyState();
    const r1 = getIssueRecord(state, 'X');
    r1.status = 'running';
    const r2 = getIssueRecord(state, 'X');
    assert.equal(r2.status, 'running');
  });

  it('isEligibleNow returns true when no backoff', () => {
    const record = getIssueRecord(createEmptyState(), 'X');
    assert.equal(isEligibleNow(record), true);
  });

  it('isEligibleNow returns false when in future', () => {
    const record = getIssueRecord(createEmptyState(), 'X');
    record.next_eligible_at_utc = new Date(Date.now() + 60000).toISOString();
    assert.equal(isEligibleNow(record), false);
  });

  it('isEligibleNow returns true on invalid timestamp (PS-compatible)', () => {
    const record = getIssueRecord(createEmptyState(), 'X');
    record.next_eligible_at_utc = 'not-a-date';
    assert.equal(isEligibleNow(record), true);
  });
});

// ============================================================
// 7. Sort order (PS-compatible: priority asc → updated_at asc → identifier asc)
// ============================================================

describe('sort order', () => {
  it('sorts by priority ascending', () => {
    const a = normalizeIssue({ identifier: 'A', title: 'A', priority: 2 });
    const b = normalizeIssue({ identifier: 'B', title: 'B', priority: 1 });
    const sorted = [a, b].sort(compareIssues);
    assert.equal(sorted[0].identifier, 'B'); // priority 1 first
  });

  it('null priority sorts as 999 (last)', () => {
    const a = normalizeIssue({ identifier: 'A', title: 'A' }); // priority=null → 999
    const b = normalizeIssue({ identifier: 'B', title: 'B', priority: 1 });
    const sorted = [a, b].sort(compareIssues);
    assert.equal(sorted[0].identifier, 'B'); // priority 1 before 999
  });

  it('sorts by updated_at ascending (older first)', () => {
    const a = normalizeIssue({ identifier: 'A', title: 'A', priority: 1, updated_at: '2026-03-02' });
    const b = normalizeIssue({ identifier: 'B', title: 'B', priority: 1, updated_at: '2026-03-01' });
    const sorted = [a, b].sort(compareIssues);
    assert.equal(sorted[0].identifier, 'B'); // older first (ascending)
  });

  it('sorts by identifier ascending as tiebreaker', () => {
    const a = normalizeIssue({ identifier: 'B', title: 'B', priority: 1 });
    const b = normalizeIssue({ identifier: 'A', title: 'A', priority: 1 });
    const sorted = [a, b].sort(compareIssues);
    assert.equal(sorted[0].identifier, 'A'); // alphabetical
  });
});
