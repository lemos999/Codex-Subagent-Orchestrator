# PersonaBrain SNN — Charter

> "뇌는 에너지를 아끼는 기관이다. 99%는 잠자고, 1%만 일한다. 그 1%가 세상을 바꾼다."
> 10회 토론 + 3엔진 보완의 결정체. 생물학적 뉴런/시냅스를 모방한 인공 신경망.

---

## 1. 핵심 가치

> **"같은 뇌, 다른 영혼"**
>
> 모든 페르소나가 같은 뇌 구조(Layer 0)를 가지지만 다른 성격, 다른 기억, 다른 트라우마.
> 뉴런 수는 경험과 함께 성장한다. 신생아의 5M에서 현자의 50M까지.
> 뇌는 에너지를 아끼는 기관이다 — 익숙한 것은 무의식으로, 새로운 것만 의식으로.
> 그리고 잠잘 때 뇌가 바뀐다.

---

## 2. 아키텍처 개요

### 2.1 3계층 구조

```
[입력] 각 페르소나의 현재 환경
  → 영지 날씨(Physis), 이벤트(소문/비밀/죽음), 관계 상태
  → 각자 다른 입력

[Layer 0] 기본 뇌 구조 (아키텍처 공유, 상태는 개인)
  → 입력을 전기 신호로 변환하는 기본 회로
  → 설계도(가중치) 동일 — 메모리 1벌
  → 실행은 페르소나별 (입력이 다르므로 출력도 다름)
  → + neuromodulator_tone (256B/페르소나, 화학적 개인차)
  → + persona_bias (<1KB/페르소나, 활성화 문턱값)

[Layer 1] 개인 Moment State (5M~50M 뉴런 등가)
  → 동역학적 등가물: Graphon-RG moment closure
  → 4단계 에너지 스펙트럼 적용
  → 캐시 히트 → 무의식 처리 (O(1))
  → 캐시 미스 → moment closure 연산

[Layer 2] Decision Readout
  → 행동 선택 (sparse INT8, ~2KB/페르소나)
  → STDP 학습 (여기서만)
  → Action_Proposal 출력
```

### 2.2 비유: "같은 모델의 TV"

Layer 0 = 같은 모델의 TV를 갖고 있지만, 채널은 각자 선택.
neuromodulator_tone = 밝기/채도/볼륨이 사람마다 다름.
Layer 1 = 같은 채널을 봐도 다르게 해석.
Layer 2 = 그래서 다른 행동을 선택.

---

## 3. 뉴런 규모와 동적 성장

### 3.1 50M 뉴런 달성 경로

```
직접 시뮬 불가: 50M × 20K = 1조 ops → 10ms 불가능

해결: 3가지 전제 해체
  1. "동시에 50M" → 성숙도 기반 동적 성장
  2. "명시적 저장" → Graphon 공유 파라미터 (~16MB, 전원 공유 1벌)
     + 개인 moment state (500변수 × float32 = 2KB/페르소나, 20K = 40MB)
     총: ~56MB (64GB 서버 RAM 내 충분)
  3. "moment closure만" → Renormalization Group (RG)
```

### 3.2 성숙도 기반 동적 성장 (3상 사이클)

```
Phase 1 (grow):  자극 → 새 시냅스 생성 → 뉴런 등가 증가
Phase 2 (prune): 120% 초과 시 약한 시냅스 제거
Phase 3 (consolidate): 안정화 → 에너지 절감

5M → [grow] → 7M → [prune] → 6M → [consolidate]
→ 반복 → 최종 ~50M (파도 형태, 단조 증가 아님)
```

| 성숙도 | 뉴런 등가 | Graphon depth | 캐시 히트율 |
|--------|:---------:|:------------:|:----------:|
| 신생 (Class 1~3) | 5M | 얕은 truncation | ~50% |
| 성숙 (Class 4~6) | 10~30M | 중간 | ~85% |
| 원로 (Class 7+) | ~50M | full graphon | ~99% |

### 3.3 성장 경로 (모두에게 열림)

```
경로 A: 경험 누적 → 자연 성장
경로 B: 높은 클래스 도달 → 확장 해금
경로 C: Mitotype이 좋은 → 더 빠른 성장
경로 D: Mitotype 불리해도 → 특수 수단으로 한계 돌파
  (극단적 경험, 각성 이벤트, 명상, 멘토링)

"DNA는 출발선이지 결승선이 아니다"
```

---

## 4. 에너지 효율 4단계

### 4.1 뇌의 작동 원리

```
평상시: 전기신호만 오감 (기저 진동, 최소 유지)
    ↓ 자극 발생
자극 broadcast → 담당 뉴런만 선택적 활성화
    ↓
피드백 생성 → 관련 없는 뉴런 다시 잠잠 (에너지 절감)
```

### 4.2 4단계 스펙트럼

