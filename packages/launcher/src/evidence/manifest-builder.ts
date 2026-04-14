/**
 * Manifest builder — constructs the Manifest object from orchestration results.
 * Extracted from orchestrator.ts to reduce its size and isolate manifest assembly.
 */

import * as path from 'node:path';

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
  ManifestEvidence,
} from '../types/manifest.js';
import type { LauncherSpec } from '../types/spec.js';
import type { ResolvedPaths } from '../types/state.js';
import type { HookResult } from '../supervisor/hooks.js';
import type { WorkflowInfo } from '../supervisor/workflow.js';

// ============================================================
// Supporting types for build inputs
// ============================================================

export interface SharedDirectiveInfo {
  text: string | null;
  source: string | null;
  sha256: string | null;
  originalCharCount?: number | null;
}

// ============================================================
// Section builders (one per manifest sub-object)
// ============================================================

function buildLiveUsageSection(
  spec: LauncherSpec,
  outputDir: string,
): ManifestLiveUsage {
  const cfg = spec.live_usage;
  return {
    enabled: cfg?.enabled ?? false,
    display_mode: cfg?.display_mode ?? 'none',
    poll_interval_ms: cfg?.poll_interval_ms ?? 500,
    status_file: cfg?.status_file
      ? path.resolve(outputDir, cfg.status_file)
      : null,
    json_output_forced: false,
  };
}

function buildSharedDirectiveSection(
  spec: LauncherSpec,
  directive: SharedDirectiveInfo,
): ManifestSharedDirective {
  const effectiveCharCount = directive.text?.length ?? 0;
  const originalCharCount = directive.originalCharCount ?? effectiveCharCount;
  return {
    source: directive.source,
    requested_mode: spec.shared_directive_mode ?? 'full',
    effective_mode: directive.text
      ? (spec.shared_directive_mode ?? 'full')
      : 'disabled',
    sha256: directive.sha256,
    char_count: originalCharCount,
    original_char_count: originalCharCount,
    effective_char_count: effectiveCharCount,
  };
}

function buildWorkflowSection(wf?: WorkflowInfo): ManifestWorkflow {
  return {
    enabled: wf?.enabled ?? false,
    source: wf?.source ?? null,
    prompt_mode: wf?.promptMode ?? 'disabled',
    strict_render: wf?.strictRender ?? true,
    auto_detected: wf?.autoDetected ?? false,
    front_matter_text: null,
    prompt_template_sha256: wf?.templateSha256 ?? null,
    prompt_template_chars: wf?.templateChars ?? 0,
    context: wf?.context ?? {},
  };
}

function buildHooksSection(
  spec: LauncherSpec,
  outputDir: string,
  hr?: HookResult,
): ManifestHooks {
  // PS stores file paths, not content, for stdout/stderr
  const hookSpec = spec.hooks?.after_create;
  const stdoutFile = hookSpec
    ? (hookSpec.stdout_file
        ? path.resolve(outputDir, hookSpec.stdout_file)
        : path.resolve(outputDir, 'workspace-bootstrap.stdout.log'))
    : null;
  const stderrFile = hookSpec
    ? (hookSpec.stderr_file
        ? path.resolve(outputDir, hookSpec.stderr_file)
        : path.resolve(outputDir, 'workspace-bootstrap.stderr.log'))
    : null;

  return {
    after_create: {
      enabled: hookSpec !== undefined,
      ran: hr?.ran ?? false,
      trigger: hr?.trigger ?? null,
      exit_code: hr?.exitCode ?? null,
      missing_sentinel_paths: hr?.missingPaths ?? [],
      workspace_was_empty: hr?.workspaceWasEmpty ?? false,
      stdout: stdoutFile,
      stderr: stderrFile,
    },
  };
}

function buildPolicySection(
  spec: LauncherSpec,
  results: WorkerResult[],
  stagePlan: StagePlan[],
): ManifestPolicy {
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

  // Find final read-only reviewers: read-only workers in stages after last writable stage
  const finalReadOnlyReviewerNames = results
    .filter((r) => r.is_read_only && r.stage > lastWritableStage)
    .map((r) => r.name);

  return {
    execution_mode: spec.execution_mode ?? 'sequential',
    supervisor_only: spec.supervisor_only ?? false,
    require_final_read_only_review: spec.require_final_read_only_review ?? false,
    material_issue_strategy: spec.material_issue_strategy ?? 'none',
    requested_deliverables: spec.requested_deliverables ?? [],
    writable_worker_names: writableWorkerNames,
    read_only_reviewer_names: readOnlyReviewerNames,
    final_read_only_reviewer_names: finalReadOnlyReviewerNames,
    final_read_only_review_present: finalReadOnlyReviewerNames.length > 0,
    last_writable_stage: lastWritableStage,
  };
}

interface WorkerCounts {
  implementer: number;
  reviewer: number;
  validator: number;
  fixer: number;
  writable: number;
  readOnly: number;
  fullAutoWritable: number;
  fullAutoReadOnly: number;
  totalPromptChars: number;
}

