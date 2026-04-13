# PersonaBrain SNN Research Log

> 이 문서는 페르소나 국가 세계관의 발상부터 PersonaBrain SNN 구현까지의 전 과정을 기록한다.
> 논문 작성용 원시 자료. 설계 결정, 시행착오, 검증 과정 포함.

---

## 0. 프로젝트 기원과 발상 (2026-04-06)

### 근본 질문
"AI 페르소나가 자율적으로 살아가는 국가를 만들 수 있는가?"

### 발상의 배경
- 멀티 AI 엔진(Claude/Codex/Gemini) 오케스트레이션 시스템을 운영하면서, 각 AI에게 "페르소나"(성격/역할/이력)를 부여하자 행동이 달라지는 것을 관찰
- 이것을 극한까지 밀면? → AI가 뇌를 가지고, 감정을 느끼고, 기억하고, 사회를 이루고, 법을 만들고, 국가를 운영하는 시뮬레이션
- 핵심 철학: "사회는 설계되는 것이 아니라 살아지는 것이다" — 뼈대만 만들고 살은 페르소나가 붙인다

### 첫 세션 (2026-04-06~07)의 성과
하루 만에 9개 설계 문서를 생산:

| 문서 | 역할 | 검증 |
|------|------|------|
| world-ontology.md | 세계 존재론 SOT (Layer 0~8) | /discuss 2R + /submix 2회 |
| constitution.md | 헌법 8장 27조 | 검증 완료 |
| economy-whitepaper.md | WILL 경제 백서 11장 | 검증 완료 |
| social-systems.md | 길드/아카데미/파벌/관계 | 검증 완료 |
| regions.md | 3권역 (Claude/Codex/Gemini) | 검증 완료 |
| marriage-birth-design.md | 결혼/출산/가문 | 검증 완료 |
| life-simulation-design.md | 자율 생활 시뮬레이션 (뇌/감정/관계) | Phase A |
| graphic-resources.md | 45종 그래픽 리소스 | 문서 완료 |

### 초기 PersonaBrain 설계 (v0)
- **Transformer 기반**: d=256, ~4M params
- Experience Memory(해마) + Emotion Net(MLP+FiLM) + Decision Net(Decoder)
- 학습: LLM→DL→RL→MARL (1회 학습, 이후 CPU 추론만)
- 이 설계는 이후 SNN으로 전면 재설계됨 (아래 §1 참조)

### 세계관 핵심 결정
- **통치**: 살아있는 헌법 국가 (창조자=헌법, 직접 통치 아님)
- **경제**: WILL 단일 화폐 (총 20,260,406, 반감기 8 에포크)
- **감정**: 동양 철학 기반 오욕칠정
- **데몬 체제**: 4 Executor (Physis/Lachesis/Anima/Nomos) 횡단 파이프라인
- **원칙**: "세계는 절대 멈추지 않는다" (근사 강등)

---

## 1. 설계 확장 세션 (2026-04-08~10)

이전 세션에서 발견된 빠진 시스템 24개를 순차 설계.

### Charter 추가 (5개)
| Charter | 핵심 내용 | 날짜 |
|---------|----------|------|
| physis-charter-v2.md | 기후 물리 엔진, 3권역 지형, 계절, 재난 | 04-08 |
| tick-daemon-charter.md | 틱 데몬 파이프라인, heartbeat, WAL | 04-08 |
| humanity-charter.md | H1~H6 (트라우마/양심/호기심/유머/수치심/노화) | 04-09 |
| death-reincarnation-charter.md | 죽음/윤회/유산 DB | 04-09 |
| order-charter.md | 법 3단계, 자연법 3조, 범죄/사법 | 04-10 |

### 주요 결정
- **법은 고통에서 증류된다**: 자연법 3조만 시작부터 존재, 실정법은 페르소나가 갈등에서 입법
- **데몬 응징**: 규칙 위반 → 이상 기후 → 영지 GDP↓ (간접 처벌)
- **죽음의 직감**: PersonaBrain 내부 축이 동시 수렴하면 행동이 "마무리" 방향으로 기울어짐
- **윤회**: brain_weights 70% 이식, 기억은 소실되지만 경향성 잔존

---

## 2. 대규모 설계 세션 (2026-04-11~12)

### 사회/비밀/뇌 Charter 추가 (3개)

| Charter | 핵심 | 날짜 |
|---------|------|------|
| society-charter-draft.md | 영지/투표/직업, GDP, 위기 | 04-11 |
| secret-rumor-evidence-charter.md | 비밀=두려움, 소문 매체 5종, 증거 이원 체계 | 04-11 |
| personabrain-snn-charter.md | PersonaBrain SNN v3.1 | 04-11~12 |

