You operate under the shared contract in `AGENTS.md` at the workspace root. Read it before starting.

# Task

Review these two documents for **fitness to purpose**:

1. `Projects/novel/nova/forcelead_README.md`
2. `Projects/novel/novel-persona.md`

The user asked:

> "각 문서의 목적에 어울리도록 개선이 필요한 사항이 있는지 파악해줘."

This is **analysis only**. Do not edit files.

# What To Judge

For each document, judge whether the current content actually serves its stated purpose.

Focus on:

- purpose clarity
- role boundary clarity
- conflict with higher-priority rules inside the document itself
- ambiguity that could mislead a future worker
- places where the document's scope drifts wider than its purpose
- missing guardrails or missing structure that would make the document more reliable in actual use

# Required Reading

Read these files directly from the workspace:

- `Projects/novel/nova/forcelead_README.md`
- `Projects/novel/novel-persona.md`

# Output Format

Return concise Korean.

Use this structure:

## 총평
- 3~6 lines max

## forcelead_README.md
- 목적 적합성: 적합 / 부분 적합 / 부적합
- 핵심 개선 필요사항:
- 각 항목은 `심각도(높음/중간/낮음)`, `문제`, `왜 목적에 안 맞는지`, `개선 방향`을 짧게

## novel-persona.md
- 목적 적합성: 적합 / 부분 적합 / 부적합
- 핵심 개선 필요사항:
- 각 항목은 `심각도(높음/중간/낮음)`, `문제`, `왜 목적에 안 맞는지`, `개선 방향`을 짧게

## 우선 수정 순서
- 가장 먼저 손대야 할 것 3개 이내

# Constraints

- 없는 설정을 만들지 마라.
- 문서의 좋고 나쁨을 추상적으로 평하지 말고, 실제 후속 작업자가 왜 헷갈리거나 실수할지 기준으로 말해라.
- 문장 스타일 취향 평가는 제외하고, 문서 목적 수행성에만 집중해라.
- 개선 제안은 "문서를 어떻게 더 목적에 맞게 만들지"에 한정해라.
