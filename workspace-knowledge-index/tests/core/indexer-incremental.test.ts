import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import Database from 'better-sqlite3';
import type { VectorBackend } from '../../src/interfaces/vector-backend.js';
import type { ChangedFiles } from '../../src/core/freshness.js';
import { Indexer } from '../../src/core/indexer.js';

function createMockVectorStore(): VectorBackend & {
  insertCalls: Array<{ chunkIds: string[] }>;
  deleteCalls: Array<{ chunkIds: string[] }>;
} {
  const insertCalls: Array<{ chunkIds: string[] }> = [];
  const deleteCalls: Array<{ chunkIds: string[] }> = [];
  return {
    insertCalls,
    deleteCalls,
    insert: vi.fn(async (chunks) => {
      insertCalls.push({ chunkIds: chunks.map((c: { id: string }) => c.id) });
    }),
    search: vi.fn(async () => []),
    delete: vi.fn(async (chunkIds: string[]) => {
      deleteCalls.push({ chunkIds: [...chunkIds] });
    }),
    rebuild: vi.fn(async () => {}),
    close: vi.fn(async () => {}),
  };
}

function createMockEmbeddingProvider() {
  return {
    dimensions: 4,
    embed: vi.fn(async () => [0.1, 0.2, 0.3, 0.4]),
    batchEmbed: vi.fn(async (contents: string[]) =>
      contents.map(() => [0.1, 0.2, 0.3, 0.4]),
    ),
  };
}