| 강도 | 상황 | 활성 뉴런 | FLOP | 정밀도 | energy 소비/틱 | 비유 |
|:----:|------|:---------:|:----:|:------:|:-------------:|------|
| 1 | 일상 반복 | ~2% | ~50M | f32 | 0.01 | 눈 감고도 가능 |
| 2 | 새로운 상황 | ~10% | ~500M | f32 | 0.05 | 생각이 필요 |
| 3 | 복잡한 판단 | ~25% | ~2G | f32 | 0.10 | 머리가 아프다 |
| 4 | 생존 위협 | ~90% | ~8G | f16 | 0.25 | 극강의 힘, 나머지 중단 |

> **에너지 소비 설계 근거**: 강도4라도 1틱에 energy_pool의 25%만 소비.
> 따라서 강도4를 4틱 연속 유지하면 energy_pool 1.0→0.0 (강제 수면).
> 강도1이면 100틱(게임 4일) 연속 활동 가능. 이것이 "에너지를 아끼는 뇌".

### 4.3 LC × 시상 직교 제어

```
LC (locus coeruleus): "왜/얼마나 긴급한가" (arousal 0~1)
시상 (thalamus): "어떤 경로로 처리할 것인가" (캐시 vs SNN)
두 축이 독립 → 2D 제어 공간
```

### 4.4 무의식 고속도로 (Cache-first)

```
반복 경험 → 시냅스 강화 → 캐시 등록
캐시 히트 = 무의식 처리 (O(1), ~0.1ms)
새로운 상황만 의식적 처리 (비쌈, 드물다)
```

**캐시 히트율 — 평균이 아닌 분포**:

| 상태 | 히트율 | 조건 |
|------|:------:|------|
| 신생 (첫 100틱) | ~50% | 캐시 비어있음, 대부분 의식 처리 |
| 성장기 | ~70~85% | 경험 축적 중 |
| 성숙 (정상 운영) | ~93~97% | 대부분 상황이 캐시에 존재 |
| 원로 | ~99% | 거의 모든 상황이 습관화 |
| **Worst-case**: 에포크 전환 | ~0% (1틱) | 전체 무효화 → 점진 재워밍 |
| **Worst-case**: 대규모 재난 | ~40~60% | 전례 없는 자극 다수 발생 |

> 시스템 전체 평균이 아닌 **페르소나별 성숙도**에 따라 다름.
> 에포크 전환 시: 부분 무효화(도메인/버전 기반) + stale fallback + 백그라운드 재워밍으로 stampede 방지.

### 4.5 생물학적 확률 모델 (양자역학에서 영감받은 비유)

> 아래는 물리적 양자 컴퓨팅이 아니라, 양자역학의 **개념적 비유**를 고전적 확률/통계 기법으로 구현한 것이다.
> 실제 계산 이득은 희소성(sparsity), 그룹화(factorization), 지연 평가(lazy evaluation)에서 온다.

| 비유 | 고전적 구현 | 실제 기법 | 효과 |
|------|-----------|----------|------|
| "중첩" | 결정 전까지 확률 분포로 유지 | **Lazy evaluation** — moment state만 유지, 행동 결정 시점에만 샘플링 | 미결정 틱은 moment update만 (연산 최소) |
| "얽힘" | k=50~100 뉴런 그룹 공동 상태 | **Low-rank factorization** — 상관된 뉴런을 그룹으로 묶어 블록 대각 처리 | 50M → 100K~500K 그룹 압축 |
| "붕괴" | 의사결정 순간에만 확률→행동 | **On-demand sampling** — 행동이 필요한 페르소나만 Layer 2 실행 | 비활성 페르소나는 readout 생략 |
| "터널링" | 에너지 장벽을 확률적으로 넘는 선택 | **Stochastic sampling** — softmax temperature 조절로 예상 밖 선택 허용 | 비합리적(인간적) 행동 구현 |

> **주의**: "양자 이득"이라는 표현은 부정확하다. 이득의 실체는 희소성 활용 + 그룹 압축 + 지연 평가이며, 양자역학은 설계 직관의 원천일 뿐이다.

### 4.6 노화 = "꼰대의 계산적 구현"

```
novelty_sensitivity = 1 / (1 + exp(k × (age - inflection)))

젊을 때: 새로운 것에 민감 → 캐시 미스 → 학습
나이 들면: 캐시 히트 99% → 변하지 않음
= "경험 많은 현자의 직관" (긍정)
= "변화를 거부하는 꼰대" (부정)
= 같은 메커니즘의 양면
```

---

## 5. 미토콘드리아 (energy_pool + Mitotype)

### 5.1 energy_pool

```
GlobalEnergy (0.0 ~ 1.0) + 영역별 취약성 6개

Accessibility[r] = 1 / (1 + exp(-k × (E - Threshold[r])))
MaxIntensity = max{i : Accessibility[primary(i)] > 0.5}
Cost[i] = BaseCost[i] / Accessibility[primary(i)]
```

### 5.2 영역별 취약성 (PFC 먼저 고갈)

