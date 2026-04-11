# Secret/Rumor/Evidence Charter Design — Run Summary

**Date**: 2026-04-11
**Target**: `Projects/personas/docs/secret-rumor-evidence-charter.md` v1
**Pattern**: Multi-engine collaborative design (3 perspectives → integration)

## Engine Assignment

| # | Agent | Engine | Model | Perspective | Status |
|---|-------|--------|-------|-------------|--------|
| 1 | drama-architect | Claude | opus | 서사 구조 | Completed |
| 2 | info-theorist | Gemini | gemini-2.5-pro | 정보 전파 모델 | Completed |
| 3 | justice-engineer | Codex | gpt-5.4 | 증거/사법 연결 | Completed |

## Integration

3개 엔진 결과를 오케스트레이터(Claude opus)가 통합:
- §1~2 핵심 가치 + 비밀 유형/생애주기 ← Claude opus
- §3 소문 전파 모델 (매체 5종+확장, 전파 공식, 전화기 효과) ← Gemini pro + Claude opus
- §4 증거 시스템 (이원 체계, 신뢰도, 위조/위증) ← Codex gpt
- §5 딜레마 메커니즘 (H2 4축) ← Claude opus
- §6 파이프라인 통합 (O(N), 성능) ← Gemini pro
- §7~8 드라마 순간 + 위기 시나리오 ← Claude opus + Codex gpt
- §9~11 스코프/성공기준/Ontology ← 오케스트레이터 통합

## Key Design Decisions

1. 비밀 5유형: 개인/관계/정치/경제/범죄
2. 매체 5종 + 확장 매체 (페르소나 발명 가능)
3. Nomos 이원 체계: 자연법 직접 탐지 vs 실정법 증거 기반
4. 전파 모델: Active Spreader Queue + Spatial Hashing + Lazy Propagation
5. 위증 = 자연법 3조(약속 위반), 무고 = 실정법 영역
6. 증거 기본 신뢰도: Nomos 기록 0.90 ~ 소문 0.00