function countWorkers(results: WorkerResult[]): WorkerCounts {
  const counts: WorkerCounts = {
    implementer: 0,
    reviewer: 0,
    validator: 0,
    fixer: 0,
    writable: 0,
    readOnly: 0,
    fullAutoWritable: 0,
    fullAutoReadOnly: 0,
    totalPromptChars: 0,
  };

  const kindKeys = new Set<string>(['implementer', 'reviewer', 'validator', 'fixer']);

  for (const r of results) {
    if (kindKeys.has(r.worker_kind)) {
      counts[r.worker_kind as 'implementer' | 'reviewer' | 'validator' | 'fixer']++;
    }
    if (r.is_read_only) {
      counts.readOnly++;
      if (r.requested_full_auto) counts.fullAutoReadOnly++;
    } else {
      counts.writable++;
      if (r.requested_full_auto) counts.fullAutoWritable++;
    }
    counts.totalPromptChars += r.prompt_chars;
  }

  return counts;
}

function buildEfficiencySection(
  spec: LauncherSpec,
  stagePlan: StagePlan[],
  results: WorkerResult[],
  counts: WorkerCounts,
  policy: ManifestPolicy,
): ManifestEfficiencySignals {
  const succeededCount = results.filter((r) => r.succeeded).length;
  const failedCount = results.length - succeededCount;
  const deliverableCount = (spec.requested_deliverables ?? []).length;
  const maxParallelInStage = Math.max(
    ...stagePlan.map((s) => s.worker_count),
    0,
  );
  const executionMode = spec.execution_mode ?? 'sequential';

  return {
    measurement_mode: 'structure_first',
    note: 'Use reruns, parent burden, repair-loop shape, and worker-to-deliverable ratios as primary efficiency signals. Treat absolute token totals as secondary.',
    execution_mode: executionMode,
    total_workers: results.length,
    succeeded_workers: succeededCount,
    failed_workers: failedCount,
    requested_deliverable_count: deliverableCount,
    workers_per_deliverable:
      deliverableCount > 0 ? results.length / deliverableCount : null,
    writable_workers_per_deliverable:
      deliverableCount > 0 ? counts.writable / deliverableCount : null,
    writable_workers: counts.writable,
    read_only_workers: counts.readOnly,
    implementer_workers: counts.implementer,
    reviewer_workers: counts.reviewer,
    validator_workers: counts.validator,
    fixer_workers: counts.fixer,
    full_auto_writable_workers: counts.fullAutoWritable,
    full_auto_read_only_workers: counts.fullAutoReadOnly,
    stage_count: stagePlan.length,
    parallel_stage_count:
      executionMode === 'parallel'
        ? stagePlan.filter((s) => s.worker_count > 1).length
        : 0,
    max_parallel_workers_in_stage: maxParallelInStage,
    uses_parallel_execution: executionMode === 'parallel',
    uses_supervisor_only_policy: spec.supervisor_only ?? false,
    uses_bounded_repair_policy: spec.material_issue_strategy === 'fixer_then_rereview',
    final_read_only_review_present: policy.final_read_only_review_present,
    total_prompt_chars: counts.totalPromptChars,
    total_footer_tokens: 0,
  };
}

function buildDefaultsRecord(spec: LauncherSpec): Record<string, unknown> {
  const defaults: Record<string, unknown> = {};
  if (!spec.defaults) return defaults;

  const d = spec.defaults;
  if (d.engine !== undefined) defaults.engine = d.engine;
  if (d.model !== undefined) defaults.model = d.model;
  if (d.sandbox !== undefined) defaults.sandbox = d.sandbox;
  if (d.reasoning_effort !== undefined) defaults.reasoning_effort = d.reasoning_effort;
  if (d.json !== undefined) defaults.json = d.json;
  if (d.prompt_profile !== undefined) defaults.prompt_profile = d.prompt_profile;
  if (d.response_style !== undefined) defaults.response_style = d.response_style;
  if (d.max_response_lines !== undefined) defaults.max_response_lines = d.max_response_lines;

  return defaults;
}

// ============================================================
// Main builder
// ============================================================

export function buildManifest(
  spec: LauncherSpec,
  resolvedPaths: ResolvedPaths,
  stagePlan: StagePlan[],
  results: WorkerResult[],
  sharedDirective: SharedDirectiveInfo,
  specSha256: string,
  hookResult?: HookResult,
  workflowInfo?: WorkflowInfo,
  evidence?: ManifestEvidence,
): Manifest {
  const counts = countWorkers(results);
  const policySection = buildPolicySection(spec, results, stagePlan);

  const archiveRoot = spec.archive_root
    ? path.resolve(resolvedPaths.workspaceRoot, spec.archive_root)
    : path.resolve(resolvedPaths.workspaceRoot, 'subagent-records');
  const archiveLabel = spec.archive_run_label ?? path.basename(resolvedPaths.outputDir);

  const archive: ManifestArchive = {
    enabled: false,
    root: archiveRoot,
    run_label: archiveLabel,
    run_directory: null,
    launcher_directory: null,
    deliverables_directory: null,
    workers_directory: null,
    supervisor_directory: null,
  };

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
    live_usage: buildLiveUsageSection(spec, resolvedPaths.outputDir),
    archive,
    execution_mode: spec.execution_mode ?? 'sequential',
    skip_git_repo_check: spec.skip_git_repo_check ?? false,
    shared_directive: buildSharedDirectiveSection(spec, sharedDirective),
    workflow: buildWorkflowSection(workflowInfo),
    hooks: buildHooksSection(spec, resolvedPaths.outputDir, hookResult),
    policy: policySection,
    efficiency_signals: buildEfficiencySection(spec, stagePlan, results, counts, policySection),
    evidence,
    stage_plan: stagePlan,
    defaults: buildDefaultsRecord(spec),
    results,
  };
}
