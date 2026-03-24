/**
 * Queue runner — main polling loop + scheduler.
 *
 * Flow per poll:
 * 1. Fetch raw issues from tracker
 * 2. Normalize issues
 * 3. Update state records with latest tracker state
 * 4. Check running processes for completion
 * 5. Filter dispatchable issues (state, auto_run, not blocked, eligible, not completed)
 * 6. Spawn new workers up to max_concurrent
 * 7. Save state + report
 */

import * as fs from 'node:fs/promises';
import * as path from 'node:path';
import { spawn } from 'node:child_process';
import type { CanonicalQueueConfig, NormalizedIssue, QueueState, RunningProcess } from './queue-types.js';
import type { Tracker } from './trackers/tracker.js';
import { LocalJsonTracker } from './trackers/local-json.js';
import { LocalFilesTracker } from './trackers/local-files.js';
import { LinearTracker } from './trackers/linear.js';
import { normalizeIssue, computeFingerprint, isBlocked, compareIssues } from './issue-normalizer.js';
import { loadState, saveState, getIssueRecord, getBackoffSeconds, isEligibleNow } from './queue-state.js';
import { generateLauncherSpec } from './launcher-adapter.js';
import { writeReport } from './queue-report.js';

const IS_WINDOWS = process.platform === 'win32';

// ============================================================
// Types
// ============================================================

export interface QueueRunnerCallbacks {
  onStatus: (message: string) => void;
  onIssueDispatched: (issueKey: string) => void;
  onIssueCompleted: (issueKey: string, exitCode: number) => void;
  onIssueFailed: (issueKey: string, exitCode: number) => void;
}

interface RunningEntry {
  process: RunningProcess;
  childProcess: ReturnType<typeof spawn>;
}

// ============================================================
// Create tracker from config
// ============================================================

function createTracker(config: CanonicalQueueConfig): Tracker {
  switch (config.tracker.kind) {
    case 'local-json':
      return new LocalJsonTracker(
        config.tracker.source_file ?? 'tasks/queue.json',
        config.config_directory,
      );
    case 'local-files':
      return new LocalFilesTracker(
        config.tracker.source_dir ?? 'tasks',
        config.config_directory,
        config.tracker.include_globs,
        config.tracker.recurse,
      );
    case 'linear':
      return new LinearTracker(
        config.tracker.project_slug ?? '',
        config.tracker.api_key_env ?? 'LINEAR_API_KEY',
        config.tracker.endpoint ?? 'https://api.linear.app/graphql',
        config.tracker.active_states,
      );
    default:
      throw new Error(`Unsupported tracker kind: ${config.tracker.kind}`);
  }
}

// ============================================================
// Main runner
// ============================================================

