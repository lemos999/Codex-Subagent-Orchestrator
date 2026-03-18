/**
 * Main orchestrator — drives the state machine through all phases.
 * Phase 1: parse -> validate -> bootstrap -> execute -> write evidence -> complete
 */

import * as fs from 'node:fs/promises';
import * as path from 'node:path';

import type { LauncherSpec } from './types/spec.js';
import type { Manifest, StagePlan, WorkerResult } from './types/manifest.js';
import type { ResolvedPaths } from './types/state.js';
import { ENGINE_DEFAULTS } from './types/engine.js';

import { sha256 } from './common/fs-helpers.js';
import { parseSpec } from './validation/spec-schema.js';
import { resolvePaths } from './supervisor/path-resolver.js';
import { runStages } from './supervisor/stage-runner.js';
import { validatePolicies } from './supervisor/policy.js';
import { runAfterCreateHook } from './supervisor/hooks.js';
import { loadWorkflow } from './supervisor/workflow.js';
import { writeManifest } from './evidence/manifest-writer.js';
import { writeSummary } from './evidence/summary-writer.js';
import { writeArchive } from './evidence/archive-writer.js';
import { buildManifest, type SharedDirectiveInfo } from './evidence/manifest-builder.js';
import { UsageMonitor } from './workers/usage-monitor.js';
import type { ResolvedWorkerSpec } from './workers/spawn.js';

// ============================================================
// Orchestrator result
// ============================================================

export interface OrchestratorResult {
  success: boolean;
  manifest: Manifest;
  manifestPath: string;
  summaryPath: string | null;
  results: WorkerResult[];
}

// ============================================================
// Shared directive loading
// ============================================================

async function loadSharedDirective(
  spec: LauncherSpec,
  resolvedPaths: ResolvedPaths,
): Promise<SharedDirectiveInfo> {
  const mode = spec.shared_directive_mode ?? 'full';
  if (mode === 'disabled') {
    return { text: null, source: null, sha256: null };
  }

  // Check for explicit text
  if (spec.shared_directive_text) {
    return {
      text: spec.shared_directive_text,
      source: 'inline',
      sha256: sha256(spec.shared_directive_text),
    };
  }

  // Check for explicit file
  if (spec.shared_directive_file) {
    const filePath = path.resolve(
      resolvedPaths.workspaceRoot,
      spec.shared_directive_file,
    );
    try {
      const content = await fs.readFile(filePath, 'utf8');
      return { text: content, source: filePath, sha256: sha256(content) };
    } catch {
      return { text: null, source: filePath, sha256: null };
    }
  }

  // Auto-detect AGENTS.md at workspace root
  if (spec.inject_shared_directive !== false) {
    const agentsPath = path.resolve(resolvedPaths.workspaceRoot, 'AGENTS.md');
    try {
      const content = await fs.readFile(agentsPath, 'utf8');
      return { text: content, source: agentsPath, sha256: sha256(content) };
    } catch {
      return { text: null, source: null, sha256: null };
    }
  }

  return { text: null, source: null, sha256: null };
}

// ============================================================
// Stage plan builder
// ============================================================

function buildStagePlan(spec: LauncherSpec): StagePlan[] {
  const stageMap = new Map<number, StagePlan>();

  for (const agent of spec.agents) {
    const stageNum = agent.stage ?? 1;
    const kind = agent.kind ?? 'custom';
    const isReadOnly =
      agent.sandbox === 'read-only' ||
      (spec.defaults?.sandbox === 'read-only' && agent.sandbox === undefined) ||
      kind === 'reviewer' ||
      kind === 'validator';

    let stage = stageMap.get(stageNum);
    if (!stage) {
      stage = {
        stage: stageNum,
        worker_count: 0,
        worker_names: [],
        worker_kinds: [],
        read_only_workers: [],
        writable_workers: [],
      };
      stageMap.set(stageNum, stage);
    }

    stage.worker_count++;
    stage.worker_names.push(agent.name);
    stage.worker_kinds.push(kind);

    if (isReadOnly) {
      stage.read_only_workers.push(agent.name);
    } else {
      stage.writable_workers.push(agent.name);
    }
  }

  return Array.from(stageMap.values()).sort((a, b) => a.stage - b.stage);
}

