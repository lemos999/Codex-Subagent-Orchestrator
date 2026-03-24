/**
 * local-json tracker (also handles mock-json alias).
 *
 * Reads a single JSON file containing issues as:
 * - Array of issues
 * - Object with "issues" or "tasks" array
 * - Single issue object (wrapped in array)
 */

import * as fs from 'node:fs/promises';
import * as path from 'node:path';
import type { RawIssue } from '../queue-types.js';
import type { Tracker } from './tracker.js';

export class LocalJsonTracker implements Tracker {
  constructor(
    private sourceFile: string,
    private configDir: string,
  ) {}

  async fetchRawIssues(): Promise<RawIssue[]> {
    const filePath = path.resolve(this.configDir, this.sourceFile);

    let raw: string;
    try {
      raw = await fs.readFile(filePath, 'utf8');
    } catch {
      return [];
    }

    const decoded = JSON.parse(raw) as unknown;

    // Array of issues
    if (Array.isArray(decoded)) {
      return decoded as RawIssue[];
    }

    // Object with issues/tasks array
    if (typeof decoded === 'object' && decoded !== null) {
      const obj = decoded as Record<string, unknown>;
      if (Array.isArray(obj.issues)) return obj.issues as RawIssue[];
      if (Array.isArray(obj.tasks)) return obj.tasks as RawIssue[];
      // Single issue object
      return [obj as RawIssue];
    }

    return [];
  }
}