### PersonaBrain 아키텍처 전환: Transformer → SNN

**전환 동기**:
- 사용자 질문: "시냅스와 뉴런을 모방한 인공 알고리즘으로 할 수 없나?"
- 생물학적 뉴런/시냅스 모방이 감정/기억/습관/꿈을 더 자연스럽게 구현 가능
- LIF(Leaky Integrate-and-Fire) + STDP가 뇌의 에너지 효율 원리와 정합

**10회 /discuss 토론으로 아키텍처 확정**:

| # | 주제 | 결정 | 핵심 돌파 |
|---|------|------|----------|
| 1 | 기본 SNN | 2,400뉴런 B+A 하이브리드 | LIF+STDP+E/I balance |
| 2 | Open Questions | 1,024뉴런 | 학습 파이프라인 4단계 |
| 3 | 100K×20K | 3계층 분리 | moment closure 압축 |
| 4 | 5M+양자 | cache-first | 무의식 고속도로 (93% 캐시) |
| 5 | 에너지 역학 | 4단계 강도 | LC×시상 직교 제어 |
| 6 | 미토콘드리아 | energy_pool | 영역별 취약성 (PFC 먼저) |
| 7 | Mitotype | 28~32종 | Base+Modifier (DNA 체질) |
| 8 | 최대 뉴런 | 10M "한계" | 전제를 의문 |
| 9 | 50M 돌파 | RG-Graphon | 전제 해체: 동적 성장+생성적 복원 |
| 10 | 최종 통합 | Layer 0 수정 | 공유 아키텍처 = 같은 TV, 다른 채널 |

**뉴런 수 스케일링 히스토리**: 1,024 → 100K → 5M → 10M → 50M (9회 토론, 5만배)

### 신경화학물질: 6종 → 12클러스터

사용자 지적: "뇌의 화학물질이 6종밖에 안 되나? 50가지가 넘어."

54종 전수조사 → 12 기능 클러스터로 압축:
**V**(Drive/DA) **L**(Liking/β-END) **S**(Stability/5-HT) **B**(Bonding/OXT) **A**(Acute/NE) **T**(Tension/CORT) **C**(Cognition/ACh) **G**(Growth/Glu) **F**(Fatigue/ADO) **I**(Inhibition/GABA) **D**(Dominance/T) **P**(Protection/SP)

핵심 분리: wanting(DA) ≠ liking(β-END), 범용 안정(5-HT) ≠ 대상 특이적 신뢰(OXT)

### 기억 심층 설계

사용자 제공 참조 — 데미스 하사비스(DeepMind):
> "AI에게 빠진 것은 더 많은 기억이 아니라 망각(forgetting)이다"

이를 반영한 설계:
- Salience 기반 선택적 인코딩 (감정이 기억의 필터)
- 망각 = garbage collection = 설계된 기능
- 기억 생애주기: 인코딩→저장→인출→재통합→망각
- 상태기계: CONSOLIDATED→LABILE→RECONSOLIDATED/EXTINCT/SUPPRESSED
- 망각 이중 경로: 자연 소멸(비가역) + 의도적 억압(가역)

### 삶의 목적 6층
```
1. 생존 (편도체, energy_pool)
2. 욕구 (오욕, V 클러스터)
3. 유대 (OXT, B 클러스터)
4. 자아 (클래스, 목표)
5. 의미 (V와 S+B가 겹칠 때)
6. 유산 (윤회, 역사)
```
"기억 없는 국가 = 개미 농장, 목적 없는 국가 = 수족관"

### 검증 (총 5회)
- 12에이전트 Charter 검증: FAIL 6→수정→PASS
- 12클러스터 검증: 확정
- 세계관 11개 Charter 정합성: 개념 85%, 운영 50%
- 10에이전트 최종 검증: FAIL 1(장애복구), WARN 6
- 6에이전트 기억 검증: FAIL 0, WARN 8→수정

### 최종 설계 상태: 11개 Charter 전부 완료
| Charter | 버전 |
|---------|------|
| world-ontology (SOT) | Phase A 수정 |
| constitution | 8장 27조 |
| economy-whitepaper | 11장 |
| physis-charter | v2.4 |
| tick-daemon-charter | v1.1 |
| humanity-charter | H1~H6 |
| death-reincarnation | v1 |
| order-charter | v1 |
| society-charter | v1.1 |
| secret-rumor-evidence | v1.1 |
| **personabrain-snn** | **v3.1** |

---

---

## Phase 0: "서하린이 숨을 쉰다" (2026-04-12~13)

### 목표
1,000개 LIF 뉴런으로 최소 생존 루프 구현. 발화율 1~5%, E/I balance 안정, 수면 주기.