// ============================================================
// Resolve workers
// ============================================================

function resolveWorkers(
  spec: LauncherSpec,
  resolvedPaths: ResolvedPaths,
  sharedDirective: string | null,
): ResolvedWorkerSpec[] {
  const defaultEngine = spec.defaults?.engine ?? 'codex';
  const defaultModel = spec.defaults?.model ?? ENGINE_DEFAULTS[defaultEngine];
  const defaultSandbox = spec.defaults?.sandbox ?? 'workspace-write';
  const defaultReasoning = spec.defaults?.reasoning_effort ?? null;
  const defaultPromptProfile = spec.defaults?.prompt_profile ?? 'full';
  const defaultResponseStyle = spec.defaults?.response_style ?? 'standard';
  const defaultMaxResponseLines = spec.defaults?.max_response_lines ?? 0;
  const defaultJson = spec.defaults?.json ?? false;
  const writePromptFiles = spec.write_prompt_files ?? false;
  const timeoutMs = (spec.timeout_seconds ?? 0) * 1000;

  return spec.agents.map((agent): ResolvedWorkerSpec => {
    const engine = agent.engine ?? defaultEngine;
    const model = agent.model ?? defaultModel;
    const kind = agent.kind ?? 'custom';
    const sandbox = agent.sandbox ?? defaultSandbox;
    const isReadOnly =
      sandbox === 'read-only' || kind === 'reviewer' || kind === 'validator';
    const agentCwd = agent.cwd
      ? path.resolve(resolvedPaths.workspaceRoot, agent.cwd)
      : resolvedPaths.workspaceRoot;

    // Build prompt
    const promptParts: string[] = [];
    if (sharedDirective) {
      promptParts.push(sharedDirective);
      promptParts.push('');
    }
    promptParts.push(agent.prompt ?? agent.task ?? '');

    const requiredPaths = (agent.required_paths ?? []).map((p) =>
      path.resolve(agentCwd, p),
    );
    const requiredNonEmptyPaths = (agent.required_non_empty_paths ?? []).map(
      (p) => path.resolve(agentCwd, p),
    );

    return {
      name: agent.name,
      engine,
      model,
      prompt: promptParts.join('\n'),
      cwd: agentCwd,
      outputDir: resolvedPaths.outputDir,
      sandbox,
      kind,
      stage: agent.stage ?? 1,
      isReadOnly,
      reasoningEffort: agent.reasoning_effort ?? defaultReasoning,
      promptProfile: agent.prompt_profile ?? defaultPromptProfile,
      responseStyle: agent.response_style ?? defaultResponseStyle,
      maxResponseLines: agent.max_response_lines ?? defaultMaxResponseLines,
      json: agent.json ?? defaultJson,
      outputSchema: agent.output_schema ?? null,
      writePromptFile: writePromptFiles,
      requiredPaths,
      requiredNonEmptyPaths,
      extraArgs: sanitizeExtraArgs(agent.extra_args ?? []),
      timeoutMs,
    };
  });
}

// ============================================================
// extra_args sanitization (review issue #3)
// ============================================================

/** Dangerous flags that could compromise sandbox or security guarantees. */
const BLOCKED_EXTRA_ARGS = new Set([
  '--full-auto',
  '--dangerously-auto-approve',
  '--no-sandbox',
  '--sandbox',
  '-y',
]);

function sanitizeExtraArgs(args: string[]): string[] {
  return args.filter((arg) => {
    const normalized = arg.split('=')[0].toLowerCase();
    return !BLOCKED_EXTRA_ARGS.has(normalized);
  });
}

// ============================================================
// Usage monitor lifecycle
// ============================================================

function initUsageMonitor(
  spec: LauncherSpec,
  outputDir: string,
): UsageMonitor | undefined {
  if (!spec.live_usage?.enabled) return undefined;

  const usageStatusFile = spec.live_usage.status_file
    ? path.resolve(outputDir, spec.live_usage.status_file)
    : path.resolve(outputDir, 'orchestration-usage.json');

  const monitor = new UsageMonitor({
    ...spec.live_usage,
    status_file: usageStatusFile,
  });
  monitor.start();
  return monitor;
}

