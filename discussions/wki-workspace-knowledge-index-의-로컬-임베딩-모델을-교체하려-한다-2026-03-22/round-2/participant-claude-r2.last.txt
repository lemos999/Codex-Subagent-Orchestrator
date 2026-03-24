[PARTIAL]

**Reasoning**: BGE-M3의 성능 우위는 인정하나, WKI 실제 운용 환경에서 "로컬 실행, ONNX 호환, rebuild 비용" 세 가지를 동시에 만족해야 한다. 1024d 모델은 이론적으로 우수하지만 실무에서 rebuild 미루다 스테일 인덱스 운용하는 사례가 많다.

**New insight**: 아직 논의에서 빠진 핵심 —

- **ONNX 변환 안정성**: BGE-M3는 sparse/colbert 헤드 때문에 ONNX export가 아직 불안정. Dense 전용으로 잘라내야 하는데 이건 별도 작업이 필요하고 upstream 지원이 약하다.
- **multilingual-e5-large ONNX**: Hugging Face 공식 optimum으로 안정적 export 가능. 이미 검증된 경로.
- **실질적 rebuild 비용**: 384d→1024d는 단순 메모리 증가 외에 인덱스 저장 공간도 2.5배. WKI가 대형 워크스페이스 지원 목표라면 이게 실제 bottleneck이 된다.

**Updated position**: BGE-M3는 ONNX 안정성 리스크 때문에 지금 당장 프로덕션 채택은 무리. **multilingual-e5-large가 현 시점 최선** — ONNX 경로 검증됨, 한-영 크로스링구얼 충분, 768d로 성능/효율 균형점. BGE-M3는 ONNX 생태계 성숙 후 다음 마이그레이션 타겟으로 남겨두는 게 실무적 판단.

[POSITION: multilingual-e5-large 채택 (768d, ONNX 안정, 한-영 크로스링구얼 충분) — BGE-M3는 ONNX export 안정화 후 차기 마이그레이션 후보로 보류]