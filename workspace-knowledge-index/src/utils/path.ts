import path from 'node:path';

/** 모든 경로를 POSIX 스타일(/)로 정규화 */
export function normalizePath(filePath: string): string {
  return filePath.replace(/\\/g, '/').split(path.sep).join('/');
}

/** 상대 경로를 POSIX 정규화하여 반환 */
export function toRelativePosix(from: string, to: string): string {
  return normalizePath(path.relative(from, to));
}