// ============================================================
// Main orchestration entry point
// ============================================================

export async function orchestrate(
  specFilePath: string,
  invocationCwd: string,
): Promise<OrchestratorResult> {
  // Phase 1: Parse
  const specRaw = await fs.readFile(specFilePath, 'utf8');
  const specJson = JSON.parse(specRaw) as unknown;
  const specSha256 = sha256(specRaw);

  // Phase 2: Validate
  const spec = parseSpec(specJson);

  // Phase 3: Resolve paths
  const resolvedPaths = resolvePaths(spec, invocationCwd, specFilePath);
  await fs.mkdir(resolvedPaths.outputDir, { recursive: true });

  // Phase 3.5: Run after_create hook
  const hookResult = await runAfterCreateHook(
    spec.hooks,
    resolvedPaths.workspaceRoot,
  );

  // Phase 4: Bootstrap (shared directive + workflow)
  const sharedDirective = await loadSharedDirective(spec, resolvedPaths);
  const workflow = await loadWorkflow(spec, resolvedPaths.workspaceRoot, resolvedPaths.specDirectory);

  // Phase 5: Build stage plan and validate policies
  const stagePlan = buildStagePlan(spec);
  enforcePolicies(spec, stagePlan);
  const workers = resolveWorkers(spec, resolvedPaths, sharedDirective.text);

  // Phase 5.5: Initialize usage monitor
  const usageMonitor = initUsageMonitor(spec, resolvedPaths.outputDir);

  // Phase 6: Execute
  const executionMode = spec.execution_mode ?? 'sequential';
  const results = await runStages(
    stagePlan,
    workers,
    executionMode,
    usageMonitor,
  );

  // Phase 6.5: Stop usage monitor
  if (usageMonitor) {
    await usageMonitor.stop();
  }

  // Phase 7: Build manifest
  const manifest = buildManifest(
    spec,
    resolvedPaths,
    stagePlan,
    results,
    sharedDirective,
    specSha256,
    hookResult,
    workflow,
  );

  // Phase 8: Write evidence
  await writeManifest(resolvedPaths.manifestFile, manifest);

  let summaryPath: string | null = null;
  if (resolvedPaths.summaryFile) {
    await writeSummary(resolvedPaths.summaryFile, manifest);
    summaryPath = resolvedPaths.summaryFile;
  }

  // Phase 8.5: Write archive and update manifest
  const archiveResult = await writeArchive(
    spec,
    resolvedPaths,
    manifest,
    results,
  );
  if (archiveResult.enabled) {
    manifest.archive = {
      enabled: true,
      root: spec.archive_root
        ? path.resolve(resolvedPaths.workspaceRoot, spec.archive_root)
        : path.resolve(resolvedPaths.workspaceRoot, 'subagent-records'),
      run_label: spec.archive_run_label ?? null,
      run_directory: archiveResult.runDirectory,
      launcher_directory: archiveResult.launcherDirectory,
      deliverables_directory: archiveResult.deliverablesDirectory,
      workers_directory: archiveResult.workersDirectory,
      supervisor_directory: archiveResult.supervisorDirectory,
    };
    await writeManifest(resolvedPaths.manifestFile, manifest);
  }

  return {
    success: results.every((r) => r.succeeded),
    manifest,
    manifestPath: resolvedPaths.manifestFile,
    summaryPath,
    results,
  };
}

// ============================================================
// Policy enforcement helper
// ============================================================

function enforcePolicies(spec: LauncherSpec, stagePlan: StagePlan[]): void {
  const violations = validatePolicies(spec, stagePlan);

  const errors = violations.filter((v) => v.severity === 'error');
  if (errors.length > 0) {
    const messages = errors
      .map((v) => `[${v.rule}] ${v.message}`)
      .join('\n');
    throw new Error(`Policy violations:\n${messages}`);
  }

  for (const v of violations.filter((w) => w.severity === 'warning')) {
    console.error(`[policy warning] ${v.rule}: ${v.message}`);
  }
}
