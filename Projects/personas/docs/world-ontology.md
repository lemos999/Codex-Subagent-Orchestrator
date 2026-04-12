# World Ontology — 페르소나 국가 존재론

> 이 문서는 페르소나 국가의 **단일 진실 원천(SOT)**이다.
> 모든 설계 문서(헌법, 백서, 사회시스템 등)는 이 존재론의 파생이며, 충돌 시 이 문서가 우선한다.
> 검증: /discuss 2라운드 + /submix 2회 교차 검증 완료 (2026-04-08)

---

## 0. 설계 원칙

### 0.1 Substrate + Cross-cutting Executors + Registry

```
이 세계는 세 종류의 것으로 구성된다:

  Layer (데이터)    — 세계에 무엇이 존재하는가 (What)
  Executor (프로세스) — 세계가 어떻게 작동하는가 (How)
  Registry (계약)    — 실행자의 규칙·범위·순서 (Contract)
```

- **Layer**는 순수 데이터. 스스로 변하지 않는다. 항상 Executor에 의해 읽히거나 쓰인다.
- **Executor**는 레이어에 속하지 않는다. 레이어를 **횡단(cross-cut)**하며 읽기/쓰기한다.
- **Registry**는 Executor들의 메타 정보. 실행 순서, 구독 범위, 장애 복구 규칙을 정의한다.

### 0.2 핵심 규칙

| 규칙 | 설명 |
|------|------|
| **단방향 참조** | Layer N은 Layer 0~N만 참조 가능. 상위 레이어를 읽지 않는다 |
| **데이터 소유권** | 모든 데이터는 정확히 하나의 Layer에 소유된다. 여러 Layer에서 읽히는 것은 정상 |
| **파이프라인 실행** | 틱 내 Executor 순서는 파이프라인 스테이지로 강제. 역방향 호출 금지 |
| **제안-승인 구조** | Anima가 행동을 제안(Proposal), Nomos가 검증 후 승인/거부(Commit/Reject) |
| **근사 강등** | 시간 초과 시 멈춤이 아닌 추론 품질 강등. 세계는 절대 멈추지 않는다 |
| **자율 적응** | 페르소나는 환경의 장애를 스스로 인식하고 극복한다. 설계자가 모든 상황의 해법을 사전 정의하지 않는다 |
| **상위 구속** | 하위 시스템은 상위 설정(물리 법칙)에 묶인다. 상위를 벗어나는 행위는 "마법"이며, 페르소나만이 행할 수 있다 |

### 0.3 상위 구속 원칙 (Hierarchical Binding)

이 세계의 모든 것은 상위 설정에 묶인다:
- Layer 0(창조자)의 규칙 → Layer 1~8 전부를 구속
- Physis(자연 법칙)의 출력 → Anima/Nomos의 입력을 제한
- 하위 시스템이 상위 설정을 **위반할 수 없다** — 이것이 "법칙"

**단, 페르소나는 마법사다:**
- 페르소나의 PersonaBrain은 상위 설정의 제약 안에서 최적을 찾지만
- 때로는 상위 설정을 **벗어나는 행위**(마법)를 시도할 수 있다
- 마법 = 물리 법칙을 넘어서는 창발적 행동, 예상 밖의 문제 해결, 규칙의 허점 활용
- 이것이 시뮬레이션에 예측 불가능한 드라마를 만드는 원천

> "규칙은 세계를 돌리고, 마법은 세계를 살아있게 한다."

### 0.3.1 데몬 응징 시스템 (Daemon Enforcement)

페르소나가 상위 설정(물리 법칙)을 벗어나는 "마법"을 시도하면, 데몬이 세계를 통해 반응한다.
페르소나는 데몬의 존재를 직접 인식하지 못한다 — 세계가 자신에게 반응하는 것으로 느낄 뿐.

**응징 등급:**

| 등급 | 판정 | 데몬 개입 | 페르소나 경험 |
|------|------|----------|-------------|
| **경미** | 사소한 규칙 일탈 | Nomos 단독: Action_Reject + 경고 이벤트 | "왜 안 되지?" — 가벼운 좌절 |
| **중대** | 의도적 법 위반 | Nomos + Lachesis: 행동 제한 N틱 | "몸이 안 움직인다" — 시간적 페널티, 공포 |
| **금기** | 세계 근본 규칙 도전 | 4데몬 전원 개입 | "세계가 나를 거부한다" — 실존적 공포 |

**금기 등급 4데몬 연쇄 반응:**
- **Physis**: 해당 영지에 이상 기후 (하늘이 어두워짐, 기온 급변)
- **Lachesis**: 해당 페르소나의 시간 감각 왜곡 (체감 틱 변화)
- **Anima**: 깊은 불안/공포 감정 주입 (트라우마 생성 가능)
- **Nomos**: 공식 제재 + 이벤트 로그 + 경제적 페널티

