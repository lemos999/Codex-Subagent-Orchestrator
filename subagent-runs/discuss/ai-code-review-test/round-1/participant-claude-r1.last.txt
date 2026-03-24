**Position:** AI code reviews should augment, not replace, human review.

**Reasoning:** AI excels at automated checks—syntax, security patterns, style violations, obvious bugs—faster and more consistently. But code reviews serve multiple purposes: architectural decisions, design intent, mentorship, and organizational knowledge transfer. These require human judgment and context. A hybrid approach maximizes efficiency: AI filters obvious issues, humans focus on design and correctness.

**Concerns:** Over-reliance on AI could miss subtle logic errors, miss design anti-patterns, and erode team cohesion. AI reviews lack understanding of *why* decisions were made. For critical systems (security, finance, safety), human review remains essential.

**Recommendation:** Deploy AI for automated pre-review (linting, type checking, basic security scan). Route to human reviewers afterward. Use AI insights to guide human attention to high-risk areas. Maintain human final authority on correctness and design.

[POSITION: AI augments human code reviews; replace only automated checks, not human judgment]