/**
 * Shared file system helpers — safe read, write, copy, and path validation.
 * Eliminates duplicated patterns across archive-writer, stage-runner, etc.
 */

import * as crypto from 'node:crypto';
import * as fs from 'node:fs/promises';
import * as fsSync from 'node:fs';
import * as path from 'node:path';

/**
 * Write a UTF-8 file, ensuring the parent directory exists.
 */
export async function writeFileSafe(
  filePath: string,
  content: string,
): Promise<void> {
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  await fs.writeFile(filePath, content, 'utf8');
}

/**
 * Copy a file if the source exists. Creates parent directories at dest.
 * Returns true if the copy succeeded.
 */
export async function copyIfExists(
  src: string,
  dest: string,
  options?: { warnIfMissing?: boolean },
): Promise<boolean> {
  try {
    if (fsSync.existsSync(src)) {
      await fs.mkdir(path.dirname(dest), { recursive: true });
      await fs.copyFile(src, dest);
      return true;
    }
    if (options?.warnIfMissing) {
      process.stderr.write(`[warn] copyIfExists: source not found: ${src}\n`);
    }
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    process.stderr.write(`[warn] copyIfExists failed: ${src} -> ${dest}: ${message}\n`);
  }
  return false;
}

/**
 * Find paths from a list that do not exist on disk.
 */
export async function findMissingPaths(paths: string[]): Promise<string[]> {
  const missing: string[] = [];
  for (const p of paths) {
    try {
      await fs.access(p);
    } catch {
      missing.push(p);
    }
  }
  return missing;
}

/**
 * Find paths from a list that exist but are empty (0 bytes for files, 0 children for directories).
 * PS considers empty directories as "empty" via Test-PathHasContent.
 */
export async function findEmptyPaths(paths: string[]): Promise<string[]> {
  const empty: string[] = [];
  for (const p of paths) {
    try {
      const stat = await fs.stat(p);
      if (stat.isDirectory()) {
        const entries = await fs.readdir(p);
        if (entries.length === 0) {
          empty.push(p);
        }
      } else if (stat.size === 0) {
        empty.push(p);
      }
    } catch {
      // File doesn't exist — handled by findMissingPaths
    }
  }
  return empty;
}

/**
 * Compute SHA-256 hex digest of a UTF-8 string.
 */
export function sha256(content: string): string {
  return crypto.createHash('sha256').update(content, 'utf8').digest('hex');
}
