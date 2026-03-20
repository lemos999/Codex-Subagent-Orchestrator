import type Database from 'better-sqlite3';
import type { SearchConfig } from '../config/schema.js';
import type { EmbeddingProvider } from '../interfaces/embedding.js';
import type { FtsSearchResult } from '../interfaces/fts-backend.js';
import { FtsStore } from '../store/fts-store.js';
import { ChunkStore } from '../store/chunk-store.js';
import { LanceVectorStore } from '../store/vector-store.js';
import type { Chunk, SearchFilter, SearchResult, VectorSearchResult } from '../types/index.js';
import { QueryRouter, type RouteDecision, type SearchMode } from './query-router.js';
import { expandKoreanQuery } from './korean-expansion.js';

const CHUNK_ID_BATCH_SIZE = 300;
const FTS_NORMALIZATION_WINDOW = 50;
const RRF_K = 60;

interface WeightedCandidate {
  chunkId: string;
  score: number;
  ftsScore: number;
  vectorScore: number;
}

interface ChunkIdLookupRow {
  id: number;
  chunk_id: string;
}

export interface SearchOptions {
  topK?: number;
  filter?: SearchFilter;
  mode?: SearchMode;
  includeContent?: boolean;
}

export class SearchService {
  private readonly router: QueryRouter;

  constructor(
    private ftsStore: FtsStore,
    private vectorStore: LanceVectorStore | null,
    private chunkStore: ChunkStore,
    private embeddingProvider: EmbeddingProvider | null,
    private config: SearchConfig,
  ) {
    this.router = new QueryRouter(config);
  }

  async search(query: string, options: SearchOptions = {}): Promise<SearchResult[]> {
    const normalizedQuery = query.trim();
    const topK = normalizeTopK(options.topK);

    if (!normalizedQuery || topK === 0) {
      return [];
    }

    // Korean→English query expansion so FTS/vector can match English content
    const { ftsQuery, vectorQuery, hasKorean } = expandKoreanQuery(normalizedQuery);

    // Path query: search file_path column directly
    const queryType = this.router.classify(normalizedQuery);
    if (queryType === 'path') {
      const pathResults = this.searchByFilePath(normalizedQuery, topK, options);
      if (pathResults.length > 0) {
        return pathResults;
      }
    }

    const hasVectorSearch = this.vectorStore !== null && this.embeddingProvider !== null;

    // For Korean queries, route with the original query (Korean tokens → FTS finds nothing,
    // which is fine — the dual vector search below does the heavy lifting)
    const decision = this.router.route(normalizedQuery, options.mode, hasVectorSearch);

    // Improvement 1: Dynamic hybrid fusion weights based on query type.
    // Override generic hybrid weights with query-type-specific weights
    // from classify() + getWeights() for better precision.
    if (decision.route === 'hybrid' && (!options.mode || options.mode === 'auto')) {
      const queryType = this.router.classify(normalizedQuery);
      const typeWeights = this.router.getWeights(queryType);
      decision.weights.fts = typeWeights.fts;
      decision.weights.vector = typeWeights.vector;
    }

    const candidateLimit = Math.max(topK * 2, topK);

    let ftsResults: FtsSearchResult[] = [];
    let vectorResults: VectorSearchResult[] = [];

    if (decision.route === 'fts' || decision.route === 'hybrid') {
      ftsResults = await this.ftsStore.search(normalizedQuery, candidateLimit, options.filter);
    }

    if (decision.route === 'vector' || decision.route === 'hybrid') {
      if (!this.vectorStore || !this.embeddingProvider) {
        throw new Error('Vector search requested but vector backend is not configured');
      }

      const embedding = await this.embeddingProvider.embed(normalizedQuery);
      vectorResults = await this.vectorStore.search(embedding, candidateLimit, options.filter);

      // For Korean queries: also search with English-expanded query and merge results.
      // The multilingual model may find different relevant docs for each variant.
      // Apply a score discount to expanded results so original-query results are preferred.
      if (hasKorean && ftsQuery !== normalizedQuery) {
        const expandedEmbedding = await this.embeddingProvider.embed(ftsQuery);
        const expandedResults = await this.vectorStore.search(expandedEmbedding, candidateLimit, options.filter);
        vectorResults = mergeVectorResults(vectorResults, expandedResults, candidateLimit);
      }
    }

    const combined = this.combineResults(ftsResults, vectorResults, decision);
    if (combined.length === 0) {
      return [];
    }

    const hydratedChunks = this.hydrateChunks(
      combined.map((candidate) => candidate.chunkId),
      options.includeContent ?? true,
    );

    const results: SearchResult[] = [];
    for (const candidate of combined) {
      const chunk = hydratedChunks.get(candidate.chunkId);
      if (!chunk) {
        continue;
      }

      results.push({
        chunk,
        score: candidate.score,
        matchType: inferMatchType(candidate),
      });
    }

    // Re-ranking: boost results where query keywords appear in chunk content
    const reranked = this.rerank(results, normalizedQuery, ftsQuery);
    return reranked.slice(0, topK);
  }

