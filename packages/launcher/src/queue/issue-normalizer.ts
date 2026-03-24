/**
 * Issue normalizer — central normalization + fingerprint.
 *
 * Handles all field aliasing (id/identifier/key, title/name, description/body)
 * and produces a stable fingerprint identical to the PS queue runner.
 */

import type { RawIssue, NormalizedIssue, Blocker } from './queue-types.js';

// ============================================================
// Helpers
// ============================================================

function getOpt(obj: RawIssue, key: string): unknown {
  return obj[key] ?? undefined;
}

function firstNonEmpty(...values: unknown[]): string {
  for (const v of values) {
    if (typeof v === 'string' && v.length > 0) return v;
  }
  return '';
}

function toStringArray(value: unknown): string[] {
  if (!value) return [];
  if (Array.isArray(value)) return value.map(String);
  return [];
}

function toBlockerArray(value: unknown): Blocker[] {
  if (!value) return [];
  if (!Array.isArray(value)) return [];
  return value.map((item) => {
    if (typeof item === 'string') return item;
    if (typeof item === 'object' && item !== null) {
      return item as { identifier?: string; id?: string; key?: string; state?: string };
    }
    return String(item);
  });
}

// ============================================================
// Normalize
// ============================================================

export function normalizeIssue(raw: RawIssue, sourcePath?: string, sourceKind?: string): NormalizedIssue {
  const identifier = firstNonEmpty(
    getOpt(raw, 'identifier'),
    getOpt(raw, 'id'),
    getOpt(raw, 'key'),
  );

  const title = firstNonEmpty(
    getOpt(raw, 'title'),
    getOpt(raw, 'name'),
    identifier,
  );

  const id = firstNonEmpty(getOpt(raw, 'id'), identifier);

  // PS-compatible: preserve original priority (null if missing), cast only at sort time
  const rawPriority = raw.priority;
  const priority = typeof rawPriority === 'number'
    ? rawPriority
    : (typeof rawPriority === 'string' ? (parseInt(rawPriority, 10) || null) : null);

  const autoRun = raw.auto_run !== false && raw.auto_run !== 'false';

  return {
    id,
    identifier,
    title,
    description: firstNonEmpty(getOpt(raw, 'description'), getOpt(raw, 'body')),
    state: firstNonEmpty(getOpt(raw, 'state')) || 'Todo',
    priority,
    labels: toStringArray(getOpt(raw, 'labels')),
    blocked_by: toBlockerArray(getOpt(raw, 'blocked_by')),
    requested_deliverables: toStringArray(
      getOpt(raw, 'requested_deliverables') ?? getOpt(raw, 'deliverables'),
    ),
    auto_run: autoRun,
    source_path: sourcePath ?? firstNonEmpty(getOpt(raw, 'source_path')),
    source_kind: sourceKind ?? firstNonEmpty(getOpt(raw, 'source_kind')),
    branch_name: firstNonEmpty(getOpt(raw, 'branch_name')),
    url: firstNonEmpty(getOpt(raw, 'url')),
    created_at: firstNonEmpty(getOpt(raw, 'created_at')),
    updated_at: firstNonEmpty(getOpt(raw, 'updated_at')),
    mode_hint: firstNonEmpty(getOpt(raw, 'mode_hint')),
  };
}

// ============================================================
// Fingerprint — PS-compatible (normalized JSON string, not SHA256)
// ============================================================

/** PS-compatible: ConvertTo-NormalizedValue preserves original order, no sorting */
function normalizeBlockedByForFingerprint(blockers: Blocker[]): unknown[] {
  return blockers.map((b) => {
    if (typeof b === 'string') return b;
    return firstNonEmpty(b.identifier, b.id, b.key) || JSON.stringify(b);
  });
  // No .sort() — PS keeps original order via ConvertTo-NormalizedValue
}

export function computeFingerprint(issue: NormalizedIssue): string {
  // PS-compatible: fields in same order, no sorting of arrays
  // PS uses Get-UniqueStringList (dedup, order-preserved) then ConvertTo-Json -Compress
  const ordered = {
    identifier: issue.identifier,
    title: issue.title,
    description: issue.description,
    priority: issue.priority,
    state: issue.state,
    branch_name: issue.branch_name,
    url: issue.url,
    labels: [...new Set(issue.labels)],                        // dedup only, no sort
    blocked_by: normalizeBlockedByForFingerprint(issue.blocked_by),
    created_at: issue.created_at,
    updated_at: issue.updated_at,
    requested_deliverables: [...new Set(issue.requested_deliverables)], // dedup only, no sort
    mode_hint: issue.mode_hint,
    auto_run: issue.auto_run,
    source_path: issue.source_path,
    source_kind: issue.source_kind,
  };
  return JSON.stringify(ordered);
}

// ============================================================
// Blocking check
// ============================================================

export function isBlocked(
  issue: NormalizedIssue,
  activeStates: string[],
  issueMap: Map<string, NormalizedIssue>,
  stateIssues: Record<string, { status?: string; last_success_fingerprint: string | null }>,
): boolean {
  for (const blocker of issue.blocked_by) {
    const blockerKey = typeof blocker === 'string'
      ? blocker
      : firstNonEmpty(blocker.identifier, blocker.id, blocker.key);

    if (!blockerKey) continue;

    const stateRecord = stateIssues[blockerKey];

    // PS-compatible: blocker present in tracker
    const blockerIssue = issueMap.get(blockerKey);
    if (blockerIssue) {
      // Has success fingerprint matching current → resolved
      if (stateRecord?.last_success_fingerprint) {
        const currentFp = computeFingerprint(blockerIssue);
        if (stateRecord.last_success_fingerprint === currentFp) continue;
      }
      // Still in active state → blocked
      if (activeStates.includes(blockerIssue.state)) return true;
      // Not in active state (e.g. Done) → resolved
      continue;
    }

    // PS-compatible: blocker NOT in tracker
    // If status=completed in state → resolved
    if (stateRecord?.status === 'completed') continue;

    // If has success fingerprint → resolved
    if (stateRecord?.last_success_fingerprint) continue;

    // PS-compatible: if blocker is an object with an active state field → blocked
    // If blocker is a string or object without active state → NOT blocked (pass through)
    if (typeof blocker !== 'string') {
      const blockerState = blocker.state ?? '';
      if (blockerState && activeStates.includes(blockerState)) return true;
    }
    // String blocker with no record → not blocked (PS passes through)
  }
  return false;
}

// ============================================================
// Sort key (PS-compatible: priority → updated_at → identifier)
// ============================================================

export function issueSortKey(issue: NormalizedIssue): [number, string, string] {
  // PS-compatible: priority null → 999 only at sort time
  const prioritySort = (typeof issue.priority === 'number') ? issue.priority : 999;
  return [
    prioritySort,
    issue.updated_at || '9999-12-31T23:59:59Z',
    issue.identifier,
  ];
}

export function compareIssues(a: NormalizedIssue, b: NormalizedIssue): number {
  const [ap, au, ai] = issueSortKey(a);
  const [bp, bu, bi] = issueSortKey(b);
  if (ap !== bp) return ap - bp;
  if (au !== bu) return au < bu ? -1 : 1; // ascending (PS-compatible)
  return ai.localeCompare(bi);
}