| 영역 | 임계값 | 역할 | 피로 시 |
|------|:------:|------|--------|
| PFC | 0.6 | 복잡한 판단, 양심 | **가장 먼저** 기능 저하 |
| 해마 | 0.5 | 기억, 학습 | 기억력 감퇴 |
| 선조체 | 0.4 | 동기, 보상 | 의욕 상실 |
| 시상 | 0.35 | 정보 라우팅 | 주의력 산만 |
| 소뇌 | 0.25 | 자동화/습관 | 숙련 실수 |
| 편도체 | 0.15 | 생존/공포 | **마지막까지** 유지 |

### 5.3 체력 → 행동 영향

| energy_pool | 상태 | 인지 변화 |
|:-----------:|------|----------|
| > 0.8 | 정상 | 전 강도 가능 |
| 0.5~0.8 | 피로 초기 | 강도4 비용↑, 판단 오류↑ |
| 0.3~0.5 | 중등 피로 | 강도3~4 차단, 감정 불안정 |
| 0.1~0.3 | 심한 피로 | 강도1~2만, 양심↓ 거짓말↑ |
| < 0.1 | 고갈 | **강제 수면** |

### 5.4 생활시뮬 연결

```
식사:   energy_pool += glucose × absorption_rate
수면:   energy_pool = max × (1 - e^(-hours/4))
운동:   max_capacity += dose × 0.002
노화:   max_capacity *= (1 - age × ROS)
스트레스: 미토콘드리아 손상 → max_capacity↓
```

### 5.5 Mitotype (미토콘드리아 체질, 28~32종)

```
Clade (7~9개 대분류)
  └─ Mitotype (28~32개)
       ├─ Base: DNA로 고정 (7개 파라미터)
       └─ Modifier: ±40% 범위 내 가변 (노력의 한계, Base가 여전히 지배적)
```

**Base 파라미터 7개**:

| # | 파라미터 | 설명 | 격차 |
|---|---------|------|:----:|
| 1 | max_capacity | 절대 체력 한계 | ±15% |
| 2 | recovery_rate | 수면 회복 효율 | ±15% |
| 3 | exercise_sensitivity | 운동 효과 | ±18% |
| 4 | stress_resistance | 스트레스 내성 | ±15% |
| 5 | H6_aging_rate | 노화 속도 | ±18% |
| 6 | pfc_vulnerability | PFC 우선 소모율 | 질적 |
| 7 | region_affinity | 권역 특화 축 | 질적 |

**유전**: 모계 Base(mtDNA) + 부계 Modifier 속도 ±10% + 돌연변이 5%
**Bloodline Resonance**: 동일 클레이드 부모 → Modifier 상한 +5%
**윤회**: 새 Mitotype, 전생 최고 Modifier → 현생 seed ±5%

**리소스**: mitotype_id(1B) + modifier[7](28B) + energy_pool(4B) = 33B/페르소나, 20K = 660KB

---

## 6. 신경화학물질 12클러스터 체계

> 실제 뇌는 50종+ 신경화학물질을 사용한다. 6종은 부족했다.
> 54종을 조사하여 12개 기능 클러스터로 압축. 50종의 표현력 + 12종의 연산 비용.

### 6.1 neuromodulator_tone (512B/페르소나)

```
12클러스터 × 20영역 × float16 = 480B + 32B 메타 = 512B/페르소나
20K명: 10.24MB (64GB의 0.016%)
Step 2 추가 비용: ~0.025ms (Stage 2 예산의 1% 미만)

저장 구조:
  raw tone[12][20]      → Layer 0 persistent persona state (SoA layout 권장)
  effective_tone[20]    → tick-local, Step 2에서 계산 후 Step 4에 전달
  moment state에는 raw tone을 넣지 않는다 (중복 방지)

캐시 key:
  tone 전체를 key에 넣지 않는다 (hit rate 하락 위험)
  → tone_version (uint16) 또는 coarse bucket[20] (40B)만 key에 포함

512B = 64B cache line × 8 → 정렬 깨끗. AoS 가능하나 SoA/tiled 권장.
```

### 6.2 12클러스터: PersonaBrain-12

