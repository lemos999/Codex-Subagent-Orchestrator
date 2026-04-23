# Loom - Persona Nation SNN Simulation: Complete Project Guide

> 이 문서는 Codex(GPT)가 프로젝트를 완전히 이해하기 위한 종합 가이드입니다.
> Claude가 설계/리뷰를 담당하고, Codex가 코딩을 담당합니다.
> **모든 구현의 최우선 원칙: SNN 기반 자연 창발. 규칙은 가이드일 뿐.**

---

## 1. 프로젝트 비전

"AI 페르소나가 뉴런으로 생각하고, 시냅스로 학습하고, 스스로 사회를 만드는 국가"

### 핵심 철학
- **사회는 설계되는 것이 아니라 살아지는 것이다** - 뼈대만 만들고 살은 페르소나가 붙인다
- **모든 행동은 뉴런에서 나온다** - if-else가 아닌 Spiking Neural Network의 발화 패턴
- **규칙(가이드)은 창발의 한계를 보완한다** - 도로와 신호등은 인프라일 뿐, 걷는 건 사람
- **위기는 내장된다** - 재난, 경제 위기, 정치 위기는 극단에서 자연 발생

### SNN 창발 vs 규칙의 경계

| 구분 | SNN 창발 (목표) | 규칙/가이드 (보완) |
|------|----------------|-------------------|
| 정의 | 뉴런 발화 -> 시냅스 학습 -> 행동 자연 발생 | if-else, 상수, 조건문으로 강제 |
| 예시 | "배고프면 먹는다" = 시냅스에서 나옴 | "NPC 식량 가격 = 15 gold" = 하드코딩 |
| 원칙 | **먼저 SNN으로 시도** | SNN 불가능할 때만 사용 |
| 계층 | Layer 2~4 (뇌/감정/행동) | Layer 0~1 (물리법칙/인프라) |
| 목표 | Layer 5~7도 SNN 연결 | 최소한의 가이드레일 |

---

## 2. 세계 존재론 (World Ontology) - Layer 0~8

```
Layer 8: Drama     -- 이벤트, 재난, 비밀, 소문, 죽음, 윤회
Layer 7: Govern    -- 헌법, 의회, 법안, 청원, 투표, 사법     [미구현]
Layer 6: Economy   -- goods, gold, 세금, 시장, 고용            [Phase 11: 골격]
Layer 5: Social    -- 관계, 계급, 길드, 가문                   [하이브리드]
Layer 4: Agency    -- 행동 선택, Deliberation                   [SNN 창발]
Layer 3: Inner     -- 감정(칠정7), 욕구(오욕5), 기억, 성격     [SNN 창발]
Layer 2: Entity    -- 페르소나, PersonaBrain SNN               [SNN 창발]
Layer 1: Substrate -- 기후, 지형, 시간, 3권역                  [규칙]
Layer 0: Origin    -- 창조자(헌법), 자연법 3조                  [규칙]
```

**상위 구속 원칙**: 하위 Layer는 상위 Layer의 제약을 받는다.
물리법칙(L1)을 뇌(L2)가 어길 수 없고, 자연법(L0.5)은 Nomos가 즉시 감지한다.

### 3권역 구조

| 권역 | 이름 | AI 엔진 | 영주 | 특징 |
|------|------|---------|------|------|
| Claude | Seorim (서림) | Claude | Seo Harin | 감성적, 협조적 |
| Codex | Ironridge (철릉) | GPT | Rex Valen | 이성적, 엄격한 |
| Gemini | Mirrordale (경곡) | Gemini | Baek Sujin | 대담한, 감성적 |

---

## 3. SNN 아키텍처 (PersonaBrain)

### 3.1 개요

```
입력(기후+욕구+신경조절물질)
  -> 1,000개 LIF 뉴런 (E:I = 80:20, 12클러스터)
    -> 10 시뮬레이션 스텝
      -> 발화율 벡터 [1000]
        -> Readout 가중치 (6x1000)
          -> action_logits [6]
            -> 욕구/성격/드라이브 보정
              -> 행동 선택 (6종)
```

### 3.2 LIF 뉴런 모델

