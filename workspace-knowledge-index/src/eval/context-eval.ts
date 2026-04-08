/**
 * context-eval.ts
 * MRR@3 (Mean Reciprocal Rank at 3) evaluation for project-context queries.
 *
 * MRR@3: For each query, look at the top 3 search results.
 *   - If a relevant file appears at rank 1 -> reciprocal rank = 1/1 = 1.0
 *   - If at rank 2 -> 1/2 = 0.5
 *   - If at rank 3 -> 1/3 = 0.333
 *   - If none match -> 0
 * MRR@3 = mean of reciprocal ranks across all queries.
 */

import fs from 'node:fs';
import path from 'node:path';
import type { SearchService } from '../search/search-service.js';
import type { SearchResult } from '../types/index.js';

/** A single relevant file entry in the evaluation set. */
export interface ContextRelevant {
  file: string;
  section?: string;
}

/** A single evaluation query. */
export interface ContextQuery {
  query: string;
  relevant: ContextRelevant[];
  type: string;
}

/** Per-query evaluation result. */
export interface ContextEvalResult {
  queryIndex: number;
  query: string;
  type: string;
  reciprocalRank: number;
  firstMatchRank: number | null;
  topResults: string[];
}

/** Overall evaluation summary. */
export interface ContextEvalSummary {
  datasetName: string;
  queryCount: number;
  mrr3: number;
  results: ContextEvalResult[];
  hitRate: number;
}

/**
 * Check if a search result's filePath matches a relevant file using endsWith partial matching.
 */
function fileMatches(resultPath: string, relevantFile: string): boolean {
  const normalized = resultPath.replace(/\\/g, '/');
  const normalizedRelevant = relevantFile.replace(/\\/g, '/');
  return normalized.endsWith(normalizedRelevant) || normalized.includes(normalizedRelevant);
}

/**
 * Evaluate context search quality using MRR@3.
 */
export async function evaluateContext(
  searchService: SearchService,
  queries: ContextQuery[],
): Promise<ContextEvalSummary> {
  const results: ContextEvalResult[] = [];

  for (let i = 0; i < queries.length; i++) {
    const q = queries[i]!;
    const searchResults = await searchService.search(q.query, {
      topK: 3,
      includeContent: false,
    });

    // Find the first rank (1-indexed) where a relevant file appears
    let firstMatchRank: number | null = null;
    const topResults: string[] = [];

    for (let rank = 0; rank < searchResults.length; rank++) {
      const sr = searchResults[rank]!;
      const filePath = sr.chunk.filePath;
      topResults.push(filePath);

      if (firstMatchRank === null) {
        for (const rel of q.relevant) {
          if (fileMatches(filePath, rel.file)) {
            firstMatchRank = rank + 1; // 1-indexed
            break;
          }
        }
      }
    }

    const reciprocalRank = firstMatchRank !== null ? 1 / firstMatchRank : 0;

    results.push({
      queryIndex: i,
      query: q.query,
      type: q.type,
      reciprocalRank,
      firstMatchRank,
      topResults,
    });
  }

  const mrr3 =
    results.length > 0
      ? results.reduce((sum, r) => sum + r.reciprocalRank, 0) / results.length
      : 0;

  const hitRate =
    results.length > 0
      ? results.filter((r) => r.firstMatchRank !== null).length / results.length
      : 0;

  return {
    datasetName: 'context-queries-v1',
    queryCount: results.length,
    mrr3,
    results,
    hitRate,
  };
}

/**
 * Print evaluation summary to console.
 */
export function printContextEvalSummary(summary: ContextEvalSummary): void {
  console.log(`\nContext Evaluation: ${summary.datasetName}`);
  console.log(`Queries: ${summary.queryCount}  |  MRR@3\n`);

  for (const result of summary.results) {
    const rankInfo =
      result.firstMatchRank !== null
        ? `rank ${result.firstMatchRank}`
        : 'miss';
    console.log(
      `  ${(result.queryIndex + 1).toString().padStart(2)}. [${result.reciprocalRank.toFixed(3)}] "${result.query}" [${result.type}] (${rankInfo})`,
    );
    for (let j = 0; j < result.topResults.length; j++) {
      const marker =
        result.firstMatchRank === j + 1 ? ' <<' : '';
      console.log(
        `      ${j + 1}. ${result.topResults[j]}${marker}`,
      );
    }
  }

  console.log(`\n  MRR@3:     ${summary.mrr3.toFixed(3)}`);
  console.log(`  Hit Rate:  ${(summary.hitRate * 100).toFixed(1)}%`);
}
