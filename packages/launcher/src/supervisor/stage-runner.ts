/**
 * Stage runner — sequential and parallel execution of worker stages.
 *
 * Same-stage workers run in parallel (Promise.allSettled).
 * Different stages run sequentially (stage 1 completes before stage 2 starts).
 */

import * as path from 'node:path';

import type { StagePlan, WorkerResult } from '../types/manifest.js';
import type { ExecutionMode } from '../types/engine.js';
import {
  spawnWorker,
  toWorkerResult,
  type ResolvedWorkerSpec,
} from '../workers/spawn.js';
import { findMissingPaths, findEmptyPaths } from '../common/fs-helpers.js';
import type { UsageMonitor } from '../workers/usage-monitor.js';

// ============================================================
// Single worker execution with validation
// ============================================================

async function executeWorker(
  spec: ResolvedWorkerSpec,
  monitor?: UsageMonitor,
): Promise<WorkerResult> {
  // Register with usage monitor before spawn
  if (monitor?.enabled) {
    const stdoutPath = path.resolve(
      spec.outputDir,
      `${spec.name}.stdout.log`,
    );
    monitor.registerWorker(spec.name, stdoutPath);
  }

  const output = await spawnWorker(spec);

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

  // Notify usage monitor
  if (monitor?.enabled) {
    monitor.markWorkerDone(spec.name, output.exitCode);
  }

  return toWorkerResult(
    spec,
    output,
    validationFailures,
    missingPaths,
    emptyPaths,
  );
}

// ============================================================
// Error result builder (for spawn-level failures)
// ============================================================

function buildSpawnErrorResult(
  spec: ResolvedWorkerSpec,
  stage: number,
  reason: unknown,
): WorkerResult {
  return {
    name: spec.name,
    engine: spec.engine,
    mode: 'exec',
    stage,
    worker_kind: spec.kind,
    is_read_only: spec.isReadOnly,
    cwd: spec.cwd,
    exit_code: -1,
    succeeded: false,
    required_paths: spec.requiredPaths,
    required_non_empty_paths: spec.requiredNonEmptyPaths,
    missing_required_paths: [],
    empty_required_paths: [],
    validation_failures: [`Spawn error: ${String(reason)}`],
    requested_model: spec.model ?? '',
    requested_full_auto: true,
    requested_json_output: false,
    actual_model: spec.model ?? '',
    requested_sandbox: spec.sandbox ?? 'workspace-write',
    actual_sandbox: null,
    requested_reasoning_effort: spec.reasoningEffort ?? null,
    actual_reasoning_effort: null,
    prompt_profile: spec.promptProfile ?? 'full',
    response_style: spec.responseStyle ?? 'standard',
    max_response_lines: spec.maxResponseLines ?? 0,
    actual_approval: null,
    actual_workdir: null,
    output_mode: 'text',
    session_id: null,
    footer_tokens_used: null,
    turn_failed: true,
    failure_message: String(reason),
    stdout: '',
    stderr: '',
    last: '',
    prompt: null,
    prompt_sha256: '',
    prompt_chars: spec.prompt.length,
    workflow_prompt_mode: 'disabled',
    workflow_prompt_chars: 0,
    command: '',
    last_exists: false,
    last_message_preview: '',
    stderr_preview: '',
    stdout_preview: '',
  };
}

// ============================================================
// Stage runner
// ============================================================

export async function runStages(
  stages: StagePlan[],
  workers: ResolvedWorkerSpec[],
  executionMode: ExecutionMode = 'sequential',
  monitor?: UsageMonitor,
): Promise<WorkerResult[]> {
  const results: WorkerResult[] = [];
  const workerMap = new Map(workers.map((w) => [w.name, w]));

  const sortedStages = [...stages].sort((a, b) => a.stage - b.stage);

  for (const stage of sortedStages) {
    const stageWorkers = stage.worker_names
      .map((name) => workerMap.get(name))
      .filter((w): w is ResolvedWorkerSpec => w !== undefined);

    if (stageWorkers.length === 0) continue;

    if (executionMode === 'parallel' && stageWorkers.length > 1) {
      // Parallel: same-stage workers run concurrently
      const settled = await Promise.allSettled(
        stageWorkers.map((w) => executeWorker(w, monitor)),
      );

      for (let i = 0; i < settled.length; i++) {
        const s = settled[i];
        if (s.status === 'fulfilled') {
          results.push(s.value);
        } else {
          results.push(
            buildSpawnErrorResult(stageWorkers[i], stage.stage, s.reason),
          );
        }
      }
    } else {
      // Sequential: one worker at a time
      for (const spec of stageWorkers) {
        const result = await executeWorker(spec, monitor);
        results.push(result);
      }
    }
  }

  return results;
}
