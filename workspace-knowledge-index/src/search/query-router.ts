import type { SearchConfig } from '../config/schema.js';
import type { QueryType } from '../types/index.js';

// ============================================================
// Types for search routing
// ============================================================

export type QueryIntent = 'exact' | 'fts' | 'semantic' | 'vector' | 'hybrid';
export type SearchRoute = 'fts' | 'vector' | 'hybrid';
export type SearchMode = 'auto' | 'fts' | 'vector' | 'hybrid';

export interface RouteDecision {
  intent: QueryIntent;
  route: SearchRoute;
  weights: {
    fts: number;
    vector: number;
  };
}

// ============================================================
// Pattern detection regexes
// ============================================================

const PATH_RE = /[/\\]|\.(?:ts|tsx|js|jsx|md|json)$/;
const CAMEL_CASE_RE = /[a-z][a-zA-Z0-9]*[A-Z]/;
const PASCAL_CASE_RE = /^[A-Z][a-zA-Z0-9]+$/;
const SNAKE_CASE_RE = /[a-z]+_[a-z]+/;
const UPPER_CASE_RE = /^[A-Z][A-Z0-9_]+$/;
const HANGUL_RE = /[\uAC00-\uD7AF]/;
const DEPS_KEYWORDS = ['import', 'require', '호출', '사용', '영향', 'depends', 'dependency'];

/**
 * Rule-based query router. No LLM usage.
 * Classifies queries and provides FTS/Vector weights accordingly.
 * Also supports search routing when constructed with a SearchConfig.
 */
export class QueryRouter {
  private readonly config: SearchConfig | null;

  constructor(config?: SearchConfig) {
    this.config = config ?? null;
  }

  // ============================================================
  // Search routing (requires config)
  // ============================================================

  /**
   * Determine the search route for a query based on mode, intent, and config.
   * Requires SearchConfig to have been passed to the constructor.
   */
  route(
    query: string,
    mode: SearchMode | undefined,
    hasVectorSearch: boolean,
  ): RouteDecision {
    if (mode === 'fts') {
      return { intent: 'fts', route: 'fts', weights: { fts: 1, vector: 0 } };
    }

    if (mode === 'vector') {
      if (!hasVectorSearch) {
        throw new Error('Vector search requested but vector backend is not configured');
      }

      return { intent: 'vector', route: 'vector', weights: { fts: 0, vector: 1 } };
    }

    if (mode === 'hybrid') {
      if (!hasVectorSearch) {
        return { intent: 'hybrid', route: 'fts', weights: { fts: 1, vector: 0 } };
      }

      return { intent: 'hybrid', route: 'hybrid', weights: this.getIntentWeights('hybrid') };
    }

    // mode === 'auto' or undefined: classify and route
    const intent = this.classifyIntent(query);

    if ((intent === 'semantic' || intent === 'vector') && hasVectorSearch) {
      return { intent, route: 'vector', weights: { fts: 0, vector: 1 } };
    }

    if (intent === 'hybrid' && hasVectorSearch) {
      return { intent, route: 'hybrid', weights: this.getIntentWeights(intent) };
    }

    return { intent, route: 'fts', weights: { fts: 1, vector: 0 } };
  }

  /**
   * Classify query intent for search routing purposes.
   * Returns a QueryIntent that drives the search strategy.
   */
  classifyIntent(query: string): QueryIntent {
    const normalized = query.trim();
    const tokens = normalized.split(/\s+/u).filter(Boolean);

    if (tokens.length === 0) {
      return 'fts';
    }

    if (isQuotedQuery(normalized) || looksLikePath(normalized) || looksLikeIdentifier(normalized)) {
      return 'exact';
    }

    if (tokens.length >= 8 && containsNaturalLanguageMarkers(tokens)) {
      return 'semantic';
    }

    if (tokens.length >= 3) {
      return 'hybrid';
    }

    return 'fts';
  }

  /**
   * Get FTS/Vector weights for the given query intent.
   * Uses config fusion weights as the base when available.
   */
  getIntentWeights(intent: QueryIntent): { fts: number; vector: number } {
    const base = this.config
      ? normalizeWeights(
          this.config.fusion.weights.fts,
          this.config.fusion.weights.vector,
        )
      : { fts: 0.5, vector: 0.5 };

    if (intent === 'semantic' || intent === 'vector') {
      return normalizeWeights(base.fts * 0.5, base.vector * 1.5);
    }

    if (intent === 'hybrid') {
      return base;
    }

    return { fts: 1, vector: 0 };
  }

  // ============================================================
  // External query classification (standalone API)
  // ============================================================

