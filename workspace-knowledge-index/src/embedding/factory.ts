import type { EmbeddingConfig } from '../config/schema.js';
import type { EmbeddingProvider } from '../interfaces/embedding.js';

/**
 * Create an EmbeddingProvider from config.
 * Uses dynamic import to avoid loading unnecessary dependencies.
 */
export async function createEmbeddingProvider(
  config: EmbeddingConfig,
): Promise<EmbeddingProvider> {
  switch (config.provider) {
    case 'openai': {
      const { OpenAIEmbeddingProvider } = await import('./openai-provider.js');
      return new OpenAIEmbeddingProvider({
        model: config.openai?.model,
        dimensions: config.openai?.dimensions,
      });
    }
    case 'voyage': {
      const { VoyageEmbeddingProvider } = await import('./voyage-provider.js');
      return new VoyageEmbeddingProvider({
        model: config.voyage?.model,
        dimensions: config.voyage?.dimensions,
      });
    }
    case 'local': {
      const { LocalEmbeddingProvider } = await import('./local-provider.js');
      return new LocalEmbeddingProvider({
        model: config.local?.model,
        dimensions: config.local?.dimensions,
      });
    }
    default:
      throw new Error(`Unknown embedding provider: "${config.provider}"`);
  }
}
