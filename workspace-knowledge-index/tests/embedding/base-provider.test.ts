import { afterEach, describe, expect, it, vi } from 'vitest';
import { BaseEmbeddingProvider } from '../../src/embedding/base-provider.js';

class MockProvider extends BaseEmbeddingProvider {
  readonly dimensions = 3;
  readonly modelName = 'mock-provider';
  readonly maxBatchSize: number;
  readonly maxTokensPerText = 1024;

  readonly batches: string[][] = [];
  private failuresRemaining: number;

  constructor(options?: { maxBatchSize?: number; failuresBeforeSuccess?: number }) {
    super();
    this.maxBatchSize = options?.maxBatchSize ?? 10;
    this.failuresRemaining = options?.failuresBeforeSuccess ?? 0;
  }

  protected async embedBatch(texts: string[]): Promise<number[][]> {
    this.batches.push([...texts]);

    if (this.failuresRemaining > 0) {
      this.failuresRemaining -= 1;
      throw new Error('mock batch failure');
    }

    return texts.map((text) => toMockVector(text));
  }
}

describe('BaseEmbeddingProvider', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it('embeds a normal batch through the subclass implementation', async () => {
    const provider = new MockProvider();

    await expect(provider.batchEmbed(['alpha', 'beta'])).resolves.toEqual([
      [5, 1, 0],
      [4, 1, 1],
    ]);
    expect(provider.batches).toEqual([['alpha', 'beta']]);
  });

  it('automatically splits large inputs that exceed maxBatchSize', async () => {
    const provider = new MockProvider({ maxBatchSize: 2 });

    const results = await provider.batchEmbed(['a', 'bb', 'ccc', 'dddd', 'eeeee']);

    expect(provider.batches).toEqual([['a', 'bb'], ['ccc', 'dddd'], ['eeeee']]);
    expect(results.map((vector) => vector[0])).toEqual([1, 2, 3, 4, 5]);
  });

  it('retries a failed batch once before succeeding', async () => {
    vi.useFakeTimers();
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const provider = new MockProvider({ failuresBeforeSuccess: 1 });

    const promise = provider.batchEmbed(['alpha']);
    await vi.runAllTimersAsync();

    await expect(promise).resolves.toEqual([[5, 1, 0]]);
    expect(provider.batches).toEqual([['alpha'], ['alpha']]);
    expect(warnSpy).toHaveBeenCalledTimes(1);
  });

  it('throws after exhausting all retries', async () => {
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    const provider = new MockProvider({
      failuresBeforeSuccess: Number.POSITIVE_INFINITY,
    });

    await expect(provider.batchEmbed(['alpha', 'beta'])).rejects.toThrow(
      'failed after 3 attempts',
    );
    expect(provider.batches).toHaveLength(3);
  });

  it('delegates single-text embed calls to batchEmbed', async () => {
    const provider = new MockProvider();
    const batchEmbedSpy = vi.spyOn(provider, 'batchEmbed').mockResolvedValue([[9, 8, 7]]);

    await expect(provider.embed('single input')).resolves.toEqual([9, 8, 7]);
    expect(batchEmbedSpy).toHaveBeenCalledWith(['single input']);
    expect(batchEmbedSpy).toHaveBeenCalledTimes(1);
  });
});

function toMockVector(text: string): number[] {
  return [text.length, text.includes('a') ? 1 : 0, text.includes('b') ? 1 : 0];
}
