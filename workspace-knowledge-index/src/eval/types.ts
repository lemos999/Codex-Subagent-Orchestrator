export interface GoldQuery {
  query: string;
  relevantChunks: Array<{
    chunkId: string;
    relevance: number; // 0-3: 0=irrelevant, 1=marginal, 2=relevant, 3=highly relevant
  }>;
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
  expectedType?: string;
  actualType?: string;
}

export interface EvalSummary {
  goldSetName: string;
  meanNdcg: number;
  medianNdcg: number;
  minNdcg: number;
  maxNdcg: number;
  queryCount: number;
  results: EvalResult[];
}