  /** Classify the query type for external consumers. */
  classify(query: string): QueryType {
    const trimmed = query.trim();

    // 1. Path pattern
    if (PATH_RE.test(trimmed)) {
      return 'path';
    }

    // 2. Identifier pattern (check individual tokens)
    const tokens = trimmed.split(/\s+/);
    if (tokens.length <= 3) {
      const hasIdentifier = tokens.some(
        (t) =>
          CAMEL_CASE_RE.test(t) ||
          PASCAL_CASE_RE.test(t) ||
          SNAKE_CASE_RE.test(t) ||
          UPPER_CASE_RE.test(t),
      );
      if (hasIdentifier) {
        return 'identifier';
      }
    }

    // 3. Dependency keywords
    const lowerQuery = trimmed.toLowerCase();
    const hasDepsKeyword = DEPS_KEYWORDS.some((kw) => lowerQuery.includes(kw));
    if (hasDepsKeyword) {
      return 'deps';
    }

    // 4. Korean / natural language
    if (HANGUL_RE.test(trimmed)) {
      return 'natural';
    }

    // 5. Multi-word queries are likely natural language
    if (tokens.length >= 3) {
      return 'natural';
    }

    // 6. Default
    return 'mixed';
  }

  /** Get FTS/Vector weights for the given query type. */
  getWeights(queryType: QueryType): { fts: number; vector: number } {
    switch (queryType) {
      case 'identifier':
        return { fts: 0.7, vector: 0.3 };
      case 'path':
        return { fts: 0.8, vector: 0.2 };
      case 'natural':
        return { fts: 0.3, vector: 0.7 };
      case 'deps':
        return { fts: 0.5, vector: 0.5 };
      case 'mixed':
        return { fts: 0.5, vector: 0.5 };
    }
  }

  /**
   * Query expansion: split camelCase / PascalCase / snake_case tokens
   * and return original + decomposed tokens.
   */
  expand(query: string): string[] {
    const trimmed = query.trim();
    if (!trimmed) {
      return [];
    }

    const result = new Set<string>();
    result.add(trimmed);

    const tokens = trimmed.split(/\s+/);
    for (const token of tokens) {
      result.add(token);
      const decomposed = this.decomposeToken(token);
      for (const part of decomposed) {
        result.add(part);
      }
    }

    return Array.from(result);
  }

  /**
   * Decompose a single token into sub-tokens.
   * - camelCase / PascalCase: split on case boundaries
   * - snake_case: split on underscores
   */
  private decomposeToken(token: string): string[] {
    const parts: string[] = [];

    // snake_case split
    if (token.includes('_')) {
      const snakeParts = token
        .split('_')
        .map((p) => p.toLowerCase())
        .filter((p) => p.length > 0);
      parts.push(...snakeParts);
      return parts;
    }

    // camelCase / PascalCase split
    // Insert space before uppercase letters that follow lowercase letters
    const spaced = token.replace(/([a-z0-9])([A-Z])/g, '$1 $2');
    // Also split consecutive uppercase followed by lowercase: "XMLParser" -> "XML Parser"
    const fullySplit = spaced.replace(/([A-Z]+)([A-Z][a-z])/g, '$1 $2');

    const camelParts = fullySplit
      .split(/\s+/)
      .map((p) => p.toLowerCase())
      .filter((p) => p.length > 0);

    if (camelParts.length > 1) {
      parts.push(...camelParts);
    }

    return parts;
  }
}

// ============================================================
// Helper functions for intent classification
// ============================================================

function isQuotedQuery(query: string): boolean {
  return /^["'`].+["'`]$/u.test(query);
}

function looksLikePath(query: string): boolean {
  return /[\\/]/u.test(query) || /^[A-Za-z]:/u.test(query) || /^\.\.?(?:[\\/]|$)/u.test(query);
}

function looksLikeIdentifier(query: string): boolean {
  return /^[A-Za-z_$][\w$.:#-]*$/u.test(query) && !query.includes(' ');
}

function containsNaturalLanguageMarkers(tokens: string[]): boolean {
  const markers = new Set([
    'a',
    'an',
    'and',
    'describe',
    'does',
    'explain',
    'for',
    'how',
    'in',
    'is',
    'of',
    'or',
    'the',
    'what',
    'where',
    'why',
  ]);

  return tokens.some((token) => markers.has(token.toLowerCase()));
}

export function normalizeWeights(fts: number, vector: number): { fts: number; vector: number } {
  const safeFts = Number.isFinite(fts) && fts > 0 ? fts : 0;
  const safeVector = Number.isFinite(vector) && vector > 0 ? vector : 0;
  const total = safeFts + safeVector;

  if (total === 0) {
    return { fts: 0.5, vector: 0.5 };
  }

  return {
    fts: safeFts / total,
    vector: safeVector / total,
  };
}
