/**
 * Main orchestrator — drives the state machine through all phases.
 * Phase 1: parse -> validate -> bootstrap -> execute -> write evidence -> complete
 */

import * as fs from 'node:fs/promises';
import * as path from 'node:path';
import * as crypto from 'node:crypto';
import { parseSpec } from './validation/spec-schema.js';
import { resolvePaths } from './supervisor/path-resolver.js';
import { runStages } from './supervisor/stage-runner.js';
import { writeManifest } from './evidence/manifest-writer.js';
import { writeSummary } from './evidence/summary-writer.js';
import { UsageMonitor } from './workers/usage-monitor.js';
import type { LauncherSpec } from './types/spec.js';
import type {
  Manifest,
  StagePlan,
  WorkerResult,
  ManifestLiveUsage,
  ManifestArchive,
  ManifestSharedDirective,
  ManifestWorkflow,
  ManifestHooks,
  ManifestPolicy,
  ManifestEfficiencySignals,
} from './types/manifest.js';
import type { ResolvedPaths } from './types/state.js';
import { ENGINE_DEFAULTS } from './types/engine.js';
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
): Promise<{ text: string | null; source: string | null; sha256: string | null }> {
  const mode = spec.shared_directive_mode ?? 'full';
  if (mode === 'disabled') {
    return { text: null, source: null, sha256: null };
  }

  // Check for explicit text
  if (spec.shared_directive_text) {
    const sha = crypto
      .createHash('sha256')
      .update(spec.shared_directive_text, 'utf8')
      .digest('hex');
    return { text: spec.shared_directive_text, source: 'inline', sha256: sha };
  }

  // Check for explicit file
  if (spec.shared_directive_file) {
    const filePath = path.resolve(
      resolvedPaths.workspaceRoot,
      spec.shared_directive_file,
    );
    try {
      const content = await fs.readFile(filePath, 'utf8');
      const sha = crypto
        .createHash('sha256')
        .update(content, 'utf8')
        .digest('hex');
      return { text: content, source: filePath, sha256: sha };
    } catch {
      return { text: null, source: filePath, sha256: null };
    }
  }

  // Auto-detect AGENTS.md at workspace root
  if (spec.inject_shared_directive !== false) {
    const agentsPath = path.resolve(resolvedPaths.workspaceRoot, 'AGENTS.md');
    try {
      const content = await fs.readFile(agentsPath, 'utf8');
      const sha = crypto
        .createHash('sha256')
        .update(content, 'utf8')
        .digest('hex');
      return { text: content, source: agentsPath, sha256: sha };
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
    const isReadOnly = agent.sandbox === 'read-only' ||
      (spec.defaults?.sandbox === 'read-only' && agent.sandbox === undefined) ||
      kind === 'reviewer' || kind === 'validator';

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
  const defaultModel =
    spec.defaults?.model ?? ENGINE_DEFAULTS[defaultEngine];
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
    const rawPrompt = agent.prompt ?? agent.task ?? '';
    promptParts.push(rawPrompt);

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
      extraArgs: agent.extra_args ?? [],
      timeoutMs,
    };
  });
}

// ============================================================
// Build complete manifest
// ============================================================