```python
V(t+1) = leak * V(t) + synaptic_input + external_input
if V >= threshold: spike, V -> 0, refractory 5 steps
```

| 파라미터 | 값 | 의미 |
|---------|-----|------|
| n_neurons | 1,000 | 총 뉴런 수 |
| E/I ratio | 80:20 | 흥분 800, 억제 200 |
| leak | 0.92 | 매 스텝 8% 전압 누출 |
| threshold | 0.8 | 발화 임계 (항상성: 0.3~2.0) |
| refractory | 5 steps | 발화 후 불응기 |
| sparsity | 5% | 시냅스 연결 확률 |
| target_firing_rate | 4% | 항상성 목표 발화율 |

### 3.3 12 클러스터

```
Index  Name    Chemistry   Role
[0]    V       DA          동기/갈망 유지
[1]    L       OXT(part)   보상 예측
[2]    S       5-HT        충동 억제, 안정
[3]    B       OXT(full)   사회적 유대
[4]    A       NE          각성/경보 (역U)
[5]    T       CORT        스트레스 (역U)
[6]    C       ACh         인지/STDP 속도
[7]    G       Glu         성장 촉진
[8]    F       -           피로도
[9]    I       GABA        잡음 차단
[10]   D       -           지배/주도
[11]   P       -           보호/방어
```

### 3.4 STDP 학습

**기본 STDP** (항상 실행):
```
eligibility_trace[post, pre] += pre_trace * connection_mask
weights += stdp_lr(0.0003) * pre_matrix * connection_mask
```

**3-factor STDP** (도파민 신호 존재 시):
```
if reward > 0.01:
    dw = rl_lr(0.005) * reward * eligibility_trace
    eligibility_trace *= 0.5  # 소비
```

가중치 범위: 흥분 [0, 0.3], 억제 [-0.5, 0]

### 3.5 입력 인코딩

| 입력 | 뉴런 범위 | 강도 | 소스 |
|------|----------|------|------|
| climate_vec[8] | 0~99 | x0.2 | 기후 (온도/강수/바람...) |
| oyok[5] | 100~149 | +0.4/-0.2 | 욕구 (hunger/sleep...) |
| fear | 150~199 | +0.3 | 칠정[3] |
| joy | 200~249 | +0.2 | 칠정[0] |
| anger | 250~299 | +0.25 | 칠정[1] |

tone[12]는 전체 입력의 게인/노이즈를 조절:
- tone_mean -> 게인 (0.8~1.2)
- A(NE) -> 노이즈 증폭 (x1.3)
- I(GABA) -> 노이즈 억제 (x0.7)

### 3.6 행동 결정 파이프라인

```
1) base_logits = readout_weights @ firing_rate      # SNN 출력
2) + 욕구 보정 (hunger->eat, fatigue->sleep)        # 생존 바이어스
3) + 성격 보정 (외향->socialize, 대담->explore)     # 개성
4) + Drive 보정 (숙달x적성x몰입xDA)                 # 숙달 동기
5) + 사회 보정 (social_pull, past_success)           # 경험
6) energy < 0.1 -> 강제 sleep                        # 생존 규칙
7) fear > 0.7 -> softmax (확률적), else -> argmax    # 공포=탐색
```

6개 행동: `idle, work, eat, sleep, explore, socialize`

### 3.7 보상 시스템

PersonaBrain은 행동 후 reward를 받아 3-factor STDP로 학습:

| 상황 | reward | 근거 |
|------|--------|------|
| 에너지 고갈 (<0.1) | -0.5 | 생존 위협 |
| 배고플 때 먹음 (hunger>0.5) | +0.5 | 적절 충족 |
| 안 배고픈데 먹음 (hunger<0.2) | -0.2 | 낭비 |
| 피곤할 때 잠 (energy<0.3) | +0.3 | 적절 휴식 |
| 여유 있을 때 일 (energy>0.5) | +0.2 | 생산적 |
| 무행동 (idle) | -0.05 | 무행동 벌점 |
| 몰입(flow) 경험 | +0.3 | 숙달 보상 |
| 적성 일치 일 | +0.1~0.3 | 적성 강화 |

---

