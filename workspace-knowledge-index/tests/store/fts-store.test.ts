import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { FtsStore } from '../../src/store/fts-store.js';
import type { Chunk } from '../../src/types/index.js';

describe('FtsStore', () => {
  let tempDir: string;
  let dbPath: string;
  let store: FtsStore;

  beforeEach(() => {
    tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'wki-test-'));
    dbPath = path.join(tempDir, 'fts.db');
    store = new FtsStore(dbPath);
  });

  afterEach(async () => {
    await store.close();

    if (fs.existsSync(tempDir)) {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
  });

  it('returns inserted chunks from full-text search', async () => {
    await store.insert([
      makeChunk({
        projectId: 'alpha',
        filePath: 'src/payment.ts',
        ordinal: 0,
        heading: 'PaymentService',
        content: 'Payment service handles billing retries and refund workflows.',
        chunkType: 'function',
        contentHash: 'hash-payment',
      }),
    ]);

    const results = await store.search('billing retries', 5);

    expect(results).toHaveLength(1);
    expect(results[0]?.chunkId).toBe('src/payment.ts::hash-payment');
    expect(results[0]?.highlights?.join(' ')).toContain('billing');
  });

  it('orders more relevant matches ahead of weaker bm25 matches', async () => {
    await store.insert([
      makeChunk({
        projectId: 'alpha',
        filePath: 'src/best.ts',
        ordinal: 0,
        heading: 'handlePayment',
        content: 'payment payment payment gateway settlement retry payment',
        chunkType: 'function',
        contentHash: 'hash-best',
      }),
      makeChunk({
        projectId: 'alpha',
        filePath: 'src/weaker.ts',
        ordinal: 0,
        heading: 'billingFlow',
        content: 'payment appears once in a much longer billing document with unrelated text.',
        chunkType: 'function',
        contentHash: 'hash-weaker',
      }),
    ]);

    const results = await store.search('payment', 2);

    expect(results).toHaveLength(2);
    expect(results[0]?.chunkId).toBe('src/best.ts::hash-best');
    expect(results[0]!.score).toBeLessThanOrEqual(results[1]!.score);
  });

  it('matches identifier-like tokens such as handlePayment', async () => {
    await store.insert([
      makeChunk({
        projectId: 'alpha',
        filePath: 'src/handlers.ts',
        ordinal: 0,
        heading: 'handlePayment',
        content: 'export function handlePayment(orderId: string) { return orderId; }',
        chunkType: 'function',
        contentHash: 'hash-handler',
      }),
    ]);

    const results = await store.search('handlePayment', 5);

    expect(results.map((result) => result.chunkId)).toContain('src/handlers.ts::hash-handler');
  });

  it('applies chunk_type filters through symbolKind', async () => {
    await store.insert([
      makeChunk({
        projectId: 'alpha',
        filePath: 'src/payment-service.ts',
        ordinal: 0,
        heading: 'PaymentService',
        content: 'payment orchestration shared content',
        chunkType: 'class',
        contentHash: 'hash-class',
      }),
      makeChunk({
        projectId: 'alpha',
        filePath: 'src/process-payment.ts',
        ordinal: 0,
        heading: 'processPayment',
        content: 'payment orchestration shared content',
        chunkType: 'function',
        contentHash: 'hash-function',
      }),
    ]);

    const results = await store.search('payment orchestration', 5, {
      symbolKind: 'function',
    });

    expect(results).toHaveLength(1);
    expect(results[0]?.chunkId).toBe('src/process-payment.ts::hash-function');
  });

  it('removes deleted chunks from subsequent searches', async () => {
    await store.insert([
      makeChunk({
        projectId: 'alpha',
        filePath: 'src/deletable.ts',
        ordinal: 0,
        heading: 'temporaryChunk',
        content: 'ephemeral content for deletion checks',
        chunkType: 'other',
        contentHash: 'hash-delete',
      }),
    ]);

    expect(await store.search('ephemeral', 5)).toHaveLength(1);

    await store.delete(['hash-delete']);

    expect(await store.search('ephemeral', 5)).toEqual([]);
  });

  it('rebuilds the FTS index from stored metadata', async () => {
    await store.insert([
      makeChunk({
        projectId: 'alpha',
        filePath: 'docs/rebuild.md',
        ordinal: 0,
        heading: 'Rebuild',
        content: 'Rebuild should restore search visibility after index removal.',
        chunkType: 'markdown-section',
        contentHash: 'hash-rebuild',
      }),
    ]);

    const row = store
      .getDatabase()
      .prepare('SELECT id, content, heading FROM chunks_meta WHERE content_hash = ?')
      .get('hash-rebuild') as { id: number; content: string; heading: string | null } | undefined;

    expect(row).toBeDefined();

    store
      .getDatabase()
      .prepare("INSERT INTO chunks_fts(chunks_fts, rowid, content, heading) VALUES ('delete', ?, ?, ?)")
      .run(row!.id, row!.content, row!.heading);

    expect(await store.search('visibility', 5)).toEqual([]);

    await store.rebuild();

    const results = await store.search('visibility', 5);
    expect(results).toHaveLength(1);
    expect(results[0]?.chunkId).toBe('docs/rebuild.md::hash-rebuild');
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