function buildManifest(
  spec: LauncherSpec,
  resolvedPaths: ResolvedPaths,
  stagePlan: StagePlan[],
  results: WorkerResult[],
  sharedDirective: { text: string | null; source: string | null; sha256: string | null },
  specSha256: string,
): Manifest {
  const defaultEngine = spec.defaults?.engine ?? 'codex';
  const succeededCount = results.filter((r) => r.succeeded).length;
  const failedCount = results.length - succeededCount;

  // Count worker types
  const kindCounts = {
    implementer: 0,
    reviewer: 0,
    validator: 0,
    fixer: 0,
  };
  let writableCount = 0;
  let readOnlyCount = 0;
  let fullAutoWritable = 0;
  let fullAutoReadOnly = 0;
  let totalPromptChars = 0;

  for (const r of results) {
    if (r.worker_kind in kindCounts) {
      kindCounts[r.worker_kind as keyof typeof kindCounts]++;
    }
    if (r.is_read_only) {
      readOnlyCount++;
      if (r.requested_full_auto) fullAutoReadOnly++;
    } else {
      writableCount++;
      if (r.requested_full_auto) fullAutoWritable++;
    }
    totalPromptChars += r.prompt_chars;
  }

  const deliverableCount = (spec.requested_deliverables ?? []).length;
  const maxParallelInStage = Math.max(
    ...stagePlan.map((s) => s.worker_count),
    0,
  );

  const writableWorkerNames = results
    .filter((r) => !r.is_read_only)
    .map((r) => r.name);
  const readOnlyReviewerNames = results
    .filter((r) => r.is_read_only)
    .map((r) => r.name);

  const lastWritableStage = Math.max(
    ...results.filter((r) => !r.is_read_only).map((r) => r.stage),
    0,
  );

  const liveUsageCfg = spec.live_usage;
  const liveUsage: ManifestLiveUsage = {
    enabled: liveUsageCfg?.enabled ?? false,
    display_mode: liveUsageCfg?.display_mode ?? 'none',
    poll_interval_ms: liveUsageCfg?.poll_interval_ms ?? 500,
    status_file: liveUsageCfg?.status_file
      ? path.resolve(resolvedPaths.outputDir, liveUsageCfg.status_file)
      : null,
    json_output_forced: false,
  };

  const archive: ManifestArchive = {
    enabled: false,
    root: null,
    run_label: null,
    run_directory: null,
    launcher_directory: null,
    deliverables_directory: null,
    workers_directory: null,
    supervisor_directory: null,
  };

  const directiveCharCount = sharedDirective.text?.length ?? 0;
  const sharedDir: ManifestSharedDirective = {
    source: sharedDirective.source,
    requested_mode: spec.shared_directive_mode ?? 'full',
    effective_mode: sharedDirective.text
      ? (spec.shared_directive_mode ?? 'full')
      : 'disabled',
    sha256: sharedDirective.sha256,
    char_count: directiveCharCount,
    original_char_count: directiveCharCount,
    effective_char_count: directiveCharCount,
  };

  const workflow: ManifestWorkflow = {
    enabled: false,
    source: null,
    prompt_mode: 'disabled',
    strict_render: true,
    auto_detected: false,
    front_matter_text: null,
    prompt_template_sha256: null,
    prompt_template_chars: 0,
    context: {},
  };

  const hooks: ManifestHooks = {
    after_create: {
      enabled: false,
      ran: false,
      trigger: null,
      exit_code: null,
      missing_sentinel_paths: [],
      workspace_was_empty: false,
      stdout: null,
      stderr: null,
    },
  };

  const policy: ManifestPolicy = {
    execution_mode: spec.execution_mode ?? 'sequential',
    supervisor_only: false,
    require_final_read_only_review: false,
    material_issue_strategy: spec.material_issue_strategy ?? 'none',
    requested_deliverables: spec.requested_deliverables ?? [],
    writable_worker_names: writableWorkerNames,
    read_only_reviewer_names: readOnlyReviewerNames,
    final_read_only_reviewer_names: [],
    final_read_only_review_present: false,
    last_writable_stage: lastWritableStage,
  };

  const efficiencySignals: ManifestEfficiencySignals = {
    measurement_mode: 'structure_first',
    note: 'Use reruns, parent burden, repair-loop shape, and worker-to-deliverable ratios as primary efficiency signals. Treat absolute token totals as secondary.',
    execution_mode: spec.execution_mode ?? 'sequential',
    total_workers: results.length,
    succeeded_workers: succeededCount,
    failed_workers: failedCount,
    requested_deliverable_count: deliverableCount,
    workers_per_deliverable:
      deliverableCount > 0 ? results.length / deliverableCount : null,
    writable_workers_per_deliverable:
      deliverableCount > 0 ? writableCount / deliverableCount : null,
    writable_workers: writableCount,
    read_only_workers: readOnlyCount,
    implementer_workers: kindCounts.implementer,
    reviewer_workers: kindCounts.reviewer,
    validator_workers: kindCounts.validator,
    fixer_workers: kindCounts.fixer,
    full_auto_writable_workers: fullAutoWritable,
    full_auto_read_only_workers: fullAutoReadOnly,
    stage_count: stagePlan.length,
    parallel_stage_count: (spec.execution_mode ?? 'sequential') === 'parallel'
      ? stagePlan.filter((s) => s.worker_count > 1).length
      : 0,
    max_parallel_workers_in_stage: maxParallelInStage,
    uses_parallel_execution: (spec.execution_mode ?? 'sequential') === 'parallel',
    uses_supervisor_only_policy: false,
    uses_bounded_repair_policy: false,
    final_read_only_review_present: false,
    total_prompt_chars: totalPromptChars,
    total_footer_tokens: 0,
  };

  const defaults: Record<string, unknown> = {};
  if (spec.defaults) {
    const d = spec.defaults;
    if (d.engine !== undefined) defaults.engine = d.engine;
    if (d.model !== undefined) defaults.model = d.model;
    if (d.sandbox !== undefined) defaults.sandbox = d.sandbox;
    if (d.reasoning_effort !== undefined) defaults.reasoning_effort = d.reasoning_effort;
    if (d.json !== undefined) defaults.json = d.json;
    if (d.prompt_profile !== undefined) defaults.prompt_profile = d.prompt_profile;
    if (d.response_style !== undefined) defaults.response_style = d.response_style;
    if (d.max_response_lines !== undefined) defaults.max_response_lines = d.max_response_lines;
  }

  return {
    created_at_utc: new Date().toISOString(),
    launcher_version: 'ts-phase1-v1',
    launcher_script: 'subagent-launch',
    spec_path: resolvedPaths.specPath,
    spec_directory: resolvedPaths.specDirectory,
    spec_sha256: specSha256,
    codex_executable: 'codex',
    claude_executable: 'claude',
    gemini_executable: process.platform === 'win32' ? 'npx.cmd' : 'npx',
    invocation_cwd: resolvedPaths.invocationCwd,
    cwd_requested: spec.cwd,
    cwd_resolution_mode: spec.cwd_resolution ?? 'invocation',
    cwd_resolution_base:
      spec.cwd_resolution === 'spec'
        ? resolvedPaths.specDirectory
        : resolvedPaths.invocationCwd,
    workspace_root: resolvedPaths.workspaceRoot,
    output_dir: resolvedPaths.outputDir,
    debug_log: resolvedPaths.debugLogFile,
    summary_file: resolvedPaths.summaryFile,
    live_usage: liveUsage,
    archive,
    execution_mode: spec.execution_mode ?? 'sequential',
    skip_git_repo_check: spec.skip_git_repo_check ?? false,
    shared_directive: sharedDir,
    workflow,
    hooks,
    policy,
    efficiency_signals: efficiencySignals,
    stage_plan: stagePlan,
    defaults,
    results,
  };
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
  const specSha256 = crypto
    .createHash('sha256')
    .update(specRaw, 'utf8')
    .digest('hex');

  // Phase 2: Validate
  const spec = parseSpec(specJson);

  // Phase 3: Resolve paths
  const resolvedPaths = resolvePaths(spec, invocationCwd, specFilePath);

  // Ensure output directory exists
  await fs.mkdir(resolvedPaths.outputDir, { recursive: true });

  // Phase 4: Bootstrap (shared directive)
  const sharedDirective = await loadSharedDirective(spec, resolvedPaths);

  // Phase 5: Build stage plan and resolve workers
  const stagePlan = buildStagePlan(spec);
  const workers = resolveWorkers(spec, resolvedPaths, sharedDirective.text);

  // Phase 5.5: Initialize usage monitor (if configured)
  let usageMonitor: UsageMonitor | undefined;
  if (spec.live_usage?.enabled) {
    const usageStatusFile = spec.live_usage.status_file
      ? path.resolve(resolvedPaths.outputDir, spec.live_usage.status_file)
      : path.resolve(resolvedPaths.outputDir, 'orchestration-usage.json');
    usageMonitor = new UsageMonitor({
      ...spec.live_usage,
      status_file: usageStatusFile,
    });
    usageMonitor.start();
  }

  // Phase 6: Execute
  const executionMode = spec.execution_mode ?? 'sequential';
  const results = await runStages(stagePlan, workers, executionMode, usageMonitor);

  // Phase 6.5: Stop usage monitor and get final snapshot
  const usageSnapshot = usageMonitor ? await usageMonitor.stop() : null;
  void usageSnapshot; // Available for manifest enhancement in Phase 3

  // Phase 7: Build manifest
  const manifest = buildManifest(
    spec,
    resolvedPaths,
    stagePlan,
    results,
    sharedDirective,
    specSha256,
  );

  // Phase 8: Write evidence
  await writeManifest(resolvedPaths.manifestFile, manifest);

  let summaryPath: string | null = null;
  if (resolvedPaths.summaryFile) {
    await writeSummary(resolvedPaths.summaryFile, manifest);
    summaryPath = resolvedPaths.summaryFile;
  }

  const allSucceeded = results.every((r) => r.succeeded);

  return {
    success: allSucceeded,
    manifest,
    manifestPath: resolvedPaths.manifestFile,
    summaryPath,
    results,
  };
}