## 4. 데이터 모델 (ontology/layers.py, 1,301줄)

### 4.1 핵심 Dataclass

#### Persona (개체)
```python
id, name, full_name, region, territory, persona_class(1~9)
neuron_count(1000), personality[5], employment_id, aptitude_map{}
# personality: [내향-외향, 신중-대담, 이성-감성, 독립-협조, 관대-엄격]
# 각 축 0.0~1.0, 0.5가 중립
```

#### InnerWorld (내면)
```python
tone[12]          # 신경조절물질 (np.float16, 기본 1.0)
energy_pool       # 에너지 (0~1)
chiljeong[7]      # 감정: joy, anger, sadness, fear, love, disgust, desire
oyok[5]           # 욕구: hunger, sleepiness, lust, greed, honor
chronic_stress    # 만성 스트레스 (0~1)
chronic_comfort   # 만성 안락 (0~1)
vitality          # 생명력 (0~1, 0이면 사망)

# 기억
episodes[]        # EpisodeTrace 목록 (ring buffer, 최대 50)
                  # 상태: FRESH -> CONSOLIDATED -> LABILE -> RECONSOLIDATED/EXTINCT/SUPPRESSED

# 숙달
skill_profiles{}  # {skill_id: SkillProfile}

# 경제 (Phase 11)
inventory{}       # {food:10, material:0, tool:0, medicine:0, knowledge:0}
equipped_tool_durability  # None 또는 0~100
consecutive_hunger_ticks  # 연속 굶주림 틱

# 승급 추적
promotion_stable_ticks    # STDP 안정화 축적
promotion_drive_history[] # drive 이력 (최근 20)
promotion_contrib_window[]# contribution 이력 (최근 500)
effective_class           # 유효 클래스 (강등 시 persona_class와 분리)

# Nomos 추적
nomos_violation_count     # 위반 횟수 (100틱 무위반 시 -1)
nomos_blocked_until       # 행동 차단 종료 틱
```

#### SkillProfile (숙달)
```python
skill_id          # "laborer", "farmer", "craftsman", "healer", "scholar", "guard"
mastery           # 0~ceiling (직업별 다름)
total_ticks       # 총 작업 틱
flow_ticks        # 몰입 상태 틱
last_tick         # 마지막 작업 틱
burnout_accumulator  # 번아웃 축적
```

#### Wallet (재정)
```python
will              # WILL 화폐 (1 WILL = 1,000 gold)
gold              # gold 소단위
# pay(amount) -> gold에서 차감
# receive(amount) -> gold에 가산
# total_in_gold() -> will*1000 + gold
```

### 4.2 경제 상수

```python
# 직업 -> 산출 재화
JOB_OUTPUT_MAP = {
    "farmer":"food", "laborer":"material", "craftsman":"tool",
    "healer":"medicine", "scholar":"knowledge", "guard":"material"
}

# 직업별 기본 산출량 (1틱, 보정 전)
JOB_BASE_OUTPUT = {
    "farmer":2.0, "laborer":1.5, "craftsman":0.5,
    "healer":0.3, "scholar":0.2, "guard":0.5
}

# NPC 상점 (외부 상단)
NPC_PRICES = {
    "food":     {"buy":15, "sell":3,  "daily_stock":50},
    "material": {"buy":20, "sell":5,  "daily_stock":30},
    "tool":     {"buy":80, "sell":15, "daily_stock":5},
    "medicine": {"buy":40, "sell":8,  "daily_stock":10},
    "knowledge":{"buy":60, "sell":12, "daily_stock":3},
}

FOOD_CONSUME_PER_TICK = 1       # 매 틱 식량 자동 소비
TOOL_MAX_DURABILITY = 100       # 도구 최대 내구도
TOOL_WEAR_PER_TICK = 1          # 마모 속도
TOOL_PRODUCTIVITY_BONUS = 0.5   # 도구 있으면 +50%
TOOL_BROKEN_PENALTY = 0.3       # 도구 없으면 -30%
GOLD_DIRECT_PAY_RATIO = 0.3     # 자영 시 gold 직접 지급 비율
```

### 4.3 승급 규칙

