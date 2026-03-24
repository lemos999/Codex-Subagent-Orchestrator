/**
 * Stage 9 normalized evidence writer.
 *
 * Preserves a Claude-style evidence bundle alongside the legacy launcher
 * manifest/summary so parent supervisors do not need to backfill it manually.
 */

import * as fs from 'node:fs/promises';
import * as path from 'node:path';

import { writeFileSafe, copyIfExists } from '../common/fs-helpers.js';
import type { Manifest, WorkerResult } from '../types/manifest.js';
import type { ResolvedPaths } from '../types/state.js';
import type { ResolvedWorkerSpec } from '../workers/spawn.js';

interface NormalizedWorkerEvidence {
  fileStem: string;
  promptFile: string;
  resultFile: string;
  role: string;
  model: string;
  status: string;
  contractSummary: string;
  resultSummary: string;
  resultText: string;
}

interface DeliverableRecord {
  path: string;
  action: string;
  description: string;
}

function toDisplayPath(filePath: string): string {
  return filePath.split(path.sep).join('/');
}

function relativeDisplayPath(baseDir: string, targetPath: string): string {
  const relative = path.relative(baseDir, targetPath);
  return toDisplayPath(relative === '' ? path.basename(targetPath) : relative);
}

function truncateLine(value: string, maxLength = 100): string {
  const normalized = value.replace(/\s+/g, ' ').trim();
  if (normalized.length <= maxLength) {
    return normalized;
  }
  return `${normalized.slice(0, maxLength - 3)}...`;
}

function escapeMarkdownCell(value: string): string {
  return value.replace(/\|/g, '\\|').replace(/\r?\n/g, ' ');
}