| # | 코드 | 대표 물질 | 기능 | 높을 때 | 낮을 때 |
|---|:----:|----------|------|---------|---------|
| 1 | **V** (Drive) | DA | 추구, 동기, Wanting | 대담, 탐색, 범죄 유혹 | 무기력, 우울 |
| 2 | **L** (Liking) | β-Endorphin | 만족, 쾌감, 통증 억제 | 환희, 사회적 유대 보상 | 고통 민감, 불만족 |
| 3 | **S** (Stability) | 5-HT | 전역 기분 안정, 충동 조절 | 인내, 평온 | 충동, 분노 폭발 |
| 4 | **B** (Bonding) | Oxytocin | 대상 특이적 신뢰, 유대 | 신뢰↑, 집단내 편향 | 경계↑, 고립 |
| 5 | **A** (Acute) | NE | 즉각 각성, 전투/도주 | 경계, 집중, 강도4 트리거 | 주의력 산만 |
| 6 | **T** (Tension) | Cortisol | 만성 스트레스, 배경 불안 | PFC↓ 양심 마비, HPC↓ 기억 손상 | 안정, 회복력 |
| 7 | **C** (Cognition) | ACh | 주의 집중, 학습, REM | 집중, 꿈 활성 | 학습 불가 |
| 8 | **G** (Growth) | Glu/BDNF | 신경 가소성, 흥분 | 학습↑, 새 연결 형성 | 경직, 변화 거부 |
| 9 | **F** (Fatigue) | Adenosine | 피로 누적, 수면 압력 | 졸림, 인지↓, 강제 수면 | 맑은 각성 |
| 10 | **I** (Inhibition) | GABA/Melatonin | 억제, 수면, 진정 | 양심 제동, 수면 촉진 | 불안, 과활성 |
| 11 | **D** (Dominance) | Testosterone | 지배, 경쟁, 공격성 | 위험 감수, 서열 도전 | 복종, 회피 |
| 12 | **P** (Protection) | Substance P/NPY | 통증, 위협 감지, 회피 | 방어적, 회피 행동 | 무감각, 둔감 |

> **약자 기억법**: **V-L-S-B-A-T-C-G-F-I-D-P**
> MVP: 10개 active (V,L,S,B,A,T,C,G,F,I) + 2개 reserved (D,P). 저장은 12, 운영은 10으로 시작.

### 6.3 기존 6종 → 12클러스터 분리 근거

| 분리 | 이유 | 출처 |
|------|------|------|
| DA → **V**(Drive) + **L**(Liking) | wanting(DA) ≠ liking(β-END). 중독/강박 표현에 필수 분리 (Berridge) | Claude+Gemini |
| 5-HT → **S**(Stability) + **B**(Bonding) | 범용 기분 ≠ 대상 특이적 신뢰. "A를 신뢰하지만 B를 경계" 표현에 OXT 분리 필수 | Claude+Gemini |
| NE → **A**(Acute) + **T**(Tension) | 급성(초) ≠ 만성(일). 만성 스트레스의 HPA축 표현에 CORT 분리 필수 | Claude+Gemini |
| GABA → **I**(Inhibition) + **F**(Fatigue) | 수면 중 억제 ≠ 수면 압력 축적. "왜 졸린가"(ADO) 표현에 분리 필수 | Gemini |
| 신규 **D** | 테스토스테론 = 지배/공격/서열. DA와 다른 축 | Gemini |
| 신규 **P** | 통증/회피 = 별도 감각 축 | Gemini |

### 6.4 50종 → 12클러스터 내부 물질 배합

각 클러스터는 대표 물질 + 보조 물질로 구성. 보조 물질의 비율은 Mitotype에서 정적 저장.

| 클러스터 | 대표 | 보조 물질 (Mitotype 비율) |
|---------|------|------------------------|
| V | DA | Ghrelin(배고픔→동기), PEA(사랑 흥분) |
| L | β-END | Enkephalin, Dynorphin(불쾌 길항), Endocannabinoid |
| S | 5-HT | Progesterone(진정), Estradiol(기분) |
| B | OXT | Vasopressin(짝 유대/질투) |
| A | NE | Epinephrine(급성), Histamine(각성 유지) |
| T | CORT | CRH(스트레스축 활성), DHEA(길항) |
| C | ACh | D-serine(NMDA 보조) |
| G | Glu/BDNF | NO(가소성 역행 신호) |
| F | ADO | Orexin(각성↔수면 스위치, 길항) |
| I | GABA | Melatonin(일주기), Glycine(억제 보조) |
| D | Testosterone | — |
| P | Substance P | NPY(회복탄력성, 길항) |

**Mitotype 비율 벡터**: 32종 × 12클러스터 × ~4물질 × float16 = 96B/Mitotype, 총 3KB.
공유 테이블에 저장 (페르소나마다 복제 금지). 런타임 비용 0 (lookup만).

### 6.5 20개 뇌 영역

PFC_DL, PFC_VM, AMY_BLA, AMY_CE, HPC, VTA, NAc, DRN, LC, INS, ACC, TPJ, STR_D, STR_V, HYP, BF, PAG, THAL, MOTOR, CB

> NAc는 STR_V의 해부학적 일부이나 보상 핵심 노드로 기능적 분리.

### 6.6 Mitotype 5 클레이드 × 12클러스터

