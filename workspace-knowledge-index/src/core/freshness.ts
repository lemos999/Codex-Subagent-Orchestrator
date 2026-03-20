import fs from 'node:fs';
import path from 'node:path';
import { execSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import type { FreshnessState } from '../types/index.js';

/** Files that have changed since the last index. */
export interface ChangedFiles {
  added: string[];
  modified: string[];
  deleted: string[];
  renamed: Array<{ from: string; to: string }>;
}

/**
 * Manages freshness.lock for incremental indexing.
 * Tracks git state to detect which files need re-indexing.
 */
export class FreshnessManager {
  private state: FreshnessState | null = null;

  /**
   * Load freshness state from a lock file.
   * @returns The loaded state, or null if the file does not exist.
   */
  load(filePath: string): FreshnessState | null {
    try {
      if (!fs.existsSync(filePath)) return null;
      const content = fs.readFileSync(filePath, 'utf-8');
      const parsed = JSON.parse(content) as FreshnessState;
      this.state = parsed;
      return parsed;
    } catch {
      return null;
    }
  }

  /**
   * Save the current freshness state to a lock file.
   */
  save(filePath: string, state: FreshnessState): void {
    const dir = path.dirname(filePath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    fs.writeFileSync(filePath, JSON.stringify(state, null, 2), 'utf-8');
    this.state = state;
  }

  /**
   * Capture the current git state as a FreshnessState snapshot.
   */
  captureState(projectRoot: string): FreshnessState {
    const headCommit = this.git(projectRoot, 'rev-parse HEAD').trim() || 'unknown';
    const branch = this.git(projectRoot, 'rev-parse --abbrev-ref HEAD').trim() || 'unknown';

    const porcelain = this.git(projectRoot, 'status --porcelain');
    const dirty = porcelain.trim().length > 0;

    const staged = this.git(projectRoot, 'diff --cached --name-only');
    const stagedFingerprint = this.fingerprint(staged);

    const untracked = this.git(projectRoot, 'ls-files --others --exclude-standard');
    const untrackedFingerprint = this.fingerprint(untracked);

    return {
      head_commit: headCommit,
      branch,
      dirty,
      staged_fingerprint: stagedFingerprint,
      untracked_fingerprint: untrackedFingerprint,
      file_hashes: {},
      indexed_at: new Date().toISOString(),
    };
  }

  /**
   * Detect files that changed between the previous state and current git state.
   */
  detectChanges(prev: FreshnessState, projectRoot: string): ChangedFiles {
    const result: ChangedFiles = {
      added: [],
      modified: [],
      deleted: [],
      renamed: [],
    };

    // 1. Committed changes since last indexed commit
    if (prev.head_commit && prev.head_commit !== 'unknown') {
      const committed = this.git(
        projectRoot,
        `diff --name-status -M ${prev.head_commit} HEAD`,
      );
      this.parseNameStatus(committed, result);
    }

    // 2. Unstaged changes in working tree
    const unstaged = this.git(projectRoot, 'diff --name-status -M HEAD');
    this.parseNameStatus(unstaged, result);

    // 3. Staged changes
    const staged = this.git(projectRoot, 'diff --cached --name-status -M');
    this.parseNameStatus(staged, result);

    // 4. Untracked files — skip if fingerprint unchanged (same set of untracked files)
    const untracked = this.git(projectRoot, 'ls-files --others --exclude-standard');
    const currentUntrackedFingerprint = this.fingerprint(untracked);
    const untrackedChanged = prev.untracked_fingerprint !== currentUntrackedFingerprint;

    if (untrackedChanged) {
      for (const line of untracked.split('\n')) {
        const trimmed = line.trim();
        if (trimmed.length > 0 && !result.added.includes(trimmed)) {
          result.added.push(trimmed);
        }
      }
    }

    // Deduplicate
    result.added = [...new Set(result.added)];
    result.modified = [...new Set(result.modified)];
    result.deleted = [...new Set(result.deleted)];

    return result;
  }

  /** Get the currently loaded state. */
  getState(): FreshnessState | null {
    return this.state;
  }

  // ---- Private helpers ----

  /**
   * Execute a git command and return stdout. Returns empty string on error.
   */
  private git(cwd: string, command: string): string {
    try {
      return execSync(`git ${command}`, { cwd, encoding: 'utf-8', stdio: ['pipe', 'pipe', 'pipe'] });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      console.warn(`[wki] git ${command.split(' ')[0]} failed: ${message.split('\n')[0]}`);
      return '';
    }
  }

  /**
   * Compute a SHA-256 fingerprint from sorted lines of output.
   */
  private fingerprint(output: string): string {
    const lines = output
      .split('\n')
      .map((l) => l.trim())
      .filter((l) => l.length > 0)
      .sort();
    return createHash('sha256').update(lines.join('\n')).digest('hex');
  }

  /**
   * Parse git diff --name-status output and populate ChangedFiles.
   * Format: STATUS\tFILE (or STATUS\tFROM\tTO for renames)
   */
  private parseNameStatus(output: string, result: ChangedFiles): void {
    for (const line of output.split('\n')) {
      const trimmed = line.trim();
      if (trimmed.length === 0) continue;

      const parts = trimmed.split('\t');
      if (parts.length < 2) continue;

      const status = parts[0]!;
      const filePath = parts[1]!;

      if (status === 'A') {
        if (!result.added.includes(filePath)) {
          result.added.push(filePath);
        }
      } else if (status === 'M') {
        if (!result.modified.includes(filePath)) {
          result.modified.push(filePath);
        }
      } else if (status === 'D') {
        if (!result.deleted.includes(filePath)) {
          result.deleted.push(filePath);
        }
      } else if (status.startsWith('R') && parts.length >= 3) {
        const from = parts[1]!;
        const to = parts[2]!;
        const alreadyRenamed = result.renamed.some((r) => r.from === from && r.to === to);
        if (!alreadyRenamed) {
          result.renamed.push({ from, to });
        }
      }
    }
  }
}
