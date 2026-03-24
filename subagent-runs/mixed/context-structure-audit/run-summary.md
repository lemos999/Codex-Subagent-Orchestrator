# Run Summary: context-structure-audit

## 요청
프로젝트 맥락 공유 구조 (project-status / WKI / CLAUDE.md / AGENTS.md / memory) 점검

## 3개 엔진 결론

| 엔진 | 핵심 진단 | 가장 큰 문제 |
|------|----------|------------|
| Claude (opus) | 중복 3건, 누락 경로 4건 식별 | /design, /gdd, /discuss에서 매크로 맥락 누락. 외부 엔진 워커에 project-status 본문 미전달 |
| Gemini (pro) | 비-런처 경로에서 WKI 마이크로 맥락 부재 | /discuss WKI 연동 미흡, Gemini AGENTS.md 의존 불확실 |
| Codex (GPT) | 과설계 아님, 다만 경로별 맥락 조립 책임이 다른 게 문제 | CLAUDE.md/AGENTS.md 중복 줄이고, WKI를 모든 경로에서 동일하게 제공해야 |

## 3엔진 합의 사항

1. **project-status/current.md = canonical source 유지** — 이건 맞는 방향 (3엔진 동의)
2. **CLAUDE.md/AGENTS.md 중복 줄여야** — 포인터만 남기고 경량화 (3엔진 동의)
3. **비-런처 경로 WKI gap이 실제 문제** — /design, /gdd, /discuss에서 마이크로 맥락 누락 (3엔진 동의)
4. **memory에 shared facts 금지** — Claude 전용 tool hint만, 공유 사실은 project-status로 (Claude+Codex 동의)
5. **유지보수 부담은 낮음** — 상태 변경은 current.md 1개만, 정책 변경 시 2~3개

## 개선 우선순위 (3엔진 종합)

1. **CLAUDE.md 경량화** — 포인터만 남기고 중복 제거
2. **/design, /gdd SKILL.md에 project-status 참조 1줄 추가**
3. **memory의 "다음 작업"은 current.md를 정본으로 명시**
4. **/discuss WKI 연동 강화** (코드 수정 — 별도 작업)
5. **TS 런처 워커에 project-status 본문 자동 주입 옵션** (코드 수정 — 별도 작업)
