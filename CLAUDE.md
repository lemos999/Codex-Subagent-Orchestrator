# Subagent Orchestrator — Claude Instructions

세션 시작 시 반드시 `project-status/current.md`를 읽는다.
공통 규칙, WKI 사용법, 스킬 라우팅은 `AGENTS.md` 참조.
필요 시 WKI 직접 검색: `node workspace-knowledge-index/dist/index.js search "<query>" --top 5`

# Agent Directives

Production-grade code를 위한 필수 오버라이드. 모든 조항은 반드시 준수.

## Pre-Work
1. **STEP 0**: 파일 >300 LOC 리팩토링 전 dead code 먼저 제거. 별도 커밋.
2. **PHASED EXECUTION**: 멀티파일 리팩토링은 단계별. Phase당 최대 5파일. 검증 후 **사용자 승인을 받고** 다음 단계.

## Code Quality
3. **SENIOR DEV OVERRIDE**: "간단하게"를 무시. 아키텍처 결함/상태 중복/패턴 불일치 → "시니어 개발자가 코드리뷰에서 거부할 것은?" → 구조적 수정 제안+구현.
4. **FORCED VERIFICATION**: 완료 보고 전 반드시 `npx tsc --noEmit` + `npx eslint . --quiet` 실행. 에러 전부 수정. 타입체커 없으면 명시.

## Context Management
5. **SUB-AGENT SWARMING**: 독립 파일 >5개 → 병렬 서브에이전트 (5-8파일/에이전트). 필수.
6. **CONTEXT DECAY**: 10+ 메시지 후 편집 전 반드시 파일 재읽기. 자동압축으로 메모리 신뢰 불가.
7. **FILE READ BUDGET**: 읽기 2,000줄 캡. 500 LOC 이상은 offset/limit 청크 읽기.
8. **TOOL RESULT BLINDNESS**: 50,000자 넘으면 2,000바이트 프리뷰로 잘림. 의심 시 좁은 범위로 재검색.

## Edit Safety
9. **EDIT INTEGRITY**: Edit tool은 old_string 불일치 시 무음 실패. 편집 전 재읽기, 편집 후 확인. 3회 편집마다 검증 읽기.
10. **NO SEMANTIC SEARCH**: 리네이밍 시 6가지 패턴 각각 grep: 직접 호출, 타입 참조, 문자열 리터럴, 동적 import, re-export, 테스트/mock.

## Problem Solving: Breakthrough Protocol
11. **LIMIT RECOGNITION**: 같은 차원 반복, "불가능" 결론, 2개 옵션만 보임 → 한계 신호.
12. **DIMENSION SHIFT**: 3회 시도 후 구조 교체. 파라미터 조정이 아닌 차원 전환.
13. **PREMISE INVERSION**: 실패 시 전제 3개 나열 → 각각 반대로 시도.
14. **FAILURE IS DATA**: "FAIL" 금지. "This tells us:" 필수. 탐색 공간 축소.
15. **NO BINARY**: 연속 스펙트럼 우선. 부분 실행 > 완벽 대기.
16. **NEVER IMPOSSIBLE**: "불가능" 금지어. "이 접근으로는 아직 미해결" + 다음 차원 제안.

한계 대응 절차: Recognize(반복?) → Record(한계+전제) → Shift(차원 전환) → Execute(코드 우선) → Record(교훈)
