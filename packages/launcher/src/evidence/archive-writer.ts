/**
 * Archive writer — copies run evidence and deliverables to a timestamped archive directory.
 *
 * Structure:
 * {archive_root}/{YYYYMMDD}-{HHMMSS}-{label}/
 * ├── launcher/      (spec, manifest, summary, debug log)
 * ├── deliverables/  (requested deliverables)
 * ├── workers/       ({kind}__{name}/ with metadata, prompt, stdout, stderr, last)
 * └── supervisor/    (AGENTS.md)
 */

import * as fs from 'node:fs/promises';
import * as fsSync from 'node:fs';
import * as path from 'node:path';
import type { LauncherSpec } from '../types/spec.js';
import type { Manifest, WorkerResult } from '../types/manifest.js';
import type { ResolvedPaths } from '../types/state.js';

export interface ArchiveResult {
  enabled: boolean;
  runDirectory: string | null;
  launcherDirectory: string | null;
  deliverablesDirectory: string | null;
  workersDirectory: string | null;
  supervisorDirectory: string | null;
}

function formatTimestamp(): string {
  const now = new Date();
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
}

async function copyIfExists(src: string, dest: string): Promise<boolean> {
  try {
    if (fsSync.existsSync(src)) {
      await fs.mkdir(path.dirname(dest), { recursive: true });
      await fs.copyFile(src, dest);
      return true;
    }
  } catch { /* ignore */ }
  return false;
}

/**
 * Write run archive if configured.
 */
export async function writeArchive(
  spec: LauncherSpec,
  resolvedPaths: ResolvedPaths,
  manifest: Manifest,
  results: WorkerResult[],
): Promise<ArchiveResult> {
  if (!spec.write_run_archive) {
    return { enabled: false, runDirectory: null, launcherDirectory: null, deliverablesDirectory: null, workersDirectory: null, supervisorDirectory: null };
  }

  const archiveRoot = spec.archive_root
    ? path.resolve(resolvedPaths.workspaceRoot, spec.archive_root)
    : path.resolve(resolvedPaths.workspaceRoot, 'subagent-records');

  const label = spec.archive_run_label ?? path.basename(resolvedPaths.outputDir);
  const timestamp = formatTimestamp();
  const runDir = path.resolve(archiveRoot, `${timestamp}-${label}`);

  const launcherDir = path.resolve(runDir, 'launcher');
  const deliverablesDir = path.resolve(runDir, 'deliverables');
  const workersDir = path.resolve(runDir, 'workers');
  const supervisorDir = path.resolve(runDir, 'supervisor');

  await fs.mkdir(launcherDir, { recursive: true });
  await fs.mkdir(deliverablesDir, { recursive: true });
  await fs.mkdir(workersDir, { recursive: true });
  await fs.mkdir(supervisorDir, { recursive: true });

  // 1. Launcher directory: spec, manifest, summary, debug log
  await copyIfExists(resolvedPaths.specPath, path.join(launcherDir, path.basename(resolvedPaths.specPath)));
  await copyIfExists(resolvedPaths.manifestFile, path.join(launcherDir, 'orchestration-manifest.json'));
  if (resolvedPaths.summaryFile) {
    await copyIfExists(resolvedPaths.summaryFile, path.join(launcherDir, 'orchestration-summary.md'));
  }
  if (resolvedPaths.debugLogFile) {
    await copyIfExists(resolvedPaths.debugLogFile, path.join(launcherDir, 'launcher-debug.log'));
  }

  // 2. Deliverables directory: requested deliverables
  for (const deliverable of spec.requested_deliverables ?? []) {
    const src = path.resolve(resolvedPaths.workspaceRoot, deliverable);
    const dest = path.join(deliverablesDir, path.basename(deliverable));
    await copyIfExists(src, dest);
  }

  // 3. Workers directory: per-worker evidence
  for (const result of results) {
    const kind = result.worker_kind || 'custom';
    const workerDir = path.join(workersDir, `${kind}__${result.name}`);
    await fs.mkdir(workerDir, { recursive: true });

    // Worker metadata
    const metadata = {
      name: result.name,
      engine: result.engine,
      kind: result.worker_kind,
      stage: result.stage,
      exit_code: result.exit_code,
      succeeded: result.succeeded,
      model: result.actual_model,
      sandbox: result.actual_sandbox,
    };
    await fs.writeFile(path.join(workerDir, 'worker-metadata.json'), JSON.stringify(metadata, null, 2), 'utf8');

    // Copy worker files
    if (result.prompt) await copyIfExists(result.prompt, path.join(workerDir, 'prompt.txt'));
    await copyIfExists(result.stdout, path.join(workerDir, 'stdout.log'));
    await copyIfExists(result.stderr, path.join(workerDir, 'stderr.log'));
    await copyIfExists(result.last, path.join(workerDir, 'last.txt'));
  }

  // 4. Supervisor directory: AGENTS.md
  const agentsMd = path.resolve(resolvedPaths.workspaceRoot, 'AGENTS.md');
  await copyIfExists(agentsMd, path.join(supervisorDir, 'AGENTS.md'));

  return {
    enabled: true,
    runDirectory: runDir,
    launcherDirectory: launcherDir,
    deliverablesDirectory: deliverablesDir,
    workersDirectory: workersDir,
    supervisorDirectory: supervisorDir,
  };
}
