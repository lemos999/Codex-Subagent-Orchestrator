import { describe, it, expect, afterEach } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { IndexLock } from '../../src/core/index-lock.js';
import type { LockInfo } from '../../src/core/index-lock.js';

describe('IndexLock', () => {
  let tmpDir: string;

  afterEach(() => {
    if (tmpDir && fs.existsSync(tmpDir)) {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    }
  });

  function makeTmpDir(): string {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'wki-lock-test-'));
    return tmpDir;
  }

  it('acquire/release lifecycle — acquire succeeds, release clears lock file', () => {
    const dir = makeTmpDir();
    const lock = new IndexLock(dir);
    const lockPath = path.join(dir, '.wki.lock');

    lock.acquire('index');
    expect(fs.existsSync(lockPath)).toBe(true);

    lock.release();
    expect(fs.existsSync(lockPath)).toBe(false);
  });

  it('reentrant acquire — second acquire from same process succeeds', () => {
    const dir = makeTmpDir();
    const lockPath = path.join(dir, '.wki.lock');
    const lock = new IndexLock(dir);

    lock.acquire('index');

    // Second acquire from same process should succeed (reentrant)
    const lock2 = new IndexLock(dir);
    expect(() => lock2.acquire('rebuild')).not.toThrow();

    // Reentrant release should NOT delete the lock file
    lock2.release();
    expect(fs.existsSync(lockPath)).toBe(true);

    // Original holder can still release
    lock.release();
    expect(fs.existsSync(lockPath)).toBe(false);
  });

  it('stale lock detection — create lock with dead PID, acquire should succeed', () => {
    const dir = makeTmpDir();
    const lockPath = path.join(dir, '.wki.lock');

    // Write a lock file with a PID that is almost certainly dead
    const staleLock: LockInfo = {
      pid: 2147483646, // Very high PID, unlikely to be alive
      lockId: 'stale-lock-id-for-test',
      timestamp: new Date().toISOString(),
      operation: 'index',
    };
    fs.writeFileSync(lockPath, JSON.stringify(staleLock, null, 2));

    const lock = new IndexLock(dir);
    // Should detect stale lock and succeed
    expect(() => lock.acquire('rebuild')).not.toThrow();

    // Verify we own the lock now
    const info = lock.getLockInfo();
    expect(info).not.toBeNull();
    expect(info!.pid).toBe(process.pid);
    expect(info!.operation).toBe('rebuild');
    expect(info!.lockId).not.toBe('stale-lock-id-for-test');

    lock.release();
  });

  it('isLocked/getLockInfo — correct status reporting', () => {
    const dir = makeTmpDir();
    const lock = new IndexLock(dir);

    expect(lock.isLocked()).toBe(false);
    expect(lock.getLockInfo()).toBeNull();

    lock.acquire('scan');

    expect(lock.isLocked()).toBe(true);
    const info = lock.getLockInfo();
    expect(info).not.toBeNull();
    expect(info!.pid).toBe(process.pid);
    expect(info!.operation).toBe('scan');
    expect(typeof info!.timestamp).toBe('string');

    lock.release();

    expect(lock.isLocked()).toBe(false);
    expect(lock.getLockInfo()).toBeNull();
  });

  it('release without acquire — no-op, no error', () => {
    const dir = makeTmpDir();
    const lock = new IndexLock(dir);

    // Should not throw
    expect(() => lock.release()).not.toThrow();
  });

  it('lock file format — valid JSON with pid, timestamp, operation', () => {
    const dir = makeTmpDir();
    const lock = new IndexLock(dir);
    const lockPath = path.join(dir, '.wki.lock');

    lock.acquire('index');

    const raw = fs.readFileSync(lockPath, 'utf-8');
    const parsed = JSON.parse(raw) as LockInfo;

    expect(typeof parsed.pid).toBe('number');
    expect(parsed.pid).toBe(process.pid);
    expect(typeof parsed.lockId).toBe('string');
    expect(parsed.lockId.length).toBeGreaterThan(0);
    expect(typeof parsed.timestamp).toBe('string');
    // Validate ISO 8601 format
    expect(new Date(parsed.timestamp).toISOString()).toBe(parsed.timestamp);
    expect(parsed.operation).toBe('index');

    lock.release();
  });

  it('creates knowledgeDir if it does not exist', () => {
    const dir = path.join(os.tmpdir(), `wki-lock-nested-${Date.now()}`);
    tmpDir = dir; // for cleanup
    const nestedDir = path.join(dir, 'sub', 'dir');

    const lock = new IndexLock(nestedDir);
    lock.acquire('scan');

    expect(fs.existsSync(nestedDir)).toBe(true);
    expect(fs.existsSync(path.join(nestedDir, '.wki.lock'))).toBe(true);

    lock.release();
  });
});
