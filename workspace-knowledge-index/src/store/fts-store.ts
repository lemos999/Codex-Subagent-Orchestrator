import fs from 'node:fs';
import path from 'node:path';
import Database from 'better-sqlite3';
import type { FtsBackend, FtsSearchResult } from '../interfaces/fts-backend.js';
import type { Chunk, ChunkType, SearchFilter } from '../types/index.js';
import { FILE_TYPE_SUFFIXES } from '../utils/file-types.js';

const CHUNK_TYPE_VALUES = new Set<ChunkType>([
  'function',
  'class',
  'interface',
  'type',
  'enum',
  'variable',
  'import',
  'export',
  'markdown-section',
  'line-block',
  'other',
]);

export interface ChunkMetaRow {
  id: number;
  project_id: string;
  file_path: string;
  ordinal: number;
  heading: string | null;
  content: string;
  chunk_type: string | null;
  start_line: number | null;
  end_line: number | null;
  token_count: number | null;
  content_hash: string | null;
}

export interface ChunkMetaStatementParams {
  projectId: string;
  filePath: string;
  ordinal: number;
  heading: string | null;
  content: string;
  chunkType: string | null;
  startLine: number | null;
  endLine: number | null;
  tokenCount: number | null;
  contentHash: string | null;
}

interface SearchRow {
  chunk_id: string;
  score: number;
  content_highlight: string | null;
  heading_highlight: string | null;
}

export const CHUNK_META_UPSERT_SQL = `
  INSERT INTO chunks_meta (
    project_id,
    file_path,
    ordinal,
    heading,
    content,
    chunk_type,
    start_line,
    end_line,
    token_count,
    content_hash
  )
  VALUES (
    @projectId,
    @filePath,
    @ordinal,
    @heading,
    @content,
    @chunkType,
    @startLine,
    @endLine,
    @tokenCount,
    @contentHash
  )
  ON CONFLICT(file_path, ordinal) DO UPDATE SET
    project_id = excluded.project_id,
    heading = excluded.heading,
    content = excluded.content,
    chunk_type = excluded.chunk_type,
    start_line = excluded.start_line,
    end_line = excluded.end_line,
    token_count = excluded.token_count,
    content_hash = excluded.content_hash
`;

const STORE_SCHEMA_SQL = `
  CREATE TABLE IF NOT EXISTS chunks_meta (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id   TEXT NOT NULL DEFAULT '',
    file_path    TEXT NOT NULL,
    ordinal      INTEGER NOT NULL,
    heading      TEXT,
    content      TEXT NOT NULL,
    chunk_type   TEXT,
    start_line   INTEGER,
    end_line     INTEGER,
    token_count  INTEGER,
    content_hash TEXT,
    UNIQUE(file_path, ordinal)
  );

  CREATE INDEX IF NOT EXISTS idx_chunks_meta_path ON chunks_meta(file_path);
  CREATE INDEX IF NOT EXISTS idx_chunks_meta_type ON chunks_meta(chunk_type);
  CREATE INDEX IF NOT EXISTS idx_chunks_meta_hash ON chunks_meta(content_hash);
  CREATE INDEX IF NOT EXISTS idx_chunks_meta_project ON chunks_meta(project_id);

  CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    content,
    heading,
    content='chunks_meta',
    content_rowid='id',
    tokenize='unicode61'
  );

  CREATE TRIGGER IF NOT EXISTS chunks_meta_ai AFTER INSERT ON chunks_meta BEGIN
    INSERT INTO chunks_fts(rowid, content, heading)
    VALUES (new.id, new.content, new.heading);
  END;

  CREATE TRIGGER IF NOT EXISTS chunks_meta_ad AFTER DELETE ON chunks_meta BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, content, heading)
    VALUES ('delete', old.id, old.content, old.heading);
  END;

  CREATE TRIGGER IF NOT EXISTS chunks_meta_au AFTER UPDATE ON chunks_meta BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, content, heading)
    VALUES ('delete', old.id, old.content, old.heading);
    INSERT INTO chunks_fts(rowid, content, heading)
    VALUES (new.id, new.content, new.heading);
  END;
`;

export function configureStoreDatabase(db: Database.Database): void {
  db.pragma('journal_mode = WAL');
  db.pragma('foreign_keys = ON');
  db.pragma('busy_timeout = 5000');
}

export function initializeStoreSchema(db: Database.Database): void {
  db.exec(STORE_SCHEMA_SQL);
}

export function toChunkMetaParams(chunk: Chunk): ChunkMetaStatementParams {
  return {
    projectId: chunk.projectId,
    filePath: chunk.filePath,
    ordinal: chunk.ordinal,
    heading: chunk.heading ?? null,
    content: chunk.content,
    chunkType: chunk.chunkType ?? null,
    startLine: chunk.startLine,
    endLine: chunk.endLine,
    tokenCount: chunk.tokenCount,
    contentHash: chunk.contentHash || null,
  };
}

