import { describe, it, expect, afterEach } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { injectContext, generateAgentContext } from '../../src/context/sub-hook.js';
import type { ContextBlock } from '../../src/context/context-builder.js';
import type { Chunk, SearchResult } from '../../src/types/index.js';
import { FtsStore, CHUNK_META_UPSERT_SQL, toChunkMetaParams } from '../../src/store/fts-store.js';

function makeContextBlock(overrides: Partial<ContextBlock> = {}): ContextBlock {
  const chunk: Chunk = {
    id: 'test:file.ts:0',
    projectId: 'test',
    filePath: 'src/app.ts',
    ordinal: 0,
    content: 'const x = 1;',
    heading: 'x',
    chunkType: 'variable',
    startLine: 1,
    endLine: 1,
    tokenCount: 10,
    contentHash: 'hash',
  };
  const result: SearchResult = {
    chunk,
    score: 0.9,
    matchType: 'fts',
  };

  return {
    markdown: '## Relevant Context (auto-injected)\n\n### src/app.ts (lines 1-1)\n**x** \u2014 variable\n```typescript\nconst x = 1;\n```\n',
    chunks: [result],
    query: 'test',
    durationMs: 10,
    ...overrides,
  };
}

function makeEmptyContextBlock(): ContextBlock {
  return {
    markdown: '## Relevant Context (auto-injected)\n\nNo relevant context found.\n',
    chunks: [],
    query: 'test',
    durationMs: 5,
  };
}

describe('injectContext', () => {
  it('should insert context before the first ## heading', () => {
    const prompt = 'Some intro text.\n\n## Task\nDo something.\n\n## Rules\nFollow rules.';
    const block = makeContextBlock();
    const result = injectContext(prompt, block);

    // Context should appear before "## Task"
    const contextIdx = result.indexOf('## Relevant Context');
    const taskIdx = result.indexOf('## Task');
    expect(contextIdx).toBeGreaterThan(-1);
    expect(taskIdx).toBeGreaterThan(contextIdx);
    // Original content preserved
    expect(result).toContain('Some intro text.');
    expect(result).toContain('## Rules');
  });

  it('should append at end if no ## headings exist', () => {
    const prompt = 'A simple prompt with no headings.';
    const block = makeContextBlock();
    const result = injectContext(prompt, block);

    expect(result).toContain('A simple prompt with no headings.');
    expect(result).toContain('## Relevant Context');
    // Context should be at the end
    const promptIdx = result.indexOf('A simple prompt');
    const contextIdx = result.indexOf('## Relevant Context');
    expect(contextIdx).toBeGreaterThan(promptIdx);
  });

  it('should not inject when context block has no chunks', () => {
    const prompt = '## Task\nDo something.';
    const block = makeEmptyContextBlock();
    const result = injectContext(prompt, block);

    // Prompt should be unchanged
    expect(result).toBe(prompt);
  });

  it('should preserve the full original prompt content', () => {
    const prompt = 'Preamble\n\n## Section A\nContent A\n\n## Section B\nContent B';
    const block = makeContextBlock();
    const result = injectContext(prompt, block);

    expect(result).toContain('Preamble');
    expect(result).toContain('## Section A');
    expect(result).toContain('Content A');
    expect(result).toContain('## Section B');
    expect(result).toContain('Content B');
    expect(result).toContain('## Relevant Context');
  });

  it('should inject context before prompt that starts with "## " (no leading newline)', () => {
    const prompt = '## Task\nDo something important.';
    const block = makeContextBlock();
    const result = injectContext(prompt, block);

    // Context should appear before the ## Task heading
    const contextIdx = result.indexOf('## Relevant Context');
    const taskIdx = result.indexOf('## Task');
    expect(contextIdx).toBeGreaterThan(-1);
    expect(taskIdx).toBeGreaterThan(contextIdx);
  });
});

describe('generateAgentContext', () => {
  let tmpDir: string;

  afterEach(() => {
    if (tmpDir && fs.existsSync(tmpDir)) {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    }
  });

  it('should return a ContextBlock in FTS-only mode (vector_backend: none)', async () => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'wki-subhook-test-'));
    const ftsDbPath = path.join(tmpDir, 'fts.db');

    // Seed the FTS store with test data
    const ftsStore = new FtsStore(ftsDbPath);
    const db = ftsStore.getDatabase();
    const upsert = db.prepare(CHUNK_META_UPSERT_SQL);
    const testChunk: Chunk = {
      id: 'test:src/app.ts:0',
      projectId: 'test',
      filePath: 'src/app.ts',
      ordinal: 0,
      content: 'function hello() { return "world"; }',
      heading: 'hello',
      chunkType: 'function',
      startLine: 1,
      endLine: 3,
      tokenCount: 20,
      contentHash: 'testhash123',
    };
    upsert.run(toChunkMetaParams(testChunk));
    await ftsStore.close();

    const block = await generateAgentContext('hello function', {
      knowledgeDir: tmpDir,
      projectId: 'test',
      ftsDbPath,
      embeddingConfig: { provider: 'openai' },
      storageConfig: { index_root: '.knowledge', vector_backend: 'none' },
      searchConfig: {
        fts_db: ftsDbPath,
        fusion: { strategy: 'weighted_sum', weights: { fts: 1, vector: 0 } },
      },
    });

    expect(block).toBeDefined();
    expect(block.markdown).toBeDefined();
    expect(typeof block.markdown).toBe('string');
    expect(block.query).toBe('hello function');
    expect(block.durationMs).toBeGreaterThanOrEqual(0);
  });

  it('should open and close ftsStore (resource cleanup)', async () => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'wki-subhook-cleanup-'));
    const ftsDbPath = path.join(tmpDir, 'fts.db');

    // Create an empty FTS store so the DB exists
    const ftsStore = new FtsStore(ftsDbPath);
    await ftsStore.close();

    // generateAgentContext should open and close without errors
    const block = await generateAgentContext('nonexistent query', {
      knowledgeDir: tmpDir,
      projectId: 'test',
      ftsDbPath,
      embeddingConfig: { provider: 'openai' },
      storageConfig: { index_root: '.knowledge', vector_backend: 'none' },
      searchConfig: {
        fts_db: ftsDbPath,
        fusion: { strategy: 'weighted_sum', weights: { fts: 1, vector: 0 } },
      },
    });

    // Should return a valid block (likely empty results)
    expect(block).toBeDefined();
    expect(block.markdown).toContain('Relevant Context');

    // The FTS DB file should still exist (not corrupted)
    expect(fs.existsSync(ftsDbPath)).toBe(true);
  });
});
