/**
 * Trust & Reputation Registry — tracks engine performance history.
 *
 * Based on Intelligent AI Delegation (Google DeepMind):
 * - Reputation = public, verifiable past performance
 * - Trust = contextual threshold set by delegator
 * - Higher trust → wider autonomy, less monitoring
 * - Lower trust → restricted roles, stronger oversight
 *
 * Stores per-engine success/failure counts and average latency.
 * Used by orchestrator to inform engine selection.
 */

import * as fs from 'node:fs';
import * as path from 'node:path';

export type TrustTier = 'probation' | 'standard' | 'trusted';

export interface EngineRecord {
  engine: string;
  successes: number;
  failures: number;
  timeouts: number;
  totalRuns: number;
  avgLatencyMs: number;
  lastFailureReason?: string;
  /** Trust score 0-1. Computed from success rate + recency. */
  trustScore: number;
  // C5 Behavioral Metrics (optional — backward compatible)
  approvalRate?: number;        // 0-1, EMA-based
  revisionRate?: number;        // 0-1, EMA-based
  scopeExitCount?: number;      // 범위 이탈 횟수
  consecutiveFailures?: number; // 현재 연속 실패 수 (성공 시 0 리셋)
  trustTier?: TrustTier;
}

export interface TrustRegistryData {
  version: 1;
  updatedAt: string;
  engines: Record<string, EngineRecord>;
}

const DEFAULT_RECORD: Omit<EngineRecord, 'engine'> = {
  successes: 0, failures: 0, timeouts: 0, totalRuns: 0,
  avgLatencyMs: 0, trustScore: 0.5,
  approvalRate: undefined, revisionRate: undefined,
  scopeExitCount: 0, consecutiveFailures: 0, trustTier: 'probation',
};

function computeTrustTier(rec: EngineRecord): TrustTier {
  // 강등 조건 우선
  if ((rec.consecutiveFailures ?? 0) >= 3) return 'probation';
  if ((rec.scopeExitCount ?? 0) >= 2) return 'probation';
  // 승급 조건
  if (rec.totalRuns >= 5 && rec.trustScore >= 0.85) return 'trusted';
  if (rec.totalRuns >= 3 && rec.trustScore >= 0.65) return 'standard';
  return 'probation';
}

export class TrustRegistry {
  private data: TrustRegistryData;
  private filePath: string;

  constructor(registryDir: string) {
    this.filePath = path.join(registryDir, 'trust-registry.json');
    this.data = this.load();
  }

  private load(): TrustRegistryData {
    try {
      if (fs.existsSync(this.filePath)) {
        return JSON.parse(fs.readFileSync(this.filePath, 'utf8'));
      }
    } catch { /* corrupt file, start fresh */ }
    return { version: 1, updatedAt: new Date().toISOString(), engines: {} };
  }

  private save(): void {
    this.data.updatedAt = new Date().toISOString();
    const dir = path.dirname(this.filePath);
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(this.filePath, JSON.stringify(this.data, null, 2), 'utf8');
  }

  private getOrCreate(engine: string): EngineRecord {
    if (!this.data.engines[engine]) {
      this.data.engines[engine] = { engine, ...DEFAULT_RECORD };
    }
    return this.data.engines[engine]!;
  }

  /** Append a JSONL event to trust-events.jsonl. */
  private appendEvent(engine: string, event: string, payload: Record<string, unknown>): void {
    const logPath = path.join(path.dirname(this.filePath), 'trust-events.jsonl');
    const entry = JSON.stringify({ ts: new Date().toISOString(), engine, event, ...payload });
    const dir = path.dirname(logPath);
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    fs.appendFileSync(logPath, entry + '\n', 'utf8');
  }

  /** Record a completed worker run. */
  recordRun(
    engine: string,
    succeeded: boolean,
    latencyMs: number,
    failureReason?: string,
    options?: {
      approved?: boolean;
      revised?: boolean;
      scopeExited?: boolean;
    },
  ): void {
    const rec = this.getOrCreate(engine);
    rec.totalRuns++;
    if (succeeded) {
      rec.successes++;
      rec.consecutiveFailures = 0;
    } else {
      rec.failures++;
      rec.consecutiveFailures = (rec.consecutiveFailures ?? 0) + 1;
      if (failureReason) rec.lastFailureReason = failureReason;
    }
    // Running average latency
    rec.avgLatencyMs = rec.avgLatencyMs === 0
      ? latencyMs
      : rec.avgLatencyMs * 0.8 + latencyMs * 0.2;

    // Trust score: success rate with minimum sample floor
    const minSamples = 3;
    if (rec.totalRuns >= minSamples) {
      rec.trustScore = Math.round((rec.successes / rec.totalRuns) * 100) / 100;
    } else {
      rec.trustScore = 0.5; // neutral until enough data
    }

    // C5 behavioral metrics
    if (options) {
      const alpha = 0.2;
      if (options.approved !== undefined) {
        const prev = rec.approvalRate ?? 0.5;
        rec.approvalRate = prev * (1 - alpha) + (options.approved ? 1 : 0) * alpha;
      }
      if (options.revised !== undefined) {
        const prev = rec.revisionRate ?? 0;
        rec.revisionRate = prev * (1 - alpha) + (options.revised ? 1 : 0) * alpha;
      }
      if (options.scopeExited) {
        rec.scopeExitCount = (rec.scopeExitCount ?? 0) + 1;
      } else if ((rec.scopeExitCount ?? 0) > 0) {
        // Decay: successful non-exit runs gradually reduce scopeExitCount
        // Simulates "recent 10 runs" window without full event log scan
        rec.scopeExitCount = Math.max(0, (rec.scopeExitCount ?? 0) - 0.2);
      }
    }

    // Recompute trust tier
    rec.trustTier = computeTrustTier(rec);

    this.appendEvent(engine, 'run', { succeeded, latencyMs, ...options });
    this.save();
  }

  /** Record a timeout (special failure type). */
  recordTimeout(engine: string): void {
    const rec = this.getOrCreate(engine);
    rec.totalRuns++;
    rec.timeouts++;
    rec.failures++;
    rec.consecutiveFailures = (rec.consecutiveFailures ?? 0) + 1;
    rec.lastFailureReason = 'timeout';
    if (rec.totalRuns >= 3) {
      rec.trustScore = Math.round((rec.successes / rec.totalRuns) * 100) / 100;
    }
    rec.trustTier = computeTrustTier(rec);
    this.appendEvent(engine, 'timeout', {});
    this.save();
  }

  /** Get trust score for an engine. Returns 0.5 (neutral) if no history. */
  getTrustScore(engine: string): number {
    return this.data.engines[engine]?.trustScore ?? 0.5;
  }

  /** Get trust tier for an engine. Returns 'probation' if no history. */
  getTrustTier(engine: string): TrustTier {
    return this.data.engines[engine]?.trustTier ?? 'probation';
  }

  /** Get full record for an engine. */
  getRecord(engine: string): EngineRecord | undefined {
    return this.data.engines[engine];
  }

  /** Get all engine records sorted by trust score descending. */
  getAllRecords(): EngineRecord[] {
    return Object.values(this.data.engines).sort((a, b) => b.trustScore - a.trustScore);
  }

  /** Summary string for logging. */
  summary(): string {
    const records = this.getAllRecords();
    if (records.length === 0) return 'No engine history yet.';
    return records.map(r =>
      `${r.engine}: trust=${r.trustScore} (${r.successes}/${r.totalRuns} ok, ${r.timeouts} timeouts)`
    ).join(', ');
  }
}