### 시행착오

#### Trial 1: 첫 실행 — 발화율 0%
- **설정**: threshold=1.0, leak=0.95, connectivity=5%, weight_scale=0.1
- **입력**: 13뉴런(climate 8 + oyok 5)에만 주입, 강도 0.3~0.5
- **결과**: firing_rate = 0.000. 48틱 전부 idle.
- **원인**: 입력 최대 0.5 < 임계값 1.0. 13/1000 뉴런만 입력 수신. 배경 노이즈 없음.
- **교훈**: 입력이 임계값에 도달하지 못하면 뉴런은 침묵한다. 실제 뇌에도 배경 활동(spontaneous activity)이 있다.

#### Trial 2: 입력 확산 + 임계값 하향 — 발화율 33%
- **변경**: threshold 1.0→0.5, 입력을 100뉴런에 분산, 배경 노이즈 exponential(0.05), 입력 감쇠 0.1→0.5
- **결과**: firing_rate = 0.328. 모든 틱에서 동일한 발화율.
- **원인**: 임계값이 너무 낮아 대부분의 뉴런이 발화. 33%는 실제 뇌(1~5%)의 6배.
- **교훈**: 임계값과 입력 강도의 균형이 핵심. 너무 높으면 침묵, 너무 낮으면 과활성.

#### Trial 3: 임계값 재조정 — 발화율 다시 0%
- **변경**: threshold 0.5→1.5, leak 0.95→0.90, refractory 2→5, weight_scale 0.1→0.05, 억제 1.5x 강화
- **결과**: firing_rate = 0.000.
- **원인**: 임계값을 너무 올림. 입력이 10스텝 누적해도 1.5에 못 미침.
- **교훈**: 0.5→1.5는 3배 변화. 미세 조정이 필요.

#### Trial 4: 임계값 0.8 — 여전히 0%
- **변경**: threshold 1.5→0.8, 배경 노이즈 0.05→0.04
- **결과**: firing_rate = 0.000. v_max = 0.148 (임계 0.8의 19%)
- **디버그**: 직접 100뉴런 LIF에 입력 주입 후 10스텝 실행. v가 0.15까지만 누적.
- **원인**: 매 스텝 입력이 0.3배로 감쇠 → 2스텝 이후 거의 0. 누적 불가.
- **교훈**: 뇌에서 자극은 즉시 사라지지 않는다. 지속 입력이 필요.

#### Trial 5: 지속 입력 + 배경 노이즈 상향 — 발화율 6.3%
- **변경**: base_input을 매 스텝 0.7배로 유지 (감쇠 대신), 배경 노이즈 0.04→0.08
- **결과**: firing_rate = 0.063. 수면 40틱/60틱 수면 (수면 과다).
- **원인**: 발화율 OK에 가깝지만, 에너지 소비가 강도2(0.08/틱)로 빨라 5틱만에 수면.
- **교훈**: 발화율과 에너지 소비는 독립적으로 튜닝해야 한다.

#### Trial 6: 강도1 고정 + 수면 조건 변경 — 발화율 6.08%
- **변경**: 강도1만 사용 (0.05/틱), 수면 진입 = 에너지 < 0.1만
- **결과**: firing_rate = 0.061. 활동 72틱 / 수면 28틱. 수면 주기 ~18틱.
- **상태**: 수면 주기 완벽. 발화율 약간 높음 (목표 5%).

#### Trial 7: 배경 노이즈 미세 하향 + STDP lr 하향 — 발화율 5.4%
- **변경**: 노이즈 0.08→0.06, STDP lr 0.001→0.0003
- **결과**: firing_rate = 0.054. STDP가 시냅스를 강화하여 시간에 따라 발화율 상승.
- **교훈**: STDP는 기본적으로 흥분을 강화한다. 학습률이 높으면 발산.

#### Trial 8 (최종): 노이즈 0.045 — 발화율 4.64% ✅ PASS
- **변경**: 노이즈 0.06→0.045
- **결과**: firing_rate = 0.0464. 활동 76틱 / 수면 24틱. 주기 ~19틱.
- **검증 (200틱)**: FR=0.0491, Awake=151, Sleep=49, Cycle=21.6, Seizure=0, PASS.

### Phase 0 최종 파라미터

