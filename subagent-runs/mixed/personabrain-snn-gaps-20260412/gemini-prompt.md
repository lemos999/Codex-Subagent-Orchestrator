## 역할: 학습 파이프라인 + 꿈/수면 설계자 (learning-dream)

PersonaBrain SNN 아키텍처의 미비 항목 C(학습 파이프라인)과 F(꿈/수면)를 보완하라.

### 확정 아키텍처 (전제)
- Layer 0: 공유 아키텍처(가중치 1벌) + neuromodulator_tone(256B) + persona_bias(<1KB)
- Layer 1: Moment State (5M~50M 동적 성장, Graphon-RG, moment closure)
- Layer 2: Decision Readout (sparse INT8, STDP)
- 4단계 에너지: 강도1(2%활성)→2(10%)→3(25%)→4(90%)
- Cache-first: 93%→99% 히트, 무의식 고속도로
- 미토콘드리아: energy_pool(0~1) + Mitotype 32종(±60%)
- 3상 성장: grow-prune-consolidate
- 뉴런 동적 성장: 신생 5M → 경험 → 50M
- LIF 뉴런, STDP, E/I balance, refractory period
- 20K명, CPU 10ms, 20틱 순환

### C. 학습 파이프라인 상세 설계

1. **Phase 0: STDP 기반 기본 회로 확인**
   - 어떤 자극 세트로 기본 동작을 검증하는가?
   - STDP 초기 가중치는 어떻게 설정? (random? structured?)
   - 성공 기준: 어떤 행동이 나오면 Phase 0 통과?
   - E/I balance 안정화까지 소요 시간(틱)?

2. **Phase 1: Teacher Net (LLM→SNN 증류)**
   - 이중 채널: Logit → 목표 발화율, Hidden state → 표상 기하
   - LLM 어느 모델? (Haiku? Sonnet?) 어느 레이어?
   - SNN firing rate와의 매핑 loss 함수 정의
   - 오프라인 학습인가 온라인인가?
   - 증류 데이터셋: 어떤 시나리오를 몇 개 생성?
   - 수렴 조건: loss < ? epoch?

3. **Phase 2: 3-factor STDP + 도파민 RL**
   - 3-factor = pre-spike × post-spike × neuromodulator(도파민)
   - reward 신호의 소스: 누가 보상을 주는가? (Nomos? 감정? 사회적 피드백?)
   - eligibility trace 시간 상수
   - Metaplasticity(BCM rule)와의 병행: 학습률 자동 조정 메커니즘
   - RL collapse 방지 구체 알고리즘
   - 개인차: Mitotype이 학습 속도에 영향?

4. **Phase 3: 꿈 replay**
   - NREM SHY: 시냅스 하향 정규화 알고리즘 (어떤 시냅스를 얼마나 줄이는가)
   - REM anti-replay: Crick-Mitchison 기생 회로 제거 방법
   - replay할 경험 선택 기준 (sharp-wave ripple 유사 신호)
   - replay 순서 (순방향? 역방향? 중요도?)
   - Phase 3과 Phase 2(RL)의 관계: 꿈 중에도 RL이 작동하는가?

5. **Graphon-RG 성장과 학습 단계의 관계**
   - 뉴런 수 증가(grow)는 어느 Phase에서 발생?
   - prune은 Phase 3(수면)에서?
   - consolidate는 Phase 2 → Phase 3 전환 시?
   - 50M까지 성장하는 데 예상 소요 시간(틱/게임일)?

### F. 꿈/수면 통합 상세

1. **수면 트리거 조건**
   - energy_pool < 0.1 → 강제 수면?
   - 게임 시간 기반 (24틱 중 6~8틱 수면)?
   - 둘의 관계: 체력이 좋으면 수면 시간 줄어드나?
   - 수면 거부 가능? (에너지 부족해도 버티기 → 성능 급락)

2. **NREM/REM 위상 구현**
   - 단일 CPU 클럭에서 논리적 위상 분리 방법
   - NREM 비율 vs REM 비율 (실제: 75%/25%)
   - 위상 전환 조건 (시간 기반? 이벤트 기반?)

3. **꿈의 5가지 이론 중 구현 채택안**
   - 경험 재조합: Phase 3 replay로 구현?
   - DNA 디코딩: 윤회 전생 가중치 70%의 replay?
   - 미래 예지: 보상 예측 오차의 시뮬레이션?
   - 심리 표현: 억압된 감정/욕구의 활성화?
   - 자기 대화: 양심 회로의 오프라인 숙고?
   → 전부 구현? 선택? 확률적 혼합?

4. **수면 중 동시 처리**
   - ATP 재충전 (energy_pool 회복)
   - 시냅스 가소성 (NREM SHY / REM anti-replay)
   - 두 프로세스의 순서? 병렬? 의존성?

### 출력 형식
Charter 형식: 핵심 가치 → 핵심 루프 → 컴포넌트 상세 → 스코프 → 성공 기준 → Ontology 연결
한글로 작성.
