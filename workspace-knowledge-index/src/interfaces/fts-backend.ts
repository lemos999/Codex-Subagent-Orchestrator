import type { Chunk, SearchFilter } from '../types/index.js';

/**
 * Backend adapter for FTS5 full-text search storage.
 */
export interface FtsBackend {
  insert(chunks: Chunk[]): Promise<void>;
  search(query: string, topK: number, filter?: SearchFilter): Promise<FtsSearchResult[]>;
  delete(chunkIds: string[]): Promise<void>;
  rebuild(): Promise<void>;
  close(): Promise<void>;
}

/** A single FTS search result. */
export interface FtsSearchResult {
  chunkId: string;
  score: number;
  highlights?: string[];
}
