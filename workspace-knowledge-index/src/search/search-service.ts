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
import { crossEncoderRerank } from './cross-encoder-reranker.js';

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
  private readonly isQuantizedIndex: boolean;

  constructor(
    private ftsStore: FtsStore,
    private vectorStore: LanceVectorStore | null,
    private chunkStore: ChunkStore,
    private embeddingProvider: EmbeddingProvider | null,
    private config: SearchConfig,
  ) {
    this.router = new QueryRouter(config);
    this.isQuantizedIndex = config.indexDtype === 'q8' || config.indexDtype === 'q4';
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

    // Mixed path+content query decomposition:
    // "engine-adapters.md codex gemini claude" → path search for file + hybrid search for content
    let pathBoostResults: SearchResult[] = [];
    const tokens = normalizedQuery.split(/\s+/);
    const pathTokens = tokens.filter(t => /[/\\]|\.(?:ts|tsx|js|jsx|md|json)$/.test(t));
    const contentTokens = tokens.filter(t => !/[/\\]|\.(?:ts|tsx|js|jsx|md|json)$/.test(t));

    if (pathTokens.length > 0 && contentTokens.length >= 2) {
      // Mixed query: get path results as boost candidates, continue to hybrid search
      pathBoostResults = this.searchByFilePath(pathTokens.join(' '), topK, options);
    } else if (queryType === 'path') {
      // Pure path query: early return
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
      const typeWeights = this.router.getWeights(queryType);
      decision.weights.fts = typeWeights.fts;
      decision.weights.vector = typeWeights.vector;
    }

    // For mixed path+content queries, force hybrid route
    if (pathBoostResults.length > 0 && decision.route === 'fts') {
      decision.route = 'hybrid';
      decision.weights = { fts: 0.4, vector: 0.6 };
    }

    const candidateLimit = Math.max(topK * 5, topK);

    let ftsResults: FtsSearchResult[] = [];
    let vectorResults: VectorSearchResult[] = [];

    if (decision.route === 'fts' || decision.route === 'hybrid') {
      ftsResults = await this.ftsStore.search(normalizedQuery, candidateLimit, options.filter);
    }

    if (decision.route === 'vector' || decision.route === 'hybrid') {
      if (!this.vectorStore || !this.embeddingProvider) {
        throw new Error('Vector search requested but vector backend is not configured');
      }

      // Use vectorQuery (original + English expansion) for richer embedding
      const vectorSearchQuery = hasKorean && vectorQuery !== normalizedQuery ? vectorQuery : normalizedQuery;
      const embedding = await this.embeddingProvider.embed(vectorSearchQuery);
      vectorResults = await this.vectorStore.search(embedding, candidateLimit, options.filter);

      // For Korean queries: also search with English-expanded query and merge results.
      if (hasKorean && ftsQuery !== normalizedQuery) {
        const expandedEmbedding = await this.embeddingProvider.embed(ftsQuery);
        const expandedResults = await this.vectorStore.search(expandedEmbedding, candidateLimit, options.filter);
        vectorResults = mergeVectorResults(vectorResults, expandedResults, candidateLimit);
      }

      // Multi-vector search: decompose query and search from multiple angles
      const queryTokens = normalizedQuery.split(/\s+/).filter(t => t.length >= 3);
      if (queryTokens.length >= 3 && !hasKorean) {
        const STOP_WORDS = new Set(['the', 'a', 'an', 'and', 'or', 'is', 'are', 'in', 'of', 'for', 'to', 'how', 'does', 'what', 'where', 'why']);
        const contentWords = queryTokens.filter(t => !STOP_WORDS.has(t.toLowerCase()));

        if (contentWords.length >= 2 && contentWords.length < queryTokens.length) {
          try {
            const keyPhraseQuery = contentWords.join(' ');
            const keyPhraseEmbedding = await this.embeddingProvider.embed(keyPhraseQuery);
            const keyPhraseResults = await this.vectorStore.search(keyPhraseEmbedding, candidateLimit, options.filter);
            vectorResults = mergeVectorResults(vectorResults, keyPhraseResults, candidateLimit);
          } catch { /* fail-soft */ }
        }

        // Sliding window for any query with 5+ content words (not just stop-word-free queries)
        if (contentWords.length >= 5) {
          const mid = Math.ceil(contentWords.length / 2);
          const firstHalf = contentWords.slice(0, mid + 1).join(' ');
          const secondHalf = contentWords.slice(mid - 1).join(' ');
          try {
            const [emb1, emb2] = await Promise.all([
              this.embeddingProvider.embed(firstHalf),
              this.embeddingProvider.embed(secondHalf),
            ]);
            const [res1, res2] = await Promise.all([
              this.vectorStore.search(emb1, candidateLimit, options.filter),
              this.vectorStore.search(emb2, candidateLimit, options.filter),
            ]);
            vectorResults = mergeVectorResults(vectorResults, res1, candidateLimit);
            vectorResults = mergeVectorResults(vectorResults, res2, candidateLimit);
          } catch { /* fail-soft */ }
        }
      }
    }

    // DTR-inspired: estimate query difficulty from initial retrieval signals
    const queryDifficulty = estimateQueryDifficulty(ftsResults, vectorResults);

    const combined = this.combineResults(ftsResults, vectorResults, decision);
    if (combined.length === 0) {
      return [];
    }

    // Always hydrate with content for cross-encoder re-ranking;
    const wantContent = options.includeContent ?? true;
    const hydratedChunks = this.hydrateChunks(
      combined.map((candidate) => candidate.chunkId),
      true,
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

    // Merge path boost results for mixed path+content queries
    // Aggressive boost: filename in query means user explicitly wants that file
    if (pathBoostResults.length > 0) {
      const pathBoostFiles = new Set(pathBoostResults.map(r => r.chunk.filePath));
      // Force-include all chunks from matched files into results
      for (const pr of pathBoostResults) {
        const existing = results.find(r => r.chunk.id === pr.chunk.id);
        if (!existing) {
          pr.score = Math.max(pr.score, 0.8); // Floor score for explicit path match
          results.push(pr);
        } else {
          existing.score = Math.min(existing.score * 2.0, 1); // Strong boost
        }
      }
      // Also boost same-file chunks already in results
      for (const r of results) {
        if (pathBoostFiles.has(r.chunk.filePath) && !pathBoostResults.some(pr => pr.chunk.id === r.chunk.id)) {
          r.score = Math.min(r.score * 1.5, 1);
        }
      }
    }

    // Re-ranking stage 1: rule-based keyword/structural boost
    const reranked = this.rerank(results, normalizedQuery, ftsQuery);

    // Re-ranking stage 2: cross-encoder model (fail-soft)
    const ceReranked = await crossEncoderRerank(reranked, normalizedQuery, topK * 2, ftsQuery);

    // Deduplicate: max 3 chunks per file to improve diversity
    const deduplicated = deduplicateByFile(ceReranked ?? reranked, 3);
    const finalResults = deduplicated.slice(0, topK);

    if (!wantContent) {
      return finalResults.map(r => ({ ...r, chunk: { ...r.chunk, content: '' } }));
    }
    return finalResults;
  }

  private rerank(results: SearchResult[], query: string, expandedQuery: string): SearchResult[] {
    if (results.length <= 1) return results;

    const RERANK_STOP_WORDS = new Set([
      'the', 'a', 'an', 'and', 'or', 'is', 'are', 'in', 'of', 'for', 'to',
      'how', 'does', 'what', 'where', 'why', 'do', 'it', 'be', 'at', 'by',
      'md', 'ts', 'js', 'json', 'tsx', 'jsx', // file extensions
    ]);

    const keywords = new Set(
      `${query} ${expandedQuery}`.toLowerCase()
        .split(/[\s,.;:!?()\[\]{}"'`]+/)
        .filter(w => w.length >= 2 && !RERANK_STOP_WORDS.has(w)),
    );

    if (keywords.size === 0) return results;

    const scored = results.map(r => {
      const content = (r.chunk.content + ' ' + r.chunk.filePath + ' ' + (r.chunk.heading ?? '')).toLowerCase();
      const filePath = r.chunk.filePath.toLowerCase();
      const heading = (r.chunk.heading ?? '').toLowerCase();

      let matchCount = 0;
      for (const kw of keywords) {
        if (content.includes(kw)) matchCount++;
      }
      const overlapRatio = matchCount / keywords.size;

      let structuralBoost = 0;
      for (const kw of keywords) {
        if (heading.includes(kw)) structuralBoost += 0.15;
        if (filePath.includes(kw)) structuralBoost += 0.1;
      }
      const fileName = filePath.split('/').pop() ?? '';
      if (fileName && keywords.has(fileName.replace(/\.\w+$/, ''))) {
        structuralBoost += 0.25;
      }
      structuralBoost = Math.min(structuralBoost, 0.5);

      const noisePenalty = isNoisePath(filePath) ? 0.3 : 0;

      // Blend: 60% original + 25% keyword overlap + 15% structural - noise
      const rerankScore = r.score * (0.60 + overlapRatio * 0.25 + structuralBoost * 0.15 - noisePenalty);
      return { ...r, score: rerankScore };
    });

    scored.sort((a, b) => b.score - a.score);
    return scored;
  }

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
        score: 1 - i * 0.01,
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

function resolveChunkRowIds(db: Database.Database, chunkIds: string[]): Map<string, number> {
  const normalizedIds = Array.from(
    new Set(chunkIds.map((chunkId) => chunkId.trim()).filter((chunkId) => chunkId.length > 0)),
  );

  const resolved = new Map<string, number>();

  for (let offset = 0; offset < normalizedIds.length; offset += CHUNK_ID_BATCH_SIZE) {
    const batch = normalizedIds.slice(offset, offset + CHUNK_ID_BATCH_SIZE);

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

const NOISE_PATH_PATTERNS = [
  'game-design-director/',
  'projects/trading',
  'trading-quest/',
  'shortlive-shop-helper/',
  'claude-sub-specs/',
  'subagent-records/',
  '.npm-cache/',
  'package-lock.json',
  'workspace-knowledge-index/docs/',
  'projects/vibe-web/_confirmed/',
  'projects/vibe-web/docs/',
  'projects/archive/',
  'discussions/',
];

/**
 * DTR-inspired query difficulty estimation.
 * Uses FTS-Vector agreement and score distribution to classify queries.
 * Easy queries skip expensive stages (multi-vector, cross-encoder).
 */
function estimateQueryDifficulty(
  ftsResults: FtsSearchResult[],
  vectorResults: VectorSearchResult[],
): 'easy' | 'medium' | 'hard' {
  // Signal 1: FTS-Vector top-5 overlap (agreement)
  const ftsTop5 = new Set(ftsResults.slice(0, 5).map(r => r.chunkId));
  const vectorTop5 = new Set(vectorResults.slice(0, 5).map(r => r.chunkId));
  const overlap = [...ftsTop5].filter(id => vectorTop5.has(id)).length;

  // Signal 2: Vector score variance (low variance = ambiguous = hard)
  const topScores = vectorResults.slice(0, 5).map(r => r.score);
  let variance = 0;
  if (topScores.length >= 2) {
    const mean = topScores.reduce((a, b) => a + b, 0) / topScores.length;
    variance = topScores.reduce((a, s) => a + (s - mean) ** 2, 0) / topScores.length;
  }

  // Signal 3: FTS has results (if FTS returns 0, vector is carrying everything)
  const ftsHasResults = ftsResults.length >= 3;

  // Easy: high agreement + FTS has results (both systems agree, early convergence)
  if (overlap >= 3 && ftsHasResults) return 'easy';

  // Hard: low agreement + low variance (ambiguous, needs deep analysis)
  if (overlap <= 1 && variance < 0.001) return 'hard';

  return 'medium';
}

function isNoisePath(filePath: string): boolean {
  const lower = filePath.toLowerCase();
  return NOISE_PATH_PATTERNS.some((p) => lower.includes(p));
}

/** Limit results to maxPerFile chunks per unique file path (preserves sort order) */
function deduplicateByFile(results: SearchResult[], maxPerFile: number): SearchResult[] {
  const counts = new Map<string, number>();
  return results.filter(r => {
    const count = counts.get(r.chunk.filePath) ?? 0;
    if (count >= maxPerFile) return false;
    counts.set(r.chunk.filePath, count + 1);
    return true;
  });
}

function clamp01(value: number): number {
  if (!Number.isFinite(value)) {
    return 0;
  }

  return Math.max(0, Math.min(1, value));
}
