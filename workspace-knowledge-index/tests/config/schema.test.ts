import { describe, it, expect } from 'vitest';
import path from 'node:path';
import { validateConfig, DEFAULT_CONFIG, resolveFtsDbPath, resolveLanceDbPath } from '../../src/config/schema.js';

describe('validateConfig', () => {
  it('should return defaults when given an empty object', () => {
    const result = validateConfig({});
    expect(result.storage.index_root).toBe('.knowledge');
    expect(result.storage.vector_backend).toBe('lancedb');
    expect(result.embedding.provider).toBe('openai');
    expect(result.chunking.max_lines).toBe(200);
    expect(result.indexing.concurrency).toBe(4);
    expect(result.logging.level).toBe('info');
    expect(result.schema_version).toBe(1);
  });

  it('should deep merge partial overrides', () => {
    const result = validateConfig({
      chunking: { max_lines: 500 },
      logging: { level: 'debug' },
    });
    // Overridden values
    expect(result.chunking.max_lines).toBe(500);
    expect(result.logging.level).toBe('debug');
    // Defaults preserved
    expect(result.chunking.overlap_lines).toBe(DEFAULT_CONFIG.chunking.overlap_lines);
    expect(result.storage.index_root).toBe('.knowledge');
  });

  it('should throw on invalid projects field', () => {
    expect(() => validateConfig({ projects: 'not-an-array' as unknown })).toThrow(
      '"projects" must be an array',
    );
  });
});

describe('storage path resolvers', () => {
  it('should strip index_root from FTS paths before resolving from knowledgeDir', () => {
    const config = validateConfig({
      projects: [{ name: 'my-project', root: '.' }],
      storage: { index_root: '.knowledge' },
      search: { fts_db: '.knowledge/{project}/fts.db' },
    });

    expect(resolveFtsDbPath(config, '/repo/.knowledge', 'my-project')).toBe(
      path.resolve('/repo/.knowledge/my-project/fts.db'),
    );
  });

  it('should strip index_root from LanceDB paths before resolving from knowledgeDir', () => {
    const config = validateConfig({
      projects: [{ name: 'my-project', root: '.' }],
      storage: {
        index_root: '.knowledge',
        vector_backend: 'lancedb',
        lancedb: { path: '.knowledge/{project}/vectors.lance' },
      },
    });

    const resolved = resolveLanceDbPath(config, '/repo/.knowledge', 'my-project');

    expect(resolved).toBe(path.resolve('/repo/.knowledge/my-project/vectors.lance'));
    expect(resolved).not.toContain(`${path.sep}.knowledge${path.sep}.knowledge${path.sep}`);
  });
});
