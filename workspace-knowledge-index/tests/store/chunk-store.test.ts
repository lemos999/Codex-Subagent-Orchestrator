import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import Database from 'better-sqlite3';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { ChunkStore } from '../../src/store/chunk-store.js';
import type { Chunk } from '../../src/types/index.js';

describe('ChunkStore', () => {
  let tempDir: string;
  let dbPath: string;
  let db: Database.Database;
  let store: ChunkStore;

  beforeEach(() => {
    tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'wki-test-'));
    dbPath = path.join(tempDir, 'chunks.db');
    db = new Database(dbPath);
    store = new ChunkStore(db);
  });

  afterEach(() => {
    db.close();

    if (fs.existsSync(tempDir)) {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
  });

  it('upserts chunks and retrieves them by row id', () => {
    store.upsert([
      makeChunk({
        projectId: 'alpha',
        filePath: 'src/a.ts',
        ordinal: 0,
        heading: 'alphaChunk',
        content: 'alpha content',
        chunkType: 'function',
        contentHash: 'hash-alpha',
      }),
    ]);

    const row = db
      .prepare('SELECT id FROM chunks_meta WHERE file_path = ? AND ordinal = ?')
      .get('src/a.ts', 0) as { id: number } | undefined;

    expect(row).toBeDefined();
    expect(store.getById(row!.id)).toMatchObject({
      id: 'hash-alpha',
      rowId: row!.id,
      filePath: 'src/a.ts',
      ordinal: 0,
    });
  });

  it('returns chunks for a file ordered by ordinal', () => {
    store.upsert([
      makeChunk({
        projectId: 'alpha',
        filePath: 'src/a.ts',
        ordinal: 1,
        heading: 'second',
        content: 'second chunk',
        chunkType: 'class',
        contentHash: 'hash-second',
      }),
      makeChunk({
        projectId: 'alpha',
        filePath: 'src/a.ts',
        ordinal: 0,
        heading: 'first',
        content: 'first chunk',
        chunkType: 'function',
        contentHash: 'hash-first',
      }),
    ]);

    const chunks = store.getByFilePath('src/a.ts');

    expect(chunks.map((chunk) => chunk.contentHash)).toEqual(['hash-first', 'hash-second']);
  });

  it('deletes all chunks for a file path', () => {
    store.upsert([
      makeChunk({
        projectId: 'alpha',
        filePath: 'src/a.ts',
        ordinal: 0,
        heading: 'one',
        content: 'first chunk',
        chunkType: 'function',
        contentHash: 'hash-one',
      }),
      makeChunk({
        projectId: 'alpha',
        filePath: 'src/a.ts',
        ordinal: 1,
        heading: 'two',
        content: 'second chunk',
        chunkType: 'class',
        contentHash: 'hash-two',
      }),
    ]);

    store.deleteByFilePath('src/a.ts');

    expect(store.getByFilePath('src/a.ts')).toEqual([]);
  });

  it('counts the total number of stored chunks', () => {
    store.upsert([
      makeChunk({
        projectId: 'alpha',
        filePath: 'src/a.ts',
        ordinal: 0,
        heading: 'a',
        content: 'alpha',
        chunkType: 'function',
        contentHash: 'hash-a',
      }),
      makeChunk({
        projectId: 'beta',
        filePath: 'src/b.ts',
        ordinal: 0,
        heading: 'b',
        content: 'beta',
        chunkType: 'interface',
        contentHash: 'hash-b',
      }),
      makeChunk({
        projectId: 'beta',
        filePath: 'src/c.ts',
        ordinal: 0,
        heading: 'c',
        content: 'gamma',
        chunkType: 'type',
        contentHash: 'hash-c',
      }),
    ]);

    expect(store.count()).toBe(3);
  });

  it('retrieves batches by row ids and preserves requested order', () => {
    store.upsert([
      makeChunk({
        projectId: 'alpha',
        filePath: 'src/a.ts',
        ordinal: 0,
        heading: 'first',
        content: 'first chunk',
        chunkType: 'function',
        contentHash: 'hash-first',
      }),
      makeChunk({
        projectId: 'alpha',
        filePath: 'src/b.ts',
        ordinal: 0,
        heading: 'second',
        content: 'second chunk',
        chunkType: 'class',
        contentHash: 'hash-second',
      }),
    ]);

    const rows = db
      .prepare('SELECT id, file_path FROM chunks_meta ORDER BY file_path ASC')
      .all() as Array<{ id: number; file_path: string }>;

    const batch = store.getByIds([rows[1]!.id, rows[0]!.id]);

    expect(Array.from(batch.keys())).toEqual([rows[1]!.id, rows[0]!.id]);
    expect(Array.from(batch.values()).map((chunk) => chunk.contentHash)).toEqual(['hash-second', 'hash-first']);
  });

  function makeChunk(overrides: {
    projectId: string;
    filePath: string;
    ordinal: number;
    heading: string;
    content: string;
    chunkType: Chunk['chunkType'];
    contentHash: string;
  }): Chunk {
    return {
      id: overrides.contentHash,
      rowId: 0,
      projectId: overrides.projectId,
      filePath: overrides.filePath,
      ordinal: overrides.ordinal,
      heading: overrides.heading,
      content: overrides.content,
      chunkType: overrides.chunkType,
      startLine: 1,
      endLine: 5,
      tokenCount: overrides.content.split(/\s+/u).filter(Boolean).length,
      contentHash: overrides.contentHash,
    };
  }
});
