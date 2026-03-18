import { BaseEmbeddingProvider } from './base-provider.js';

interface VoyageEmbeddingResponse {
  data: Array<{ index: number; embedding: number[] }>;
  usage?: { total_tokens: number };
}

/**
 * Voyage AI embedding provider.
 * Uses voyage-4-lite (1024d) by default.
 * Calls the Voyage REST API with native fetch (Node 20+).
 */
export class VoyageEmbeddingProvider extends BaseEmbeddingProvider {
  readonly dimensions: number;
  readonly modelName: string;
  readonly maxBatchSize = 128;
  readonly maxTokensPerText = 32000;

  private readonly apiKey: string;
  private readonly endpoint: string;

  constructor(options?: {
    apiKey?: string;
    model?: string;
    dimensions?: number;
    endpoint?: string;
  }) {
    super();

    const apiKey =
      options?.apiKey ||
      process.env['WKI_VOYAGE_KEY'] ||
      process.env['VOYAGE_API_KEY'];

    if (!apiKey) {
      throw new Error(
        'Voyage API key not found. Set WKI_VOYAGE_KEY or VOYAGE_API_KEY environment variable.',
      );
    }

    this.apiKey = apiKey;
    this.modelName = options?.model || 'voyage-4-lite';
    this.dimensions = options?.dimensions || 1024;
    this.endpoint = options?.endpoint || 'https://api.voyageai.com/v1/embeddings';
  }

  protected async embedBatch(texts: string[]): Promise<number[][]> {
    const response = await fetch(this.endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${this.apiKey}`,
      },
      body: JSON.stringify({
        model: this.modelName,
        input: texts,
        output_dimension: this.dimensions,
      }),
    });

    if (!response.ok) {
      const body = await response.text().catch(() => '');
      throw new Error(
        `Voyage API error ${response.status}: ${body.slice(0, 200)}`,
      );
    }

    const result = (await response.json()) as VoyageEmbeddingResponse;

    if (result.data.length !== texts.length) {
      throw new Error(
        `Voyage API returned ${result.data.length} embeddings for ${texts.length} inputs`,
      );
    }

    const embeddings = result.data
      .sort((a, b) => a.index - b.index)
      .map((d) => d.embedding);

    // Validate first embedding dimension matches expected
    if (embeddings.length > 0 && embeddings[0]!.length !== this.dimensions) {
      throw new Error(
        `Voyage returned ${embeddings[0]!.length}d embeddings, expected ${this.dimensions}d`,
      );
    }

    return embeddings;
  }
}
