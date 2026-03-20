/**
 * Korean-to-English query expansion for cross-lingual search.
 * Appends English keywords when Korean terms are detected in the query.
 *
 * This mirrors the expansion logic in packages/launcher/src/supervisor/wki-context.ts
 * but lives in the search layer so that all callers (including the eval CLI) benefit.
 */

const HANGUL_RE = /[\uAC00-\uD7AF]/;

const KO_EN_KEYWORDS: Record<string, string[]> = {
  '증거': ['evidence'],
  '기록': ['recording', 'log', 'manifest'],
  '규칙': ['rules', 'policy'],
  '워커': ['worker', 'agent'],
  '실행': ['execution', 'run', 'launch'],
  '검증': ['validation', 'review', 'verify'],
  '오케스트레이션': ['orchestration', 'orchestrator'],
  '파일': ['file', 'path'],
  '디렉터리': ['directory', 'folder'],
  '구조': ['structure', 'architecture'],
  '설정': ['config', 'settings'],
  '스펙': ['spec', 'specification'],
  '매니페스트': ['manifest'],
  '프롬프트': ['prompt', 'contract'],
  '에이전트': ['agent', 'worker'],
  '리뷰': ['review', 'reviewer'],
  '수정': ['fix', 'fixer', 'repair'],
  '계획': ['plan', 'planner'],
  '단계': ['stage', 'phase'],
  '엔진': ['engine', 'codex', 'claude', 'gemini'],
  '런처': ['launcher'],
  '아카이브': ['archive'],
  '인덱스': ['index', 'indexing'],
  '검색': ['search', 'query'],
  '맥락': ['context'],
  '임베딩': ['embedding'],
  '토큰': ['token'],
  '배치': ['batch'],
  '워크플로우': ['workflow'],
  // Improvement 2: Domain-specific Korean→English mappings
  '타입': ['type'],
  '인터페이스': ['interface'],
  '함수': ['function'],
  '메서드': ['method'],
  '모듈': ['module'],
  '패키지': ['package'],
  '테스트': ['test'],
  '빌드': ['build'],
  '컴파일': ['compile'],
  '배포': ['deploy'],
  '릴리스': ['release'],
  '설계': ['design'],
  '아키텍처': ['architecture'],
  '의존성': ['dependency'],
  '에러': ['error'],
  '오류': ['exception', 'error'],
  '성능': ['performance'],
  '최적화': ['optimize'],
};

export interface ExpandedQuery {
  /** For FTS: English-only terms (Korean tokens removed since FTS content is English) */
  ftsQuery: string;
  /** For vector/embedding: original query + English terms (multilingual model handles both) */
  vectorQuery: string;
  /** Whether the original query contained Korean characters */
  hasKorean: boolean;
}

/**
 * Expand a Korean query for cross-lingual search.
 *
 * Returns separate queries for FTS and vector search:
 * - FTS query uses only English expansion terms (Korean tokens can't match English FTS content)
 * - Vector query uses original + English terms (multilingual embedding model handles both)
 *
 * If the query contains no Korean characters, both fields return the original query.
 */
export function expandKoreanQuery(query: string): ExpandedQuery {
  if (!HANGUL_RE.test(query)) {
    return { ftsQuery: query, vectorQuery: query, hasKorean: false };
  }

  const primaryTerms: string[] = [];  // First translation per Korean word (for FTS)
  const allTerms: string[] = [];      // All translations (for vector)
  for (const [ko, enList] of Object.entries(KO_EN_KEYWORDS)) {
    if (query.includes(ko)) {
      if (enList.length > 0) {
        primaryTerms.push(enList[0]!);
      }
      allTerms.push(...enList);
    }
  }

  if (primaryTerms.length === 0) {
    return { ftsQuery: query, vectorQuery: query, hasKorean: true };
  }

  // For FTS: use only the primary English term per Korean word
  // (FTS uses AND between tokens, so fewer terms = broader match)
  const ftsQuery = primaryTerms.join(' ');
  // For vector: append all English terms to original query for better multilingual matching
  const vectorQuery = `${query} ${allTerms.join(' ')}`;

  return { ftsQuery, vectorQuery, hasKorean: true };
}
