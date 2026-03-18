import fs from 'node:fs';
import path from 'node:path';
import type { FileMapEntry } from '../types/index.js';
import { normalizePath } from '../utils/path.js';
import { EXTENSION_TYPE_MAP } from '../utils/file-types.js';
import { Scanner } from './scanner.js';

interface FileMapJson {
  version: number;
  root: string;
  generatedAt: string;
  files: FileMapEntry[];
}

/**
 * Manages the file-map.json that tracks all indexed files in a project.
 */
export class FileMap {
  private entries: Map<string, FileMapEntry> = new Map();
  private rootDir: string = '';

  /**
   * Generate a complete file map by scanning the project directory.
   */
  generate(rootDir: string, excludePatterns?: string[]): void {
    this.rootDir = path.resolve(rootDir);
    const scanner = new Scanner(excludePatterns);
    const scanned = scanner.scan(this.rootDir);
    this.entries.clear();
    for (const entry of scanned) {
      this.entries.set(entry.path, entry);
    }
  }

  /**
   * Incrementally update the file map with changed files only.
   * @param rootDir - Project root directory
   * @param changedPaths - List of changed file paths (POSIX relative)
   * @param excludePatterns - Glob patterns to exclude
   */
  update(rootDir: string, changedPaths: string[], excludePatterns?: string[]): void {
    const resolvedRoot = path.resolve(rootDir);
    const scanner = new Scanner(excludePatterns);

    for (const relPath of changedPaths) {
      const normalized = normalizePath(relPath);

      // If excluded, remove from entries if present
      if (scanner.shouldExclude(normalized)) {
        this.entries.delete(normalized);
        continue;
      }

      const fullPath = path.join(resolvedRoot, normalized);

      // Check if file exists; if not, it was deleted
      if (!fs.existsSync(fullPath)) {
        this.entries.delete(normalized);
        continue;
      }

      try {
        const stat = fs.statSync(fullPath);
        if (!stat.isFile()) {
          this.entries.delete(normalized);
          continue;
        }

        const ext = path.extname(normalized).toLowerCase();
        const type = EXTENSION_TYPE_MAP[ext] ?? 'other';

        this.entries.set(normalized, { path: normalized, size: stat.size, type });
      } catch {
        // File inaccessible; remove it
        this.entries.delete(normalized);
      }
    }
  }

  /**
   * Save the current file map to a JSON file.
   */
  save(filePath: string): void {
    const data: FileMapJson = {
      version: 1,
      root: path.basename(this.rootDir || '.'),
      generatedAt: new Date().toISOString(),
      files: Array.from(this.entries.values()),
    };

    const dir = path.dirname(filePath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }

    fs.writeFileSync(filePath, JSON.stringify(data, null, 2), 'utf-8');
  }

  /**
   * Load file map from a JSON file.
   */
  load(filePath: string): void {
    try {
      const content = fs.readFileSync(filePath, 'utf-8');
      const data = JSON.parse(content) as FileMapJson;
      this.entries.clear();
      for (const entry of data.files) {
        this.entries.set(entry.path, entry);
      }
    } catch {
      // File does not exist or is invalid; start fresh
      this.entries.clear();
    }
  }

  /** Get a single entry by path. */
  getEntry(entryPath: string): FileMapEntry | undefined {
    return this.entries.get(entryPath);
  }

  /** Get all entries as an array. */
  getEntries(): FileMapEntry[] {
    return Array.from(this.entries.values());
  }

  /** Number of entries in the file map. */
  get size(): number {
    return this.entries.size;
  }
}
