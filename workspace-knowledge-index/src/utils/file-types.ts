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
