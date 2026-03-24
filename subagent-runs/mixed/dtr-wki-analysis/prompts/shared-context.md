# DTR x WKI Analysis — Shared Context

## DTR (Deep-Thinking Tokens) 논문 핵심
- 토큰 길이와 정확도는 역상관 (r = -0.594). 길수록 오히려 부정확.
- DTR(Deep-Thinking Ratio) = 깊은 레이어에서야 수렴하는 토큰 비율. 정확도와 r = +0.683 양의 상관.
- Think@n: 50토큰 prefix만 보고 상위 50% 필터링 → 비용 49% 절감, 정확도 유지/향상.
- 핵심 통찰: "깊이 우선 사고" — 자명한 곳은 짧게, 판단이 필요한 분기점에만 깊이.

## WKI 검색 파이프라인 현재 구조 (Mean nDCG 0.744)
1. Query Processing: classify + Korean expansion + path decomposition
2. Dual Retrieval: FTS5 (bm25, AND) + Vector (384d cosine, multi-vector sliding window)
3. Hybrid Fusion: weighted_sum (fts×w_f + vec×w_v), query-type-specific weights
4. Rule-based Rerank: keyword overlap + structural boost + noise penalty
5. Cross-encoder Rerank: ms-marco-MiniLM, 45% orig + 55% CE, English-only

## 알려진 한계
- FTS AND: 4+ keywords → recall 0
- Vector similarity: [0.5, 1.0] 압축 범위
- Cross-encoder: 영어 전용, 한글 스킵
- 파이프라인 민감성: 14 attempts 중 7 regression (교훈 8: 복잡계)

## 분석 질문
1. DTR의 "깊이 우선" 원리가 검색 파이프라인의 어느 단계에 적용 가능한가?
2. Think@n의 "prefix 기반 조기 필터링"을 검색 후보 선별에 활용할 수 있는가?
3. "overthinking 방지"가 FTS AND recall 0 문제나 cross-encoder 노이즈에 적용 가능한가?
4. DTR 원리에서 파생되는 WKI에 특화된 새로운 아이디어가 있는가?
