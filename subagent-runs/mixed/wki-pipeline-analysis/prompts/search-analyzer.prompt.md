# WKI Search Pipeline Deep Analysis

You are analyzing a workspace knowledge index (WKI) search pipeline that currently achieves Mean nDCG 0.742. Your goal is to find **hidden bugs, dead code paths, and suboptimal conditions** that could improve performance.

## Context
- Previous bug fix (multi-vector skip) improved nDCG by +0.026 — similar bugs may exist
- 7 out of 14 improvement attempts caused regression — the pipeline is sensitive
- Weak queries: #3 (0.527, 6-keyword AND), #5 (0.506, mixed path+content)
- FTS AND condition yields 0 results for 4+ keyword queries (OR causes noise explosion)

## Files to analyze
Read these files in workspace-knowledge-index/src/:
1. search/search-service.ts — main search orchestration
2. search/query-router.ts — query classification and routing
3. search/korean-expansion.ts — Korean→English expansion
4. search/cross-encoder-reranker.ts — cross-encoder re-ranking
5. store/fts-store.ts — FTS5 search
6. store/vector-store.ts — LanceDB vector search

## What to look for

1. **Dead/unreachable code paths**: conditions that can never be true, variables computed but unused
2. **Condition bugs**: like the previous `contentWords.length < queryTokens.length` bug that skipped multi-vector search
3. **Suboptimal magic numbers**: hardcoded values (thresholds, weights, limits) that may not be optimal
4. **FTS AND alternative**: creative solutions for multi-keyword FTS that aren't pure OR (e.g., partial AND, NEAR, weighted terms)
5. **Cross-encoder blend ratio**: is 40:60 (original:CE) optimal? What about query-type-specific ratios?
6. **Normalization issues**: score normalization that might distort rankings
7. **Race conditions or ordering bugs**: in merge/combine operations

## Output format
For each finding, provide:
- File and line number
- The problematic code
- Why it's suboptimal
- Proposed fix (concept only, don't implement)
- Expected impact (high/medium/low)
