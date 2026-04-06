import Database from 'better-sqlite3';
import type { Chunk } from '../types/index.js';
import {
  CHUNK_META_UPSERT_SQL,
  type ChunkMetaRow,
  configureStoreDatabase,
  initializeStoreSchema,
  mapChunkMetaRowToChunk,
  toChunkMetaParams,
} from './fts-store.js';

export class ChunkStore {
  constructor(private readonly db: Database.Database) {
    configureStoreDatabase(this.db);
    initializeStoreSchema(this.db);
  }

  getById(id: number): Chunk | null {
    const row = this.db
      .prepare(
        `
          SELECT
            id,
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
          FROM chunks_meta
          WHERE id = ?
        `,
      )
      .get(id) as ChunkMetaRow | undefined;

    return row ? mapChunkMetaRowToChunk(row) : null;
  }

  getByIds(ids: number[]): Map<number, Chunk> {
    const normalizedIds = Array.from(new Set(ids.filter((id) => Number.isInteger(id) && id > 0)));
    if (normalizedIds.length === 0) {
      return new Map();
    }

    // Batch in groups to stay under SQLITE_MAX_VARIABLE_NUMBER (999)
    const BATCH_SIZE = 999;
    const found = new Map<number, Chunk>();

    for (let offset = 0; offset < normalizedIds.length; offset += BATCH_SIZE) {
      const batch = normalizedIds.slice(offset, offset + BATCH_SIZE);
      const placeholders = batch.map(() => '?').join(', ');
      const rows = this.db
        .prepare(
          `
            SELECT
              id,
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
            FROM chunks_meta
            WHERE id IN (${placeholders})
          `,
        )
        .all(...batch) as ChunkMetaRow[];

      for (const row of rows) {
        found.set(row.id, mapChunkMetaRowToChunk(row));
      }
    }

    const ordered = new Map<number, Chunk>();
    for (const id of normalizedIds) {
      const chunk = found.get(id);
      if (chunk) {
        ordered.set(id, chunk);
      }
    }

    return ordered;
  }

  getByFilePath(filePath: string): Chunk[] {
    const rows = this.db
      .prepare(
        `
          SELECT
            id,
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
          FROM chunks_meta
          WHERE file_path = ?
          ORDER BY ordinal ASC
        `,
      )
      .all(filePath) as ChunkMetaRow[];

    return rows.map((row) => mapChunkMetaRowToChunk(row));
  }

  getByProjectId(projectId: string): Chunk[] {
    const rows = this.db
      .prepare(
        `
          SELECT
            id,
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
          FROM chunks_meta
          WHERE project_id = ?
          ORDER BY file_path ASC, ordinal ASC
        `,
      )
      .all(projectId) as ChunkMetaRow[];

    return rows.map((row) => mapChunkMetaRowToChunk(row));
  }

  upsert(chunks: Chunk[]): void {
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
  }

  deleteByFilePath(filePath: string): void {
    this.db.prepare('DELETE FROM chunks_meta WHERE file_path = ?').run(filePath);
  }

  deleteByProjectId(projectId: string): void {
    this.db.prepare('DELETE FROM chunks_meta WHERE project_id = ?').run(projectId);
  }

  /**
   * Get chunk boundaries for a file (no content — lightweight).
   * Useful for Rule #7 (File Read Budget): agents can see where chunks start/end
   * to plan precise offset/limit reads.
   */
  getChunkMap(filePath: string): Array<{
    ordinal: number;
    heading: string | null;
    chunkType: string;
    startLine: number;
    endLine: number;
    tokenCount: number;
  }> {
    const rows = this.db
      .prepare(
        `
          SELECT ordinal, heading, chunk_type, start_line, end_line, token_count
          FROM chunks_meta
          WHERE file_path = ?
          ORDER BY ordinal ASC
        `,
      )
      .all(filePath) as Array<{
        ordinal: number;
        heading: string | null;
        chunk_type: string;
        start_line: number;
        end_line: number;
        token_count: number;
      }>;

    return rows.map(r => ({
      ordinal: r.ordinal,
      heading: r.heading,
      chunkType: r.chunk_type,
      startLine: r.start_line,
      endLine: r.end_line,
      tokenCount: r.token_count,
    }));
  }

  /**
   * Get chunk boundaries matching a file path substring.
   */
  getChunkMapByPathLike(pathSubstring: string): Array<{
    filePath: string;
    ordinal: number;
    heading: string | null;
    chunkType: string;
    startLine: number;
    endLine: number;
    tokenCount: number;
  }> {
    const rows = this.db
      .prepare(
        `
          SELECT file_path, ordinal, heading, chunk_type, start_line, end_line, token_count
          FROM chunks_meta
          WHERE file_path LIKE ?
          ORDER BY file_path ASC, ordinal ASC
        `,
      )
      .all(`%${pathSubstring}%`) as Array<{
        file_path: string;
        ordinal: number;
        heading: string | null;
        chunk_type: string;
        start_line: number;
        end_line: number;
        token_count: number;
      }>;

    return rows.map(r => ({
      filePath: r.file_path,
      ordinal: r.ordinal,
      heading: r.heading,
      chunkType: r.chunk_type,
      startLine: r.start_line,
      endLine: r.end_line,
      tokenCount: r.token_count,
    }));
  }

  count(): number {
    const row = this.db.prepare('SELECT COUNT(*) AS count FROM chunks_meta').get() as
      | { count: number }
      | undefined;

    return row?.count ?? 0;
  }
}
