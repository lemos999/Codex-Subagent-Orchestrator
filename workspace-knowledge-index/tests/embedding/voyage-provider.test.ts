import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

describe('VoyageEmbeddingProvider', () => {
  const originalEnv = { ...process.env };

  beforeEach(() => {
    process.env['VOYAGE_API_KEY'] = 'test-voyage-key';
  });

  afterEach(() => {
    process.env = { ...originalEnv };
    vi.restoreAllMocks();
  });

  it('throws if no API key is provided', async () => {
    delete process.env['VOYAGE_API_KEY'];
    delete process.env['WKI_VOYAGE_KEY'];

    const { VoyageEmbeddingProvider } = await import(
      '../../src/embedding/voyage-provider.js'
    );

    expect(() => new VoyageEmbeddingProvider()).toThrow(
      'Voyage API key not found',
    );
  });

  it('uses default model and dimensions', async () => {
    const { VoyageEmbeddingProvider } = await import(
      '../../src/embedding/voyage-provider.js'
    );

    const provider = new VoyageEmbeddingProvider();
    expect(provider.modelName).toBe('voyage-4-lite');
    expect(provider.dimensions).toBe(1024);
    expect(provider.maxBatchSize).toBe(128);
  });

  it('accepts custom model and dimensions', async () => {
    const { VoyageEmbeddingProvider } = await import(
      '../../src/embedding/voyage-provider.js'
    );

    const provider = new VoyageEmbeddingProvider({
      model: 'voyage-3',
      dimensions: 512,
    });
    expect(provider.modelName).toBe('voyage-3');
    expect(provider.dimensions).toBe(512);
  });

  it('calls the Voyage API with correct payload', async () => {
    const mockResponse = {
      data: [
        { index: 0, embedding: [0.1, 0.2, 0.3] },
        { index: 1, embedding: [0.4, 0.5, 0.6] },
      ],
    };

    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(mockResponse), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    const { VoyageEmbeddingProvider } = await import(
      '../../src/embedding/voyage-provider.js'
    );

    const provider = new VoyageEmbeddingProvider({ dimensions: 3 });
    const results = await provider.batchEmbed(['hello', 'world']);

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url, options] = fetchSpy.mock.calls[0]!;
    expect(url).toBe('https://api.voyageai.com/v1/embeddings');
    expect(options?.method).toBe('POST');

    const body = JSON.parse(options?.body as string) as Record<string, unknown>;
    expect(body['model']).toBe('voyage-4-lite');
    expect(body['input']).toEqual(['hello', 'world']);

    expect(results).toEqual([
      [0.1, 0.2, 0.3],
      [0.4, 0.5, 0.6],
    ]);
  });

  it('throws on API error response after retries', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response('Rate limit exceeded', { status: 429 }),
    );

    const { VoyageEmbeddingProvider } = await import(
      '../../src/embedding/voyage-provider.js'
    );

    const provider = new VoyageEmbeddingProvider({ dimensions: 3 });

    await expect(provider.batchEmbed(['test'])).rejects.toThrow(
      'failed after 3 attempts',
    );
  });
});
