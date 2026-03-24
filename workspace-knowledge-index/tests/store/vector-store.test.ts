import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import * as lancedb from '@lancedb/lancedb';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { LanceVectorStore } from '../../src/store/vector-store.js';
import type { ChunkWithEmbedding } from '../../src/types/index.js';

describe('LanceVectorStore', () => {
  let tempDir: string;
  let dbPath: string;
  let store: LanceVectorStore;

  beforeEach(async () => {
    tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'wki-lance-test-'));
    dbPath = path.join(tempDir, 'vectors.lance');
    store = new LanceVectorStore(dbPath, 3);
    await store.init();
  });

  afterEach(async () => {
    await store.close();

    if (fs.existsSync(tempDir)) {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
  });

  it('creates the chunks table during init', async () => {
    const db = await lancedb.connect(dbPath);

    expect(await db.tableNames()).toContain('chunks');

    db.close();
  });

  it('stores vectors and returns cosine-similarity scores', async () => {
    await store.insert([
      makeChunk({
        filePath: 'src/payment.ts',
        chunkType: 'function',
        contentHash: 'hash-payment',
        embedding: [1, 0, 0],
      }),
      makeChunk({
        filePath: 'docs/payment.md',
        chunkType: 'markdown-section',
        contentHash: 'hash-doc',
        embedding: [0, 1, 0],
      }),
    ]);

    const results = await store.search([1, 0, 0], 2);

    expect(results).toHaveLength(2);
    expect(results[0]?.chunkId).toBe('src/payment.ts::hash-payment');
    expect(results[0]?.score).toBeCloseTo(1);
    expect(results[1]?.score).toBeLessThan(results[0]!.score);
  });

  it('applies project, file type, and symbol filters', async () => {
    await store.insert([
      makeChunk({
        projectId: 'alpha',
        filePath: 'src/payment.ts',
        chunkType: 'function',
        contentHash: 'hash-function',
        embedding: [1, 0, 0],
      }),
      makeChunk({
        projectId: 'alpha',
        filePath: 'docs/payment.md',
        chunkType: 'markdown-section',
        contentHash: 'hash-markdown',
        embedding: [1, 0, 0],
      }),
      makeChunk({
        projectId: 'beta',
        filePath: 'src/payment.ts',
        chunkType: 'function',
        contentHash: 'hash-other-project',
        embedding: [1, 0, 0],
      }),
    ]);

    const results = await store.search([1, 0, 0], 10, {
      projectId: 'alpha',
      fileType: 'typescript',
      symbolKind: 'function',
    });

    expect(results.map((result) => result.chunkId)).toEqual(['src/payment.ts::hash-function']);
  });

  it('deletes chunks in batches and removes them from search results', async () => {
    await store.insert([
      makeChunk({
        filePath: 'src/delete-a.ts',
        chunkType: 'function',
        contentHash: 'hash-delete-a',
        embedding: [1, 0, 0],
      }),
      makeChunk({
        filePath: 'src/delete-b.ts',
        chunkType: 'function',
        contentHash: 'hash-delete-b',
        embedding: [1, 0, 0],
      }),
    ]);

    expect(await store.search([1, 0, 0], 10)).toHaveLength(2);

    await store.delete(['src/delete-a.ts::hash-delete-a', 'src/delete-b.ts::hash-delete-b']);

    expect(await store.search([1, 0, 0], 10)).toEqual([]);
  });

  it('requires init before use', async () => {
    const uninitialized = new LanceVectorStore(path.join(tempDir, 'uninitialized.lance'), 3);

    await expect(uninitialized.search([1, 0, 0], 5)).rejects.toThrow(
      'LanceVectorStore.init() must be called before search()',
    );
  });

  it('returns to an uninitialized state after close', async () => {
    await store.close();

    await expect(
      store.insert([
        makeChunk({
          filePath: 'src/closed.ts',
          chunkType: 'function',
          contentHash: 'hash-closed',
          embedding: [1, 0, 0],
        }),
      ]),
    ).rejects.toThrow('LanceVectorStore.init() must be called before insert()');
  });

  function makeChunk(
    overrides: Partial<ChunkWithEmbedding> & {
      filePath: string;
      chunkType: ChunkWithEmbedding['chunkType'];
      contentHash: string;
      embedding: number[];
    },
  ): ChunkWithEmbedding {
    return {
      id: overrides.contentHash,
      projectId: overrides.projectId ?? 'alpha',
      filePath: overrides.filePath,
      ordinal: overrides.ordinal ?? 0,
      heading: overrides.heading ?? 'heading',
      content: overrides.content ?? 'content',
      chunkType: overrides.chunkType,
      startLine: overrides.startLine ?? 1,
      endLine: overrides.endLine ?? 5,
      tokenCount: overrides.tokenCount ?? 3,
      contentHash: overrides.contentHash,
      embedding: overrides.embedding,
    };
  }
});
