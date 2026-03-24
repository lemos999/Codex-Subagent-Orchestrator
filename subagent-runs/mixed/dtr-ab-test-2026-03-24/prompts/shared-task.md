# Task: FTS AND Recall 0 Problem Analysis

WKI 검색 파이프라인에서 FTS5가 4개 이상 키워드 쿼리에서 recall 0을 반환하는 문제의 해결 방안을 분석하고 **하나를 선택**하라.

## 배경
- FTS5는 모든 토큰을 AND로 연결: `"t1" AND "t2" AND "t3" AND "t4"`
- 4+ 키워드 → 모든 단어를 동시에 포함하는 문서가 거의 없음 → recall 0
- 이미 시도하고 실패한 것: OR 전환 (노이즈 폭발로 regression)
- 현재 벡터 검색이 이를 보완하지만, hybrid fusion에서 FTS 기여가 0이 되어 전체 품질 저하

## 요구사항
- 해결 방안 후보를 나열하고 **하나를 선택**하라
- 선택한 방안의 **구체적 구현 방법**과 **예상 리스크**를 제시하라
- 코드를 수정하지 마라 (분석만)

## 참고 파일
- workspace-knowledge-index/src/store/fts-store.ts (buildFtsMatchExpression 함수)
- workspace-knowledge-index/src/search/search-service.ts (hybrid fusion)