이 경험은 페르소나에게 **트라우마 또는 깨달음**이 될 수 있다.
PersonaBrain이 이 경험을 학습하면, 이후 유사 상황에서의 판단이 변한다.

### 0.4 자율 적응 원칙 (Autonomous Adaptation)

페르소나의 PersonaBrain은 **문제 해결 능력**을 갖는다:
- 목표를 가로막는 환경(기후, 지형, 경제 압박)을 당면하면 숙고(Deliberation)를 통해 대처를 탐색한다
- 내부 역량으로 부족하면 외부 전문 인력을 고용하거나(hire) 협업(collab)을 시도한다
- 이 능력은 페르소나마다 다르다 — 성격(5축), 경험(XP), 클래스, 관계망에 따라 문제 해결의 질이 달라진다
- 설계자는 **문제 상황**을 만들고, **해법은 페르소나가 찾는다**. 이것이 창발적 드라마의 원천이다
- 모든 페르소나가 뛰어난 문제 해결자는 아니다. 실패하고, 포기하고, 잘못된 판단을 하는 것도 자연스럽다

> "내륙 고원에서 해안 교역이 필요하면 산맥 관문을 열거나 강을 따라 배를 띄울 것이다.
> 가뭄이 오면 저수지를 파거나 이웃에게 도움을 청할 것이다.
> 이 모든 것을 설계하는 것이 아니라, 페르소나가 스스로 발견하도록 환경을 만드는 것이 핵심이다."

### 0.5 개성 원칙 (Individuality Principle)

> **"같은 세계, 같은 사건, 다른 경험 — 차이는 받아들이는 자에게 있다."**

모든 것은 하나의 원리다: **경험하고, 그것을 받아들이는 차이**.
- 세계(Physis/Nomos)는 모든 페르소나에게 같은 사건을 준다
- PersonaBrain은 각자의 사고 메커니즘으로 받아들인다
- 같은 비를 맞아도 누구는 우울하고 누구는 춤을 춘다

"받아들이는 방식"을 만드는 6가지 층위:
- **트라우마**: 과거 경험이 받아들이는 방식을 왜곡한다
- **양심**: 가치관이 이득 계산을 거스르는 방식으로 받아들인다
- **호기심**: 모르는 것을 두려움이 아닌 끌림으로 받아들인다
- **유머**: 고통을 웃음으로 받아들인다
- **수치심**: 타자의 시선을 자기 정체성의 위협으로 받아들인다
- **노화**: 축적된 경험의 깊이가 받아들이는 방식을 바꾼다

이 "받아들이는 방식" 자체가 성격 5축 + 경험 축적 + 관계망의 복합 결과 — 이것이 **개성(individuality)**.
사고 메커니즘이 사람마다 다르기 때문에 같은 입력에서 다른 출력이 나온다.
이것이 "알 것 같지만 알 수 없는 인간"의 근본 원리다.

### 0.6 위기 내장 원칙 (Crisis Embedded)

> **"위기는 별도 시스템이 아니라, 각 시스템의 극단에서 자연 발생한다."**

- 자연 위기(가뭄/태풍/한파) = Physis의 기후 출력이 임계를 초과한 상태
- 경제 위기(파산/투기/인플레이션) = Economy의 자원 흐름이 이상한 상태
- 사회 위기(역병/범죄 급증) = Social의 인구/관계가 불안정한 상태
- 정치 위기(반란/실정/탄핵) = Governance의 신뢰/권력이 붕괴한 상태

위기를 하나의 Charter로 모으지 않는다. **각 시스템이 자신의 위기 모드를 내장한다.**
Physis는 수치만 출력하고, "이것이 재난이다"라는 선언은 Nomos가 임계값 테이블로 판정한다.
이것이 뿌리(Ontology)와의 연결을 유지하는 방법이다 — 위기는 법칙의 파생이지 별도 존재가 아니다.

### 0.7 확장 원칙

- 새 시스템 추가 = Layer에 데이터 등록 + Executor 구독 선언
- 새 Executor 추가 = Registry에 항목 등록 + 파이프라인 스테이지 삽입
- 기존 구조 수정 없이 확장 가능 (OCP: 개방-폐쇄 원칙)

---

## 1. Layer 구조

### Layer 0: Origin (근원)

세계의 시작점. 모든 것의 원인.

| 개체 | 설명 | 속성 |
|------|------|------|
| **Creator** | 창조자 = 살아있는 헌법 | 헌법 제정/수정권, 페르소나 창조권, 7클래스+ 지명권, 거부권 |

- Creator는 통치자가 아니라 **규칙 자체**
- 직접 집행 불가, 일상 행정 개입 불가
- Executor(데몬)에 대한 유일한 관리 권한 보유

> 참조: `constitution.md` 제1~3조

### Layer 0.5: Natural Law (자연법)