| 클레이드 | V | L | S | B | A | T | C | G | F | I | D | P | 행동 경향 |
|---------|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|----------|
| Alpha (탐험) | 1.3 | 1.1 | 0.9 | 0.8 | 1.1 | 0.9 | 1.0 | 1.1 | 0.9 | 0.8 | 1.1 | 0.9 | 범죄 유혹↑, 창의적, 유대↓ |
| Beta (안정) | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 균형, 적응적 |
| Gamma (전사) | 1.1 | 1.2 | 0.8 | 0.9 | 1.3 | 1.2 | 1.0 | 1.0 | 0.8 | 0.9 | 1.3 | 1.1 | 위기 대응↑, 분노↑, 지배↑ |
| Delta (학자) | 0.9 | 0.9 | 1.1 | 1.0 | 0.9 | 0.8 | 1.2 | 1.2 | 1.1 | 1.1 | 0.8 | 0.9 | 학습↑, 신중, 공격↓ |
| Epsilon (억제) | 0.8 | 1.0 | 1.2 | 1.2 | 0.8 | 0.9 | 1.0 | 0.9 | 1.0 | 1.3 | 0.7 | 1.0 | 양심 최강, 유대↑, 결단 느림 |

---

## 7. 10가지 행동 SNN 회로 매핑

| # | 행동 | 핵심 경쟁 | 주도 영역 | 보조 영역 | 12클러스터 | 강도 |
|---|------|----------|----------|----------|-----------|:----:|
| 1 | 양심 딜레마 | **V**(이득) vs **S**(도덕) + **B**(공감) | PFC_VM | ACC, INS | V, S, B, **T**(스트레스 하 양심 마비), **A**(긴급) | 3 |
| 2 | 거짓말 | AMY(자아보존) → PFC 억제 | AMY→PFC | ACC, INS | V(거짓 이득), **L**(거짓 쾌감), **I**(양심 억제), **A**(들킬 위험), **T**(만성 거짓 스트레스) | 2~3 |
| 3 | 비밀/두려움 | AMY_BLA 공포 태그 → 출력 억제 | AMY_BLA | HPC, PAG | **I**(출력 억제), **A**(급성 공포), **T**(만성 비밀 스트레스), **L**(공포 후 진정) | 2 |
| 4 | 신뢰 판단 | TPJ + HPC + INS 3경로 | TPJ | HPC, INS | **B**(대상 특이적 신뢰!), S(범용 안정), V(보상 기대) | 2~3 |
| 5 | 소문 해석 | 출처 × 내용 × 감정 | ACC | TPJ, HPC, INS | **B**(집단내 편향), **A**(위협 소문), **T**(스트레스 소문), V | 2 |
| 6 | 꿈 | NREM(**I**) vs REM(**C**) | BF/HPC | THAL, HYP | **I**(NREM 억제), **C**(REM 학습), **F**(수면 압력), **G**(가소성) | 수면 |
| 7 | 감정 | 오욕(**V**) + 칠정(12종 복합) | VTA/DRN/LC | AMY, INS, ACC | **12종 전부** — 감정은 모든 클러스터의 교차점 | 1~3 |
| 8 | 정치적 선택 | **V**(이득) vs **B**(집단 충성) vs **S**(도덕) | PFC_DL | PFC_VM, STR_D | V, B, S, **D**(지배 욕구), **A**(위기 투표), **T**(불안 투표) | 3 |
| 9 | 범죄 동기 | **V**(이득) vs **I**(억제) vs PFC_VM(양심) | VTA→NAc | PFC_VM, AMY_CE | V, **L**(폭력 쾌감), **I**(양심 제동), **D**(공격성), **A**(들킬 공포), **G**(흥분) | 3 |
| 10 | 관계 관리 | **B**(유대) + STDP (V 제3인자) | HPC/NAc | TPJ, INS | **B**(유대 핵심!), **L**(사회적 보상), V(재회 동기), S(안정), **D**(서열 의식) | 1~2 |