```python
CLASS_RULES = {
    2: {"base_obs_ticks":200,  "flow_thr":0.05, "drive_var_max":0.15,
        "gate":{"mastery_ratio":0.3, "contribution":0.05, "peer_recognition":0.05, "stability":0.5}},
    3: {"base_obs_ticks":400,  "flow_thr":0.10, "drive_var_max":0.12,
        "gate":{"mastery_ratio":0.5, "contribution":0.15, "peer_recognition":0.15, "stability":0.6}},
    4: {"base_obs_ticks":700,  "flow_thr":0.18, "drive_var_max":0.10,
        "gate":{"mastery_ratio":0.7, "contribution":0.30, "peer_recognition":0.3, "stability":0.7}},
    5: {"base_obs_ticks":1000, "flow_thr":0.25, "drive_var_max":0.08,
        "gate":{"mastery_ratio":0.85,"contribution":0.50, "peer_recognition":0.45,"stability":0.75}},
}
CLASS_TITLES = {1:"초심자", 2:"견습생", 3:"장인", 4:"숙련가", 5:"대가"}

SKILL_CEILINGS = {
    "laborer":   (0.3, 0.2, 0.010),  # (ceiling, complexity, base_lr)
    "farmer":    (0.5, 0.4, 0.006),
    "guard":     (0.5, 0.4, 0.005),
    "craftsman": (0.8, 0.7, 0.003),
    "healer":    (0.9, 0.8, 0.002),
    "scholar":   (1.0, 0.9, 0.001),
}
```

### 4.4 Nomos (자연법) 응징

```python
NOMOS_SEVERITY = {
    "경미": {"threshold":1,  "class_penalty":0, "blocked_ticks":0,   "stress_delta":0.01},
    "중대": {"threshold":5,  "class_penalty":1, "blocked_ticks":48,  "stress_delta":0.05},
    "금기": {"threshold":10, "class_penalty":3, "blocked_ticks":200, "stress_delta":0.15},
}
NOMOS_DECAY_INTERVAL = 100  # 무위반 100틱마다 violation_count -1
```

### 4.5 기타 모델

```python
Relationship(persona_a, persona_b, familiarity, trust, interaction_count)
Secret(owner_id, content_tag, salience, known_by{}, revealed_tick)
Rumor(about_id, content_tag, accuracy, origin_tick, known_by{}, spread_count)
# Rumor.distort(): accuracy *= 0.85 (전파마다 왜곡)

EpisodeTrace(tick, action, emotion_snapshot, energy_at_time, salience)
# 상태기계: FRESH -> CONSOLIDATED -> LABILE -> RECONSOLIDATED/EXTINCT/SUPPRESSED

MarketOrder(id, seller_id, goods_type, quantity, price_per_unit, created_tick, territory_id)

Territory(id, name, region, lord_id, treasury_gold, treasury_will, facilities[])
```

---

## 5. 엔진 구조 (core/multi_tick_engine.py, 3,010줄)

### 5.1 초기화

```python
class MultiTickEngine:
    def __init__(self):
        self.creator       # Creator (헌법)
        self.climate        # 기후 엔진 (Physis)
        self.time           # GameTime (틱/시간/계절)
        
        # 10명 페르소나
        self.personas{}     # {pid: Persona}
        self.inners{}       # {pid: InnerWorld}
        self.brains{}       # {pid: PersonaBrain}
        self.secrets{}      # {pid: Secret}
        
        # 사회
        self.relationships[]  # Relationship 목록
        self.rumors[]         # Rumor 목록
        
        # 경제
        self.wallets{}        # {pid: Wallet} (초기 gold 2,000)
        self.jobs{}           # {job_id: Job}
        self.employments{}    # {employment_id: Employment}
        self.market_orders[]  # MarketOrder 목록
        self.knowledge_records[]  # KnowledgeRecord 목록
        
        # 영지 (3개)
        self.territories{}    # {territory_id: Territory} (금고 gold 3,000)
```

### 5.2 tick() 전체 흐름

