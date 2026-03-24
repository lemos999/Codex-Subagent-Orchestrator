import { describe, it, expect, afterEach } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { Scanner } from '../../src/core/scanner.js';

describe('Scanner', () => {
  let tmpDir: string;

  afterEach(() => {
    if (tmpDir && fs.existsSync(tmpDir)) {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    }
  });

  // --- shouldExclude tests ---

  describe('shouldExclude', () => {
    it('should exclude default patterns (node_modules, .git, dist)', () => {
      const scanner = new Scanner();
      expect(scanner.shouldExclude('node_modules/foo/bar.js')).toBe(true);
      expect(scanner.shouldExclude('.git/HEAD')).toBe(true);
      expect(scanner.shouldExclude('dist/index.js')).toBe(true);
      expect(scanner.shouldExclude('.knowledge/file-map.json')).toBe(true);
    });

    it('should exclude user-added patterns', () => {
      const scanner = new Scanner(['coverage/**', '**/*.log']);
      expect(scanner.shouldExclude('coverage/lcov.info')).toBe(true);
      expect(scanner.shouldExclude('logs/app.log')).toBe(true);
    });

    it('should not exclude files that do not match any pattern', () => {
      const scanner = new Scanner();
      expect(scanner.shouldExclude('src/index.ts')).toBe(false);
      expect(scanner.shouldExclude('README.md')).toBe(false);
      expect(scanner.shouldExclude('package.json')).toBe(false);
    });
  });

  // --- scan tests ---

  describe('scan', () => {
    it('should scan files from a temporary directory', () => {
      tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'wki-test-'));
      fs.writeFileSync(path.join(tmpDir, 'index.ts'), 'export const a = 1;');
      fs.mkdirSync(path.join(tmpDir, 'lib'));
      fs.writeFileSync(path.join(tmpDir, 'lib', 'util.js'), 'module.exports = {};');

      const scanner = new Scanner();
      const entries = scanner.scan(tmpDir);

      expect(entries.length).toBe(2);
      const paths = entries.map((e) => e.path).sort();
      expect(paths).toEqual(['index.ts', 'lib/util.js']);
    });

    it('should apply exclude patterns during scan', () => {
      tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'wki-test-'));
      fs.writeFileSync(path.join(tmpDir, 'app.ts'), 'const x = 1;');
      fs.mkdirSync(path.join(tmpDir, 'build'));
      fs.writeFileSync(path.join(tmpDir, 'build', 'out.js'), 'var x = 1;');

      const scanner = new Scanner(['build/**']);
      const entries = scanner.scan(tmpDir);

      expect(entries.length).toBe(1);
      expect(entries[0]!.path).toBe('app.ts');
    });

    it('should return POSIX-normalized paths', () => {
      tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'wki-test-'));
      fs.mkdirSync(path.join(tmpDir, 'src', 'core'), { recursive: true });
      fs.writeFileSync(path.join(tmpDir, 'src', 'core', 'main.ts'), '// main');

      const scanner = new Scanner();
      const entries = scanner.scan(tmpDir);

      expect(entries.length).toBe(1);
      expect(entries[0]!.path).toBe('src/core/main.ts');
      expect(entries[0]!.path).not.toContain('\\');
    });
  });
});
