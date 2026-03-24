import { describe, it, expect } from 'vitest';
import { validateConfig, DEFAULT_CONFIG } from '../../src/config/schema.js';

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