```
Stage 0:   기후 계산 (Physis -> 권역별 Weather)
Stage 1:   개별 페르소나 루프
  |-- [NEW] _process_survival_consume(pid)     # 매 틱 food -1
  |-- Brain.tick() -> action 결정              # SNN 추론
  |-- Nomos 차단 검사                          # 위반 시 idle 강제
  |-- action별 처리:
  |   |-- work:  _update_mastery_tick + _process_economy + _wear_tool + _update_promotion_trigger
  |   |-- eat:   _process_eat (인벤토리/시설/자연/굶음)
  |   |-- sleep: _sleep_tick (NREM SHY + REM replay)
  |   |-- explore: try_forage + try_write_knowledge
  |   |-- idle:  try_read_knowledge
  |-- 감정/tone 갱신: update_emotion + update_tone_from_emotion
  |-- 만성 상태 갱신: update_chronic
  |-- reward 계산 + brain.apply_reward (3-factor STDP)

Stage 0.5: Nomos 자연법 탐지 + 응징
Stage 1.5a: 사망 판정 + 환생
Stage 1.5b: 재난 판정
Stage 2:   사회 상호작용 (socialize 페르소나 쌍 매칭)
  |-- 친밀도/신뢰 변화
  |-- 감정 전이 (공감)
  |-- 비밀 공유 + 소문 전파
  |-- 지식 전수 (숙련자 -> 미숙련자)
Stage 2.5: 승급/강등 (24틱마다)
  |-- promotion_stable_ticks >= required -> gate 검증 -> 승급
  |-- flow_ratio < threshold * 0.7 -> 경고 축적 -> 강등
Stage 3:   관계 요약
Stage 4:   자동 경제 (24틱마다)
  |-- 영주 deliberation -> Job 생성
  |-- 무직자 구직
  |-- _process_market() P2P 시장
  |-- _process_npc_shop() NPC 상점
  |-- _auto_tool_management() 도구 관리
```

### 5.3 10명 페르소나

```
Seorim (Claude 권역)
  persona_001  Seo Harin   영주  외향0.7 신중0.3 감성0.8 협조0.8 관대0.4
  persona_002  Yun Daeho         내향0.2 신중0.3 이성0.2 엄격0.8 엄격0.9
  persona_003  Chae Rina         외향0.8 신중0.4 감성0.9 협조0.9 관대0.3

Ironridge (Codex 권역)
  persona_020  Rex Valen   영주  내향0.3 신중0.4 이성0.2 독립0.3 엄격0.8
  persona_022  Kael Storn        외향0.8 대담0.8 감성0.6 협조0.7 관대0.4
  persona_023  Mira Dusk         내향0.4 신중0.3 감성0.8 독립0.3 관대0.3
  persona_024  Orin Flint        내향0.2 신중0.4 이성0.3 독립0.2 엄격0.8

Mirrordale (Gemini 권역)
  persona_021  Baek Sujin  영주  외향0.7 대담0.7 감성0.6 협조0.6 관대0.5
  persona_025  Lian Moss         외향0.6 신중0.3 이성0.4 협조0.6 관대0.5
  persona_026  Fen Grave         내향0.3 대담0.7 감성0.7 독립0.4 관대0.4
```

### 5.4 주요 메서드 요약 (37개)

