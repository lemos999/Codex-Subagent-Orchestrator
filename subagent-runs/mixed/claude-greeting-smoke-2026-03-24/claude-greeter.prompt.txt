## Relevant Context (auto-injected)

### C:/Users/haj/projects/subagent-orchestrator/workspace-knowledge-index/src/search/korean-expansion.ts (lines 9-9)
**HANGUL_RE** — variable
```typescript
const HANGUL_RE = /[\uAC00-\uD7AF]/;
```

### C:/Users/haj/projects/subagent-orchestrator/workspace-knowledge-index/src/search/korean-expansion.ts (lines 70-79)
**other** — other
```typescript
/**
 * Expand a Korean query for cross-lingual search.
 *
 * Returns separate queries for FTS and vector search:
 * - FTS query uses only English expansion terms (Korean tokens can't match English FTS content)
```

### C:/Users/haj/projects/subagent-orchestrator/workspace-knowledge-index/src/search/korean-expansion.ts (lines 1-8)
**other** — other
```typescript
/**
 * Korean-to-English query expansion for cross-lingual search.
 * Appends English keywords when Korean terms are detected in the query.
 *
 * This mirrors the expansion logic in packages/launcher/src/supervisor/wki-context.ts
```

### C:/Users/haj/projects/subagent-orchestrator/packages/launcher/src/supervisor/wki-context.ts (lines 131-135)
**other** — other
```typescript
/**
 * Expand a query by appending English keywords for Korean terms.
 * Returns the original query + English expansion.
 */
```

### C:/Users/haj/projects/subagent-orchestrator/packages/launcher/src/supervisor/wki-context.ts (lines 92-100)
**other** — other
```typescript
// ============================================================
// Query expansion for multilingual search
// ============================================================

/**
```

Greet the user in Korean with exactly one short sentence. Output only the greeting sentence and nothing else.