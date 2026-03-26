import fs from 'node:fs';
import path from 'node:path';
import picomatch from 'picomatch';
import type { FileMapEntry } from '../types/index.js';
import { normalizePath, toRelativePosix } from '../utils/path.js';
import { EXTENSION_TYPE_MAP } from '../utils/file-types.js';

const DEFAULT_EXCLUDES = [
  // Build/dependency artifacts
  '**/node_modules/**',
  '**/.git/**',
  '**/.next/**',
  '**/dist/**',
  '**/.npm-cache/**',
  '**/.pytest_cache/**',
  // WKI internal data
  '**/*.db',
  '**/*.lance',
  '**/.knowledge/**',
  // Run artifacts (regeneratable)
  '**/subagent-runs/**',
  '**/subagent-records/**',
  '**/tests/artifacts/**',
  // Discussion artifacts
  '**/discussions/**',
  '**/*.prompt.txt',
  '**/*.stdout.log',
  '**/*.stderr.log',
  '**/*.last.txt',
  '**/wki-context-snapshot.md',
  '**/personas.json',
  '**/auto-personas.md',
  // Archive/data (not source)
  '**/Projects/archive/**',
  '**/Projects/Trading Value/data/**',
  '**/Projects/vibe-web/node_modules/**',
  '**/Projects/vibe-web/.next/**',
  // Generated reports
  '**/game-design-director/reports/**',
  // Eval gold sets (self-reference)
  '**/eval/gold-set-*.json',
  // Large generated files
  '**/*.html',
  '**/package-lock.json',
  // Security: secrets and credentials
  '**/.env',
  '**/.env.*',
  '**/*.key',
  '**/*.pem',
  '**/*.p12',
  '**/*.pfx',
  '**/credentials.*',
  '**/secrets.*',
  '**/*secret*',
  '**/.aws/**',
  '**/.ssh/**',
];

/**
 * Scans a project directory tree, respecting gitignore and exclude patterns.
 */
export class Scanner {
  private excludePatterns: string[];
  private matcher: (input: string) => boolean;

  constructor(excludePatterns: string[] = []) {
    this.excludePatterns = [
      ...DEFAULT_EXCLUDES,
      ...excludePatterns,
    ];
    this.matcher = picomatch(this.excludePatterns, { dot: true });
  }

  /**
   * Scan the given directory and return all indexable files as FileMapEntry[].
   * @param rootDir - Project root directory
   */
  scan(rootDir: string): FileMapEntry[] {
    const resolvedRoot = path.resolve(rootDir);

    // Load .gitignore patterns if present
    const gitignorePatterns = this.loadGitignore(resolvedRoot);
    if (gitignorePatterns.length > 0) {
      const combined = [...this.excludePatterns, ...gitignorePatterns];
      this.matcher = picomatch(combined, { dot: true });
    }

    const entries: FileMapEntry[] = [];

    let dirents: fs.Dirent[];
    try {
      dirents = fs.readdirSync(resolvedRoot, {
        recursive: true,
        withFileTypes: true,
      });
    } catch (err) {
      console.error(`[scanner] Failed to read directory: ${resolvedRoot}`, err); // TODO: Phase 1B+ -- Logger 인터페이스 도입 후 교체
      return [];
    }

    for (const dirent of dirents) {
      if (!dirent.isFile()) continue;

      const fullPath = path.join(
        dirent.parentPath ?? dirent.path,
        dirent.name,
      );
      const relativePath = toRelativePosix(resolvedRoot, fullPath);

      if (this.shouldExclude(relativePath)) continue;

      let size = 0;
      try {
        size = fs.statSync(fullPath).size;
      } catch {
        // File may have been deleted between readdir and stat
        continue;
      }

      const ext = path.extname(dirent.name).toLowerCase();
      const type = EXTENSION_TYPE_MAP[ext] ?? 'other';

      entries.push({ path: relativePath, size, type });
    }

    return entries;
  }

  /**
   * Check if a file path should be excluded from indexing.
   * @param relativePath - POSIX-normalized relative file path
   */
  shouldExclude(relativePath: string): boolean {
    const normalized = normalizePath(relativePath);
    return this.matcher(normalized);
  }

  /**
   * Load .gitignore patterns from the project root.
   */
  private loadGitignore(rootDir: string): string[] {
    const gitignorePath = path.join(rootDir, '.gitignore');
    try {
      if (!fs.existsSync(gitignorePath)) return [];
      const content = fs.readFileSync(gitignorePath, 'utf-8');
      return content
        .split('\n')
        .map((line) => line.trim())
        .filter((line) => line.length > 0 && !line.startsWith('#'));
    } catch {
      return [];
    }
  }
}