| 메서드 | 역할 |
|--------|------|
| `tick()` | 1틱 전체 시뮬 |
| `_process_survival_consume(pid)` | 매 틱 food 1 소비, 미충족 시 stress 에스컬레이션 |
| `_process_economy(pid, action)` | work -> goods 산출 + gold/tax |
| `_process_eat(pid)` | 4경로: 인벤토리/시설/자연/굶음 |
| `_process_market()` | P2P 주문 매칭 |
| `_process_npc_shop()` | NPC 긴급 매수 + 잉여 매도 |
| `_process_interaction(pid_a, pid_b)` | 친밀도/신뢰/감정전이/비밀/소문/지식전수 |
| `_update_mastery_tick(pid, job_title)` | 숙달 성장 + 몰입(flow) 판정 |
| `_compute_neural_drive(pid)` | SNN 기반 drive (mastery x aptitude x flow x DA) |
| `_compute_reward(pid, action)` | 행동 후 보상 계산 |
| `_update_promotion_trigger(pid)` | work 시 STDP 안정화 축적 |
| `_evaluate_promotion_gate(pid)` | 4중 gate (mastery/contrib/peer/stability) |
| `_execute_promotion(event)` | class 변경 + 감정/기억/소문 |
| `_check_demotion(pid)` | effective_demotion + actual_demotion |
| `_nomos_check(actions, tick_result)` | 자연법 3조 위반 탐지 + 3단계 응징 |
| `_check_deaths()` | vitality <= 0 시 사망 + 윤회 |
| `_auto_economy_tick()` | 24틱: 영주 Job 생성 + 무직자 구직 |
| `_get_tool_multiplier(pid)` | 도구 배율 (0.7x~1.5x) |
| `_wear_tool(pid)` | 도구 마모 |
| `_auto_tool_management(pid)` | 장착/수리 |
| `_get_persona_job_title(pid)` | 현재 직업 |
| `_sleep_tick(pid)` | 수면 처리 (NREM SHY + REM replay) |
| `create_job(employer_id, title, wage)` | 일자리 생성 |
| `hire(job_id, employee_id)` | 고용 |
| `quit_job(employment_id)` | 퇴직 |
| `try_forage(pid)` | 자연 채집 |
| `try_write_knowledge(pid)` | 서적 저술 |
| `try_read_knowledge(pid)` | 서적 열람 |

---

## 6. 구현 이력 (Phase 0~11)

| Phase | 이름 | 핵심 | 방식 |
|-------|------|------|------|
| 0 | 뉴런이 깨어난다 | LIF 뉴런 1000개, E/I 균형, 발화율 4% | SNN |
| 1 | 서하린이 느낀다 | 칠정7 감정, EpisodeTrace 기억, tone 7종 | SNN |
| 2 | 서하린이 배운다 | 3-factor STDP, 도파민 RL, 보상 v2 | SNN |
| 3 | 서하린이 꿈꾼다 | NREM SHY + REM replay, 항상성 가소성 | SNN |
| 4 | 관계의 시작 | 멀티 페르소나 3명, Relationship, Secret/Rumor | 하이브리드 |
| 5 | 기억의 변질 | 기억 상태기계 6상태, 재통합, 억압/재출현 | SNN |
| 6 | 숙달과 집중 | SkillProfile, concentration(기하평균), 적성맵 | 하이브리드 |
| 7 | 창발적 교육 | socialize 지식전수, 적성 발견, 직업 다양화 | 하이브리드 |
| 8 | Neural Drive | STDP 안정화 -> 승급 트리거 + 사회적 검증 | SNN 기반 |
| 9 | 클래스 승급 | 4중 gate, 단계적 강등, effective_class | 하이브리드 |
| 10 | 자연법 Nomos | 3조 3단계 에스컬레이션, Physis 연동 | 규칙(가이드) |
| 11 | 경제 골격 | goods 생산, 생존소비, 도구, P2P 시장, NPC | **규칙** |

### Phase 11 현황 (최신)

**완료**: goods 5종, 도구 시스템, P2P 시장, NPC 상점, 생존 소비
**테스트**: test_economy 6/6, test_nomos 5/5, test_class_promotion 6/6 ALL PASS
**문제**: 경제 행동이 전부 규칙. SNN과 연결되지 않음.

---

## 7. 현재 SNN vs 규칙 분류

### SNN 창발 (동작 중)

| 컴포넌트 | 설명 |
|---------|------|
| 행동 선택 | LIF 발화 -> readout -> logit (brain.tick()) |
| 도파민 학습 | 3-factor STDP, reward_history |
| 감정 반응 | 칠정 -> tone -> 뉴런 게인/노이즈 |
| 기억 통합 | NREM SHY + REM replay |
| 숙달 동기 | neural_drive = mastery x aptitude x flow x DA |
| 수면 욕구 | 에너지 -> SNN input -> sleep logit |
| 식욕 | oyok[0] -> SNN input -> eat logit |

### 규칙 기반 (SNN 연결 필요)