export function buildStoredChunkId(row: Pick<ChunkMetaRow, 'content_hash' | 'file_path' | 'ordinal'>): string {
  const storedHash = row.content_hash?.trim();
  if (storedHash) {
    return storedHash;
  }

  return `${row.file_path}:${row.ordinal}`;
}

export function mapChunkMetaRowToChunk(row: ChunkMetaRow): Chunk {
  return {
    id: buildStoredChunkId(row),
    rowId: row.id,
    projectId: row.project_id ?? '',
    filePath: row.file_path,
    ordinal: row.ordinal,
    heading: row.heading ?? undefined,
    content: row.content,
    chunkType: normalizeChunkType(row.chunk_type),
    startLine: row.start_line ?? 0,
    endLine: row.end_line ?? 0,
    tokenCount: row.token_count ?? 0,
    contentHash: row.content_hash ?? '',
  };
}

export interface FtsStoreOptions {
  readonly?: boolean;
}

export class FtsStore implements FtsBackend {
  private readonly db: Database.Database;
  private closed = false;
  private readonly readonlyMode: boolean;

  constructor(dbPath: string, options?: FtsStoreOptions) {
    this.readonlyMode = options?.readonly === true;

    if (this.readonlyMode) {
      // In readonly mode, if the DB doesn't exist, use an in-memory empty DB
      if (dbPath !== ':memory:' && !dbPath.startsWith('file:') && !fs.existsSync(dbPath)) {
        this.db = new Database(':memory:');
        configureStoreDatabase(this.db);
        initializeStoreSchema(this.db);
        return;
      }
      this.db = new Database(dbPath, { readonly: true });
    } else {
      ensureDatabaseDirectory(dbPath);
      this.db = new Database(dbPath);
      configureStoreDatabase(this.db);
      initializeStoreSchema(this.db);
    }
  }

  getDatabase(): Database.Database {
    this.assertOpen();
    return this.db;
  }

  insert(chunks: Chunk[]): Promise<void> {
    return Promise.resolve().then(() => {
      this.assertOpen();

      if (chunks.length === 0) {
        return;
      }

      const upsert = this.db.prepare(CHUNK_META_UPSERT_SQL);
      const transaction = this.db.transaction((items: Chunk[]) => {
        for (const chunk of items) {
          upsert.run(toChunkMetaParams(chunk));
        }
      });

      transaction(chunks);
    });
  }

  search(query: string, topK: number, filter?: SearchFilter): Promise<FtsSearchResult[]> {
    return Promise.resolve().then(() => {
      this.assertOpen();

      const matchQuery = buildFtsMatchExpression(query);
      const safeTopK = Number.isFinite(topK) ? Math.max(0, Math.trunc(topK)) : 0;

      if (!matchQuery || safeTopK === 0) {
        return [];
      }

      const whereClauses: string[] = ['chunks_fts MATCH ?'];
      const params: Array<string | number> = [matchQuery];

      if (filter?.projectId?.trim()) {
        whereClauses.push('chunks_meta.project_id = ?');
        params.push(filter.projectId.trim());
      }

      if (filter?.symbolKind?.trim()) {
        whereClauses.push('chunks_meta.chunk_type = ?');
        params.push(filter.symbolKind.trim());
      }

      if (filter?.fileType?.trim()) {
        const fileTypeFilter = buildFileTypeFilter(filter.fileType);
        whereClauses.push(fileTypeFilter.clause);
        params.push(...fileTypeFilter.params);
      }

      params.push(safeTopK);

      const sql = `
        SELECT
          CASE
            WHEN chunks_meta.content_hash IS NOT NULL AND chunks_meta.content_hash != ''
            THEN chunks_meta.file_path || '::' || chunks_meta.content_hash
            ELSE chunks_meta.file_path || ':' || chunks_meta.ordinal
          END AS chunk_id,
          bm25(chunks_fts, 1.0, 2.5) AS score,
          snippet(chunks_fts, 0, '[', ']', '...', 12) AS content_highlight,
          snippet(chunks_fts, 1, '[', ']', '...', 6) AS heading_highlight
        FROM chunks_fts
        JOIN chunks_meta ON chunks_meta.id = chunks_fts.rowid
        WHERE ${whereClauses.join(' AND ')}
        ORDER BY score ASC, chunks_meta.id ASC
        LIMIT ?
      `;

      const rows = this.db.prepare(sql).all(...params) as SearchRow[];

      return rows.map((row) => {
        const highlights = [row.heading_highlight, row.content_highlight].filter(
          (value): value is string => Boolean(value && value.trim()),
        );

        return {
          chunkId: row.chunk_id,
          score: row.score,
          highlights: highlights.length > 0 ? highlights : undefined,
        };
      });
    });
  }

  delete(chunkIds: string[]): Promise<void> {
    return Promise.resolve().then(() => {
      this.assertOpen();

      const normalizedIds = Array.from(
        new Set(chunkIds.map((chunkId) => chunkId.trim()).filter((chunkId) => chunkId.length > 0)),
      );

      if (normalizedIds.length === 0) {
        return;
      }

      // #6: Batch in groups to stay under SQLITE_MAX_VARIABLE_NUMBER (999)
      const BATCH_SIZE = 300; // Each ID appears in up to 3 conditions, so 300 * 3 = 900 < 999
      for (let offset = 0; offset < normalizedIds.length; offset += BATCH_SIZE) {
        const batch = normalizedIds.slice(offset, offset + BATCH_SIZE);
        this.deleteBatch(batch);
      }
    });
  }