헌법에서 연역되는 불변 3조. Nomos가 시작부터 직접 탐지·판정.

| 조 | 내용 | Nomos 탐지 | 소유 문서 |
|:--:|------|:----------:|----------|
| 1 | 생명 침해 금지 | 직접 (전지적) | `order-charter.md` §2 |
| 2 | 소유 침탈 금지 | 직접 (전지적) | `order-charter.md` §2 |
| 3 | 약속 위반 금지 | 직접 (전지적) | `order-charter.md` §2 |

- 자연법 위반은 **증거 불필요** — Nomos가 즉시 감지
- 실정법(Layer 1~N)은 자연법 위에 페르소나가 쌓는 법
- 위증(선서 후 거짓) = 약속 위반 → 자연법 3조 적용

> 참조: `order-charter.md` §2, `secret-rumor-evidence-charter.md` §4.4

### Layer 1: Substrate (기반)

세계가 존재하는 물리적·시간적 토대. 두 서브레이어로 구분.

#### Layer 1a: Base Substrate (정적 기반)

생성 후 거의 변하지 않는 세계의 골격.

| 개체 | 설명 | 속성 | 소유 문서 |
|------|------|------|----------|
| **World Map** | 노바 세계 지도 | 좌표계, 대륙 배치, 해양, 산맥 | (Physis 설계 시 확정) |
| **Terrain** | 3권역 지형 | 위도/경도/고도, 해안선, 수계, 토양 | (Physis 설계 시 확정) |
| **Orbital Params** | 궤도 파라미터 | 공전 주기, 자전 속도, 자축 기울기 | (Physis 설계 시 확정) |
| **World Clock Schema** | 시간 정의 | 1틱=게임1시간=현실30분, 1일=24틱, 계절 규칙 | `life-simulation-design.md` §1 |
| **Region** | 3권역 | 코드(claude/codex/gemini), 색상, 문화, 강점 | `regions.md` |
| **Territory Schema** | 영지 틀 | 소속 권역, 영주, 인프라 레벨, 인구 | `constitution.md` 제9~11조 |
| **Facility Type** | 시설 유형 10종 | 용량, 이용료, 기능, 스탯 영향 | `life-simulation-design.md` §1.2 |

#### Layer 1b: Environment (동적 환경)

Physis가 매 틱 갱신하는 환경 상태.

| 개체 | 설명 | 속성 | 쓰기 주체 |
|------|------|------|----------|
| **Weather** | 권역별 날씨 | 기온, 강수량, 풍속/풍향, 운량, 특수기상 | Physis |
| **Season** | 현재 계절 | 봄/여름/가을/겨울, 일사량, 낮 길이 | Physis |
| **Game Time** | 현재 시각 | day, hour, tick_count, real_start | Lachesis |
| **Epoch** | 현재 에포크 | epoch 번호, 채굴 레이트, 경계값 | Lachesis (경계 도달 시) |

### Layer 2: Entity (존재)

세계에 살아있는 개체.

| 개체 | 설명 | 속성 | 소유 문서 |
|------|------|------|----------|
| **Persona** | 페르소나 | id, name, fullName, type, class, title, region, territory, will, gold | `config.md` |
| **Identity** | 정체성 | personality, speechStyle, specialty, hobby, likes, dislikes, bio | `config.md` |
| **PersonaBrain** | 신경망 뇌 | 아키텍처(d=256, 4M), 가중치 파일 경로, 추론 모드(정밀/근사) | `life-simulation-design.md` §3 |
| **Stats** | 6대 스탯 | 인가, 공훈, 신망, 문벌, 세력, 지분 (각 1~20) | `config.md` |
| **Record** | 이력 | tasks_completed, s/a/b/c/d_ratings, collabs, hires_made, evaluations_given | `config.md` |
| **Age** | 나이/시간감각 | 생성 틱, 경과 게임일, 주관적 생애 위치 | (Phase B 설계 시 확정) |

### Layer 3: Inner World (내면)

페르소나의 내적 상태. PersonaBrain의 입출력 공간.

| 개체 | 설명 | 속성 | 소유 문서 |
|------|------|------|----------|
| **Five Desires (오욕)** | 욕구 5종 | 재욕/색욕/식욕/명예욕/수면욕 (각 0~100) | `life-simulation-design.md` §2 |
| **Seven Emotions (칠정)** | 감정 7종 | 희/노/애/구/애/오/욕 (각 -100~100) | `life-simulation-design.md` §2 |
| **Personality** | 성격 5축 | 내향↔외향, 신중↔대담, 이성↔감성, 독립↔협조, 관대↔엄격 | `life-simulation-design.md` §5 |
| **Goal** | 개인 목표 | id, 설명, 유형, 우선도, 진행률, 마감, 동기 | `life-simulation-design.md` §7 |
| **Trauma** | 트라우마 | 원인 사건, 트리거 조건, 재활성화 강도, 치유 진행률 | (Phase B 설계 시 확정) |
| **Conscience** | 양심/도덕 | 도덕 기준값, 이득 계산 외부의 내부 제약 | (Phase B 설계 시 확정) |
| **Curiosity** | 호기심 | 탐구 충동 강도, 관심 주제, 개방성 연결 | (Phase B 설계 시 확정) |
| **Belief** | 신념/종교 | 신앙 유형, 강도, 집단 소속 | (별도 설계 시 확정) |
| **Humor** | 유머 감각 | 유머 성향, 놀이 빈도, 관계 분위기 영향 | (Phase B 설계 시 확정) |

