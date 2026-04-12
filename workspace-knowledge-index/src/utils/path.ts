import path from 'node:path';

/** 모든 경로를 POSIX 스타일(/)로 정규화 */
export function normalizePath(filePath: string): string {
  return filePath.replace(/\\/g, '/').split(path.sep).join('/').replace(/^\.\//, '');
}

/** 상대 경로를 POSIX 정규화하여 반환 */
export function toRelativePosix(from: string, to: string): string {
  return normalizePath(path.relative(from, to));
}

function isWindowsAbsolutePath(filePath: string): boolean {
  const normalized = normalizePath(filePath);
  return /^[A-Za-z]:\//.test(normalized) || normalized.startsWith('//');
}

function isAbsolutePath(filePath: string): boolean {
  return path.isAbsolute(filePath) || isWindowsAbsolutePath(filePath);
}

/**
 * Convert parser, scanner, and stored DB paths into the canonical index key.
 *
 * The index stores project-root-relative POSIX paths. This helper is idempotent
 * for already-relative paths and safely handles legacy Windows absolute rows.
 */
export function toIndexPath(projectRoot: string, filePath: string): string {
  const normalizedFile = normalizePath(filePath);
  if (!normalizedFile) {
    return normalizedFile;
  }

  if (!isAbsolutePath(filePath)) {
    return normalizedFile;
  }

  const normalizedRoot = normalizePath(path.resolve(projectRoot));
  const rootForCompare = normalizedRoot.toLowerCase();
  const fileForCompare = normalizedFile.toLowerCase();
  const rootPrefix = rootForCompare.endsWith('/') ? rootForCompare : `${rootForCompare}/`;

  if (fileForCompare === rootForCompare) {
    return '';
  }

  if (fileForCompare.startsWith(rootPrefix)) {
    return normalizedFile.slice(rootPrefix.length);
  }

  if (path.isAbsolute(filePath)) {
    const relativePath = normalizePath(path.relative(projectRoot, filePath));
    if (relativePath && !relativePath.startsWith('../') && relativePath !== '..') {
      return relativePath;
    }
  }

  return normalizedFile;
}