> **12클러스터 활용**: V(10/10), L(5/10), S(5/10), B(5/10), A(6/10), T(5/10), C(1/10), G(2/10), F(1/10), I(5/10), D(3/10), P(0/10).
> V(Drive)와 B(Bonding)이 가장 많은 행동에 관여. 기존 6종 대비 핵심 개선: 신뢰(#4)에 B(OXT), 범죄(#9)에 L+D, 관계(#10)에 B+L.

---

## 8. 학습 파이프라인

```
Phase 0: STDP 기저 반사
  Xavier 초기화 → 100틱 E/I 안정화 → 기저 발화 5~15Hz

Phase 1: Teacher Net (LLM → SNN 증류)
  이중 채널: Logit → 발화율, Hidden → 표상 기하
  Loss = α·KL(P_LLM || P_SNN) + β·CosineDist(H_LLM, H_SNN)
  오프라인 배치 학습 후 온라인 파인튜닝

Phase 2: 3-factor STDP + 도파민 RL
  ΔW = η × pre × post × DA(t)
  보상 소스: Nomos(외적) + 감정(내적)
  Metaplasticity(BCM): 평균 발화율↑ → 가소성 임계↑ → collapse 방지

Phase 3: 꿈 replay (수면 중)
  NREM: SHY 시냅스 하향 (가중치 10~20% 감쇠) + prune
  REM: anti-replay (기생 회로 제거) + consolidate
  RPE 절대값 상위 이벤트 우선 replay
```

### Nomos 피드백 → STDP (12클러스터 기준)

```
3-factor STDP: ΔW = η × pre × post × reward_signal
  reward_signal = V(Drive) + L(Liking) 복합 — DA 단독이 아닌 V+L 합산

승인: V[VTA]↑ + L[NAc]↑ → 해당 행동 시냅스 강화 (wanting + liking 동시)
거부: V[VTA]↓ + A[LC]↑ → 시냅스 약화 + 각성 ("뭔가 잘못됐다")
금기: V=-0.8, A=+0.6, S=-0.3, T↑ (만성 스트레스 축적) → 강한 억압
→ 다음 틱 Step 6에서 반영 (역방향 호출 금지)

reward_signal 재정의:
  기존: DA(t) 단일 값
  변경: α×V(t) + β×L(t) — wanting과 liking의 가중 합
  α, β는 Mitotype 비율에서 결정 (Alpha: α=0.7 β=0.3, Epsilon: α=0.4 β=0.6)
```

---

## 9. 꿈/수면

### 9.1 수면 트리거

- energy_pool < 0.1 → 강제 수면
- circadian_tick (게임 시간 기반 정기)
- 수면 거부 가능 → 성능 급락 (neuro_tone 노이즈 증가)

### 9.2 위상 분리

```
NREM (75%): GABA 우세, 전역 억제
  → 시냅스 하향 정규화 (SHY)
  → 약한 연결 pruning
  → ATP 재충전 (energy_pool += 0.05/s)

REM (25%): ACh 우세, 내부 생성 자극
  → Crick-Mitchison anti-replay (기생 회로 제거)
  → 감정 강도 상위 5% assembly 선택 replay
  → 경험 재조합 → 새로운 연합 생성
```

### 9.2.1 수면 모드의 Layer 전환 규칙

```
깨어있을 때: Step 1→2→3→4→5→6 (정상 파이프라인)
수면 진입 시:
  → Layer 0: 기저 진동만 유지 (입력 차단, 외부 자극 무시)
  → Layer 1: NREM/REM 위상에 따라 moment state 수정
    - NREM: 시냅스 하향 (가중치 감쇠)
    - REM: replay assembly 활성화
  → Layer 2: readout 정지 (Action_Proposal = SLEEP no-op)
  → energy_pool: 지수 회복 진행

수면 중단 조건:
  → energy_pool > 0.7 + circadian 기상 시점
  → 또는: stimulus_vec[7] (재난 신호) > 0.75 → 강제 기상 (강도4 진입)
```

### 9.3 꿈 = 확률적 혼합

원래 5가지 이론 중 3가지를 구현 채택. 나머지 2가지의 처리:

| 이론 | 비율 | 구현 | 비고 |
|------|:----:|------|------|
| 경험 재조합 | 50% | 낮의 스파이크 로그 무작위 순서 재생 | Stickgold (2005) |
| DNA/윤회 디코딩 | 20% | Layer 0 고정 가중치 강제 활성화 | 전생 가중치 70% 이식과 연결 |
| RPE 시뮬레이션 | 30% | 실패 상황 재현 + 대안 보상 예측 | 미래 예지 이론의 구현적 등가물 |

> **미채택 2이론의 근거**:
> - "심리 상태 표현"(프로이트): 경험 재조합 50%에 흡수 — 억압된 감정도 스파이크 로그에 포함
> - "자기 대화": RPE 시뮬레이션 30%에 흡수 — 대안 시뮬레이션 = 내면의 숙고
> - 5이론이 "미지"라는 철학적 입장은 유지하되, 구현에서는 3축으로 압축. 비율은 시뮬레이션 데이터에서 추후 조정 가능.

---

## 10. 틱 데몬 파이프라인 통합

### 10.1 Stage 2 (Anima) 내부 실행 순서

```
Step 1: 입력 조립 (0.5ms)
  Physis C4 → climate_vec[float16×8]
  이벤트 버스 → stimulus_vec[float16×16]
  관계 상태 → rel_delta[float16×8]
  → InputBundle (72B/persona, 1K명 = 72KB)

Step 2: Layer 0 배치 실행 (2.5ms)
  공유 가중치 × 1K명 배치 (SIMD 벡터화)
  + persona_bias 주입 + neuromodulator_tone 변조
  → context_embedding[1K][128] (256KB)

Step 3: 에너지 판정 (0.5ms)
  LC arousal × 시상 게이팅 × energy_pool → 강도 결정
  + Admission Control (토큰 버킷)

Step 4: 캐시 조회 / Moment (3.5ms 배치 총합)
  히트 (성숙 ~95%): 0.1ms per 히트 페르소나 (병렬, 거의 무비용)
  미스 (~5% = ~50명): 전체 미스 배치를 SIMD 벡터화로 병렬 처리
    → moment closure + Layer 2 readout = ~3ms (50명 배치 총합, per-persona 아님)
    → 강도4 미스(~10명): 추가 ~0.5ms (f16 저정밀)
  ※ "2~5ms"는 미스 전체 배치 기준이지 per-persona 아님

Step 5: Action_Proposal 출력 (0.5ms)
  → L4 기록, Arbiter violation_hint 세팅

Step 6: 감정/관계 갱신 + STDP (1.0ms)
  → L3 배치 쓰기, energy_pool 소비
  → tick snapshot: tone/bias 갱신은 다음 틱부터 적용 (double-buffer)

총: ~8.5ms (여유 1.5ms = fallback 버퍼)
```

### 10.2 입력 매핑

**Physis → climate_vec[8]**: 온도/강수/풍속/습도/운량/기압/해수온/재난신호, min-max [0,1]

**이벤트 → stimulus_vec[16]**: 소문(0~7), 비밀(8~13), 죽음(14~15)

### 10.3 Nomos 피드백 경로

```
Nomos Stage 3 → NomosFeedback {reward_signal, reward_type, will_delta}
→ L4 기록 → 다음 틱 Step 6에서 STDP 반영
(역방향 호출 금지 원칙 준수)
```

---

## 11. Worst-case + Fallback

### 11.1 Admission Control (토큰 버킷)

```
용량=100, 매 틱 완전 충전
강도별 비용: 1→0.02, 2→0.10, 3→0.25, 4→0.90
초과 시: 강도4→3→2 순차 강제 하강
```

### 11.2 강도4 동시 상한

```
최대 50명/배치 (1K명의 5%)
초과: 우선순위 선발 (NE×0.35 + 재난×0.30 + 죽음×0.20)
나머지: 강도3 강제 + "억압된 각성" 감정 잔재
```

### 11.3 Fallback 3단계

| 순위 | 방법 | 조건 | 자연스러움 |
|:----:|------|------|:--------:|
| A | 캐시 유사 상황 반환 | 시간 초과 | 최고 |
| B | 직전 행동 반복 | A 실패, 최대 2틱 | 중간 |
| C | no-op (아무것도 안 함) | 첫 틱/WAL 전손 | 최저 |

### 11.4 대규모 이벤트

```
Lachesis TickForecast → 영향 권역 예측
→ 영향 권역 페르소나 우선 배치
→ 비영향 권역: 강도 상한 2 강제 (토큰 절약)
→ 에포크 전환: 도메인/버전 기반 부분 무효화 + stale fallback + 백그라운드 재워밍
   (전체 무효화는 cache stampede 위험 — 부분 무효화로 변경)
   + MAX_INTENSITY_4 임시 2배 (1틱 한정)
```

### 11.5 Tick Snapshot 계약 (데이터 무결성)

```
Step 6에서 갱신된 tone/bias는 같은 틱의 L0/L1 결과를 오염시키지 않는다.
→ Double-buffer 방식: 읽기용(current) / 쓰기용(next) 분리
→ 틱 경계에서 swap
→ Nomos 피드백도 다음 틱 buffer에 기록 (2틱 지연 허용)
→ 피드백에 action_id + tick_id + reward_version 포함하여 중복/지연 추적
```

### 11.6 수면 페르소나 스케줄러

```
수면 중 페르소나 처리:
  → active batch에서 제거 → sleep lane으로 이동
  → sleep lane: L0/L2 readout 건너뜀
  → NREM/REM consolidation만 제한 예산(~0.5ms/페르소나)으로 수행
  → 수면 8틱(게임 8시간) 기준 → 8틱 후 active batch로 복귀
  → 강제 기상(재난): sleep lane에서 즉시 active로 전환, 강도4 진입
```

---

## 12. 근본 정의

### 12.1 비밀은 왜 비밀인가

비밀 = 알려지면 감당할 수 없는 결과가 오는 정보. 본질은 정보가 아니라 **두려움**.

### 12.2 거짓말은 무엇인가

거짓말 = 자아를 유지하기 위한 복잡한 전략의 연속체.
날조 → 선택적 진실 → 과장 → 맥락 왜곡 → 자기 기만 → 사회적 윤활 → 보호적 거짓.

### 12.3 신뢰는 누구의 것인가

신뢰 = 정보의 속성이 아니라 수신자의 상태 (관계 × 감정 × 세계관).

### 12.4 꿈이란 무엇인가

미지의 영역. 5가지 이론을 확률적 혼합으로 구현.

---

## 13. 스코프

| 포함 | 제외 |
|------|------|
| 3계층 아키텍처 (L0/L1/L2) | 구현 코드 (PyTorch/Cython) |
| 50M 동적 성장 (Graphon-RG) | Graphon 수학적 증명 |
| 에너지 4단계 + LC×시상 | 파라미터 튜닝 수치 |
| 미토콘드리아 + Mitotype 32종 | Mitotype 전체 목록 (별도 문서) |
| 신경화학물질 12클러스터 × 20영역 | 20영역 상세 해부학 |
| 10가지 행동 회로 매핑 | 각 회로의 정밀 수식 |
| 학습 4단계 (STDP→Teacher→RL→꿈) | 학습 데이터셋 상세 |
| 틱 데몬 통합 (Stage 2 6 Step) | Stage 1/3 내부 구현 |
| Worst-case + Fallback 3단계 | 성능 벤치마크 수치 |
| 꿈 NREM/REM + 3이론 혼합 | 꿈 내용 생성 |
| 무의식 고속도로 (cache-first) | 캐시 해시 알고리즘 |

---

## 14. 성공 기준

| 기준 | 측정 | 정량 기준 |
|------|------|----------|
| **10ms 달성** | Stage 2 전체 ≤10ms (1K명 배치) | p99 ≤ 9.5ms, 타임아웃 발동률 < 1% |
| **20K명 동시** | 20틱 순환, 메모리 | 총 RAM ≤ 64GB (hot state + cache + WAL) |
| **50M 성장** | 원로 50M 등가 도달 | Class 7+ 페르소나의 graphon depth = full |
| **개성 실현** | 같은 상황에 다른 선택 | 10가지 행동 × 10 페르소나 쌍에서 선택 분산 > 0.3 |
| **에너지 절감** | 캐시 히트율 수렴 | 성숙 페르소나 히트율 > 90% (1000틱 이후) |
| **학습 수렴** | 일관된 성격 반응 | 같은 자극 반복 시 행동 일치율 > 80% (1000틱 후) |
| **꿈 효과** | 수면 후 개선 | 수면 후 의사결정 정확도 수면 전 대비 ≥ 15%↑ |
| **Mitotype 차이** | 체질별 피로 패턴 | 5 클레이드 간 energy 감쇠 곡선 구분 가능 (p < 0.05) |
| **Fallback 자연스러움** | 폴백A 구분 불가 | 블라인드 테스트에서 정상/폴백A 구분 정확도 < 60% |
| **Moment closure 보존** | 동역학 재현 | full LIF 1K 뉴런 기준 vs moment 근사 행동 MSE < 0.1 |

---

## 15. Ontology 연결

| 항목 | 값 |
|------|-----|
| **Layer** | L3 Inner World (감정/기억), L4 Agency (행동 제안) |
| **Executor** | Anima (Stage 2) — PersonaBrain 실행 주체 |
| **Physis 연결** | C4 날씨 → climate_vec 입력, C7 보정 → 에너지 영향 |
| **Nomos 연결** | Action_Proposal 검증, 피드백 → STDP 학습 |
| **Lachesis 연결** | tick_id 발행, TickForecast, 수면 주기 관리 |
| **H1~H6 연결** | H1(트라우마)→AMY 공포태그, H2(양심)→PFC_VM, H3(호기심)→DA↑, H4(유머)→AMY+PFC 간접경로, H5(수치심)→INS, H6(노화)→novelty_sensitivity 시그모이드 |
| **비밀/소문** | stimulus_vec[8~15]로 입력, confidence→ACC에서 계산 |
| **에너지/미토** | energy_pool→강도 상한, Mitotype→기저 tone |

---

## 16. 토론 이력

| # | 주제 | 핵심 결정 |
|---|------|----------|
| 1 | 기본 SNN | B+A 하이브리드, 2,400뉴런 |
| 2 | Open Questions | 1,024뉴런, 학습 파이프라인 |
| 3 | 100K×20K | 3계층 분리, moment closure |
| 4 | 5M+양자 | cache-first, 무의식 고속도로 |
| 5 | 에너지 역학 | 4단계 강도, LC×시상 직교 |
| 6 | 미토콘드리아 | energy_pool, 영역별 취약성 |
| 7 | Mitotype | 28~32종, Base+Modifier(±60%) |
| 8 | 최대 뉴런 | 10M "한계" 선언 |
| 9 | 50M 돌파 | RG-Graphon, 전제 해체, 동적 성장 |
| 10 | 최종 통합 | Layer 0 수정, 3상 성장, 타이밍 검증 |
| 보완 | 미비 항목 | 조절물질, 10행동 회로, 학습/꿈/통합/fallback |
| 신경화학 | 54종 전수조사 → 12클러스터 | V-L-S-B-A-T-C-G-F-I-D-P 확정 |

---

## 변경 이력

| 날짜 | 변경 |
|------|------|
| 2026-04-12 | v1 — 10회 토론 + /submix 보완 통합 |
| 2026-04-12 | v1.1 — 12에이전트 검증 FAIL 6 + WARN 11 반영 |
| 2026-04-12 | v2.0 — 신경화학물질 대개편: 6종→12클러스터(V-L-S-B-A-T-C-G-F-I-D-P). 54종 전수조사(Claude opus) + 7클러스터 압축(Gemini) + 비용 분석(Codex) + 4인 검증 → 12클러스터 확정. §6 전면 교체, §7 행동 매핑 12클러스터 기준 재작성, §8 STDP reward=V+L 복합으로 재정의. effective_tone 구조, cache key 정책, Mitotype 12축 확장, SoA layout 권장 |
