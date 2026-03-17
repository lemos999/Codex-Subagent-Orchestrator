/**
 * Stage runner — sequential execution of worker stages (Phase 1).
 * Parallel execution is deferred to Phase 2.
 */

import * as fs from 'node:fs/promises';
import type { StagePlan, WorkerResult } from '../types/manifest.js';
import {
  spawnWorker,
  toWorkerResult,
  type ResolvedWorkerSpec,
} from '../workers/spawn.js';

// ============================================================
// Path validation helpers
// ============================================================

async function findMissingPaths(paths: string[]): Promise<string[]> {
  const missing: string[] = [];
  for (const p of paths) {
    try {
      await fs.access(p);
    } catch {
      missing.push(p);
    }
  }
  return missing;
}

async function findEmptyPaths(paths: string[]): Promise<string[]> {
  const empty: string[] = [];
  for (const p of paths) {
    try {
      const stat = await fs.stat(p);
      if (stat.size === 0) {
        empty.push(p);
      }
    } catch {
      // File doesn't exist — handled by findMissingPaths
    }
  }
  return empty;
}

// ============================================================
// Stage runner (sequential only — Phase 1)
// ============================================================

export async function runStages(
  stages: StagePlan[],
  workers: ResolvedWorkerSpec[],
): Promise<WorkerResult[]> {
  const results: WorkerResult[] = [];
  const workerMap = new Map(workers.map((w) => [w.name, w]));

  // Sort stages by stage number
  const sortedStages = [...stages].sort((a, b) => a.stage - b.stage);

  for (const stage of sortedStages) {
    for (const workerName of stage.worker_names) {
      const spec = workerMap.get(workerName);
      if (!spec) {
        throw new Error(
          `Worker "${workerName}" referenced in stage ${stage.stage} but not found in spec`,
        );
      }

      // Spawn worker
      const output = await spawnWorker(spec);

      // Validate required_paths and required_non_empty_paths
      const missingPaths = await findMissingPaths(spec.requiredPaths);
      const emptyPaths = await findEmptyPaths(spec.requiredNonEmptyPaths);
      const validationFailures: string[] = [];

      if (missingPaths.length > 0) {
        validationFailures.push(
          `Missing required paths: ${missingPaths.join(', ')}`,
        );
      }
      if (emptyPaths.length > 0) {
        validationFailures.push(
          `Empty required paths: ${emptyPaths.join(', ')}`,
        );
      }

      const result = toWorkerResult(
        spec,
        output,
        validationFailures,
        missingPaths,
        emptyPaths,
      );
      results.push(result);
    }
  }

  return results;
}
