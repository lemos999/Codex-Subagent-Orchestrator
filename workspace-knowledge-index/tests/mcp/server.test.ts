import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { handleKnowledgeSearch, handleKnowledgeStatus, createServer } from '../../src/mcp/server.js';
import { FtsStore } from '../../src/store/fts-store.js';
import type { Chunk } from '../../src/types/index.js';

function makeChunk(overrides: Partial<Chunk> & {
  filePath: string;
  content: string;
  chunkType: Chunk['chunkType'];
  contentHash: string;
}): Chunk {
  return {
    id: overrides.contentHash,
    rowId: overrides.rowId ?? 0,
    projectId: overrides.projectId ?? 'test-project',
    filePath: overrides.filePath,
    ordinal: overrides.ordinal ?? 0,
    heading: overrides.heading,
    content: overrides.content,
    chunkType: overrides.chunkType,
    startLine: overrides.startLine ?? 1,
    endLine: overrides.endLine ?? 10,
    tokenCount: overrides.tokenCount ?? overrides.content.split(/\s+/u).filter(Boolean).length,
    contentHash: overrides.contentHash,
  };
}

describe('MCP Server Handlers', () => {
  let tempDir: string;
  let knowledgeDir: string;

  beforeEach(() => {
    tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'wki-mcp-test-'));
    knowledgeDir = path.join(tempDir, '.knowledge');
    fs.mkdirSync(knowledgeDir, { recursive: true });

    // Write a minimal config so loadConfig resolves correctly
    const config = {
      projects: [{ name: 'test-project', root: '.' }],
      storage: {
        index_root: '.knowledge',
        vector_backend: 'none',
      },
      search: {
        fts_db: '.knowledge/{project}/fts.db',
        fusion: {
          strategy: 'weighted_sum',
          weights: { fts: 1, vector: 0 },
        },
      },
    };
    fs.writeFileSync(path.join(tempDir, 'wki.config.json'), JSON.stringify(config));
  });

  afterEach(() => {
    if (fs.existsSync(tempDir)) {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
  });

  describe('knowledge_search', () => {
    it('returns results matching the query', async () => {
      // Seed FTS database
      const projectDir = path.join(knowledgeDir, 'test-project');
      fs.mkdirSync(projectDir, { recursive: true });
      const ftsDbPath = path.join(projectDir, 'fts.db');
      const ftsStore = new FtsStore(ftsDbPath);
      await ftsStore.insert([
        makeChunk({
          filePath: 'src/utils.ts',
          heading: 'parseConfig',
          content: 'function parseConfig reads and validates configuration files',
          chunkType: 'function',
          contentHash: 'hash-parse-config',
          startLine: 1,
          endLine: 15,
        }),
        makeChunk({
          filePath: 'src/main.ts',
          heading: 'main',
          content: 'main entry point for the application startup',
          chunkType: 'function',
          contentHash: 'hash-main',
          ordinal: 1,
          startLine: 20,
          endLine: 30,
        }),
      ]);
      await ftsStore.close();

      const response = await handleKnowledgeSearch(
        { query: 'parseConfig' },
        tempDir,
      ) as Record<string, unknown>;

      const results = response['results'] as Array<Record<string, unknown>>;
      expect(results).toHaveLength(1);
      expect(results[0]).toMatchObject({
        filePath: 'src/utils.ts',
        startLine: 1,
        endLine: 15,
        chunkType: 'function',
        matchType: 'fts',
        heading: 'parseConfig',
      });
      expect(results[0]['score']).toBeGreaterThan(0);
      expect(results[0]['content']).toContain('parseConfig');
    });

    it('returns empty results for no matches', async () => {
      const projectDir = path.join(knowledgeDir, 'test-project');
      fs.mkdirSync(projectDir, { recursive: true });
      const ftsDbPath = path.join(projectDir, 'fts.db');
      const ftsStore = new FtsStore(ftsDbPath);
      await ftsStore.close();

      const response = await handleKnowledgeSearch(
        { query: 'nonexistent_term_xyz' },
        tempDir,
      ) as Record<string, unknown>;

      expect(response['results']).toEqual([]);
    });

    it('returns empty results for empty query string', async () => {
      const response = await handleKnowledgeSearch(
        { query: '' },
        tempDir,
      ) as Record<string, unknown>;

      expect(response['results']).toEqual([]);
    });

    it('returns empty results for whitespace-only query', async () => {
      const response = await handleKnowledgeSearch(
        { query: '   ' },
        tempDir,
      ) as Record<string, unknown>;

      expect(response['results']).toEqual([]);
    });

    it('includes warning when vector/hybrid mode is requested', async () => {
      const projectDir = path.join(knowledgeDir, 'test-project');
      fs.mkdirSync(projectDir, { recursive: true });
      const ftsDbPath = path.join(projectDir, 'fts.db');
      const ftsStore = new FtsStore(ftsDbPath);
      await ftsStore.close();

      const response = await handleKnowledgeSearch(
        { query: 'test', mode: 'vector' },
        tempDir,
      ) as Record<string, unknown>;

      expect(response['warning']).toContain('downgraded');
      expect(response['warning']).toContain('vector');
    });
  });

  describe('knowledge_status', () => {
    it('returns all expected fields', async () => {
      // Seed file-map.json
      const fileMap = {
        'src/a.ts': { path: 'src/a.ts', size: 100, type: 'ts' },
        'src/b.ts': { path: 'src/b.ts', size: 200, type: 'ts' },
      };
      fs.writeFileSync(
        path.join(knowledgeDir, 'file-map.json'),
        JSON.stringify(fileMap),
      );

      // Seed FTS database with some chunks
      const projectDir = path.join(knowledgeDir, 'test-project');
      fs.mkdirSync(projectDir, { recursive: true });
      const ftsDbPath = path.join(projectDir, 'fts.db');
      const ftsStore = new FtsStore(ftsDbPath);
      await ftsStore.insert([
        makeChunk({
          filePath: 'src/a.ts',
          content: 'some content',
          chunkType: 'function',
          contentHash: 'hash-a',
        }),
      ]);
      await ftsStore.close();

      // Seed freshness.lock
      fs.writeFileSync(
        path.join(knowledgeDir, 'freshness.lock'),
        JSON.stringify({ indexed_at: '2025-01-15T10:00:00Z', dirty: false }),
      );

      const status = await handleKnowledgeStatus({}, tempDir);

      expect(status).toMatchObject({
        health: 'healthy',
        filesCount: 2,
        chunksCount: 1,
        symbolsCount: 0,
        vectorStatus: 'none',
        lastIndexed: '2025-01-15T10:00:00Z',
        dirty: false,
        locked: false,
      });
      expect(status.lockInfo).toBeUndefined();
    });

    it('reports degraded health when no index exists', async () => {
      // No FTS db, no file-map -- just .knowledge dir exists
      const status = await handleKnowledgeStatus({}, tempDir);

      expect(status.health).toBe('stale');
      expect(status.filesCount).toBe(0);
      expect(status.chunksCount).toBe(0);
      expect(status.lastIndexed).toBe('never');
    });

    it('reports not_initialized when .knowledge dir does not exist', async () => {
      // Remove .knowledge dir
      fs.rmSync(knowledgeDir, { recursive: true, force: true });

      const status = await handleKnowledgeStatus({}, tempDir);

      expect(status.health).toBe('not_initialized');
    });
  });

  describe('createServer', () => {
    it('creates an McpServer with the expected tools registered', () => {
      const server = createServer(tempDir);
      expect(server).toBeDefined();
      // The server object itself is an McpServer -- verify it has the connect method
      expect(typeof server.connect).toBe('function');
    });
  });
});
