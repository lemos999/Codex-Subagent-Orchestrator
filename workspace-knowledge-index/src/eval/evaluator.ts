import type { SearchService } from '../search/search-service.js';
import type { SearchResult } from '../types/index.js';
import { dcg, idcg } from './ndcg.js';
import type { EvalResult, EvalSummary, GoldChunk, GoldSet } from './types.js';

/**
 * Match a search result against a gold chunk.
 *
 * Matching priority:
 * 1. filePath contains gold.filePath (partial match — handles absolute vs relative paths)
 * 2. If gold has startLine/endLine, check line range overlap
 * 3. Fallback: content hash exact match (legacy)
 */
function matchesGoldChunk(result: SearchResult, gold: GoldChunk): boolean {
  // Normalize paths for comparison
  const resultPath = result.chunk.filePath.replace(/\\/g, '/');
  const goldPath = gold.filePath.replace(/\\/g, '/');

  // Path match: result path must contain the gold path (handles absolute/relative)
  if (!resultPath.includes(goldPath)) {
    // Fallback: legacy content hash match
    if (gold.chunkId && result.chunk.contentHash === gold.chunkId) {
      return true;
    }
    return false;
  }

  // If gold specifies line range, check overlap
  if (gold.startLine !== undefined && gold.endLine !== undefined) {
    const rStart = result.chunk.startLine;
    const rEnd = result.chunk.endLine;
    // Overlap: result range intersects gold range
    return rStart <= gold.endLine && rEnd >= gold.startLine;
  }

  // Path matched, no line range specified → match
  return true;
}

/**
 * Find the best matching gold chunk for a search result.
 * Returns the relevance score (0 if no match).
 */
function findRelevance(result: SearchResult, goldChunks: GoldChunk[]): number {
  let bestRelevance = 0;
  for (const gold of goldChunks) {
    if (matchesGoldChunk(result, gold) && gold.relevance > bestRelevance) {
      bestRelevance = gold.relevance;
    }
  }
  return bestRelevance;
}

/**
 * Evaluate search quality against a gold set.
 * For each query, runs the search service and computes nDCG@k.
 *
 * Uses file_path + line_range matching (stable across code changes)
 * with content_hash as fallback (legacy gold sets).
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

    // Map search results to relevance scores (retrieved order)
    // Fix: each gold chunk can only be matched once (dedupe to prevent nDCG > 1)
    const usedGoldIndices = new Set<number>();
    const retrievedRelevance = searchResults.map((sr) => {
      let bestRelevance = 0;
      let bestIndex = -1;
      for (let gi = 0; gi < goldQuery.relevantChunks.length; gi++) {
        if (usedGoldIndices.has(gi)) continue;
        const gold = goldQuery.relevantChunks[gi]!;
        if (matchesGoldChunk(sr, gold) && gold.relevance > bestRelevance) {
          bestRelevance = gold.relevance;
          bestIndex = gi;
        }
      }
      if (bestIndex >= 0) usedGoldIndices.add(bestIndex);
      return bestRelevance;
    });

    const matchedCount = retrievedRelevance.filter((r) => r > 0).length;

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
      matchedCount,
      expectedType: goldQuery.expectedQueryType,
    });
  }

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
