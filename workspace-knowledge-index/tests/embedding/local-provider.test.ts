import { describe, expect, it } from 'vitest';
import { LocalEmbeddingProvider } from '../../src/embedding/local-provider.js';

describe('LocalEmbeddingProvider', () => {
  it('has correct default model and dimensions', () => {
    const provider = new LocalEmbeddingProvider();
    expect(provider.modelName).toBe('Xenova/bge-small-en-v1.5');
    expect(provider.dimensions).toBe(384);
    expect(provider.maxBatchSize).toBe(16);
  });

  it('accepts custom model and dimensions', () => {
    const provider = new LocalEmbeddingProvider({
      model: 'custom-model',
      dimensions: 512,
    });
    expect(provider.modelName).toBe('custom-model');
    expect(provider.dimensions).toBe(512);
  });

  it('embeds text successfully with default model', async () => {
    const provider = new LocalEmbeddingProvider();
    const result = await provider.embed('test');
    expect(result).toHaveLength(384);
    expect(typeof result[0]).toBe('number');
  });

  it('batch embeds multiple texts', async () => {
    const provider = new LocalEmbeddingProvider();
    const results = await provider.batchEmbed(['a', 'b']);
    expect(results).toHaveLength(2);
    expect(results[0]).toHaveLength(384);
    expect(results[1]).toHaveLength(384);
  });
});