  private deleteBatch(normalizedIds: string[]): void {
    const numericIds = Array.from(
      new Set(
        normalizedIds
          .filter((chunkId) => /^\d+$/.test(chunkId))
          .map((chunkId) => Number.parseInt(chunkId, 10)),
      ),
    );

    const conditions: string[] = [];
    const params: Array<string | number> = [];
    const stringPlaceholders = normalizedIds.map(() => '?').join(', ');

    conditions.push(`content_hash IN (${stringPlaceholders})`);
    params.push(...normalizedIds);

    conditions.push(`(file_path || ':' || ordinal) IN (${stringPlaceholders})`);
    params.push(...normalizedIds);

    if (numericIds.length > 0) {
      const numericPlaceholders = numericIds.map(() => '?').join(', ');
      conditions.push(`id IN (${numericPlaceholders})`);
      params.push(...numericIds);
    }

    const sql = `DELETE FROM chunks_meta WHERE ${conditions.join(' OR ')}`;
    const statement = this.db.prepare(sql);
    const transaction = this.db.transaction((bindParams: Array<string | number>) => {
      statement.run(...bindParams);
    });

    transaction(params);
  }

  rebuild(): Promise<void> {
    return Promise.resolve().then(() => {
      this.assertOpen();
      initializeStoreSchema(this.db);
      this.db.prepare(`INSERT INTO chunks_fts(chunks_fts) VALUES ('rebuild')`).run();
    });
  }

  close(): Promise<void> {
    return Promise.resolve().then(() => {
      if (this.closed) {
        return;
      }

      this.db.close();
      this.closed = true;
    });
  }

  private assertOpen(): void {
    if (this.closed) {
      throw new Error('FtsStore is already closed');
    }
  }
}

function ensureDatabaseDirectory(dbPath: string): void {
  if (dbPath === ':memory:' || dbPath.startsWith('file:')) {
    return;
  }

  const directoryPath = path.dirname(path.resolve(dbPath));
  if (!fs.existsSync(directoryPath)) {
    fs.mkdirSync(directoryPath, { recursive: true });
  }
}

function normalizeChunkType(value: string | null): ChunkType {
  if (value && CHUNK_TYPE_VALUES.has(value as ChunkType)) {
    return value as ChunkType;
  }

  return 'other';
}

// Common words that rarely narrow search results when used with AND
const FTS_STOP_WORDS = new Set([
  'the', 'a', 'an', 'and', 'or', 'is', 'are', 'in', 'of', 'for', 'to',
  'how', 'does', 'what', 'where', 'why', 'do', 'it', 'be', 'at', 'by',
  'with', 'from', 'this', 'that', 'on', 'not', 'can', 'but', 'all',
  'writing', 'using', 'based', 'about', 'into', 'through', 'between',
]);

function buildFtsMatchExpression(query: string, operator: 'AND' | 'OR' = 'AND'): string {
  let tokens = query
    .trim()
    .split(/\s+/u)
    .map((token) => sanitizeFtsToken(token))
    .filter((token): token is string => token.length > 0);

  // For long AND queries, remove stop words to improve recall
  if (operator === 'AND' && tokens.length >= 4) {
    const filtered = tokens.filter(t => !FTS_STOP_WORDS.has(t.toLowerCase()));
    if (filtered.length >= 2) tokens = filtered;
  }


  if (tokens.length === 0) {
    return '';
  }

  return tokens.map((token) => `"${token}"`).join(` ${operator} `);
}

function sanitizeFtsToken(token: string): string {
  const trimmed = token.trim();
  if (!trimmed) {
    return '';
  }

  const stripped = trimmed.replace(/^[()[\]{}'"`]+|[()[\]{}'"`]+$/g, '');
  if (!/[\p{L}\p{N}_]/u.test(stripped)) {
    return '';
  }

  return stripped.replace(/"/g, '""');
}

function buildFileTypeFilter(fileType: string): { clause: string; params: string[] } {
  const normalized = fileType.trim().toLowerCase();
  const suffixes = FILE_TYPE_SUFFIXES[normalized] ?? [normalizeFileTypeSuffix(normalized)];

  return {
    clause: `(${suffixes.map(() => `chunks_meta.file_path LIKE ? ESCAPE '\\'`).join(' OR ')})`,
    params: suffixes.map((suffix) => `%${escapeLikeValue(suffix)}`),
  };
}

function normalizeFileTypeSuffix(fileType: string): string {
  if (fileType.startsWith('*.')) {
    return fileType.slice(1);
  }

  if (fileType.startsWith('.')) {
    return fileType;
  }

  return `.${fileType}`;
}

function escapeLikeValue(value: string): string {
  return value.replace(/[\\%_]/g, '\\$&');
}
