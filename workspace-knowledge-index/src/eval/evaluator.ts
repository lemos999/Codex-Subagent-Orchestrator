import type { SearchService } from '../search/search-service.js';
import { dcg, idcg } from './ndcg.js';
import type { EvalResult, EvalSummary, GoldSet } from './types.js';

/**
 * Evaluate search quality against a gold set.
 * For each query, runs the search service and computes nDCG@k.
 *
 * IDCG is computed from the gold set's full relevance list (not just
 * the retrieved results), so missing a highly relevant chunk correctly
 * lowers the score.
 */
export async function evaluate(
  searchService: SearchService,
  goldSet: GoldSet,
  k: number = 10,
): Promise<EvalSummary> {
  const results: EvalResult[] = [];

  for (let i = 0; i < goldSet.queries.length; i++) {
    const goldQuery = goldSet.queries[i]!;

    const searchResults = await searchService.search(goldQuery.query, {
      topK: k,
      includeContent: false,
    });

    // Build relevance lookup from gold set
    const relevanceLookup = new Map<string, number>();
    for (const rc of goldQuery.relevantChunks) {
      relevanceLookup.set(rc.chunkId, rc.relevance);
    }

    // Map search results to relevance scores (retrieved order)
    const retrievedRelevance = searchResults.map(
      (sr) => relevanceLookup.get(sr.chunk.contentHash) ?? 0,
    );

    // IDCG from the full gold set relevance (not just retrieved results)
    const goldRelevance = goldQuery.relevantChunks.map((rc) => rc.relevance);
    const idealDcg = idcg(goldRelevance, k);
    const actualDcg = dcg(retrievedRelevance, k);
    const score = idealDcg === 0 ? 0 : actualDcg / idealDcg;

    results.push({
      queryIndex: i,
      query: goldQuery.query,
      ndcg: score,
      resultsCount: searchResults.length,
      expectedType: goldQuery.expectedQueryType,
    });
  }

  // Compute summary statistics
  const ndcgValues = results.map((r) => r.ndcg);
  const sorted = [...ndcgValues].sort((a, b) => a - b);

  const meanNdcg =
    ndcgValues.length > 0
      ? ndcgValues.reduce((sum, v) => sum + v, 0) / ndcgValues.length
      : 0;

  const medianNdcg =
    sorted.length === 0
      ? 0
      : sorted.length % 2 === 1
        ? sorted[Math.floor(sorted.length / 2)]!
        : (sorted[sorted.length / 2 - 1]! + sorted[sorted.length / 2]!) / 2;

  return {
    goldSetName: goldSet.name,
    meanNdcg,
    medianNdcg,
    minNdcg: sorted.length > 0 ? sorted[0]! : 0,
    maxNdcg: sorted.length > 0 ? sorted[sorted.length - 1]! : 0,
    queryCount: results.length,
    results,
  };
}
