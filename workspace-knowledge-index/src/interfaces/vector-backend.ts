import type { ChunkWithEmbedding, VectorSearchResult, SearchFilter } from '../types/index.js';

/**
 * Backend adapter for vector storage and similarity search.
 * Implementations: LanceDB (Phase 1), Qdrant (Phase 2+).
 */
export interface VectorBackend {
  insert(chunks: ChunkWithEmbedding[]): Promise<void>;
  search(query: number[], topK: number, filter?: SearchFilter): Promise<VectorSearchResult[]>;
  delete(chunkIds: string[]): Promise<void>;
  rebuild(): Promise<void>;
  close(): Promise<void>;
}
