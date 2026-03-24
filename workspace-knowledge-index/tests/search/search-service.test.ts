import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { SearchConfig } from '../../src/config/schema.js';
import type { EmbeddingProvider } from '../../src/interfaces/embedding.js';
import { SearchService, normalizeFtsScores, normalizeVectorScores } from '../../src/search/search-service.js';
import { ChunkStore } from '../../src/store/chunk-store.js';
import { FtsStore } from '../../src/store/fts-store.js';
import { LanceVectorStore } from '../../src/store/vector-store.js';
import type { Chunk, ChunkWithEmbedding } from '../../src/types/index.js';

vi.mock('../../src/search/cross-encoder-reranker.js', () => ({
  crossEncoderRerank: vi.fn(async () => null),
}));

describe('SearchService', () => {
  let tempDir: string;
  let ftsStore: FtsStore;
  let chunkStore: ChunkStore;
  let vectorStore: LanceVectorStore;
  let searchService: SearchService;
  let embeddingProvider: EmbeddingProvider;
  let embedMock: ReturnType<typeof vi.fn>;

  beforeEach(async () => {
    tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'wki-search-test-'));

    ftsStore = new FtsStore(path.join(tempDir, 'fts.db'));
    chunkStore = new ChunkStore(ftsStore.getDatabase());
    vectorStore = new LanceVectorStore(path.join(tempDir, 'vectors.lance'), 3);
    await vectorStore.init();

    embedMock = vi.fn(async (text: string): Promise<number[]> => {
      if (text.toLowerCase().includes('refund')) {
        return [0, 0, 1];
      }

      return [1, 0, 0];
    });

    embeddingProvider = {
      dimensions: 3,
      modelName: 'mock-embedding',
      embed: (text: string) => embedMock(text) as Promise<number[]>,
      batchEmbed: (texts: string[]) =>
        Promise.all(texts.map((text) => embedMock(text) as Promise<number[]>)),
    };

    const chunks = [
      makeChunk({
        filePath: 'src/fts-favored.ts',
        heading: 'handleBillingRetry',
        content:
          'billing retry settlement billing retry settlement payment safeguards for processors',
        chunkType: 'function',
        contentHash: 'hash-fts-favored',
        startLine: 5,
        endLine: 18,
      }),
      makeChunk({
        filePath: 'src/vector-favored.ts',
        heading: 'describeRetryFlow',
        content:
          'billing retry settlement appears once inside broader operational notes for support staff',
        chunkType: 'function',
        contentHash: 'hash-vector-favored',
        startLine: 20,
        endLine: 30,
      }),
      makeChunk({
        filePath: 'src/refund.ts',
        heading: 'refundOrder',
        content: 'refund compensation workflow for canceled orders and manual review',
        chunkType: 'function',
        contentHash: 'hash-refund',
        startLine: 31,
        endLine: 44,
      }),
    ];

    await ftsStore.insert(chunks);
    await vectorStore.insert([
      { ...chunks[0]!, embedding: [0, 1, 0] },
      { ...chunks[1]!, embedding: [1, 0, 0] },
      { ...chunks[2]!, embedding: [0, 0, 1] },
    ]);

    searchService = new SearchService(
      ftsStore,
      vectorStore,
      chunkStore,
      embeddingProvider,
      createConfig(0.4, 0.6),
    );
  });

  afterEach(async () => {
    await vectorStore.close();
    await ftsStore.close();
    vi.restoreAllMocks();

    if (fs.existsSync(tempDir)) {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
  });

  it('searches in FTS-only mode without requesting embeddings', async () => {
    const results = await searchService.search('handleBillingRetry', { mode: 'fts', topK: 5 });

    expect(results).toHaveLength(1);
    expect(results[0]?.chunk.contentHash).toBe('hash-fts-favored');
    expect(results[0]?.matchType).toBe('fts');
    expect(embedMock).not.toHaveBeenCalled();
  });

  it('combines FTS and vector results in hybrid mode', async () => {
    const results = await searchService.search('billing retry settlement', {
      mode: 'hybrid',
      topK: 2,
    });

    expect(embedMock).toHaveBeenCalledTimes(1);
    expect(results).toHaveLength(2);
    expect(results[0]?.chunk.contentHash).toBe('hash-fts-favored');
    expect(results[0]?.matchType).toBe('hybrid');
    expect(results[1]?.chunk.contentHash).toBe('hash-vector-favored');
    expect(results[1]?.matchType).toBe('vector');
    expect(results[0]!.score).toBeGreaterThan(results[1]!.score);
  });

  it('normalizes FTS and vector scores into the 0..1 range', () => {
    const normalizedFts = normalizeFtsScores([
      { chunkId: 'strong', score: -10 },
      { chunkId: 'weak', score: -1 },
    ]);
    const normalizedVector = normalizeVectorScores([
      { chunkId: 'clamped-high', score: 1.2 },
      { chunkId: 'middle', score: 0.4 },
      { chunkId: 'clamped-low', score: -1 },
    ]);

    for (const score of normalizedFts.values()) {
      expect(score).toBeGreaterThanOrEqual(0);
      expect(score).toBeLessThanOrEqual(1);
    }

    expect(normalizedFts.get('strong')).toBeGreaterThan(normalizedFts.get('weak')!);
    expect(normalizedVector.get('clamped-high')).toBe(1);
    expect(normalizedVector.get('middle')).toBe(0.4);
    expect(normalizedVector.get('clamped-low')).toBe(0);
  });

  it('applies dynamic fusion weights when ranking hybrid results', async () => {
    const ftsHeavyService = new SearchService(
      ftsStore,
      vectorStore,
      chunkStore,
      embeddingProvider,
      createConfig(0.9, 0.1),
    );
    const vectorHeavyService = new SearchService(
      ftsStore,
      vectorStore,
      chunkStore,
      embeddingProvider,
      createConfig(0.1, 0.9),
    );

    const ftsHeavyResults = await ftsHeavyService.search('billing retry settlement', {
      mode: 'hybrid',
      topK: 1,
    });
    const vectorHeavyResults = await vectorHeavyService.search('billing retry settlement', {
      mode: 'hybrid',
      topK: 1,
    });

    expect(ftsHeavyResults[0]?.chunk.contentHash).toBe('hash-fts-favored');
    expect(vectorHeavyResults[0]?.chunk.contentHash).toBe('hash-vector-favored');
  });

  it('hydrates vector hits through ChunkStore and can omit content payloads', async () => {
    const results = await searchService.search('refund semantic explanation', {
      mode: 'vector',
      topK: 1,
      includeContent: false,
    });

    expect(results).toHaveLength(1);
    expect(results[0]?.chunk).toMatchObject({
      contentHash: 'hash-refund',
      filePath: 'src/refund.ts',
      heading: 'refundOrder',
      projectId: 'alpha',
      startLine: 31,
      endLine: 44,
      content: '',
    });
    expect(results[0]?.matchType).toBe('vector');
  });

  function makeChunk(
    overrides: Partial<Chunk> & {
      filePath: string;
      heading: string;
      content: string;
      chunkType: Chunk['chunkType'];
      contentHash: string;
    },
  ): Chunk {
    return {
      id: overrides.contentHash,
      rowId: overrides.rowId ?? 0,
      projectId: overrides.projectId ?? 'alpha',
      filePath: overrides.filePath,
      ordinal: overrides.ordinal ?? 0,
      heading: overrides.heading,
      content: overrides.content,
      chunkType: overrides.chunkType,
      startLine: overrides.startLine ?? 1,
      endLine: overrides.endLine ?? 5,
      tokenCount: overrides.tokenCount ?? overrides.content.split(/\s+/u).filter(Boolean).length,
      contentHash: overrides.contentHash,
    };
  }

  function createConfig(fts: number, vector: number): SearchConfig {
    return {
      fts_db: 'fts.db',
      fusion: {
        strategy: 'weighted_sum',
        weights: {
          fts,
          vector,
        },
      },
    };
  }
});