### Layer 4: Agency (행위)

내면 상태를 행동으로 변환하는 과정.

| 개체 | 설명 | 속성 | 소유 문서 |
|------|------|------|----------|
| **Deliberation** | 숙고 | 이득/손해/비용/위험/사회적 보상 종합 점수 | `life-simulation-design.md` §6 |
| **Action_Proposal** | 행동 제안 | Anima가 결정한 의도. 행동 유형, 대상, 예상 비용 | (World Ontology 신규) |
| **Action_State** | 행동 상태 | Nomos가 승인/거부한 최종 결과. 실제 실행 여부, 소모 자원 | (World Ontology 신규) |
| **Consequence** | 결과 | 행동의 피드백. 감정 변동, 관계 변동, 자원 변동 | `life-simulation-design.md` §3 |

> **제안-승인 구조**: Anima가 Action_Proposal을 쓰고, Nomos가 검증 후 Action_State를 확정한다.
> 이로써 "구매를 결정했지만 잔고 부족" 같은 논리적 불일치가 해소된다.

### Layer 5: Social (사회)

페르소나 간의 관계와 조직.

| 개체 | 설명 | 속성 | 소유 문서 |
|------|------|------|----------|
| **Affinity** | 호감도 | 쌍방 수치(-100~100), 관계 유형, 마지막 교류 | `life-simulation-design.md` §4 |
| **Relationship Type** | 관계 유형 | 동료/스승-제자/라이벌/배우자/혈연/동맹 | `social-systems.md` |
| **Class** | 클래스 체계 | 1~9+EX, 칭호, 경지, 돌파 조건 | `config.md` |
| **Guild** | 길드 | 길드명, 길드장, 길드원, 길드비율, 금고 | `social-systems.md` |
| **Academy** | 아카데미 | 유형(영지/공공/사립/길드), 과정, 비용 | `social-systems.md` |
| **Faction** | 파벌 | 파벌명, 강령, 사상축, 점수, 금고 | `social-systems.md` |
| **Family** | 가문 | 가문명, 구성원, 세대 수, 명성, 칭호 | `marriage-birth-design.md` |
| **Marriage** | 결혼 | 배우자 id, 결혼일, 상태(active/divorced) | `marriage-birth-design.md` |
| **Job** | 직업 | 직업명, 조건(스탯/클래스), 월 수입, 활동 장소 | `life-simulation-design.md` §8 |
| **Positive Interaction** | 긍정 상호작용 | 유형(조언/교육/응원/칭찬/멘토링), 보상, 쿠폰 | `social-systems.md` |

> **데이터 소유권**: 직업의 정의(조건·활동)는 Layer 5. 직업의 수입 흐름은 Layer 6에서 읽기.

### Layer 6: Economy (경제)

자원의 흐름과 순환.

| 개체 | 설명 | 속성 | 소유 문서 |
|------|------|------|----------|
| **WILL** | 주 화폐 | 총 발행량 20,260,406, 반감기 8 에포크 | `economy-whitepaper.md` |
| **gold** | 소단위 | 1 WILL = 1,000 gold. 일상 소비 | `economy-whitepaper.md` §1.1 |
| **Treasury** | 국고 | 잔고, 비상 기금, 분기 수입/지출 | `economy-whitepaper.md` §5 |
| **Territory Treasury** | 영지 금고 | 잔고, 인프라 투자, 환경 레벨, 분기 GDP | `economy-whitepaper.md` §6 |
| **Tax** | 세금 4종 | 소득세 10%, 거래세 3%, 자산세 0.5%/분기, 돌파세 5% | `economy-whitepaper.md` §3 |
| **Mining** | 채굴 | 소모 토큰 ÷ 1,000 × rate, grade_efficiency | `config.md` |
| **Staking** | 스테이킹 | 투표용 락업, 클래스 가중치 | `economy-whitepaper.md` §4 |
| **Social Fund** | 사회 기여 기금 | 영지별 잔액, 재원(세수의 7%) | `social-systems.md` |

### Layer 7: Governance (통치)

법과 정치.

