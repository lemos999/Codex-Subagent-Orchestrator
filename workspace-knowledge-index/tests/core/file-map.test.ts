import { describe, it, expect, afterEach } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { FileMap } from '../../src/core/file-map.js';

describe('FileMap', () => {
  let tmpDir: string;

  afterEach(() => {
    if (tmpDir && fs.existsSync(tmpDir)) {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    }
  });

  it('should generate a file map from a temporary directory', () => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'wki-test-'));
    fs.writeFileSync(path.join(tmpDir, 'a.ts'), 'export const a = 1;');
    fs.writeFileSync(path.join(tmpDir, 'b.md'), '# Hello');

    const fm = new FileMap();
    fm.generate(tmpDir);

    expect(fm.size).toBe(2);
    const entry = fm.getEntry('a.ts');
    expect(entry).toBeDefined();
    expect(entry!.type).toBe('typescript');
  });

  it('should save and load (round-trip) via JSON', () => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'wki-test-'));
    fs.writeFileSync(path.join(tmpDir, 'index.ts'), 'const x = 1;');

    const fm = new FileMap();
    fm.generate(tmpDir);

    const jsonPath = path.join(tmpDir, 'file-map.json');
    fm.save(jsonPath);

    const fm2 = new FileMap();
    fm2.load(jsonPath);

    expect(fm2.size).toBe(fm.size);
    expect(fm2.getEntry('index.ts')).toBeDefined();
    expect(fm2.getEntry('index.ts')!.type).toBe('typescript');
  });

  it('should update changed files incrementally', () => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'wki-test-'));
    fs.writeFileSync(path.join(tmpDir, 'a.ts'), 'const a = 1;');
    fs.writeFileSync(path.join(tmpDir, 'b.ts'), 'const b = 2;');

    const fm = new FileMap();
    fm.generate(tmpDir);
    expect(fm.size).toBe(2);

    // Add a new file and update
    fs.writeFileSync(path.join(tmpDir, 'c.ts'), 'const c = 3;');
    fm.update(tmpDir, ['c.ts']);
    expect(fm.size).toBe(3);
    expect(fm.getEntry('c.ts')).toBeDefined();
  });

  it('should support getEntry and getEntries', () => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'wki-test-'));
    fs.writeFileSync(path.join(tmpDir, 'x.json'), '{}');
    fs.writeFileSync(path.join(tmpDir, 'y.md'), '# Y');

    const fm = new FileMap();
    fm.generate(tmpDir);

    expect(fm.getEntry('x.json')!.type).toBe('json');
    expect(fm.getEntry('y.md')!.type).toBe('markdown');
    expect(fm.getEntries().length).toBe(2);
  });

  it('should report correct size', () => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'wki-test-'));
    fs.writeFileSync(path.join(tmpDir, 'one.ts'), 'a');

    const fm = new FileMap();
    fm.generate(tmpDir);
    expect(fm.size).toBe(1);
  });

  it('should handle an empty directory', () => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'wki-test-'));

    const fm = new FileMap();
    fm.generate(tmpDir);
    expect(fm.size).toBe(0);
    expect(fm.getEntries()).toEqual([]);
  });
});
