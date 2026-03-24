# Discussion Manifest

- **Topic**: WKI 검색 파이프라인 최적화의 한계와 다음 전략. 현재 Mean nDCG 0.742 달성. 시도한 것: (1) 임베딩 모델 교체 5개 비교 → 현재 모델 유지, (2) q8/fp16 양자화 → 비효율 또는 역효과, (3) 파이프라인 개선 14건 중 7건 성공 7건 실패, (4) 핵심 발견: multi-vector 스킵 버그 수정이 가장 큰 개선(+0.026). 실패한 것: consensus bonus, 복합어 확장, FTS 가중치 조정, cross-encoder 한글 활성화, dtype 분리, q8 rerank 가중치 — 모두 regression. 교훈: 이미 최적화된 파이프라인은 추가 조정에 민감하고, 양자화 손실은 후처리로 보정 불가. 남은 약한 쿼리: #3(0.527) orchestration workflow 다중키워드, #5(0.506) engine-adapters 혼합쿼리. 질문: (1) 0.742를 넘기 위한 현실적 다음 단계는? (2) bi-encoder의 다중 키워드 한계를 극복하는 방법? (3) BM25 앙상블(#7)은 효과가 있을까? (4) ColBERT/late interaction 접근의 실용성은?
- **Participants**: claude (sonnet), codex (gpt-5.4), gemini (gemini-2.5-flash)
- **Max rounds**: 3
- **Actual rounds**: 3
- **Converged**: no
- **Stopped by user**: no
- **Timestamp**: 2026-03-23T06:47:59.829Z

## Round 1
- Failed engines: codex
- claude: responded
- codex: failed
- gemini: responded

## Round 2
- Convergence: partial
- claude: responded
- codex: responded
- gemini: responded

## Round 3
- Convergence: disagree
- claude: responded
- codex: responded
- gemini: responded