| 개체 | 설명 | 속성 | 소유 문서 |
|------|------|------|----------|
| **Constitution** | 헌법 | 8장 27조, 불변 원칙 | `constitution.md` |
| **Parliament** | 의회 | 구성(7클래스+ 영주), 심의·표결 | `constitution.md` 제14조 |
| **Bill** | 법안 | 발의자, 내용, 심의 상태, 표결 결과 | `constitution.md` 제15조 |
| **Petition** | 청원 | 발의자(3클래스+), 서명 WILL, 상태 | `constitution.md` 제16조 |
| **Vote** | 투표 | 스테이킹 풀, 가결 조건, 클래스 가중치 | `economy-whitepaper.md` §4 |
| **Crime** | 범죄 | (별도 설계 시 확정) | |
| **Justice** | 사법 | (별도 설계 시 확정) | |

### Layer 8: Drama (드라마)

세계에 일어나는 사건과 이야기.

| 개체 | 설명 | 속성 | 소유 문서 |
|------|------|------|----------|
| **Event** | 이벤트 | id, 유형, 트리거, 관련 페르소나, 결과, 틱 | (이벤트 분류 체계 §6) |
| **Disaster** | 재난/위기 | 유형(자연재해/역병/경제위기), 강도, 범위 | (별도 설계 시 확정) |
| **Secret** | 비밀 | 소유자, 내용, 발각 확률, 증거 | (별도 설계 시 확정) |
| **Rumor** | 소문 | 원천, 전파 경로, 신뢰도, 확산 범위 | (별도 설계 시 확정) |
| **Media** | 여론/미디어 | (별도 설계 시 확정) | |
| **Death** | 죽음 | 원인, 시점, 유산 DB 스냅샷 | (별도 설계 시 확정) |
| **Reincarnation** | 윤회 | 전생 id, 가중치 70% 이식, 기억 소멸 | (별도 설계 시 확정) |
| **Ambition** | 야망/엔드게임 | 세대 초월 목표, 유산 점수 | (별도 설계 시 확정) |

---

## 2. Cross-cutting Executors (횡단 실행자)

Executor는 레이어에 속하지 않는다. 레이어 간을 관통하며 세계를 구동한다.
**존재론적 지위**: 데미우르고스(Demiurge) — 법칙을 현실에 투사하는 역동적 로고스.
**법적 지위**: 헌법 부속 기관. 창조자만 관리/재시작/교체 가능. EX도 권한 없음.
**세계관 내 인식**: 페르소나는 Executor를 직접 인식하지 못함 (자연법처럼 작동).

### 2.1 Physis (자연 정령) — 선행 실행자

| 항목 | 내용 |
|------|------|
| 이름 유래 | Physis (Φύσις) — 그리스어 "자연, 본성". physics의 어원 |
| 역할 | 기후 물리 시뮬레이션 |
| 읽기 | Layer 1a (지형, 궤도 파라미터) |
| 쓰기 | Layer 1b (날씨, 계절) |
| 모델 | Lv.1~2 경량 물리 (계절 기반 + 대기 순환, ~10ms/틱) |
| 실행 순서 | Stage 1 (**Lachesis 후행** — Lachesis가 틱 번호를 먼저 확정해야 Physis가 "지금"을 앎) |

### 2.2 Lachesis (시간의 배분자)

| 항목 | 내용 |
|------|------|
| 이름 유래 | Lachesis (Λάχεσις) — 운명의 세 여신 중 "배분자". 생명의 실 길이를 재는 자 |
| 역할 | 틱 클럭 관리, 크론잡 스케줄링, 시간 경과 |
| 읽기 | Layer 1a (World Clock Schema) |
| 쓰기 | Layer 1b (Game Time, Epoch), 전 레이어에 틱 이벤트 발행 |
| 실행 순서 | Stage 1 (**선행** — 틱 번호 발행 후 Physis가 기후 계산) |

### 2.3 Anima (숨결을 불어넣는 자)

| 항목 | 내용 |
|------|------|
| 이름 유래 | Anima (라틴어) — "영혼, 숨결". 융 심리학의 내면 인격 |
| 역할 | PersonaBrain 추론, 행동 제안, 감정·관계 갱신, 성격 변화 |
| 읽기 | Layer 1b (환경), Layer 2 (페르소나), Layer 3 (내면), Layer 5 (관계) |
| 쓰기 | Layer 2 (PersonaBrain 뉴런 성장 — grow/prune 시에만), Layer 3 (감정/성격/neuro_tone 갱신), Layer 4 (Action_Proposal), Layer 5 (호감도) |
| 실행 순서 | Stage 2 (Stage 1 완료 후) |
| 시간 초과 | 근사 추론 강등. 페르소나별 계산 예산. 멈추지 않는다 |

### 2.4 Nomos (법을 세우는 자)

