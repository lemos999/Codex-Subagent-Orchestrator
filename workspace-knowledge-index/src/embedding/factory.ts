import type { EmbeddingConfig } from '../config/schema.js';
import type { EmbeddingProvider } from '../interfaces/embedding.js';

export type EmbeddingPurpose = 'index' | 'search';

/**
 * Resolve the effective dtype for the given purpose.
 * Priority: purpose-specific override > general dtype > 'fp32'
 */
function resolveDtype(config: EmbeddingConfig, purpose: EmbeddingPurpose): string {
  const local = config.local;
  if (!local) return 'fp32';
  if (purpose === 'index' && local.indexDtype) return local.indexDtype;
  if (purpose === 'search' && local.searchDtype) return local.searchDtype;
  return local.dtype ?? 'fp32';
}

/**
 * Create an EmbeddingProvider from config.
 * Uses dynamic import to avoid loading unnecessary dependencies.
 *
 * @param purpose - 'index' for batch indexing, 'search' for query embedding.
 *   When indexDtype/searchDtype are set in config, different dtypes are used.
 */
export async function createEmbeddingProvider(
  config: EmbeddingConfig,
  purpose: EmbeddingPurpose = 'search',
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
        dtype: resolveDtype(config, purpose),
      });
    }
    default:
      throw new Error(`Unknown embedding provider: "${config.provider}"`);
  }
}
