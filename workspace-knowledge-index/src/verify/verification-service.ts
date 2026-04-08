import fs from 'node:fs';
import path from 'node:path';
import Database from 'better-sqlite3';

export interface VerifyMatch {
  filePath: string;
  line?: number;
  snippet?: string;
}

export interface VerifyResult {
  exists: boolean;
  type: 'file' | 'symbol' | 'path';
  matches: VerifyMatch[];
  confidence: 'exact' | 'fuzzy';
}

interface MetaRow {
  file_path: string;
  start_line: number | null;
  end_line: number | null;
  content: string;
  chunk_type: string | null;
  heading: string | null;
}

/**
 * Lightweight entity-existence verification against the FTS5 database.
 * Read-only access only -- never modifies the index.
 */
export class VerificationService {
  private db: Database.Database;

  constructor(private ftsDbPath: string) {
    if (!fs.existsSync(ftsDbPath)) {
      throw new Error(`FTS database not found: ${ftsDbPath}. Run "wki index" first.`);
    }
    this.db = new Database(ftsDbPath, { readonly: true });
    this.db.pragma('busy_timeout = 3000');
  }

  close(): void {
    this.db.close();
  }

  /**
   * Verify whether a file exists in the index (and optionally on disk).
   * Accepts partial paths like "core/indexer.ts".
   */
  verifyFile(query: string): VerifyResult {
    const normalizedQuery = query.replace(/\\/g, '/');

    // 1. Exact match in chunks_meta
    const exactRows = this.db.prepare(
      `SELECT DISTINCT file_path FROM chunks_meta WHERE file_path = ?`,
    ).all(normalizedQuery) as Array<{ file_path: string }>;

    if (exactRows.length > 0) {
      return {
        exists: true,
        type: 'file',
        matches: exactRows.map((r) => ({ filePath: r.file_path })),
        confidence: 'exact',
      };
    }

    // 2. LIKE match for partial paths
    const likePattern = `%${normalizedQuery}%`;
    const likeRows = this.db.prepare(
      `SELECT DISTINCT file_path FROM chunks_meta WHERE file_path LIKE ? LIMIT 20`,
    ).all(likePattern) as Array<{ file_path: string }>;

    if (likeRows.length > 0) {
      // Check if any match ends with the query (suffix match = higher confidence)
      const suffixMatches = likeRows.filter((r) =>
        r.file_path.replace(/\\/g, '/').endsWith(normalizedQuery),
      );
      const isExact = suffixMatches.length > 0;

      return {
        exists: true,
        type: 'file',
        matches: (isExact ? suffixMatches : likeRows).map((r) => ({
          filePath: r.file_path,
        })),
        confidence: isExact ? 'exact' : 'fuzzy',
      };
    }

    return { exists: false, type: 'file', matches: [], confidence: 'fuzzy' };
  }

  /**
   * Verify whether a symbol (function, class, type, etc.) exists in the index.
   * Uses FTS5 MATCH for content search, then filters for symbol-like chunk types.
   */
  verifySymbol(query: string): VerifyResult {
    const symbolChunkTypes = new Set([
      'function', 'class', 'interface', 'type', 'enum', 'variable', 'export',
    ]);

    // Detect if query looks like a symbol (camelCase, snake_case, PascalCase)
    const isSymbolLike = /^[a-zA-Z_$][a-zA-Z0-9_$]*$/.test(query);

    // FTS5 MATCH query -- quote to handle special chars
    const ftsQuery = `"${query.replace(/"/g, '""')}"`;

    let rows: MetaRow[];
    try {
      rows = this.db.prepare(`
        SELECT m.file_path, m.start_line, m.end_line, m.content, m.chunk_type, m.heading
        FROM chunks_meta m
        JOIN chunks_fts f ON f.rowid = m.id
        WHERE chunks_fts MATCH ?
        LIMIT 50
      `).all(ftsQuery) as MetaRow[];
    } catch {
      // FTS match can fail on certain inputs; fall back to LIKE
      rows = this.db.prepare(`
        SELECT file_path, start_line, end_line, content, chunk_type, heading
        FROM chunks_meta
        WHERE content LIKE ?
        LIMIT 50
      `).all(`%${query}%`) as MetaRow[];
    }

    if (rows.length === 0) {
      return { exists: false, type: 'symbol', matches: [], confidence: 'fuzzy' };
    }

    // Prefer symbol-typed chunks, then fall back to all matches
    const symbolRows = rows.filter((r) => r.chunk_type && symbolChunkTypes.has(r.chunk_type));
    const resultRows = symbolRows.length > 0 ? symbolRows : rows;

    // Extract the most relevant line within the chunk
    const matches: VerifyMatch[] = resultRows.slice(0, 10).map((r) => {
      const match: VerifyMatch = { filePath: r.file_path };

      // Find the exact line containing the symbol within the chunk
      if (r.content && r.start_line != null) {
        const lines = r.content.split('\n');
        for (let i = 0; i < lines.length; i++) {
          if (lines[i].includes(query)) {
            match.line = r.start_line + i;
            match.snippet = lines[i].trim().slice(0, 120);
            break;
          }
        }
        // If no exact line match, just use start_line
        if (match.line == null) {
          match.line = r.start_line;
        }
      }

      return match;
    });

    const confidence = isSymbolLike && symbolRows.length > 0 ? 'exact' : 'fuzzy';

    return { exists: true, type: 'symbol', matches, confidence };
  }

  /**
   * Verify what files exist under a given path pattern.
   * E.g., "project-status/" returns all indexed files in that directory.
   */
  verifyPath(pattern: string): VerifyResult {
    const normalizedPattern = pattern.replace(/\\/g, '/').replace(/\/+$/, '');
    const likePattern = `%${normalizedPattern}/%`;

    const rows = this.db.prepare(
      `SELECT DISTINCT file_path FROM chunks_meta WHERE file_path LIKE ? ORDER BY file_path LIMIT 100`,
    ).all(likePattern) as Array<{ file_path: string }>;

    if (rows.length === 0) {
      // Try without trailing slash for exact directory name match
      const broadPattern = `%${normalizedPattern}%`;
      const broadRows = this.db.prepare(
        `SELECT DISTINCT file_path FROM chunks_meta WHERE file_path LIKE ? ORDER BY file_path LIMIT 100`,
      ).all(broadPattern) as Array<{ file_path: string }>;

      if (broadRows.length === 0) {
        return { exists: false, type: 'path', matches: [], confidence: 'fuzzy' };
      }

      return {
        exists: true,
        type: 'path',
        matches: broadRows.map((r) => ({ filePath: r.file_path })),
        confidence: 'fuzzy',
      };
    }

    return {
      exists: true,
      type: 'path',
      matches: rows.map((r) => ({ filePath: r.file_path })),
      confidence: 'exact',
    };
  }

  /**
   * Auto-detect query type and dispatch to the appropriate method.
   */
  autoVerify(query: string): VerifyResult {
    // If it looks like a path (contains / or \, or ends with a known extension)
    if (query.includes('/') || query.includes('\\')) {
      // If it ends with / it's a directory pattern
      if (query.endsWith('/') || query.endsWith('\\')) {
        return this.verifyPath(query);
      }
      // If it has a file extension, treat as file
      if (path.extname(query)) {
        return this.verifyFile(query);
      }
      // Could be a directory path without trailing slash
      return this.verifyPath(query);
    }

    // If it has a file extension, treat as file
    if (path.extname(query)) {
      return this.verifyFile(query);
    }

    // Default: treat as symbol
    return this.verifySymbol(query);
  }
}