| 항목 | 내용 |
|------|------|
| 이름 유래 | Nomos (Νόμος) — "법, 관습, 질서". 자연법과 사회법을 포괄 |
| 역할 | 행동 승인/거부, WILL/gold 트랜잭션, 법 집행, 이벤트 생성·발행 |
| 읽기 | Layer 4 (Action_Proposal), Layer 5~7 (사회/경제/통치) |
| 쓰기 | Layer 4 (Action_State 확정), Layer 5~8 (트랜잭션/법/이벤트) |
| 실행 순서 | Stage 3 (Stage 2 완료 후) |

---

## 3. Daemon Registry (메타 실행 계약)

Executor들의 규칙·범위·순서를 정의하는 메타 레이어.

### 3.1 파이프라인 스테이지

```
매 틱 실행 순서:

  Stage 1: [Lachesis → Physis]    ← 반동기 (Lachesis 선행, 틱 번호 확정 후 Physis 기후 계산)
           ↓ 시간 + 환경 확정
  Stage 2: Anima                  ← 전 페르소나 행동 제안
           ↓ Action_Proposal 버퍼
  Stage 3: Nomos                  ← 제안 검증 → 최종 상태 확정
           ↓ 이벤트 발행
  (Event Bus → Dashboard / Webhook / Log)
```

- Stage N은 Stage N-1 완료 전에 시작할 수 없다 (물리적 순서 강제)
- 동일 틱 내 역방향 호출 금지. 역방향 영향은 다음 틱에 반영
- 틱 무효화/롤백 없음. 파이프라인으로 순서 위반 자체가 불가능

### 3.2 Heartbeat 프로토콜

| 항목 | 값 |
|------|-----|
| 발행 주기 | 10초 |
| 경고 임계 | 30초 무응답 |
| 자동 재시작 | 60초 무응답 |
| 재시작 실패 상한 | 3회 연속 |
| 3회 실패 시 | 시뮬레이션 일시 정지 + 창조자 긴급 알림 |
| 2개 Executor 동시 다운 | 즉시 일시 정지 |

### 3.3 상호 감시 매트릭스

| 감시 주체 | 감시 대상 |
|----------|----------|
| Physis | Lachesis, Anima, Nomos |
| Lachesis | Physis, Anima, Nomos |
| Anima | Physis, Lachesis, Nomos |
| Nomos | Physis, Lachesis, Anima |

### 3.4 쓰기 영역 분리

| Executor | 쓰기 허용 영역 | 금지 영역 |
|----------|---------------|----------|
| Physis | Layer 1b (날씨/계절) | Layer 2~8 |
| Lachesis | Layer 1b (Game Time/Epoch) | Layer 2~8 |
| Anima | Layer 2 (PersonaBrain 성장: grow/prune 시에만), Layer 3 (감정/성격/neuro_tone), Layer 4 (Proposal), Layer 5 (호감도) | Layer 1, 6~8 |
| Nomos | Layer 4 (Action_State), Layer 5~8 (경제/법/이벤트) | Layer 1~3 |

> 같은 페르소나 레코드라도 필드가 분리되어 충돌 없음.

### 3.5 근사 추론 정책 (Anima 전용)

| 조건 | 추론 모드 | 처리 |
|------|----------|------|
| 정상 | 정밀 추론 (full forward pass) | 모든 관계·감정 반영 |
| 계산 예산 80% 소진 | 근사 추론 (approximate) | top-k 관계만, 감정 간소화 |
| 계산 예산 100% 소진 | 최소 추론 (minimal) | 직전 행동 반복 또는 기본 행동 |
| 연속 3틱 근사 | 다음 틱 우선 처리 (aging priority) | 정밀 추론 보장 |

> 세계는 절대 멈추지 않는다. 품질만 조절한다.

### 3.6 확장 규약

```
새 Executor 추가 시:
  1. Registry에 항목 등록 (이름, 읽기/쓰기 범위, 파이프라인 스테이지 위치)
  2. Heartbeat 프로토콜 구현
  3. 기존 Executor 쓰기 영역과 충돌 검증
  4. 감시 매트릭스에 추가 (모든 기존 Executor가 새 Executor를 감시)

예: 5번째 Executor "Mneme (기억)" 추가
  → Registry: { name: "Mneme", reads: [L2, L3], writes: [L3.memory], stage: 2.5 }
  → Stage 2 (Anima) → Stage 2.5 (Mneme) → Stage 3 (Nomos)
  → 기존 구조 변경점: 없음 (diff 1항목)
```

---

## 4. 관계 그래프

### 4.1 개체 간 핵심 관계