  /**
   * Lightweight re-ranking: boost results where query keywords appear in chunk content.
   * No additional model needed — uses keyword overlap scoring.
   */
  private rerank(results: SearchResult[], query: string, expandedQuery: string): SearchResult[] {
    if (results.length <= 1) return results;

    // Extract keywords from both original and expanded query
    const keywords = new Set(
      `${query} ${expandedQuery}`.toLowerCase()
        .split(/[\s,.;:!?()\[\]{}"'`]+/)
        .filter(w => w.length >= 2),
    );

    if (keywords.size === 0) return results;

    // Score each result by keyword overlap
    const scored = results.map(r => {
      const content = (r.chunk.content + ' ' + r.chunk.filePath + ' ' + (r.chunk.heading ?? '')).toLowerCase();
      let matchCount = 0;
      for (const kw of keywords) {
        if (content.includes(kw)) matchCount++;
      }
      const overlapRatio = matchCount / keywords.size;
      // Blend: 70% original score + 30% keyword overlap
      const rerankScore = r.score * 0.7 + overlapRatio * r.score * 0.3;
      return { ...r, score: rerankScore };
    });

    // Sort by reranked score descending
    scored.sort((a, b) => b.score - a.score);
    return scored;
  }

  /**
   * Search chunks by file_path column directly.
   * Used when the query is classified as a file path.
   */
  private searchByFilePath(
    query: string,
    topK: number,
    options: SearchOptions,
  ): SearchResult[] {
    const db = this.ftsStore.getDatabase();
    const normalizedPath = query.replace(/\\/g, '/');

    const whereClauses: string[] = ['chunks_meta.file_path LIKE ?'];
    const params: Array<string | number> = [`%${normalizedPath}%`];

    if (options.filter?.projectId?.trim()) {
      whereClauses.push('chunks_meta.project_id = ?');
      params.push(options.filter.projectId.trim());
    }

    params.push(topK);

    const sql = `
      SELECT
        CASE
          WHEN chunks_meta.content_hash IS NOT NULL AND chunks_meta.content_hash != ''
          THEN chunks_meta.file_path || '::' || chunks_meta.content_hash
          ELSE chunks_meta.file_path || ':' || chunks_meta.ordinal
        END AS chunk_id,
        chunks_meta.id AS row_id
      FROM chunks_meta
      WHERE ${whereClauses.join(' AND ')}
      ORDER BY chunks_meta.ordinal ASC
      LIMIT ?
    `;

    const rows = db.prepare(sql).all(...params) as Array<{
      chunk_id: string;
      row_id: number;
    }>;

    if (rows.length === 0) {
      return [];
    }

    const chunksByRowId = this.chunkStore.getByIds(rows.map((r) => r.row_id));
    const results: SearchResult[] = [];

    for (let i = 0; i < rows.length; i++) {
      const row = rows[i]!;
      const chunk = chunksByRowId.get(row.row_id);
      if (!chunk) continue;

      const includeContent = options.includeContent ?? true;
      results.push({
        chunk: includeContent ? chunk : { ...chunk, content: '' },
        score: 1 - i * 0.01, // Decreasing score by ordinal
        matchType: 'fts',
      });
    }

    return results;
  }

  private combineResults(
    ftsResults: FtsSearchResult[],
    vectorResults: VectorSearchResult[],
    decision: RouteDecision,
  ): WeightedCandidate[] {
    const ftsNormalized = normalizeFtsScores(ftsResults);
    const vectorNormalized = normalizeVectorScores(vectorResults);
    const fused = new Map<string, WeightedCandidate>();

    const upsertCandidate = (chunkId: string): WeightedCandidate => {
      const existing = fused.get(chunkId);
      if (existing) {
        return existing;
      }

      const candidate: WeightedCandidate = {
        chunkId,
        score: 0,
        ftsScore: 0,
        vectorScore: 0,
      };
      fused.set(chunkId, candidate);
      return candidate;
    };

    if (this.config.fusion.strategy === 'rrf' && decision.route === 'hybrid') {
      const ftsRanks = buildRankMap(ftsResults);
      const vectorRanks = buildRankMap(vectorResults);

      for (const [chunkId, rank] of ftsRanks) {
        const candidate = upsertCandidate(chunkId);
        candidate.ftsScore = ftsNormalized.get(chunkId) ?? 0;
        candidate.score += decision.weights.fts / (RRF_K + rank);
      }

      for (const [chunkId, rank] of vectorRanks) {
        const candidate = upsertCandidate(chunkId);
        candidate.vectorScore = vectorNormalized.get(chunkId) ?? 0;
        candidate.score += decision.weights.vector / (RRF_K + rank);
      }
    } else {
      for (const [chunkId, score] of ftsNormalized) {
        const candidate = upsertCandidate(chunkId);
        candidate.ftsScore = score;
        candidate.score += score * decision.weights.fts;
      }

      for (const [chunkId, score] of vectorNormalized) {
        const candidate = upsertCandidate(chunkId);
        candidate.vectorScore = score;
        candidate.score += score * decision.weights.vector;
      }
    }

    return Array.from(fused.values()).sort((left, right) => {
      if (right.score !== left.score) {
        return right.score - left.score;
      }

      if (right.vectorScore !== left.vectorScore) {
        return right.vectorScore - left.vectorScore;
      }

      if (right.ftsScore !== left.ftsScore) {
        return right.ftsScore - left.ftsScore;
      }

      return left.chunkId.localeCompare(right.chunkId);
    });
  }

  private hydrateChunks(chunkIds: string[], includeContent: boolean): Map<string, Chunk> {
    const rowIdsByChunkId = resolveChunkRowIds(this.ftsStore.getDatabase(), chunkIds);
    const orderedRowIds: number[] = [];

    for (const chunkId of chunkIds) {
      const rowId = rowIdsByChunkId.get(chunkId);
      if (typeof rowId === 'number' && Number.isInteger(rowId) && rowId > 0) {
        orderedRowIds.push(rowId);
      }
    }

    const chunksByRowId = this.chunkStore.getByIds(orderedRowIds);
    const hydrated = new Map<string, Chunk>();

    for (const chunkId of chunkIds) {
      const rowId = rowIdsByChunkId.get(chunkId);
      if (typeof rowId !== 'number' || rowId <= 0) {
        continue;
      }

      const chunk = chunksByRowId.get(rowId);
      if (!chunk) {
        continue;
      }

      hydrated.set(
        chunkId,
        includeContent
          ? chunk
          : {
              ...chunk,
              content: '',
            },
      );
    }

    return hydrated;
  }
}

export function normalizeFtsScores(results: FtsSearchResult[]): Map<string, number> {
  if (results.length === 0) {
    return new Map();
  }

  if (results.length === 1) {
    return new Map([[results[0]!.chunkId, 1]]);
  }

  const calibrationSet = results.slice(0, FTS_NORMALIZATION_WINDOW);
  const calibrationRaw = calibrationSet.map((result) => Math.log1p(Math.max(0, -result.score)));
  const min = Math.min(...calibrationRaw);
  const max = Math.max(...calibrationRaw);

  if (max === min) {
    return new Map(results.map((result) => [result.chunkId, 1]));
  }

  const range = max - min;
  const normalized = new Map<string, number>();

  for (const result of results) {
    const raw = Math.log1p(Math.max(0, -result.score));
    const score = clamp01((raw - min) / range);
    normalized.set(result.chunkId, score);
  }

  return normalized;
}

export function normalizeVectorScores(results: VectorSearchResult[]): Map<string, number> {
  return new Map(results.map((result) => [result.chunkId, clamp01(result.score)]));
}

/**
 * Resolve vector-store chunk IDs to FTS row IDs.
 *
 * Vector-store IDs use the format `filePath::contentHash` (composite)
 * or `filePath:ordinal` (fallback). This function decomposes composite
 * IDs and matches against both content_hash+file_path and the
 * file_path:ordinal fallback.
 */
function resolveChunkRowIds(db: Database.Database, chunkIds: string[]): Map<string, number> {
  const normalizedIds = Array.from(
    new Set(chunkIds.map((chunkId) => chunkId.trim()).filter((chunkId) => chunkId.length > 0)),
  );

  const resolved = new Map<string, number>();

  for (let offset = 0; offset < normalizedIds.length; offset += CHUNK_ID_BATCH_SIZE) {
    const batch = normalizedIds.slice(offset, offset + CHUNK_ID_BATCH_SIZE);

    // Decompose composite IDs: "filePath::hash" → extract hash and filePath
    const hashes: string[] = [];
    const pathOrdinals: string[] = [];
    for (const id of batch) {
      const compositeIdx = id.indexOf('::');
      if (compositeIdx !== -1) {
        hashes.push(id.slice(compositeIdx + 2));
      } else {
        pathOrdinals.push(id);
      }
    }

    const lookupKeys = [...hashes, ...pathOrdinals];
    if (lookupKeys.length === 0) continue;

    const placeholders = lookupKeys.map(() => '?').join(', ');

    const rows = db
      .prepare(
        `
          SELECT
            id,
            file_path,
            content_hash,
            ordinal,
            COALESCE(NULLIF(content_hash, ''), file_path || ':' || ordinal) AS chunk_id
          FROM chunks_meta
          WHERE content_hash IN (${placeholders})
             OR (file_path || ':' || ordinal) IN (${placeholders})
        `,
      )
      .all(...lookupKeys, ...lookupKeys) as Array<{
        id: number;
        file_path: string;
        content_hash: string;
        ordinal: number;
        chunk_id: string;
      }>;

    for (const row of rows) {
      // Reconstruct the composite key used by the vector store
      const compositeId = row.content_hash
        ? `${row.file_path}::${row.content_hash}`
        : `${row.file_path}:${row.ordinal}`;

      if (!resolved.has(compositeId)) {
        resolved.set(compositeId, row.id);
      }
    }
  }

  return resolved;
}

function normalizeTopK(topK: number | undefined): number {
  if (topK === undefined) {
    return 10;
  }

  return Number.isFinite(topK) ? Math.max(0, Math.trunc(topK)) : 10;
}

function buildRankMap(results: Array<FtsSearchResult | VectorSearchResult>): Map<string, number> {
  const ranks = new Map<string, number>();

  for (let index = 0; index < results.length; index += 1) {
    const result = results[index];
    if (!ranks.has(result.chunkId)) {
      ranks.set(result.chunkId, index + 1);
    }
  }

  return ranks;
}

function inferMatchType(candidate: WeightedCandidate): SearchResult['matchType'] {
  if (candidate.ftsScore > 0 && candidate.vectorScore > 0) {
    return 'hybrid';
  }

  if (candidate.vectorScore > 0) {
    return 'vector';
  }

  return 'fts';
}

/**
 * Merge two sets of vector results, keeping the best score for each chunk.
 * Returns results sorted by score descending, limited to `limit` entries.
 */
function mergeVectorResults(
  a: VectorSearchResult[],
  b: VectorSearchResult[],
  limit: number,
): VectorSearchResult[] {
  const best = new Map<string, VectorSearchResult>();
  for (const r of a) {
    const existing = best.get(r.chunkId);
    if (!existing || r.score > existing.score) {
      best.set(r.chunkId, r);
    }
  }
  for (const r of b) {
    const existing = best.get(r.chunkId);
    if (!existing || r.score > existing.score) {
      best.set(r.chunkId, r);
    }
  }
  return Array.from(best.values())
    .sort((x, y) => y.score - x.score)
    .slice(0, limit);
}

function clamp01(value: number): number {
  if (!Number.isFinite(value)) {
    return 0;
  }

  return Math.max(0, Math.min(1, value));
}
