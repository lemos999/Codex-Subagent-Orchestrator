## Summary

### Claude
- **Position**: Query decomposition (subquery intersection ranking) + chunking improvements should precede ColBERT.
- **Reasoning**: Weak queries (#3, #5) suffer from bi-encoder vector dilution in multi-keyword scenarios; fixable without architectural overhaul. Estimated ceiling: 0.78–0.80 with current arch.
- **Stance**: ColBERT is overkill for 0.74→0.78 target; prioritize low-cost mitigations first.

### Codex
- **Position**: Redesign facet/file-aware candidate generation pipeline, then conditionally integrate late-interaction methods.
- **Reasoning**: Implicit: tweaking weights or adding BM25 won't solve structural ranking failures; pipeline redesign is prerequisite.
- **Stance**: Defer late-interaction decision until candidate generation is revisited.

### Gemini
- **Position**: Migrate to late-interaction models (ColBERT or advanced cross-encoders) via phased, data-driven approach.
- **Reasoning**: Bi-encoder has hit intrinsic limits on multi-keyword queries; no incremental tuning solves this. Phased reranking mitigates risk.
- **Stance**: Architectural shift is necessary; cost of inaction (stagnation) exceeds implementation cost.

---

## Consensus & Gaps

| Aspect | Status |
|--------|--------|
| **Agree** | Current bi-encoder is locally optimized; queries #3/#5 expose structural weaknesses; incremental tuning fails |
| **Disagree** | Urgency & sequencing: Claude/Codex advocate preliminary improvements first; Gemini argues late-interaction is the only path forward |
| **Open** | (1) Does 0.78–0.80 ceiling hold? (2) ROI of phased cross-encoder reranking vs. full ColBERT? (3) Will candidate-gen redesign alone yield meaningful gains? |