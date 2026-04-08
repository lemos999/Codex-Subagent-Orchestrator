/**
 * Shared extension-to-type mapping used by Scanner, FileMap, and FtsStore.
 * Single source of truth to avoid EXTENSION_TYPE_MAP duplication.
 */
export const EXTENSION_TYPE_MAP: Record<string, string> = {
  '.ts': 'typescript',
  '.tsx': 'typescript',
  '.mts': 'typescript',
  '.cts': 'typescript',
  '.js': 'javascript',
  '.jsx': 'javascript',
  '.mjs': 'javascript',
  '.cjs': 'javascript',
  '.md': 'markdown',
  '.mdx': 'markdown',
  '.json': 'json',
};

/**
 * Reverse mapping: type name -> suffixes.
 * Used by FtsStore for file type filtering in search queries.
 */
export const FILE_TYPE_SUFFIXES: Record<string, string[]> = {
  typescript: ['.ts', '.tsx', '.mts', '.cts'],
  javascript: ['.js', '.jsx', '.mjs', '.cjs'],
  markdown: ['.md', '.mdx'],
  json: ['.json'],
};

// ============================================================
// Source Type Classification
// ============================================================

import type { SourceType } from '../types/index.js';
import * as path from 'path';

/** Config file names that should be classified as 'config'. */
const CONFIG_FILENAMES = new Set([
  'CLAUDE.md',
  'AGENTS.md',
]);

/** Extensions for code files. */
const CODE_EXTENSIONS = new Set([
  '.ts', '.tsx', '.js', '.jsx', '.py', '.rs', '.go',
  '.java', '.c', '.cpp', '.h', '.mts', '.cts', '.mjs', '.cjs',
]);

/**
 * Classify a file path into a source type category.
 * Priority: status > config > code > doc > other
 */
export function classifySourceType(filePath: string): SourceType {
  const normalized = filePath.replace(/\\/g, '/');
  const basename = path.basename(normalized);
  const ext = path.extname(basename).toLowerCase();

  // 1. project-status/ path → 'status'
  if (normalized.includes('project-status/')) {
    return 'status';
  }

  // 2. Known config filenames
  if (CONFIG_FILENAMES.has(basename)) {
    return 'config';
  }

  // 2b. Config-like extensions: *.config.*, settings*.json, wki.config.json, *.json in root-like patterns
  if (basename.includes('.config.')) {
    return 'config';
  }
  if (/^settings.*\.json$/i.test(basename)) {
    return 'config';
  }
  if (ext === '.json') {
    return 'config';
  }

  // 3. Code extensions
  if (CODE_EXTENSIONS.has(ext)) {
    return 'code';
  }

  // 4. Markdown (not config) → 'doc'
  if (ext === '.md' || ext === '.mdx') {
    return 'doc';
  }

  // 5. Everything else
  return 'other';
}