| 컴포넌트 | 현재 | 필요한 SNN 연결 |
|---------|------|----------------|
| goods 산출량 | 고정 상수 (JOB_BASE_OUTPUT) | 숙달 + 집중 + 동기에 의한 변동 |
| 가격 결정 | `rng.uniform(0.4, 0.7) * npc_buy` | 페르소나 욕구 강도 -> 가격 |
| 직업 선택 | aptitude_map 규칙 | SNN이 직업 만족도 학습 |
| NPC 매수 판단 | `hunger_ticks > 6 and food < 5` | SNN 절박함 신호 |
| 세금 징수 | `tax_rate * gold` 자동 | 영주 SNN 의사결정 |
| 임금 설정 | 고용주 수동 | 수급 + SNN 협상 |

---

## 8. 파일 구조

```
Projects/personas/loom/
  brain/
    __init__.py
    lif_network.py          # LIF 뉴런, STDP, 항상성 (189줄)
    persona_brain.py        # PersonaBrain: 입력->SNN->행동 (268줄)
    teacher_scenarios.py    # 800개 학습 시나리오
    teacher_train.py        # Teacher Net 학습
    teacher_collect.py      # LLM Teacher 데이터 수집
  
  ontology/
    __init__.py             # 전체 export
    layers.py               # 모든 데이터 모델 + 상수 (1,301줄)
  
  core/
    multi_tick_engine.py    # 시뮬레이션 엔진 (3,010줄)
    tick_engine.py          # 단일 페르소나 엔진 (구형)
  
  physis/                   # 기후 물리 엔진
  dashboard/                # 웹 대시보드 (실시간 모니터링)
  data/                     # 학습 데이터 + 모델 가중치
  tests/                    # 단위 테스트
  
  test_economy.py           # Phase 11 경제 검증 (500틱, 6항목)
  test_class_promotion.py   # Phase 9 승급 검증 (3000틱, 6항목)
  test_nomos.py             # Phase 10 Nomos 검증 (3000틱, 5항목)
  test_neural_drive.py      # Phase 8 drive 검증
  verify_all.py             # 전체 검증 스크립트
  RESEARCH-LOG.md           # 연구 일지 (발상~현재)
```

---

## 9. 협업 규칙

### Claude의 역할
1. **설계서 작성**: 아키텍처, 창발 경계, 수정 대상 코드, 검증 기준
2. **리뷰**: SNN 연결 여부, 규칙 침범 여부, 테스트 통과, 기존 호환

### Codex의 역할
1. **플랜 수립**: 설계서 기반 구현 계획 (md 출력)
2. **코딩**: Step별 구현 + 중간 검증
3. **리뷰 요청서**: 변경 요약 + 테스트 결과 + 창발 경계 준수 여부

### 리뷰 체크리스트

| # | 항목 | 기준 |
|---|------|------|
| 1 | SNN 연결 | "SNN"으로 표시된 부분이 실제로 뉴런 신호를 읽는가? |
| 2 | 규칙 침범 | "SNN"으로 표시된 부분을 if-else로 구현하지 않았는가? |
| 3 | 테스트 통과 | 설계서 검증 기준 전항 PASS? |
| 4 | 기존 호환 | test_economy + test_nomos + test_class_promotion ALL PASS? |

### 테스트 실행 방법

```bash
cd Projects/personas/loom
py test_economy.py           # 500틱, ~2분
py test_class_promotion.py   # 3000틱, ~12분
py test_nomos.py             # 3000틱, ~12분
```

---

## 10. 다음 과제 (Phase 12 예정)

**목표**: Phase 11의 규칙 경제에 SNN 연결을 만든다.

| 순서 | 과제 | SNN/가이드 |
|:----:|------|:----------:|
| 1 | 경제 욕구의 SNN화 (물자 욕구를 뉴런 신호로) | SNN |
| 2 | 가격 협상의 창발 (절박 -> 싸게, 여유 -> 비싸게) | SNN |
| 3 | 직업 선택의 창발 (만족도 학습 -> 이직) | SNN |
| 4 | 통치 욕구의 창발 (세금 불만 -> 저항 신호) | SNN |
| 5 | 통치 체계 (제도적 해소 통로) | 가이드 |

> 상세 설계서는 Claude가 별도 md 파일로 작성합니다.