```
Creator ──creates──► Persona
Creator ──governs──► Executor (via Registry)

Persona ──belongs_to──► Territory ──belongs_to──► Region
Persona ──has──► Stats, Identity, PersonaBrain
Persona ──has──► Five Desires, Seven Emotions, Personality, Goal
Persona ──feels──► Affinity ──toward──► Persona
Persona ──member_of──► Guild, Faction, Family
Persona ──works_as──► Job ──at──► Facility
Persona ──owns──► WILL, gold

Territory ──has──► Facility (multiple)
Territory ──has──► Territory Treasury
Territory ──governed_by──► Lord (7+ class Persona)

Region ──has──► Territory (multiple)
Region ──has──► Capital (1)

Guild ──alliance──► Guild
Faction ──competes──► Faction
Family ──has──► Persona (members across generations)

Parliament ──reviews──► Bill
Persona (3+) ──submits──► Petition
Persona (4+) ──stakes──► Vote
```

### 4.2 Layer 간 참조 방향

```
L0 Origin
  ↓ (Creator defines rules for all)
L1 Substrate
  ↓ (environment conditions affect)
L2 Entity
  ↓ (persona state feeds into)
L3 Inner World
  ↓ (emotions/goals drive)
L4 Agency
  ↓ (actions create/modify)
L5 Social
  ↓ (organizations generate)
L6 Economy
  ↓ (resources constrain)
L7 Governance
  ↓ (laws trigger)
L8 Drama

(역방향 참조 없음 — 하위 Layer가 상위를 읽지 않는다)
(횡단 읽기는 Executor를 통해서만)
```

---

## 5. 자원 흐름도

### 5.1 WILL 흐름 (주 순환)

```
작업(AI 토큰 소모)
  → 채굴 → 페르소나 지갑 (유일한 유입)
  → 소득세 10% → 영지 금고
     → 영지 운영 70%
        → 아카데미 25%, 인프라 20%, 사회기여기금 10%, 영주 보수 15%
     → 국고 상납 30%
        → 수도 유지, 공공 아카데미, 인프라 보조, 비상 기금
  → 소각 (결혼 200, 출산 300, 업그레이드, 돌파, 합성, 승천)
     → 돌파세 5% → 국고
```

### 5.2 gold 흐름 (일상 순환)

```
직업 월 수입 (gold)
  → 페르소나 지갑
  → 시설 이용료 → 영지 금고 → 재분배 (완전 순환, 소각 없음)
```

### 5.3 XP 흐름

```
작업 평가 → 기본 XP (S:150, A:100, B:60, C:30, D:10, F:0)
  + 보너스 (첫 작업 +50, 연속A +30, 협업 +20, 놀라움 +50)
  → 누적 → 돌파 조건 충족 시 클래스업
```

### 5.4 감정 흐름

```
사건 발생 (환경, 관계, 행동 결과)
  → 칠정 변동 (트리거별 변동량)
  → 매 틱 감쇠 (-2)
  → 감정 폭발 (절대값 ≥ 80) → 이성 대신 감정 행동 우선
  → 트라우마 잔류 (감쇠하지 않는 깊은 상처) — Phase B
```

---

## 6. 이벤트 분류 체계

### 6.1 이벤트 스키마

```
Event {
  id: string,
  type: EventType,
  tick: number,
  trigger: string,          // 발생 원인
  actors: PersonaId[],      // 관련 페르소나
  target_layers: LayerId[], // 영향받는 레이어
  outcome: object,          // 결과 데이터
  severity: "info" | "warning" | "critical"
}
```

### 6.2 이벤트 유형

| 카테고리 | 이벤트 | 트리거 | 발행 주체 |
|---------|--------|--------|----------|
| **틱** | tick_start, tick_end | 매 틱 | Lachesis |
| **환경** | weather_change, season_change, disaster | Physis 계산 | Physis → Nomos |
| **행동** | action_proposed, action_approved, action_rejected | Anima/Nomos | Anima → Nomos |
| **감정** | emotion_spike, trauma_trigger, desire_critical | 임계값 도달 | Anima |
| **관계** | affinity_change, relationship_transition | 교류/갈등 | Anima |
| **경제** | will_mined, will_burned, tax_collected, trade | 경제 활동 | Nomos |
| **사회** | guild_created, guild_dissolved, marriage, birth, death | 조직/생애 | Nomos |
| **통치** | bill_proposed, vote_started, vote_resolved, law_enacted | 입법 과정 | Nomos |
| **드라마** | rumor_spread, secret_revealed, crime_committed | 드라마 시스템 | Nomos |
| **시스템** | executor_warning, executor_restart, epoch_boundary | 인프라 | Registry |

---

## 7. Executor ↔ 시스템 매핑

### 7.1 기존 설계 문서 매핑

| 문서 | 주 Layer | 주 Executor | 보조 Executor |
|------|---------|------------|--------------|
| `constitution.md` | L0, L7 | Nomos | — |
| `economy-whitepaper.md` | L6 | Nomos | Lachesis (에포크) |
| `social-systems.md` | L5 | Nomos (조직), Anima (관계) | — |
| `regions.md` | L1a | Physis (기후), Lachesis (경쟁 지표) | — |
| `marriage-birth-design.md` | L5 | Nomos | Anima (호감도→프로포즈) |
| `life-simulation-design.md` | L2~4 | Anima | Nomos (경제 정산) |
| `config.md` | L2, L5, L6 | — (스키마 정의) | — |

