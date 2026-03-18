import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

export interface LockInfo {
  pid: number;
  lockId: string;     // unique per acquire() call — prevents PID-reuse collisions
  timestamp: string;  // ISO 8601
  operation: string;  // 'index' | 'rebuild' | 'scan'
}

export class IndexLock {
  private readonly lockPath: string;
  private currentLockId: string | null = null;
  private reentrant = false;

  constructor(private knowledgeDir: string) {
    this.lockPath = path.join(knowledgeDir, '.wki.lock');
  }

  /**
   * Acquire an exclusive lock for a write operation.
   * Throws if lock already held by another live process.
   * Detects stale locks (process no longer alive).
   * Reentrant: if this instance already holds the lock, acquire succeeds.
   */
  acquire(operation: string): void {
    // Ensure the knowledge directory exists
    if (!fs.existsSync(this.knowledgeDir)) {
      fs.mkdirSync(this.knowledgeDir, { recursive: true });
    }

    // Reentrant check: if this instance already holds the lock, allow re-acquire
    if (this.currentLockId) {
      const existing = this.getLockInfo();
      if (existing && existing.lockId === this.currentLockId && existing.pid === process.pid) {
        return;
      }
    }

    const lockId = crypto.randomUUID();
    const lockInfo: LockInfo = {
      pid: process.pid,
      lockId,
      timestamp: new Date().toISOString(),
      operation,
    };

    try {
      // Atomic creation — fails if file already exists
      fs.writeFileSync(this.lockPath, JSON.stringify(lockInfo, null, 2), { flag: 'wx' });
      this.currentLockId = lockId;
    } catch (err: unknown) {
      // File already exists — check if stale or reentrant
      if (isFileExistsError(err)) {
        const existing = this.getLockInfo();
        if (existing && this.isProcessAlive(existing.pid)) {
          // Same-process reentrant acquire: borrow existing lock without overwriting
          if (existing.pid === process.pid) {
            this.currentLockId = existing.lockId;
            this.reentrant = true;
            return;
          }
          throw new Error(
            `Another WKI operation is in progress (PID ${existing.pid}, started ${existing.timestamp}, operation: ${existing.operation}).\n` +
            `Wait for it to complete or remove ${this.lockPath} if the process is dead.`,
          );
        }
        // Stale lock — compare-and-swap: delete stale, then try exclusive create
        try {
          fs.unlinkSync(this.lockPath);
        } catch {
          // Another process may have already cleaned up
        }
        fs.writeFileSync(this.lockPath, JSON.stringify(lockInfo, null, 2), { flag: 'wx' });
        this.currentLockId = lockId;
        return;
      }
      throw err;
    }
  }

  /**
   * Release the lock. Only unlinks if this instance owns the lock file.
   * Reentrant instances (same-process borrowers) do not unlink — the original holder does.
   * Safe to call even if not holding.
   */
  release(): void {
    if (this.reentrant) {
      // Borrowed lock — don't unlink; let the original holder release
      this.currentLockId = null;
      this.reentrant = false;
      return;
    }
    try {
      if (this.currentLockId) {
        const existing = this.getLockInfo();
        // Only delete if we own the lock
        if (existing && existing.lockId !== this.currentLockId) {
          this.currentLockId = null;
          return;
        }
      }
      fs.unlinkSync(this.lockPath);
    } catch {
      // Ignore — file may not exist
    }
    this.currentLockId = null;
  }

  /**
   * Check if a lock is currently held (without acquiring).
   */
  isLocked(): boolean {
    return this.getLockInfo() !== null;
  }

  /**
   * Read current lock info, or null if unlocked.
   */
  getLockInfo(): LockInfo | null {
    try {
      const content = fs.readFileSync(this.lockPath, 'utf-8');
      return JSON.parse(content) as LockInfo;
    } catch {
      return null;
    }
  }

  private isProcessAlive(pid: number): boolean {
    try {
      process.kill(pid, 0);
      return true;
    } catch {
      return false;
    }
  }
}

function isFileExistsError(err: unknown): boolean {
  return (err as NodeJS.ErrnoException).code === 'EEXIST';
}