describe('Indexer incremental', () => {
  let tmpDir: string;
  let projectRoot: string;
  let knowledgeDir: string;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'wki-inc-test-'));
    projectRoot = path.join(tmpDir, 'project');
    knowledgeDir = path.join(tmpDir, 'knowledge');
    fs.mkdirSync(projectRoot, { recursive: true });
    fs.mkdirSync(knowledgeDir, { recursive: true });
  });

  afterEach(() => {
    if (tmpDir && fs.existsSync(tmpDir)) {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    }
  });

  it('should delete old vector chunks and insert new ones for a modified file', async () => {
    // Create a source file
    const srcFile = path.join(projectRoot, 'hello.txt');
    fs.writeFileSync(srcFile, 'original content line one\noriginal content line two\n');

    const vectorStore = createMockVectorStore();
    const embeddingProvider = createMockEmbeddingProvider();

    const indexer = new Indexer(
      'test-proj',
      projectRoot,
      knowledgeDir,
      [],
      undefined,
      embeddingProvider,
      vectorStore,
    );

    // Full index to populate FTS + vector store
    const fullResult = await indexer.indexFull();
    expect(fullResult.filesProcessed).toBeGreaterThanOrEqual(1);
    expect(vectorStore.insertCalls.length).toBe(1);

    // Modify the source file
    fs.writeFileSync(srcFile, 'modified content completely new\nmodified line two\n');

    const changedFiles: ChangedFiles = {
      added: [],
      modified: ['hello.txt'],
      deleted: [],
      renamed: [],
    };

    // Create a new indexer that reads the same FTS db
    const indexer2 = new Indexer(
      'test-proj',
      projectRoot,
      knowledgeDir,
      [],
      undefined,
      embeddingProvider,
      vectorStore,
    );

    const incResult = await indexer2.indexIncremental(changedFiles);
    expect(incResult.filesProcessed).toBe(1);

    // vectorStore.delete should have been called with old chunk IDs
    expect(vectorStore.delete).toHaveBeenCalled();
    expect(vectorStore.deleteCalls.length).toBeGreaterThanOrEqual(1);

    // vectorStore.insert should have been called again with new chunks
    // insertCalls[0] is from indexFull, insertCalls[1+] from incremental
    expect(vectorStore.insertCalls.length).toBeGreaterThanOrEqual(2);
  });

  it('should remove chunks from both FTS and vector store for a deleted file', async () => {
    const srcFile = path.join(projectRoot, 'to-delete.txt');
    fs.writeFileSync(srcFile, 'some content to be deleted\n');

    const vectorStore = createMockVectorStore();
    const embeddingProvider = createMockEmbeddingProvider();

    const indexer = new Indexer(
      'test-proj',
      projectRoot,
      knowledgeDir,
      [],
      undefined,
      embeddingProvider,
      vectorStore,
    );

    await indexer.indexFull();
    expect(vectorStore.insertCalls.length).toBe(1);

    // Delete the file from disk
    fs.unlinkSync(srcFile);

    const changedFiles: ChangedFiles = {
      added: [],
      modified: [],
      deleted: ['to-delete.txt'],
      renamed: [],
    };

    const indexer2 = new Indexer(
      'test-proj',
      projectRoot,
      knowledgeDir,
      [],
      undefined,
      embeddingProvider,
      vectorStore,
    );

    const incResult = await indexer2.indexIncremental(changedFiles);
    expect(incResult.chunksDeleted).toBeGreaterThanOrEqual(1);

    // vectorStore.delete should have been called for the deleted file's chunks
    expect(vectorStore.delete).toHaveBeenCalled();
    expect(vectorStore.deleteCalls.length).toBeGreaterThanOrEqual(1);
    expect(vectorStore.deleteCalls[0].chunkIds.length).toBeGreaterThanOrEqual(1);
  });

  it('should work in FTS-only mode without vector store (no delete called)', async () => {
    const srcFile = path.join(projectRoot, 'fts-only.txt');
    fs.writeFileSync(srcFile, 'fts only content here\n');

    // No vector store, no embedding provider
    const indexer = new Indexer(
      'test-proj',
      projectRoot,
      knowledgeDir,
      [],
      undefined,
      undefined,
      undefined,
    );

    await indexer.indexFull();

    // Modify the file
    fs.writeFileSync(srcFile, 'updated fts only content\n');

    const changedFiles: ChangedFiles = {
      added: [],
      modified: ['fts-only.txt'],
      deleted: [],
      renamed: [],
    };

    const indexer2 = new Indexer(
      'test-proj',
      projectRoot,
      knowledgeDir,
      [],
      undefined,
      undefined,
      undefined,
    );

    const incResult = await indexer2.indexIncremental(changedFiles);
    expect(incResult.filesProcessed).toBe(1);
    expect(incResult.chunksAdded).toBeGreaterThanOrEqual(1);
    // No vector store means no delete should have been attempted -- no errors
    expect(incResult.errors).toHaveLength(0);
  });

  it('should not treat legacy absolute DB paths as missing files during gap repair', async () => {
    const srcDir = path.join(projectRoot, 'src');
    fs.mkdirSync(srcDir, { recursive: true });
    const srcFile = path.join(srcDir, 'util.ts');
    fs.writeFileSync(srcFile, 'export const value = 1;\n');

    const indexer = new Indexer(
      'test-proj',
      projectRoot,
      knowledgeDir,
      [],
      undefined,
      undefined,
      undefined,
    );
    await indexer.indexFull();

    const db = new Database(path.join(knowledgeDir, 'fts.db'));
    try {
      db.prepare('UPDATE chunks_meta SET file_path = ? WHERE file_path = ?').run(srcFile, 'src/util.ts');
    } finally {
      db.close();
    }

    const indexer2 = new Indexer(
      'test-proj',
      projectRoot,
      knowledgeDir,
      [],
      undefined,
      undefined,
      undefined,
    );

    const incResult = await indexer2.indexIncremental({
      added: [],
      modified: [],
      deleted: [],
      renamed: [],
    });

    expect(incResult.filesProcessed).toBe(0);
  });

  it('should store relative POSIX paths for incremental TypeScript chunks', async () => {
    fs.writeFileSync(
      path.join(projectRoot, 'tsconfig.json'),
      JSON.stringify({ include: ['src/**/*.ts'], compilerOptions: { target: 'ES2022', module: 'Node16' } }),
    );
    const srcDir = path.join(projectRoot, 'src');
    fs.mkdirSync(srcDir, { recursive: true });
    const srcFile = path.join(srcDir, 'math.ts');
    fs.writeFileSync(srcFile, 'export function add(left: number, right: number) {\n  return left + right;\n}\n');

    const indexer = new Indexer(
      'test-proj',
      projectRoot,
      knowledgeDir,
      [],
      undefined,
      undefined,
      undefined,
    );
    await indexer.indexFull();

    fs.writeFileSync(srcFile, 'export function add(left: number, right: number) {\n  return left + right + 1;\n}\n');
    const indexer2 = new Indexer(
      'test-proj',
      projectRoot,
      knowledgeDir,
      [],
      undefined,
      undefined,
      undefined,
    );

    const incResult = await indexer2.indexIncremental({
      added: [],
      modified: ['src/math.ts'],
      deleted: [],
      renamed: [],
    });
    expect(incResult.filesProcessed).toBe(1);

    const db = new Database(path.join(knowledgeDir, 'fts.db'), { readonly: true });
    try {
      const paths = db
        .prepare('SELECT DISTINCT file_path FROM chunks_meta WHERE project_id = ? ORDER BY file_path')
        .all('test-proj')
        .map((row) => (row as { file_path: string }).file_path);

      expect(paths).toContain('src/math.ts');
      expect(paths.some((filePath) => path.isAbsolute(filePath) || /^[A-Za-z]:[\\/]/.test(filePath))).toBe(false);
    } finally {
      db.close();
    }
  });
});
