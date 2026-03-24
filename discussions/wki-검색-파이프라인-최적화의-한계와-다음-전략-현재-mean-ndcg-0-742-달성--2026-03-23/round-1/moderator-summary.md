## Summary by Participant

**Claude:**
- 0.742 is near ceiling of current architecture; structural changes needed but cost-benefit unclear first
- 7/14 failure rate indicates local optimum; weak queries are bi-encoder structural limits, not tuning issues
- Recommends query rewriting + chunking strategy improvement over architecture overhaul; ColBERT deemed over-engineered

**Codex:**
- (Operation aborted; no position provided)

**Gemini:**
- 0.742 breakthrough requires fundamental shift from bi-encoder to late-interaction models (ColBERT/similar)
- Current architecture cannot capture token-level interactions needed for multi-keyword queries; simple tuning exhausted
- Recommends aggressive migration to interaction-based paradigm with targeted weak-query analysis for training data

---

## Agreement
- Current system at local optimum; 7/14 failure rate proves further tuning ineffective
- Weak queries (#3, #5) stem from structural multi-keyword/multi-concept intersection problems
- BM25 ensemble redundant with existing FTS and risky for balance

## Disagreement
- **Incremental vs. Structural**: Claude favors low-cost query preprocessing; Gemini favors high-cost architectural rewrite
- **ColBERT Practicality**: Claude views it as over-engineered for codebase search; Gemini sees it as necessary for breakthrough
- **Weak Query Solutions**: Claude targets preprocessing; Gemini targets new model architecture

## Open Questions
- Is cost of ColBERT/late-interaction justified vs. expected nDCG gain?
- Can query rewriting + chunking improvements meaningfully close the gap in #3, #5 without architectural change?
- What is realistic performance ceiling if architecture stays unchanged?
- Would improved chunking (function-level) vs. new embedding model have larger impact?