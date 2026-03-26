export interface GoldChunk {
  /** Primary match: file path (partial match supported) */
  filePath: string;
  /** Optional: line range for precise matching */
  startLine?: number;
  endLine?: number;
  /** Relevance score: 0=irrelevant, 1=marginal, 2=relevant, 3=highly relevant */
  relevance: number;
  /** Legacy: content hash (used as fallback if filePath doesn't match) */
  chunkId?: string;
}

export interface GoldQuery {
  query: string;
  relevantChunks: GoldChunk[];
  expectedQueryType?: string;
}

export interface GoldSet {
  name: string;
  description: string;
  queries: GoldQuery[];
}

export interface EvalResult {
  queryIndex: number;
  query: string;
  ndcg: number;
  resultsCount: number;
  matchedCount: number;
  expectedType?: string;
  actualType?: string;
}

export interface SubsetStats {
  count: number;
  meanNdcg: number;
}

export interface EvalSummary {
  goldSetName: string;
  meanNdcg: number;
  medianNdcg: number;
  minNdcg: number;
  maxNdcg: number;
  queryCount: number;
  results: EvalResult[];
  /** Breakdown: queries where gold chunks have only filePath (no line range) */
  fileOnlySubset?: SubsetStats;
  /** Breakdown: queries where gold chunks have line range */
  lineScopedSubset?: SubsetStats;
}