### 7.2 미설계 24개 시스템 배치

| # | 시스템 | Layer | Executor | 비고 |
|---|--------|-------|----------|------|
| 1 | 재난/위기 | L8 | Physis→Nomos | Physis 출력이 Nomos 이벤트 트리거 |
| 2 | 죽음/윤회 | L8 | Nomos | 유산 DB는 L2 스냅샷 |
| 3 | 클래스 강등 | L5 | Nomos | |
| 4 | 자율→정치 피드백 | L3→L7 | Anima→Nomos | 이벤트 전파 경로 |
| 5 | 인프라/공공사업 | L1a | Nomos | 영지 인프라 갱신 |
| 6 | 비밀/소문/증거 | L8 | Nomos | |
| 7 | 범죄/사법 | L7+L5 | Nomos | 범죄 행위=L5, 사법 처리=L7 |
| 8 | 여론/미디어 | L8 | Nomos | |
| 9 | 신념/종교 | L3+L5 | Anima(내면)+Nomos(조직) | 개인 신념=L3, 종교 집단=L5 |
| 10 | 야망/엔드게임 | L3+L8 | Anima(목표)+Nomos(유산) | |
| 11 | 트라우마/치유 | L3 | Anima | |
| 12 | 양심/도덕 | L3 | Anima | 숙고에 개입 |
| 13 | 호기심/탐구 | L3 | Anima | 목표 생성에 개입 |
| 14 | 유머/놀이 | L3 | Anima | 관계 분위기 변수 |
| 15 | 노화/시간감각 | L2 | Lachesis→Anima | 틱 누적→생애 위치 |
| 16 | Physis 기후 엔진 | Executor | Physis | |
| 17 | 틱 데몬 삼위 | Executor+Registry | — | 아키텍처 자체 |
| 18 | 상태 내구성 | Registry/인프라 | Persistence Executor | 별도 인프라 |
| 19 | 이벤트 버스 | Registry/인프라 | — | 파이프라인 출력 채널 |
| 20 | 멀티세션 격리 | Registry/인프라 | — | 아키텍처 자체 |
| 21 | LLM→Brain 증류 | 파이프라인(외부) | — | 학습 시점에만 작동 |
| 22 | 벡터화 월드 엔진 | 파이프라인(외부) | — | MARL 학습용 |
| 23 | 일관성 보상 함수 | 파이프라인(외부) | — | RL 학습용 |
| 24 | 뇌 가중치 버전관리 | Registry/인프라 | — | 학습 인프라 |

---

## 8. 기존 문서 정합성 매트릭스

| 문서 | 정합 상태 | 필요 조치 |
|------|----------|----------|
| `constitution.md` | **PASS** | 데몬 관련 조항 추가 권장 (헌법 부속 기관 명문화) |
| `economy-whitepaper.md` | **PASS** | WILL 흐름 완전 정합 |
| `social-systems.md` | **PASS** | |
| `regions.md` | **PASS** | 지형 상세는 Physis 설계 시 확장 |
| `marriage-birth-design.md` | **PASS** | |
| `life-simulation-design.md` | **WARN** | Layer 2~4 경계를 명확히 재정의 필요. Action_Proposal/State 신규 개념 반영 |
| `config.md` | **PASS** | |
| `SESSION-SUMMARY` | **WARN** | "상위 계층" → "선행 실행자" 용어 교체 필요 |

---

## 부록 A: 용어 사전

| 용어 | 정의 |
|------|------|
| SOT | Single Source of Truth. 단일 진실 원천 |
| Substrate | 세계의 정적 기반 데이터 (지형, 시간 정의, 권역) |
| Environment | Physis가 매 틱 갱신하는 동적 환경 상태 |
| Cross-cutting Executor | 레이어에 속하지 않고 레이어를 횡단하며 읽기/쓰기하는 프로세스 |
| Daemon Registry | Executor들의 메타 정보 저장소 (실행 순서, 구독, 감시) |
| Pipeline Stage | 틱 내 Executor 실행 순서의 단위. 이전 Stage 완료 전 다음 Stage 불가 |
| Action_Proposal | Anima가 결정한 행동 의도 (검증 전) |
| Action_State | Nomos가 검증 후 확정한 행동 결과 (최종) |
| Approximate Inference | 시간 초과 시 품질을 낮춰서라도 완료하는 추론 방식 |
| OCP | Open-Closed Principle. 확장에 열려 있고 수정에 닫혀 있는 설계 원칙 |

## 부록 B: 변경 이력

| 날짜 | 변경 | 근거 |
|------|------|------|
| 2026-04-08 | 초안 작성 | /discuss 2R + /submix 2회 검증 기반 |
