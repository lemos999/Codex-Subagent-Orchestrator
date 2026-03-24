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
}

export interface TrustRegistryData {
  version: 1;
  updatedAt: string;
  engines: Record<string, EngineRecord>;
}

const DEFAULT_RECORD: Omit<EngineRecord, 'engine'> = {
  successes: 0, failures: 0, timeouts: 0, totalRuns: 0,
  avgLatencyMs: 0, trustScore: 0.5,
};

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

  /** Record a completed worker run. */
  recordRun(engine: string, succeeded: boolean, latencyMs: number, failureReason?: string): void {
    const rec = this.getOrCreate(engine);
    rec.totalRuns++;
    if (succeeded) {
      rec.successes++;
    } else {
      rec.failures++;
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

    this.save();
  }

  /** Record a timeout (special failure type). */
  recordTimeout(engine: string): void {
    const rec = this.getOrCreate(engine);
    rec.totalRuns++;
    rec.timeouts++;
    rec.failures++;
    rec.lastFailureReason = 'timeout';
    if (rec.totalRuns >= 3) {
      rec.trustScore = Math.round((rec.successes / rec.totalRuns) * 100) / 100;
    }
    this.save();
  }

  /** Get trust score for an engine. Returns 0.5 (neutral) if no history. */
  getTrustScore(engine: string): number {
    return this.data.engines[engine]?.trustScore ?? 0.5;
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
