# Round 1 — Gemini 2.5-pro

### Topic 1 응답
- **Position**: **제외 (Exclude)**
- **Reasoning**:
    - **계층 분리 원칙**: Oracle은 '무엇이 일어날지(Prediction)'를 답하는 레이어임. BollRev 같은 '어떻게 거래할지(Strategy)'가 침투하면 V3(Meta-decision)와의 역할 정의가 붕괴됨.
    - **피처 중복 및 부채화**: `dl_features.py`에 이미 BB 데이터가 존재함. Oracle은 이를 활용해 '회귀 확률'을 예측하면 족하며, 로직 자체를 내장하는 것은 불필요한 결합임.
    - **초점 최적화**: 초기 Oracle은 리스크 성향별(Control/Agg/Cons) 예측 성능 검증에 집중해야 함. 특정 전략 variant 추가는 모델의 일반화 능력을 흐트러뜨릴 위험이 있음.
- **Concerns**:
    - Low-vol 구간에서 Oracle의 범용 예측력이 BollRev의 통계적 우위를 대체하지 못할 경우 단기 수익성 저하.
    - V3에서 Mean-reversion 대응 로직이 미비할 경우, Oracle의 고품질 신호를 실행단에서 놓칠 가능성.
- **Recommendation**: BollRev는 V3의 확장 전략이나 `reusable-components` 레벨에서 처리하고, Oracle은 BB 위치 정보를 학습 데이터로 삼아 'Directional Conviction'을 고도화하는 방향으로 정립.

### Topic 2 응답
- **Position**: **A (scripts/v2_ablation.py)**
- **Reasoning**:
    - **실험의 순수성**: Ablation은 '단일 변수(Rule 2) 제거' 외에 모든 환경이 동일해야 함. 검증되지 않은 Oracle 골격(B) 도입은 실험 결과에 노이즈를 추가함.
    - **맥락적 격리**: Charter의 "oracle.py 격리"는 'Live 운영 환경(v2.py)에 영향을 주지 않는 독립된 프로세스'로 해석하는 것이 타당함. 파일 분리만으로도 충분한 안정성 확보.
    - **개발 속도**: Phase 3 설계 확정 전까지 대기하는 기회비용을 최소화하고, 48h 타임라인 내에 Rule 2의 유효성 데이터를 즉시 확보 가능.
- **Concerns**:
    - 실험용 임시 파일이 Archive되지 않고 방치되어 프로젝트의 복잡도를 높일 위험.
    - V2 코드 복제본과 실시간 Live 환경 간의 설정(Config) 불일치 발생 가능성.
- **Recommendation**: `v2_ablation.py`로 진행하되, 파일 서두에 Ablation 목적과 만료일을 명시하고 데이터 수집 종료 즉시 `archive/`로 이동시키는 라이프사이클 강제.

[POSITION: T1=제외, T2=A]
