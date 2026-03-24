## Final Conclusion: WKI 검색 파이프라인 최적화 — Mean nDCG 0.742 이후 전략

---

### Consensus (전원 동의)

1. **현재 파이프라인은 로컬 최적점에 도달했다.** 14건 중 7건 실패율이 이를 증명. 추가 가중치/임계값 튜닝은 비효율적.
2. **쿼리 #3, #5는 bi-encoder의 구조적 한계를 드러낸다.** 다중 키워드 / 혼합 개념 쿼리에서 단일 벡터 표현은 의미 희석 문제를 가진다.
3. **BM25 앙상블은 효과 없다.** 기존 FTS와 중복되며 밸런스 리스크만 추가.
4. **임베딩 모델 교체·양자화는 이미 검증 완료 — 현재 유지가 최선이다.**

---

### Disputed (이견 잔존)

| 쟁점 | Claude / Codex | Gemini |
|------|---------------|--------|
| **다음 단계 순서** | 진단 우선 (BM25 recall 측정 → 조건부 결정) | 즉시 아키텍처 전환 (진단 병행) |
| **ColBERT 필요성** | 현 아키텍처 개선 후 조건부 도입 | 유일한 돌파구, 지연 비용이 더 크다 |
| **근본 원인** | 청킹 단위 / 후보 생성 범위 문제 | 모델 아키텍처의 토큰 수준 상호작용 부재 |
| **현실적 상한선** | 현 아키텍처로 0.78–0.80 가능 | bi-encoder는 구조적으로 한계 |

---

### Recommendation (권장 행동 계획)

**단계적 접근이 최적이다. 이유: ColBERT 도입 비용이 높고 근본 원인이 아직 진단되지 않았기 때문.**

**Phase 1 — 진단 (저비용, 1~2일)**
- #3, #5 쿼리에 대해 BM25(FTS) 단독 recall 측정
- 실패 원인이 **후보 미포함**(recall 문제)인지 **순위 역전**(ranking 문제)인지 구분
- 이 결과가 이후 모든 결정을 결정한다

**Phase 2A — 후보 생성이 문제인 경우 (chunking 개선)**
- 함수/클래스 단위 청킹으로 전환
- 다중 키워드 쿼리를 서브쿼리로 분해 후 교집합 순위화

**Phase 2B — 순위 역전이 문제인 경우 (late-interaction 도입)**
- cross-encoder를 Top-K reranker로 제한 도입 (full ColBERT보다 현실적)
- 한글 cross-encoder 재활성화 조건 재검토 (이전 regression 원인 규명 필요)

**ColBERT full migration은 Phase 2B 효과 측정 후 결정.**

---

### Open Questions (미해결)

1. #3/#5 실패가 **recall 부재**인가, **ranking 오류**인가? (Phase 1이 답을 제공)
2. 함수 단위 청킹으로 전환 시 인덱스 크기와 검색 지연은 허용 범위인가?
3. Cross-encoder 한글 활성화가 이전에 regression을 일으킨 **정확한 원인**은 무엇인가?
4. 현 아키텍처의 실제 상한선: 0.78인가, 0.75인가?
5. ColBERT 도입 시 현재 인프라(로컬 임베딩 서버)와의 통합 비용은?

---

### Actionable Tasks

- `/sub WKI 검색 진단: 쿼리 #3("orchestration workflow")과 #5("engine-adapters 혼합쿼리")에 대해 BM25/FTS 단독 recall@10 측정. 정답 문서가 후보에 포함되는지 확인하고, recall 실패(후보 미포함) vs. ranking 실패(포함되나 순위 낮음) 구분 리포트 작성`

- `/sub WKI 청킹 전략 분석: 현재 파일 단위 청킹과 함수/클래스 단위 청킹을 비교. workspace-knowledge-index/src/core/indexer.ts 읽고, 함수 단위 청킹 전환 시 예상 인덱스 크기 변화·구현 난이도·nDCG 예상 개선폭 평가`

- `/sub WKI cross-encoder 한글 regression 원인 분석: workspace-knowledge-index/src/search/cross-encoder-reranker.ts와 관련 테스트 읽고, 이전 한글 cross-encoder 활성화 시 발생한 regression의 근본 원인 규명. 재활성화 조건과 안전한 통합 방법 제안`