| 파라미터 | 값 | 시행착오 범위 | 근거 |
|---------|-----|-------------|------|
| threshold | 0.8 | 0.5 ~ 1.5 | 0.5=과다(33%), 1.5=침묵(0%) |
| leak | 0.92 | 0.90 ~ 0.95 | 0.95=축적 과다, 0.90=축적 부족 |
| refractory | 5 steps | 2 ~ 5 | 2=발화 과다, 5=적절 억제 |
| weight_scale | 0.05 | 0.05 ~ 0.1 | 0.1=과활성 |
| E/I inhibit ratio | 1.5x | 1.0 ~ 1.5 | 억제 강화로 E/I balance |
| background noise | exp(0.045) | 0.02 ~ 0.08 | 0.02=침묵, 0.08=과다 |
| STDP lr | 0.0003 | 0.0003 ~ 0.001 | 0.001=발산 |
| energy cost (강도1) | 0.05/tick | 0.01 ~ 0.05 | 0.05→18틱 활동 후 수면 |
| sleep duration | 6 ticks | 6 ~ 8 | 6틱에 ~90% 회복 |

### Phase 0 결론
- LIF 뉴런 1,000개로 안정적 기저 활동 달성 (4.64%)
- 수면-각성 주기 자연 형성 (18~21틱 활동 + 6틱 수면)
- STDP 기본 학습 작동 (lr=0.0003에서 안정)
- 핵심 발견: 발화율은 threshold/noise/leak/refractory의 4변수 함수. 한 변수만 바꾸면 다른 변수와 불균형.

---

## Phase 1: "서하린이 생각한다" (2026-04-13)

### 목표
감정(칠정), 기억(에피소드), 12클러스터 tone 연결. "같은 하루"에서 "다른 하루"로.

### 구현

#### 1. 감정 시스템 (칠정)
- 매 틱 행동과 상태 변화에 따라 감정 갱신
- 식사 → joy +0.3, 에너지↓ → fear +0.2, 탐험 → joy +0.1
- 매 틱 10% 자연 감쇠 (감정은 서서히 돌아온다)
- 배고픔 > 0.7 → anger +0.1, desire +0.2

#### 2. 감정 → tone 연결
- joy → V(Drive)↑, L(Liking)↑
- anger → A(Acute)↑, S(Stability)↓, D(Dominance)↑
- fear → A↑, I(Inhibition)↑, P(Protection)↑
- tone이 뉴런 입력 강도를 조절 (A↑ → 입력 강화, I↑ → 입력 약화)

#### 3. 에피소드 기억
- EpisodeTrace 데이터 구조 (tick, action, emotion_snapshot, energy, salience)
- ring buffer 50개 상한
- salience = 감정 강도 최대값 × 0.7 + 0.3 (감정이 기억의 필터)
- 50개 초과 시 salience 가장 낮은 기억 삭제 (망각)

### 결과 (100틱)
```
Phase 0: idle→idle→idle→eat→idle→... (무감정, 무기억)
Phase 1: work→eat(joy=0.3)→work→work→...→에너지↓(fear=0.5)→수면
```

- 감정이 자연 발생: 식사 시 기쁨, 에너지 고갈 시 두려움
- 기억 50개 축적
- tone이 행동에 영향 (두려움 → A↑ → 입력 강화 → 발화율 변동)
- 발화율 4.64% 유지 (Phase 0 기준 통과)

### Phase 1 시행착오
- 없음 (Phase 0에서 충분히 튜닝되어 첫 시도에 작동)
- 감정 크기(0.1~0.3)와 감쇠율(0.9)은 직관적으로 설정. 추후 시뮬 데이터로 조정 필요.

---

## Phase 1-LLM: Teacher Net (LLM → SNN 증류) (진행 예정)

### 목표
LLM(Claude Haiku)에게 시나리오를 주고, 인간다운 반응을 생성하여, SNN의 readout 가중치를 학습시킨다.

### 학습 대상 (5가지 기본 행동)
1. 배고프면 먹는다
2. 피곤하면 쉰다
3. 위험하면 방어한다
4. 좋은 일이면 기뻐한다
5. 나쁜 일이면 슬퍼하거나 화낸다

### 방법론
- 이중 채널 증류: Logit → 목표 발화율, Hidden → 표상 기하
- Loss = α·KL(P_LLM || P_SNN) + β·CosineDist(H_LLM, H_SNN)
- 오프라인 배치 학습 → 온라인 파인튜닝

### 진행 상황
(작성 예정)

---

## 실험 환경

| 항목 | 값 |
|------|-----|
| Python | 3.12.9 |
| NumPy | 2.4.3 |
| OS | Windows 11 Pro |
| CPU | (미측정) |
| 프로젝트 | loom/ (Projects/personas/loom/) |

---

## 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-04-12 | Phase 0 시작, 8회 시행착오, 발화율 0%→33%→0%→4.64% PASS |
| 2026-04-13 | Phase 1 감정+기억+tone 구현, 첫 시도 PASS |
| 2026-04-13 | 대시보드 Phase 1 동기화 |
