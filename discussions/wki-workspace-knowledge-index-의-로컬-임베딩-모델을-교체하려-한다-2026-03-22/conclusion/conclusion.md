## Final Conclusion: WKI 임베딩 모델 교체

---

### Consensus (전원 동의)

- **현재 모델(paraphrase-multilingual-MiniLM-L12-v2, 384d)은 교체 대상**이며, 코드+문서 혼합 검색과 한-영 크로스링구얼 요구를 충족하는 더 강력한 모델이 존재
- **BGE-M3가 이론적 최적 후보**이며, E5-large가 현실적 차선책
- ONNX 로컬 실행, 크로스링구얼, 코드+문서 혼합 검색은 비협상 조건
- **실제 WKI 데이터셋에서의 실증 검증이 필수** — 이론적 벤치마크만으로 결정 불가

---

### Disputed (미합의)

| 쟁점 | Claude | Codex | Gemini |
|------|--------|-------|--------|
| 1차 선택 | E5-large (안정성 우선) | BGE-M3 (성능 최우선) | BGE-M3 (단, 검증 후) |
| BGE-M3 ONNX 위험 | dense-only는 안정적 | 문제없음 | 미검증, 조사 필요 |
| E5-large 실용성 | 즉시 배포 가능 | query/doc 분리 없으면 저하 | 안정적 대안 |
| 384d→1024d 비용 | 저장소 병목 우려 | 수용 가능 | 테스트 필요 |

---

### Recommendation (권장 행동)

**2-Track 병렬 검증 후 결정:**

**Track A — BGE-M3 (우선 검증 대상)**
- `BAAI/bge-m3` dense-head-only ONNX export 테스트
- WKI 실제 쿼리 20~50개로 recall@5 측정
- 현재 청크 수 기준 인덱스 rebuild 시간 및 저장 용량 증가 측정

**Track B — multilingual-e5-large (폴백)**
- `intfloat/multilingual-e5-large` ONNX 경로 확인 (안정적으로 알려짐)
- WKI 검색 파이프라인에 `query: ` / `passage: ` prefix 추가 구현
- 동일 쿼리셋으로 recall@5 비교

**결정 기준:**
- BGE-M3 dense-only ONNX export 성공 + recall@5 ≥ 5% 개선 → BGE-M3 채택
- ONNX 불안정 또는 rebuild 비용 과다 → E5-large 채택

---

### Open Questions (미해결)

1. BGE-M3 dense-head-only ONNX export의 실제 안정성 및 추론 성능
2. WKI 현재 데이터셋 기준 1024d 인덱스의 메모리·저장 실측치
3. E5-large가 query/document prefix 없이 WKI에서 실제로 성능 저하가 발생하는지
4. BGE-M3 vs E5-large의 WKI 실쿼리 recall 차이 (%, 유의미한 차이인지)

---

### Actionable Tasks

- `/sub WKI 임베딩 모델 비교 실험 설계: BGE-M3(dense-only ONNX) vs multilingual-e5-large를 workspace-knowledge-index에서 테스트하는 스크립트 작성. 평가 지표: ONNX export 성공 여부, recall@5(20개 샘플 쿼리), 인덱스 rebuild 시간, 저장 용량`
- `/sub workspace-knowledge-index 코드베이스 분석: 현재 임베딩 파이프라인(모델 로딩, 청킹, 인덱싱, 검색) 흐름을 파악하고 BGE-M3 또는 E5-large 교체에 필요한 변경 범위 리포트`
- `/sub multilingual-e5-large ONNX export 검증: intfloat/multilingual-e5-large를 ONNX로 변환하고 query/passage prefix 포함 추론 정확성 확인. 결과를 재현 가능한 스크립트로 저장`