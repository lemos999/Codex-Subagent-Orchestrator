// ============================================================
// WKI Core Types
// ============================================================

export type ChunkType =
  | 'function'
  | 'class'
  | 'interface'
  | 'type'
  | 'enum'
  | 'variable'
  | 'import'
  | 'export'
  | 'markdown-section'
  | 'line-block'
  | 'other';

/** A raw chunk output from a Parser (before ID/token assignment). */
export interface RawChunk {
  filePath: string;
  ordinal: number;
  content: string;
  heading?: string;
  chunkType: ChunkType;
  startLine: number;
  endLine: number;
}

/** A fully enriched chunk ready for storage. */
export interface Chunk extends RawChunk {
  id: string;           // 외부 식별자: `${projectId}:${filePath}:${ordinal}` (참고용, 검색 경로에서는 미사용)
  rowId?: number;       // FTS5 DB 내부 식별자 (INTEGER PRIMARY KEY)
  projectId: string;
  tokenCount: number;
  contentHash: string;
}

/** A chunk with its computed embedding vector. */
export interface ChunkWithEmbedding extends Chunk {
  embedding: number[];
}

/** A search result returned to the caller. */
export interface SearchResult {
  chunk: Chunk;
  score: number;
  matchType: 'fts' | 'vector' | 'hybrid' | 'graph';
}

/** A raw vector search result (before hydration). */
export interface VectorSearchResult {
  chunkId: string;
  score: number;
}

/** Filter criteria for search queries. */
export interface SearchFilter {
  projectId?: string;
  fileType?: string;
  symbolKind?: string;
  /** Restrict results to chunks from these file paths (substring match). */
  filePaths?: string[];
}

/** Symbol information extracted by ProgramParser. */
export interface SymbolInfo {
  name: string;
  kind: string;  // 'function' | 'class' | 'method' | 'property' | 'interface' | 'type' | 'enum' | 'variable' | 'namespace' | 'module' | 'getter' | 'setter' | 'enumMember' | 'decorator' 등
  filePath: string;
  startLine: number;
  endLine: number;
  signature?: string;
  docstring?: string;
  exported: boolean;
  modifiers?: string[];
}

/** Import relationship extracted by ProgramParser. */
export interface ImportInfo {
  source: string;
  target: string;
  specifiers: string[];
  isTypeOnly: boolean;
}

/** Dependency graph composed of ImportInfo edges. */
export interface DepsGraph {
  edges: ImportInfo[];
}

/** Git-based freshness state for incremental indexing. */
export interface FreshnessState {
  head_commit: string;
  branch: string;
  dirty: boolean;
  staged_fingerprint: string;
  untracked_fingerprint: string;
  untracked_files?: string[];
  file_hashes: Record<string, string>;
  indexed_at: string;
}

/** An entry in the file map. */
export interface FileMapEntry {
  path: string;
  size: number;
  type: string;
  symbols?: string[];
  headings?: string[];
}

/** Query classification types for the Query Router. */
export type QueryType = 'identifier' | 'path' | 'natural' | 'deps' | 'mixed';

// ============================================================
// Symbol Search Types
// ============================================================

/** Options for symbol search queries. */
export interface SymbolSearchOptions {
  /** Symbol name pattern (exact, prefix, or regex). */
  name?: string;
  /** Match mode for the name field. */
  nameMode?: 'exact' | 'prefix' | 'contains' | 'regex';
  /** Filter by symbol kind (function, class, interface, etc.). */
  kind?: string;
  /** Filter to only exported symbols. */
  exportedOnly?: boolean;
  /** Filter by file path pattern (substring match). */
  filePath?: string;
  /** Maximum results to return. */
  topK?: number;
}

/** A single symbol search result. */
export interface SymbolSearchResult {
  symbol: SymbolInfo;
  /** How well this result matched the query (0-1). */
  score: number;
}
