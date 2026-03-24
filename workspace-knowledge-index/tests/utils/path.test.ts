import { describe, it, expect } from 'vitest';
import { normalizePath, toRelativePosix } from '../../src/utils/path.js';

describe('normalizePath', () => {
  it('should convert backslashes to forward slashes', () => {
    expect(normalizePath('src\\core\\scanner.ts')).toBe('src/core/scanner.ts');
  });

  it('should leave POSIX paths unchanged', () => {
    expect(normalizePath('src/core/scanner.ts')).toBe('src/core/scanner.ts');
  });
});

describe('toRelativePosix', () => {
  it('should return a POSIX-normalized relative path', () => {
    const result = toRelativePosix('/project/root', '/project/root/src/index.ts');
    expect(result).toBe('src/index.ts');
  });
});
