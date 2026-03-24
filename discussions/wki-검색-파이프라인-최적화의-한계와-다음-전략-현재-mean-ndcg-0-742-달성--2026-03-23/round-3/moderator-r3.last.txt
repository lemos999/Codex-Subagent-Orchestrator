## Summary by Participant

**Claude**:
- Diagnosis first: measure BM25 recall on #3/#5 to distinguish coverage failure vs. ranking failure before architectural decisions.
- Hypothesizes #3 is chunking-issue, #5 is retrieval-scope issue (not vector dilution).
- Position: diagnose → then conditionally review ColBERT.

**Codex**:
- Candidate recall diagnosis + structural redesign is the realistic path to 0.742 breakthrough (not BM25 tuning).
- Acknowledges candidate-generation redesign is directionally correct but lacks specifics.
- Position: recall-based structural fix → ColBERT as conditional next step.

**Gemini**:
- 0.742 plateau demands immediate architectural pivot to late-interaction models (ColBERT/advanced cross-encoders).
- Bi-encoder's fundamental limitation is inability to capture token-level semantic interactions in multi-keyword queries.
- Position: Launch late-interaction modeling in parallel with candidate-generation refinement; do not delay.

---

## Areas of Agreement
- Current 0.742 is a plateau; #3 and #5 queries are failing cases.
- Bi-encoder has limitations for multi-keyword complex queries.

## Areas of Disagreement
- **Sequencing**: Claude/Codex → diagnose first (BM25 recall); Gemini → pivot architecture immediately.
- **ColBERT timing**: Claude/Codex → conditional/deferred; Gemini → urgent/parallel.
- **Root cause**: Claude/Codex frame as retrieval-unit/chunking problem; Gemini as fundamental model-architecture constraint.

## Open Questions
1. Is #3/#5 failure due to chunking/scope or token-level semantic interaction?
2. What is BM25 single-model recall on #3/#5?
3. What is the cost/benefit of ColBERT implementation vs. expected nDCG gain?
4. Which sequencing (parallel vs. sequential) minimizes time-to-answer?