import type { EmbeddingProvider } from '../interfaces/embedding.js';

export interface BatchEmbedResult {
  embeddings: (number[] | null)[];
  failures: Array<{ index: number; error: string }>;
}

/**
 * Base class for embedding providers with automatic batching,
 * chunked splitting, and exponential-backoff retry.
 */
export abstract class BaseEmbeddingProvider implements EmbeddingProvider {
  abstract readonly dimensions: number;
  abstract readonly modelName: string;
  abstract readonly maxBatchSize: number;
  abstract readonly maxTokensPerText: number;

  /** Single text embedding -- delegates to batchEmbed([text]). */
  async embed(text: string): Promise<number[]> {
    const results = await this.batchEmbed([text]);
    return results[0];
  }

  /** Batch embedding with auto-splitting and retry. */
  async batchEmbed(texts: string[]): Promise<number[][]> {
    if (texts.length === 0) {
      return [];
    }

    const allResults: number[][] = new Array<number[]>(texts.length);

    // Split into maxBatchSize chunks
    for (let offset = 0; offset < texts.length; offset += this.maxBatchSize) {
      const batchTexts = texts.slice(offset, offset + this.maxBatchSize);
      const batchResults = await this.embedBatchWithRetry(batchTexts, offset);

      if (batchResults.length !== batchTexts.length) {
        throw new Error(
          `Embedding provider returned ${batchResults.length} results for ${batchTexts.length} inputs (batch offset=${offset})`,
        );
      }

      for (let i = 0; i < batchResults.length; i++) {
        allResults[offset + i] = batchResults[i];
      }
    }

    return allResults;
  }

  /**
   * Retry wrapper: exponential backoff (1s -> 2s -> 4s), max 3 attempts.
   * On final failure, fills the batch with zero vectors and logs a warning.
   */
  private async embedBatchWithRetry(
    texts: string[],
    globalOffset: number,
  ): Promise<number[][]> {
    const MAX_RETRIES = 3;
    const BASE_DELAY_MS = 1000;

    for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
      try {
        return await this.embedBatch(texts);
      } catch (error: unknown) {
        const message = error instanceof Error ? error.message : String(error);

        if (attempt < MAX_RETRIES) {
          const delayMs = BASE_DELAY_MS * Math.pow(2, attempt - 1);
          console.warn(
            `[WKI] Embedding batch (offset=${globalOffset}) attempt ${attempt}/${MAX_RETRIES} failed: ${message}. Retrying in ${delayMs}ms...`,
          );
          await this.sleep(delayMs);
        } else {
          throw new Error(
            `Embedding batch (offset=${globalOffset}) failed after ${MAX_RETRIES} attempts: ${message}`,
          );
        }
      }
    }

    // Unreachable — the loop always returns or throws
    throw new Error('Unreachable');
  }

  /** Subclass implements the actual API call for a single batch. */
  protected abstract embedBatch(texts: string[]): Promise<number[][]>;

  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}
