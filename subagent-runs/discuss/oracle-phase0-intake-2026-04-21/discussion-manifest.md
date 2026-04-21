# Discussion Manifest — Oracle Phase 0 Intake 적합성

**Date**: 2026-04-21
**Topic**: Phase 0 Intake 요약이 Oracle 예측 엔진 (V2 재설계) 설계 착수 조건으로 적합한가?
**Trigger**: 사용자 `/discuss 해당 사항이 적합한지 토론해주세요. 8인 토론. claude는 2인 참여. opus, sonnet`

## Participants (8)

| # | Engine | Model | Role | Status |
|---|--------|-------|------|--------|
| 1 | Claude | opus | Senior Architect | OK |
| 2 | Claude | sonnet | 운영 리스크 | OK |
| 3 | Codex | gpt-5.4 | 구현 가능성 | OK |
| 4 | Codex | gpt-5.4 | 알고리즘 엄밀성 | OK |
| 5 | Codex | gpt-5.4 | 비용/효율 | OK |
| 6 | Gemini | 2.5-pro (찬성) | Oracle 찬성 | **FAILED** (쿼터 소진) → Claude sonnet fallback |
| 7 | Gemini | 2.5-pro (반대) | Devil's Advocate | **FAILED** (쿼터 소진) → Claude sonnet fallback |
| 8 | Gemini | 2.5-flash | 사용자 관점 요약 | OK |

## Rounds

- **Round 1**: 8 독립 의견 수집 → `round-1/moderator-summary.md` → 수렴 PARTIAL
- **Round 2**: 3 집중 쟁점 (v2.py 처리 / 48h 실험 선행 / V3 차별화) → `round-2/` → 수렴 **AGREE (조건부)**

## Outcome

- **최종 결론**: `conclusion.md`
- **수렴 판정**: AGREE with 10 Charter 전 확정 조건
- **핵심 합의**: 신규 oracle.py 분리, V3=setup/Oracle=prediction 레이어 분리, 48h Rule 2 ablation Charter 태스크 1번 편입

## WKI Context

인덱싱: 2026-04-21, gap repair 3 files. 맥락 주입은 개별 역할 프롬프트 + context.md 파일 hand-off.

## Evidence

- `context.md` — 배경
- `role_*.md` — 역할별 프롬프트 (6개)
- `round-1/{codex_A,B,C,gemini_A,B,flash}.md` — 6개 외부 엔진 응답 (Claude opus/sonnet은 task notification result에만 보존)
- `round-1/moderator-summary.md` — Round 1 판정
- `round-2/focus.md` — Round 2 집중 쟁점
- `round-2/*.md` — 8명 Round 2 응답
- `conclusion.md` — 최종 결론
