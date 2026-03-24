# Discussion Summary

**Topic**: Should AI code reviews replace human code reviews?
**Rounds**: 2/2
**Converged**: no

## Conclusion

## Final Conclusion: Should AI Code Reviews Replace Human Code Reviews?

---

### Consensus

All three participants reached clear agreement on the following:

- **AI should not replace human code reviews.** Pure replacement is too risky given AI's limitations in understanding context, architecture, and intent.
- **A hybrid model is necessary.** AI handles routine, mechanical checks (syntax, security patterns, style, obvious bugs); humans retain authority over design decisions, correctness, and risk assessment.
- **AI's primary value is efficiency.** It reduces cognitive load on human reviewers by pre-filtering noise and surfacing surface-level issues consistently and at scale.
- **Human judgment is irreplaceable** for architectural decisions, subtle logic errors, mentorship, organizational knowledge, and strategic feedback.

---

### Disputed

- **Review order — parallel vs. sequential:**
  - Claude proposed parallel independent reviews (AI and human simultaneously, findings merged) to avoid anchoring bias and redundant commentary.
  - Codex favored sequential (AI first to narrow scope, human reviews what remains), prioritizing focused human effort.
  - Gemini did not take a strong position on order, focusing instead on the feedback loop.

- **AI adaptation over time:**
  - Gemini emphasized continuous learning — AI should improve by processing human reviewer feedback and adapting to team-specific patterns.
  - Claude and Codex were largely silent on AI adaptation, focusing on static tooling and workflow design instead.

- **Tooling responsibility:** No consensus on what prevents redundant AI-human commentary or how findings should be merged and surfaced in practice.

---

### Recommendation

**Adopt a hybrid model with context-sensitive configuration:**

1. **Default to sequential for high-risk codebases** — AI runs first as a fast, automated gate, humans review the narrowed scope with full context. This preserves human focus and avoids overwhelming reviewers with duplicate commentary.

2. **Use parallel review for exploratory or greenfield code** — where anchoring bias from AI findings is more harmful than helpful, run both independently and merge.

3. **Invest in tooling** that clearly distinguishes AI-flagged issues from human concerns in the review interface, preventing duplication and preserving reviewer clarity.

4. **Do not treat hybrid as one-size-fits-all.** Teams with high test coverage and mature style guides can delegate more to AI; teams working on safety-critical or novel architecture should weight human review more heavily.

5. **Treat mentorship as non-negotiable.** Even where AI handles the bulk of mechanical review, junior developers need human feedback for learning and team cohesion. AI cannot substitute for this.

---

### Open Questions

- **Metrics**: How do we measure hybrid review effectiveness? Defect escape rate, time-to-merge, reviewer satisfaction, or post-release incident frequency?
- **Parallel vs. sequential tradeoffs**: Is there empirical data on which model reduces review time while maintaining quality? Context probably matters, but we lack benchmarks.
- **Continuous learning risks**: If AI adapts to team patterns over time, how do we prevent it from learning bad habits, drifting from security best practices, or encoding bias? Who audits the model's evolution?
- **Privacy and IP**: Can AI models trained on team feedback be safely isolated from data leakage to other organizations or model providers?
- **Threshold calibration**: At what confidence level should AI flag vs. silently pass an issue? False positives create noise; false negatives create risk. This threshold is currently team-specific and not well-defined.