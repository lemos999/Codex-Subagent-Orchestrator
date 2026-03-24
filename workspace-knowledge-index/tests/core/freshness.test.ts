import { describe, it, expect, afterEach } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { execSync } from 'node:child_process';
import { FreshnessManager } from '../../src/core/freshness.js';
import type { FreshnessState } from '../../src/types/index.js';

describe('FreshnessManager', () => {
  let tmpDir: string;

  afterEach(() => {
    if (tmpDir && fs.existsSync(tmpDir)) {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    }
  });

  /** Helper: create a temporary git repo with an initial commit. */
  function createGitRepo(): string {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'wki-test-'));
    execSync('git init', { cwd: tmpDir, stdio: 'pipe' });
    execSync('git config user.email "test@test.com"', { cwd: tmpDir, stdio: 'pipe' });
    execSync('git config user.name "Test"', { cwd: tmpDir, stdio: 'pipe' });
    fs.writeFileSync(path.join(tmpDir, 'init.txt'), 'hello');
    execSync('git add .', { cwd: tmpDir, stdio: 'pipe' });
    execSync('git commit -m "init"', { cwd: tmpDir, stdio: 'pipe' });
    return tmpDir;
  }

  describe('save / load round-trip', () => {
    it('should save and load a freshness state', () => {
      tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'wki-test-'));
      const lockPath = path.join(tmpDir, 'freshness.lock');

      const state: FreshnessState = {
        head_commit: 'abc123',
        branch: 'main',
        dirty: false,
        staged_fingerprint: 'fp1',
        untracked_fingerprint: 'fp2',
        file_hashes: {},
        indexed_at: new Date().toISOString(),
      };

      const fm = new FreshnessManager();
      fm.save(lockPath, state);

      const fm2 = new FreshnessManager();
      const loaded = fm2.load(lockPath);
      expect(loaded).not.toBeNull();
      expect(loaded!.head_commit).toBe('abc123');
      expect(loaded!.branch).toBe('main');
      expect(loaded!.dirty).toBe(false);
    });
  });

  describe('captureState', () => {
    it('should capture state from a git repo', () => {
      const repoDir = createGitRepo();

      const fm = new FreshnessManager();
      const state = fm.captureState(repoDir);

      expect(state.head_commit).toMatch(/^[a-f0-9]{40}$/);
      expect(state.branch).toBeTruthy();
      expect(state.dirty).toBe(false);
      expect(state.indexed_at).toBeTruthy();
    });

    it('should degrade gracefully in a non-git directory', () => {
      tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'wki-test-'));

      const fm = new FreshnessManager();
      const state = fm.captureState(tmpDir);

      // git commands fail silently, returning empty/unknown
      expect(state.head_commit).toBe('unknown');
      expect(state.branch).toBe('unknown');
    });
  });

  describe('detectChanges', () => {
    it('should detect modified files after a commit', () => {
      const repoDir = createGitRepo();

      const fm = new FreshnessManager();
      const prevState = fm.captureState(repoDir);

      // Modify a file and commit
      fs.writeFileSync(path.join(repoDir, 'init.txt'), 'modified');
      execSync('git add .', { cwd: repoDir, stdio: 'pipe' });
      execSync('git commit -m "modify"', { cwd: repoDir, stdio: 'pipe' });

      const changes = fm.detectChanges(prevState, repoDir);
      expect(changes.modified).toContain('init.txt');
    });
  });

  describe('load non-existent file', () => {
    it('should return null for a non-existent file', () => {
      const fm = new FreshnessManager();
      const result = fm.load('/tmp/does-not-exist-ever-12345.lock');
      expect(result).toBeNull();
    });
  });
});
