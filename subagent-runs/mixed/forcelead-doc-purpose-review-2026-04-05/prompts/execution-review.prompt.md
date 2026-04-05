You are reviewing two project documents for operational fitness.

Read these workspace files directly:

- `Projects/novel/nova/forcelead_README.md`
- `Projects/novel/novel-persona.md`

Task:

Find improvements needed so each document better matches its own purpose.

Treat this as a practical systems/documentation review:

- `forcelead_README.md` is an onboarding + handoff document for future workers.
- `novel-persona.md` is an operating framework for planning, scene design, and drafting.

Judge from these angles:

- does the doc let a new worker act correctly without over-reading?
- are decision boundaries explicit enough?
- are there duplicated concepts that should be condensed?
- are there missing operational checklists, summaries, or "when to use / not use" rules?
- does the document over-specify ideas that belong elsewhere?
- would a future worker likely misuse the document because of current structure?

Output in Korean with this exact structure:

## forcelead_README.md
- 목적 적합성:
- 개선 필요사항:
- each bullet: `문제 / 실수 위험 / 개선 방법`

## novel-persona.md
- 목적 적합성:
- 개선 필요사항:
- each bullet: `문제 / 실수 위험 / 개선 방법`

## 공통 개선 포인트
- 5 bullets max

## 최우선 1차 수정안
- if only 3 things can be changed first, list those 3

Constraints:

- analysis only, no file edits
- do not invent lore
- focus on operational clarity and document architecture, not prose taste
- prefer high-signal findings over exhaustive enumeration
