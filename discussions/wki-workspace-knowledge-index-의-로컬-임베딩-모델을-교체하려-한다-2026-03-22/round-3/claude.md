[PARTIAL]

**Reasoning**: Gemini의 "BGE-M3 dense-head only ONNX" 워크어라운드는 실제로 유효한 경로다. FlagEmbedding 라이브러리는 `BGEM3FlagModel`에서 dense embedding만 추출하는 옵션을 지원하고, Optimum으로 ONNX 변환 시 colbert/sparse head를 제외하면 안정적이다. 내 이전 주장("ONNX export instability")은 full multi-vector 모드에 국한된 우려였다 — dense-only는 별개다.

**New insight**: 실무 관점에서 결정적 변수는 **index rebuild 비용**이다. WKI가 이미 수십만 청크를 384d로 인덱싱했다면, 768d→1024d 차이보다 **재인덱싱 시간과 스토리지 증가율**이 모델 선택을 좌우한다. 구체적으로:
- 384d → 768d: 메모리 2×, 저장 2× (E5-large)  
- 384d → 1024d: 메모리 2.67×, 저장 2.67× (BGE-M3 dense-only)  

코드+문서 혼합에서 BGE-M3의 실질적 recall 향상이 ~5-10%라면 768d가 더 실용적이다. **하지만 WKI의 실제 청크 수와 검색 품질 gap을 모른 채 이론만으로 결론 내리는 건 아키텍처 실수다.**

**Updated position**: Gemini가 옳다 — BGE-M3 dense-only ONNX는 테스트할 가치가 있다. 단, 테스트 기준을 명확히 해야 한다: (1) ONNX dense-only export 성공 여부, (2) WKI 실 데이터 100개 쿼리 recall@5 측정, (3) 인덱싱 속도 비교. 이 세 지표로 판단하고, 실패 시 E5-large fallback.

[POSITION: BGE-M3 dense-only ONNX를 구체적 검증 기준으로 테스트하되, E5-large를 확정 fallback으로 설정하는 2-track 접근]