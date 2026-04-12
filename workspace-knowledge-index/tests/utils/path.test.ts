import { describe, it, expect } from 'vitest';
import path from 'node:path';
import { normalizePath, toIndexPath, toRelativePosix } from '../../src/utils/path.js';

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

describe('toIndexPath', () => {
  it('should keep already-relative paths idempotent', () => {
    expect(toIndexPath('/project/root', './src\\index.ts')).toBe('src/index.ts');
  });

  it('should convert absolute paths inside the project root to relative POSIX paths', () => {
    const projectRoot = path.join('/tmp', 'project');
    const filePath = path.join(projectRoot, 'src', 'index.ts');

    expect(toIndexPath(projectRoot, filePath)).toBe('src/index.ts');
  });

  it('should convert legacy Windows absolute rows under the project root', () => {
    const projectRoot = 'C:/Users/haj/projects/subagent-orchestrator';
    const filePath = 'C:\\Users\\haj\\projects\\subagent-orchestrator\\Projects\\vibe-web\\app\\page.tsx';

    expect(toIndexPath(projectRoot, filePath)).toBe('Projects/vibe-web/app/page.tsx');
  });
});