export async function runQueue(
  config: CanonicalQueueConfig,
  callbacks: QueueRunnerCallbacks,
  maxPollsOverride?: number,
): Promise<QueueState> {
  const tracker = createTracker(config);
  const statePath = path.resolve(
    config.config_directory,
    config.output.state_file ?? `${config.output.root}/queue-state.json`,
  );
  const outputRoot = path.resolve(config.config_directory, config.output.root);
  const workspaceRoot = path.resolve(config.config_directory, config.workspace.root);
  const generatedSpecsDir = path.join(outputRoot, 'generated-specs');
  const logsDir = path.join(outputRoot, 'queue-logs');

  await fs.mkdir(outputRoot, { recursive: true });
  await fs.mkdir(generatedSpecsDir, { recursive: true });
  await fs.mkdir(workspaceRoot, { recursive: true });

  let state = await loadState(statePath);
  const running = new Map<string, RunningEntry>();
  const maxPolls = maxPollsOverride ?? config.polling.max_polls;
  let pollCount = 0;

  // ---- Poll loop ----
  while (true) {
    pollCount++;
    callbacks.onStatus(`Poll ${pollCount}${maxPolls > 0 ? `/${maxPolls}` : ''}`);

    // 1. Fetch + normalize issues
    const rawIssues = await tracker.fetchRawIssues();
    const issues = rawIssues.map((raw) => normalizeIssue(raw));
    const issueMap = new Map<string, NormalizedIssue>();
    for (const issue of issues) {
      issueMap.set(issue.identifier, issue);
    }

    // 2. Update state records with latest tracker state
    for (const issue of issues) {
      const record = getIssueRecord(state, issue.identifier);
      record.last_state = issue.state;
      record.last_seen_at_utc = new Date().toISOString();
      record.last_issue_fingerprint = computeFingerprint(issue);
      if (issue.source_path) record.source_path = issue.source_path;
    }

    // 3. Check running processes — stop if issue removed or terminal
    for (const [key, entry] of running) {
      const issue = issueMap.get(key);
      if (!issue) {
        // Issue removed from tracker
        callbacks.onStatus(`  ${key}: 트래커에서 사라짐 — 중단`);
        entry.process.kill();
        const record = getIssueRecord(state, key);
        record.status = 'stopped';
        record.stop_reason = 'issue_missing_from_tracker';
        running.delete(key);
        continue;
      }

      if (config.tracker.terminal_states.includes(issue.state)) {
        callbacks.onStatus(`  ${key}: 터미널 상태 ${issue.state} — 중단`);
        entry.process.kill();
        const record = getIssueRecord(state, key);
        record.status = 'stopped';
        record.stop_reason = `terminal_state:${issue.state}`;
        running.delete(key);
        continue;
      }

      if (!config.tracker.active_states.includes(issue.state)) {
        callbacks.onStatus(`  ${key}: 비활성 상태 ${issue.state} — 중단`);
        entry.process.kill();
        const record = getIssueRecord(state, key);
        record.status = 'stopped';
        record.stop_reason = `inactive_state:${issue.state}`;
        running.delete(key);
      }
    }

    // 4. Check completed processes
    for (const [key, entry] of running) {
      if (entry.childProcess.exitCode !== null) {
        const exitCode = entry.childProcess.exitCode;
        const record = getIssueRecord(state, key);
        record.last_exit_code = exitCode;
        record.last_finished_at_utc = new Date().toISOString();
        record.last_stdout = entry.process.stdoutPath;
        record.last_stderr = entry.process.stderrPath;

        // Parse launcher result for manifest/summary paths
        try {
          const stdoutContent = await fs.readFile(entry.process.stdoutPath, 'utf8');
          const jsonMatch = stdoutContent.match(/\{[\s\S]*"manifest"[\s\S]*\}/);
          if (jsonMatch) {
            const parsed = JSON.parse(jsonMatch[0]) as Record<string, unknown>;
            record.last_manifest = (parsed.manifest as string) ?? null;
            record.last_summary = (parsed.summary as string) ?? null;
          }
        } catch { /* stdout not parseable — leave null */ }

        if (exitCode === 0) {
          record.status = 'completed';
          record.consecutive_failures = 0;
          record.next_eligible_at_utc = null;
          record.last_success_fingerprint = record.last_issue_fingerprint;
          record.last_success_at_utc = new Date().toISOString();
          callbacks.onIssueCompleted(key, exitCode);
        } else {
          record.status = 'failed';
          record.consecutive_failures++;
          const backoff = getBackoffSeconds(
            record.consecutive_failures,
            config.retry.base_backoff_seconds,
            config.retry.max_backoff_seconds,
          );
          record.next_eligible_at_utc = new Date(Date.now() + backoff * 1000).toISOString();
          callbacks.onIssueFailed(key, exitCode);
        }

        running.delete(key);
      }
    }

    // 5. Filter dispatchable issues
    const dispatchable = issues
      .filter((issue) => {
        // Active state
        if (!config.tracker.active_states.includes(issue.state)) return false;
        // Auto-run enabled
        if (!issue.auto_run) return false;
        // Not currently running
        if (running.has(issue.identifier)) return false;
        // Not blocked
        if (isBlocked(issue, config.tracker.active_states, issueMap, state.issues)) return false;
        // Eligible (backoff expired)
        const record = getIssueRecord(state, issue.identifier);
        if (!isEligibleNow(record)) return false;
        // Not already completed with same fingerprint
        const currentFp = computeFingerprint(issue);
        if (record.status === 'completed' && record.last_success_fingerprint === currentFp) return false;

        return true;
      })
      .sort(compareIssues);

    // 6. Dispatch up to max_concurrent
    const slotsAvailable = config.launcher.max_concurrent_issues - running.size;
    const toDispatch = dispatchable.slice(0, Math.max(0, slotsAvailable));

    for (const issue of toDispatch) {
      const record = getIssueRecord(state, issue.identifier);
      record.dispatch_count++;
      record.status = 'running';
      record.last_started_at_utc = new Date().toISOString();

      // Workspace path
      const safeName = issue.identifier.replace(/[^a-zA-Z0-9가-힣_-]/g, '_');
      const wsPath = path.resolve(workspaceRoot, safeName);
      await fs.mkdir(wsPath, { recursive: true });
      record.workspace_path = wsPath;

      // Generate spec
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
      const runOutputDir = path.join(outputRoot, 'issue-runs', safeName, timestamp);
      const spec = generateLauncherSpec(issue, config, wsPath, runOutputDir, record.dispatch_count);
      const specPath = path.join(generatedSpecsDir, `${safeName}.json`);
      await fs.writeFile(specPath, JSON.stringify(spec, null, 2), 'utf8');

      // Spawn
      const launcherPath = path.resolve(config.config_directory, 'packages/launcher/dist/cli.js');
      const stdoutPath = path.join(logsDir, safeName, `${timestamp}.stdout.log`);
      const stderrPath = path.join(logsDir, safeName, `${timestamp}.stderr.log`);
      await fs.mkdir(path.dirname(stdoutPath), { recursive: true });

      const stdoutFd = await fs.open(stdoutPath, 'w');
      const stderrFd = await fs.open(stderrPath, 'w');

      const child = spawn('node', [launcherPath, '--spec', specPath], {
        cwd: config.config_directory,
        stdio: ['ignore', 'pipe', 'pipe'],
        shell: IS_WINDOWS,
      });

      child.stdout?.on('data', (chunk: Buffer) => { stdoutFd.write(chunk); });
      child.stderr?.on('data', (chunk: Buffer) => { stderrFd.write(chunk); });
      child.on('exit', () => { stdoutFd.close(); stderrFd.close(); });

      const processHandle: RunningProcess = {
        issueKey: issue.identifier,
        pid: child.pid ?? -1,
        specPath,
        stdoutPath,
        stderrPath,
        startedAt: new Date().toISOString(),
        kill: () => { try { child.kill('SIGTERM'); } catch { /* */ } },
      };

      running.set(issue.identifier, { process: processHandle, childProcess: child });
      record.last_stdout = stdoutPath;
      record.last_stderr = stderrPath;

      callbacks.onIssueDispatched(issue.identifier);
      callbacks.onStatus(`  ${issue.identifier}: 디스패치됨 (attempt ${record.dispatch_count})`);
    }

    // 7. Save state + report
    await saveState(statePath, state);
    await writeReport(config, state, pollCount);

    // Exit conditions
    if (maxPolls > 0 && pollCount >= maxPolls) {
      callbacks.onStatus(`최대 폴링 횟수 도달 (${maxPolls})`);
      break;
    }

    // Wait for interval
    await sleep(config.polling.interval_seconds * 1000);
  }

  // Drain on exit
  if (config.polling.drain_on_exit && running.size > 0) {
    callbacks.onStatus(`Drain: ${running.size}개 실행 중인 작업 대기...`);

    while (running.size > 0) {
      for (const [key, entry] of running) {
        if (entry.childProcess.exitCode !== null) {
          const exitCode = entry.childProcess.exitCode;
          const record = getIssueRecord(state, key);
          record.last_exit_code = exitCode;
          record.last_finished_at_utc = new Date().toISOString();
          record.last_stdout = entry.process.stdoutPath;
          record.last_stderr = entry.process.stderrPath;

          // Parse manifest/summary from launcher stdout
          try {
            const stdoutContent = await fs.readFile(entry.process.stdoutPath, 'utf8');
            const jsonMatch = stdoutContent.match(/\{[\s\S]*"manifest"[\s\S]*\}/);
            if (jsonMatch) {
              const parsed = JSON.parse(jsonMatch[0]) as Record<string, unknown>;
              record.last_manifest = (parsed.manifest as string) ?? null;
              record.last_summary = (parsed.summary as string) ?? null;
            }
          } catch { /* */ }

          if (exitCode === 0) {
            record.status = 'completed';
            record.consecutive_failures = 0;
            record.last_success_fingerprint = record.last_issue_fingerprint;
            record.last_success_at_utc = new Date().toISOString();
            callbacks.onIssueCompleted(key, exitCode);
          } else {
            record.status = 'failed';
            record.consecutive_failures++;
            callbacks.onIssueFailed(key, exitCode);
          }

          running.delete(key);
        }
      }

      if (running.size > 0) {
        await sleep(1000);
      }
    }

    await saveState(statePath, state);
    await writeReport(config, state, pollCount);
  }

  return state;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
