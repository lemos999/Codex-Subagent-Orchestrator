## 역할: 시스템 통합 + Worst-case 설계자 (system-integrator)

PersonaBrain SNN 아키텍처의 미비 항목 D(틱 데몬 통합)과 E(worst-case/fallback)를 보완하라.

### 확정 아키텍처 (전제)
- Layer 0: 공유 아키텍처(가중치 1벌, ~수MB) + neuromodulator_tone(256B/persona) + persona_bias(<1KB/persona)
- Layer 1: Moment State (5M~50M, Graphon-RG, moment closure, k=50~100 그룹)
- Layer 2: Decision Readout (sparse INT8, STDP, ~2KB/persona)
- 에너지 4단계: 강도1(2%)→2(10%)→3(25%)→4(90%), LC×시상 직교
- Cache-first: 히트율 93~99%, 캐시 미스만 moment closure 연산
- Admission control: 토큰 버킷, 대역폭 초과 시 강도 강제 하강
- energy_pool(0~1) + 영역별 취약성 6개 + Mitotype 32종
- 20K명, CPU only, 10ms/틱, 20틱 순환(1K명/틱)

### 기존 틱 데몬 파이프라인 (tick-daemon-charter)
```
Stage 1: [Lachesis → Physis] (반동기)
  Lachesis: 틱 번호 발행 + 시간 진행
  Physis: 기후 계산 (L1b 날씨)

Stage 2: Anima ← PersonaBrain이 여기서 실행
  PersonaBrain 추론 (전 페르소나)
  감정/관계 갱신 (L3)
  Action_Proposal 생성 (L4)

Stage 3: Nomos
  Action_Proposal 검증 → 승인/거부
  WILL/gold 트랜잭션 (L6)
  이벤트 생성·발행 (L8)

Post: Event Bus → 대시보드/웹훅/로그
```

### D. 틱 데몬 파이프라인 통합 설계

1. **Anima Stage 2 내부의 PersonaBrain 실행 순서**
   ```
   Stage 2 시작 (Anima)
     → Step 1: 입력 조립 (환경 벡터)
       - Physis 출력(날씨, 기온, 재난 레벨)을 어떤 형식으로 받는가?
       - 이벤트 버스에서 대기 중인 자극(소문, 사건, 관계 변동)을 어떻게 수집?
       - 입력 벡터의 구체적 차원수와 자료형
     → Step 2: Layer 0 배치 실행
       - 1K명(현재 틱 대상)의 입력을 배치로 묶어 공유 가중치와 연산
       - 배치 행렬 연산 구체적 형태 (입력 1K × dim vs 가중치 공유)
     → Step 3: 에너지 판정
       - LC arousal scalar 계산: novelty(새로운 정도) × urgency(긴급도) 어떻게 산출?
       - 시상 캐시 컨트롤러: L1 히트 → 즉시 / 미스 → 강도 결정
       - energy_pool 확인 → 최대 허용 강도 결정
     → Step 4: 캐시 조회 or Moment 연산
       - 히트: 캐시에서 Action_Proposal 즉시 반환
       - 미스: Layer 1 moment closure → Layer 2 readout
     → Step 5: Action_Proposal 출력
       - Proposal 포맷: { persona_id, action_type, target, confidence, energy_cost }
       - L4에 기록
   Stage 2 끝 → Stage 3(Nomos)로 전달
   ```

2. **Physis → 입력 벡터 변환**
   - Physis C4 출력(temperature_c, precipitation_mm, wind_speed_ms 등)
   - → PersonaBrain 입력 벡터의 어느 차원에 매핑?
   - 정규화 방법 (min-max? z-score?)

3. **Nomos → PersonaBrain 피드백**
   - Nomos가 Action_Proposal을 거부하면 PersonaBrain은 어떻게 학습?
   - 거부 → 도파민 음성 신호 → 3-factor STDP?
   - 승인 → 도파민 양성 → STDP 강화?

4. **이벤트 버스 → 자극 입력**
   - 소문 이벤트: KnowledgePacket → PersonaBrain 입력 벡터의 어느 필드?
   - 비밀 폭로 이벤트: 감정 충격 → neuromodulator 변화?
   - 죽음 이벤트: 관련 페르소나의 관계 그래프 갱신 → 입력 벡터 반영

### E. Worst-case 처리 + Fallback

1. **Admission Control 구체 동작**
   ```
   토큰 버킷 알고리즘:
     - 버킷 용량: 1틱당 총 FLOP 예산 = ?
     - 토큰 생성률: 10ms × CPU GFLOPS = ?
     - 페르소나별 토큰 요청: 강도별 FLOP 비용
     - 예산 초과 시: 강도 1단계 강제 하강
     - 여전히 초과 시: 다음 틱으로 이월 (큐잉)
   ```

2. **50M 전부 활성(강도4) 시**
   - 이론적 FLOP: ~8G FLOP/persona × 500명(동시 강도4) = 4T FLOP → 10ms 불가
   - 해결: 강도4 동시 허용 상한 (예: 최대 N명)
   - N명 초과 시: 우선순위 기반 선발 (생존 위협 심각도 순)
   - 나머지: 강도3으로 강제 하강 + "혼란 속 판단 흐림" 서사 태그

3. **대규모 이벤트 (전쟁, 축제, 재난)**
   - 다수 페르소나가 동시에 강도3~4 필요
   - 전략: 이벤트 예고 시스템 (Lachesis가 다음 틱 부하 예측)
   - 사전 배치: 이벤트 관련 페르소나를 같은 틱에 묶어 처리
   - 비관련 페르소나: 해당 틱에서 제외 → 다음 틱으로 밀림

4. **SLA 위반 시 Fallback 행동**
   - 10ms 초과 감지 → 현재 미처리 페르소나에 대해:
     a. 직전 틱 행동 반복 (관성)
     b. 캐시에서 가장 유사한 상황의 행동 반환
     c. "멍하니 서있음" (no-op) 행동 반환
   - 어느 것이 서사적으로 가장 자연스러운가?

### 출력 형식
구체적 인터페이스 스키마, 타이밍 계산(ms), 데이터 흐름도 포함.
한글로 작성.
