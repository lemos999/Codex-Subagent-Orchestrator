import OpenAI from 'openai';
import { BaseEmbeddingProvider } from './base-provider.js';

/**
 * OpenAI embedding provider.
 * Uses text-embedding-3-large (768d) by default.
 */
export class OpenAIEmbeddingProvider extends BaseEmbeddingProvider {
  readonly dimensions: number;
  readonly modelName: string;
  readonly maxBatchSize = 2048;
  readonly maxTokensPerText = 8191;

  private readonly client: OpenAI;

  constructor(options?: {
    apiKey?: string;
    model?: string;
    dimensions?: number;
  }) {
    super();

    const apiKey =
      options?.apiKey ||
      process.env['WKI_OPENAI_KEY'] ||
      process.env['OPENAI_API_KEY'];

    if (!apiKey) {
      throw new Error(
        'OpenAI API key not found. Set WKI_OPENAI_KEY or OPENAI_API_KEY environment variable.',
      );
    }

    this.client = new OpenAI({ apiKey });
    this.modelName = options?.model || 'text-embedding-3-large';
    this.dimensions = options?.dimensions || 768;
  }

  protected async embedBatch(texts: string[]): Promise<number[][]> {
    const response = await this.client.embeddings.create({
      model: this.modelName,
      input: texts,
      dimensions: this.dimensions,
    });

    return response.data
      .sort((a, b) => a.index - b.index)
      .map((d) => d.embedding);
  }
}