function safeFileStem(value: string): string {
  const stem = value
    .replace(/[<>:"/\\|?*\x00-\x1f]/g, '-')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^[.-]+|[.-]+$/g, '');
  return stem || 'worker';
}

function isPathInside(baseDir: string, targetPath: string): boolean {
  const relative = path.relative(baseDir, targetPath);
  return (
    relative === '' ||
    (!relative.startsWith('..') && !path.isAbsolute(relative))
  );
}

async function readTextIfPresent(filePath: string | null | undefined): Promise<string> {
  if (!filePath) {
    return '';
  }

  try {
    return await fs.readFile(filePath, 'utf8');
  } catch {
    return '';
  }
}

function fallbackResultText(result: WorkerResult): string {
  const lines: string[] = [];

  if (result.failure_message) {
    lines.push(result.failure_message);
  }

  for (const failure of result.validation_failures) {
    lines.push(failure);
  }

  if (lines.length === 0) {
    if (result.succeeded) {
      lines.push('Worker completed without a recorded final response.');
    } else {
      lines.push(`Worker failed with exit code ${result.exit_code}.`);
    }
  }

  return lines.join('\n');
}

async function resolveWorkerResultText(result: WorkerResult): Promise<string> {
  const lastText = await readTextIfPresent(result.last);
  if (lastText.trim() !== '') {
    return lastText;
  }

  if (!result.succeeded) {
    const stderrText = await readTextIfPresent(result.stderr);
    if (stderrText.trim() !== '') {
      return stderrText;
    }
  }

  const stdoutText = await readTextIfPresent(result.stdout);
  if (stdoutText.trim() !== '') {
    return stdoutText;
  }

  return fallbackResultText(result);
}

function inferClassification(manifest: Manifest, results: WorkerResult[]): string {
  const kinds = new Set(results.map((result) => result.worker_kind));

  if (kinds.has('fixer')) {
    return 'fix';
  }

  if (
    results.length > 0 &&
    results.every(
      (result) =>
        result.worker_kind === 'reviewer' || result.worker_kind === 'validator',
    )
  ) {
    return 'review';
  }

  if (manifest.policy.requested_deliverables.length > 0 || kinds.has('implementer')) {
    return 'create';
  }

  return 'analyze';
}

function inferComplexity(manifest: Manifest, results: WorkerResult[]): string {
  const hasParallelStage = manifest.stage_plan.some((stage) => stage.worker_count > 1);

  if (results.length >= 4 || manifest.stage_plan.length >= 3 || hasParallelStage) {
    return 'high';
  }

  if (results.length >= 2) {
    return 'medium';
  }

  return 'low';
}

function inferPattern(manifest: Manifest, results: WorkerResult[]): string {
  const hasReviewer = results.some(
    (result) =>
      result.worker_kind === 'reviewer' || result.worker_kind === 'validator',
  );
  const implementers = results.filter((result) => result.worker_kind === 'implementer');

  if (results.length === 1 && implementers.length === 1) {
    return 'A (Solo implementer)';
  }

  if (
    results.length === 2 &&
    implementers.length === 1 &&
    hasReviewer &&
    manifest.stage_plan.length >= 2
  ) {
    return 'B (Implementer + Reviewer)';
  }

  if (
    manifest.execution_mode === 'parallel' &&
    manifest.stage_plan.some((stage) => stage.worker_count > 1) &&
    hasReviewer
  ) {
    return 'C (Parallel workers + Reviewer)';
  }

  return `launcher-${manifest.execution_mode}`;
}

function inferVerdict(results: WorkerResult[]): string {
  return results.every((result) => result.succeeded)
    ? 'ACCEPTED'
    : 'MATERIAL_ISSUES';
}

function summarizeCostProfile(results: WorkerResult[]): string {
  const counts = new Map<string, number>();

  for (const result of results) {
    const model = result.actual_model || result.requested_model || 'unknown';
    const key = `${result.engine}/${model}`;
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }

  if (counts.size === 0) {
    return 'none';
  }

  return [...counts.entries()]
    .map(([label, count]) => `${count}x ${label}`)
    .join(' + ');
}

function finalReviewerLabel(results: WorkerResult[]): string {
  const reviewers = results
    .filter(
      (result) =>
        result.worker_kind === 'reviewer' || result.worker_kind === 'validator',
    )
    .sort((a, b) => b.stage - a.stage);

  if (reviewers.length === 0) {
    return 'none recorded';
  }

  const reviewer = reviewers[0];
  const model = reviewer.actual_model || reviewer.requested_model || 'unknown';
  return `${reviewer.name} (${model})`;
}

async function collectDeliverables(
  manifest: Manifest,
  resolvedPaths: ResolvedPaths,
  results: WorkerResult[],
): Promise<DeliverableRecord[]> {
  const seen = new Map<string, { absolutePath: string; description: string }>();

  for (const deliverable of manifest.policy.requested_deliverables) {
    const absolutePath = path.resolve(resolvedPaths.workspaceRoot, deliverable);
    const relativePath = relativeDisplayPath(resolvedPaths.workspaceRoot, absolutePath);
    seen.set(relativePath, {
      absolutePath,
      description: 'Requested deliverable',
    });
  }

  if (seen.size === 0) {
    for (const result of results) {
      for (const absolutePath of [
        ...result.required_paths,
        ...result.required_non_empty_paths,
      ]) {
        if (!absolutePath || !isPathInside(resolvedPaths.workspaceRoot, absolutePath)) {
          continue;
        }

        const relativePath = relativeDisplayPath(
          resolvedPaths.workspaceRoot,
          absolutePath,
        );

        if (!seen.has(relativePath)) {
          seen.set(relativePath, {
            absolutePath,
            description: 'Validated worker path',
          });
        }
      }
    }
  }

  const deliverables = await Promise.all(
    [...seen.entries()].map(async ([relativePath, item]) => {
      const exists = (await readTextIfPresent(item.absolutePath)) !== '';

      if (!exists) {
        try {
          await fs.access(item.absolutePath);
        } catch {
          return {
            path: relativePath,
            action: 'missing',
            description: `${item.description} missing at evidence time`,
          };
        }
      }

      return {
        path: relativePath,
        action: 'present',
        description: item.description,
      };
    }),
  );

  return deliverables.sort((left, right) => left.path.localeCompare(right.path));
}

async function buildWorkerEvidence(
  result: WorkerResult,
  spec: ResolvedWorkerSpec | null,
  outputDir: string,
): Promise<NormalizedWorkerEvidence> {
  const fileStem = safeFileStem(result.name);
  const promptText = spec?.prompt ?? (await readTextIfPresent(result.prompt));
  const resultText = await resolveWorkerResultText(result);
  const status = result.succeeded ? 'completed' : 'failed';
  const model = result.actual_model || result.requested_model || 'unknown';
  const contractSummary = truncateLine(
    spec?.taskText || promptText || 'No task text recorded.',
  );
  const resultSummary = truncateLine(
    resultText || fallbackResultText(result) || result.last_message_preview,
  );

  const promptFile = `prompts/${fileStem}.prompt.md`;
  const resultFile = `results/${fileStem}.result.md`;

  await writeFileSafe(path.join(outputDir, promptFile), promptText);
  await writeFileSafe(path.join(outputDir, resultFile), resultText);

  return {
    fileStem,
    promptFile: toDisplayPath(promptFile),
    resultFile: toDisplayPath(resultFile),
    role: result.name,
    model,
    status,
    contractSummary,
    resultSummary,
    resultText,
  };
}

async function writeMixedEngineRawEvidence(
  outputDir: string,
  result: WorkerResult,
  fileStem: string,
): Promise<void> {
  if (!result.stdout) {
    return;
  }

  const rawTarget = path.join(outputDir, 'engines', result.engine, `${fileStem}.raw.txt`);
  const copied = await copyIfExists(result.stdout, rawTarget);

  if (!copied) {
    const fallback = await readTextIfPresent(result.stdout);
    if (fallback !== '') {
      await writeFileSafe(rawTarget, fallback);
    }
  }
}

function buildManifestMarkdown(
  runName: string,
  manifest: Manifest,
  resolvedPaths: ResolvedPaths,
  workerEvidence: NormalizedWorkerEvidence[],
  results: WorkerResult[],
  deliverables: DeliverableRecord[],
): string {
  const classification = inferClassification(manifest, results);
  const complexity = inferComplexity(manifest, results);
  const pattern = inferPattern(manifest, results);
  const verdict = inferVerdict(results);
  const fixCycles = results.filter((result) => result.worker_kind === 'fixer').length;

  const lines: string[] = [
    `# Run Manifest - ${runName}`,
    '',
    '## Request',
    '',
    `- **Original**: Launcher spec ${relativeDisplayPath(resolvedPaths.workspaceRoot, resolvedPaths.specPath)}`,
    `- **Classification**: ${classification}`,
    `- **Complexity**: ${complexity}`,
    '',
    '## Team',
    '',
    `- **Pattern**: ${pattern}`,
    `- **Agent count**: ${results.length}`,
    `- **Shared directive**: ${manifest.shared_directive.source ?? 'none'}`,
    '',
    '## Agents',
    '',
    '| # | Role | Engine | Model | Stage | Status | Agent ID |',
    '|---|---|---|---|---|---|---|',
  ];

  for (let index = 0; index < results.length; index++) {
    const result = results[index];
    const evidence = workerEvidence[index];
    lines.push(
      `| ${index + 1} | ${escapeMarkdownCell(evidence.role)} | ${result.engine} | ${escapeMarkdownCell(evidence.model)} | ${result.stage} | ${evidence.status} | ${escapeMarkdownCell(result.session_id ?? 'n/a')} |`,
    );
  }

  for (let index = 0; index < results.length; index++) {
    const result = results[index];
    const evidence = workerEvidence[index];
    lines.push('');
    lines.push(`### Agent ${index + 1}: ${evidence.role} (${result.worker_kind})`);
    lines.push('');
    lines.push(`- **Contract summary**: ${evidence.contractSummary}`);
    lines.push(`- **Result summary**: ${evidence.resultSummary}`);
    lines.push(`- **Prompt file**: ${evidence.promptFile}`);
    lines.push(`- **Result file**: ${evidence.resultFile}`);
  }

  lines.push('');
  lines.push('## Deliverables');
  lines.push('');
  lines.push('| Path | Action | Description |');
  lines.push('|---|---|---|');

  if (deliverables.length === 0) {
    lines.push('| none recorded | n/a | No requested deliverables were recorded in the launcher manifest. |');
  } else {
    for (const deliverable of deliverables) {
      lines.push(
        `| ${escapeMarkdownCell(deliverable.path)} | ${deliverable.action} | ${escapeMarkdownCell(deliverable.description)} |`,
      );
    }
  }

  lines.push('');
  lines.push('## Review');
  lines.push('');
  lines.push(`- **Verdict**: ${verdict}`);
  lines.push(`- **Fix cycles**: ${fixCycles}`);
  lines.push(`- **Final reviewer**: ${finalReviewerLabel(results)}`);
  lines.push('');
  lines.push('### Settlement Record');
  lines.push('');
  lines.push('| Worker | Engine | Status | Contribution |');
  lines.push('|---|---|---|---|');
  for (const result of results) {
    const status = result.succeeded ? 'OK' : 'FAILED';
    const contrib = result.worker_kind === 'reviewer' ? 'review'
      : result.worker_kind === 'fixer' ? 'fix'
      : result.worker_kind === 'watchdog' ? 'watchdog'
      : 'deliverable';
    lines.push(`| ${result.name} | ${result.engine} | ${status} | ${contrib} |`);
  }
  lines.push('');
  lines.push('## Metrics');
  lines.push('');
  lines.push(`- **Agents used**: ${results.length}`);
  lines.push(
    `- **Deliverables/agents**: ${
      results.length === 0
        ? 'n/a'
        : (deliverables.length / results.length).toFixed(2)
    }`,
  );
  lines.push(`- **Fix cycles**: ${fixCycles}`);
  lines.push(`- **Model cost profile**: ${summarizeCostProfile(results)}`);
  lines.push(
    `- **Final read-only review**: ${manifest.policy.final_read_only_review_present ? 'yes' : 'no'}`,
  );
  lines.push('');
  lines.push('## Timeline');
  lines.push('');
  lines.push('- **Started**: not recorded by TS launcher');
  lines.push(`- **Completed**: ${manifest.created_at_utc}`);
  lines.push('');
  lines.push('## Errors / Notes');

  const notes: string[] = [];

  for (const result of results) {
    if (!result.succeeded) {
      const reason =
        result.validation_failures[0] ??
        result.failure_message ??
        `exit code ${result.exit_code}`;
      notes.push(`${result.name}: ${reason}`);
    }
  }

  for (const deliverable of deliverables) {
    if (deliverable.action === 'missing') {
      notes.push(`${deliverable.path}: requested deliverable missing at evidence time`);
    }
  }

  if (notes.length === 0) {
    lines.push('- none');
  } else {
    for (const note of notes) {
      lines.push(`- ${note}`);
    }
  }

  lines.push('');
  return lines.join('\n');
}

function buildSummaryMarkdown(
  runName: string,
  resolvedPaths: ResolvedPaths,
  workerEvidence: NormalizedWorkerEvidence[],
  results: WorkerResult[],
  deliverables: DeliverableRecord[],
): string {
  const lines: string[] = [
    `# Run Summary - ${runName}`,
    '',
    '| # | Role | Engine | Model | Stage | Status | Result |',
    '|---|---|---|---|---|---|---|',
  ];

  for (let index = 0; index < results.length; index++) {
    const result = results[index];
    const evidence = workerEvidence[index];
    lines.push(
      `| ${index + 1} | ${escapeMarkdownCell(evidence.role)} | ${result.engine} | ${escapeMarkdownCell(evidence.model)} | ${result.stage} | ${evidence.status} | ${escapeMarkdownCell(evidence.resultSummary)} |`,
    );
  }

  const deliverableSummary =
    deliverables.length === 0
      ? 'none recorded'
      : deliverables
          .map((deliverable) => `${deliverable.path} (${deliverable.action})`)
          .join(', ');

  lines.push('');
  lines.push(`- **Verdict**: ${inferVerdict(results)}`);
  lines.push(`- **Deliverables**: ${deliverableSummary}`);
  lines.push(`- **Cost profile**: ${summarizeCostProfile(results)}`);
  lines.push(
    `- **Evidence**: ${relativeDisplayPath(resolvedPaths.workspaceRoot, resolvedPaths.outputDir)}/`,
  );
  lines.push('');

  return lines.join('\n');
}

export async function writeNormalizedEvidence(
  resolvedPaths: ResolvedPaths,
  manifest: Manifest,
  results: WorkerResult[],
  workers: ResolvedWorkerSpec[],
): Promise<void> {
  const specsByName = new Map(workers.map((worker) => [worker.name, worker]));
  const outputDir = resolvedPaths.outputDir;
  const runName = path.basename(outputDir);
  const isMixedEngine = new Set(results.map((result) => result.engine)).size > 1;

  const workerEvidence = await Promise.all(
    results.map(async (result) => {
      const evidence = await buildWorkerEvidence(
        result,
        specsByName.get(result.name) ?? null,
        outputDir,
      );

      if (isMixedEngine) {
        await writeMixedEngineRawEvidence(outputDir, result, evidence.fileStem);
      }

      return evidence;
    }),
  );

  const deliverables = await collectDeliverables(manifest, resolvedPaths, results);
  const manifestMarkdown = buildManifestMarkdown(
    runName,
    manifest,
    resolvedPaths,
    workerEvidence,
    results,
    deliverables,
  );
  const summaryMarkdown = buildSummaryMarkdown(
    runName,
    resolvedPaths,
    workerEvidence,
    results,
    deliverables,
  );

  await writeFileSafe(path.join(outputDir, 'run-manifest.md'), manifestMarkdown);
  await writeFileSafe(path.join(outputDir, 'run-summary.md'), summaryMarkdown);
}
