# /persona 스킬 + WILL 엔진 — 통합 설계 문서

---

# Part 1. 기획서

## 1.1 제품 정의

`/persona`는 페르소나의 생애 전체(생성→배치→평가→성장→거래→승천)를 관리하는 Claude Code 스킬이다. WILL 경제 엔진이 내장되어 모든 코인 발행·소각·이전을 처리한다.

### 핵심 가치
1. **단일 인터페이스** — 페르소나와 관련된 모든 행위는 `/persona` 하나로 수행
2. **경제 무결성** — WILL 발행량은 절대 20,260,406을 초과하지 않음. 모든 거래는 로그됨
3. **즉시 반영** — 명령 실행 즉시 registry.json/economy.json/logs 갱신

### 비핵심 (안 하는 것)
- 대시보드 시각화 (대시보드가 담당)
- AI 작업 실행 자체 (스킬은 관리만, 실제 작업은 사용자/에이전트가 수행)
- 페르소나 간 자동 상호작용 (사용자가 명시적으로 명령)

## 1.2 명령어 목록

### 생성·관리

| 명령어 | 사용법 | 설명 |
|---|---|---|
| `create` | `/persona create "이름" --type 관리형 --domain "설정 검증" --personality "신중한"` | 새 페르소나 생성 (1클래스 시작) |
| `status` | `/persona status "정본 관리자"` | 개별 상태 조회 (스탯·XP·WILL·돌파 조건·현재 배치) |
| `list` | `/persona list --class 4+ --type 관리형 --sort xp` | 목록 조회 (필터·정렬) |
| `rank` | `/persona rank --by xp --top 10` | 랭킹 |

### 작업·평가

| 명령어 | 사용법 | 설명 |
|---|---|---|
| `deploy` | `/persona deploy "정본 관리자" --project "포스리드" --task "종족 재정리"` | 작업에 배치 |
| `undeploy` | `/persona undeploy "정본 관리자"` | 배치 해제 |
| `evaluate` | `/persona evaluate "정본 관리자" --rating A --tokens 50000 [--surprise] [--with "철학 관리자"]` | 작업 평가. XP 부여 + WILL 채굴. `--surprise`: 놀라움 보너스 +50 XP. `--with`: 협업 페르소나 (채굴 ��배) |

### 성장

| 명령어 | 사용법 | 설명 |
|---|---|---|
| `upgrade` | `/persona upgrade "정본 관리자" --stat 분석력` | 능력치 +1 (비용: 현재 수치 × 30 WILL 소각) |
| `breakthrough` | `/persona breakthrough "정본 관리자"` | 클래스 돌파 시험 (조건 검증 + WILL 소각) |
| `ascend` | `/persona ascend "정본 관리자"` | 승천 9→EX (WILL 20,260 소각) |

### 경제

| 명령어 | 사용법 | 설명 |
|---|---|---|
| `hire` | `/persona hire "정본 관리자" --target "철학 관리자"` | 고용 (WILL 이전) |
| `economy` | `/persona economy` | WILL 경제 현황 (채굴률·에포크·유통량·소각량) |
| `shop` | `/persona shop` | 구매 가능 항목·가격표 |

### 유틸리티

| 명령어 | 사용법 | 설명 |
|---|---|---|
| `synthesize` | `/persona synthesize "A" "B" --into "C"` | 합성 (2→1, WILL 500 소각) |
| `history` | `/persona history "정본 관리자" --days 30` | 작업·거래 이력 |

## 1.3 명령어 입출력 형식

### `/persona create`

**입력:**
```
/persona create "정본 관리자" --type 관리형 --domain "설정 검증" --personality "신중한"
```

**출력:**
```
[Persona Created]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  정본 관리자 (Canon Keeper)
  Class 1 · 초심자 · 관리형 · #신중한
  도메인: 설정 검증
  스탯: 분석력 1 / 창작력 1 / 정밀도 4 / 판단력 3 / 협업력 1
  XP: 0 | WILL: 0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### `/persona evaluate`

**입력:**
```
/persona evaluate "정본 관리자" --rating A --tokens 50000
```

**출력:**
```
[Evaluation Complete]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  정본 관리자 · Class 3 · 숙련자
  Rating: A
  XP: +100 (350 → 450 / 800)
  WILL 채굴: +1,000 (Epoch 0, Rate 20.0/1K)
  보너스: 연속 A 2/3회 (달성 시 +30 XP)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Economy: Mined 15,200 / 20,260,406
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### `/persona breakthrough`

**입력:**
```
/persona breakthrough "정본 관리자"
```

**출력 (성공):**
```
[Breakthrough: 일반의 벽 돌파!]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  정본 관리자: Class 3 → Class 4 (달인)
  경지: 숙련의 길 → 대가의 경지
  
  조건 충족:
  ✅ XP 800+ (현재 850)
  ✅ 작업 15회 (현재 18)
  ✅ A등급 3회 (현재 5)
  ✅ WILL 200 → 소각 완료
  
  WILL: 1,200 → 1,000 (-200 소각)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**출력 (실패):**
```
[Breakthrough Failed: 조건 미충족]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  정본 관리자: Class 3 → Class 4 시도
  
  ✅ XP 800+ (현재 850)
  ✅ 작업 15회 (현재 18)
  ❌ A등급 3회 (현재 2) ← 부족
  ✅ WILL 200 (보유 1,200)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### `/persona economy`

```
[WILL Economy]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Total Supply: 20,260,406
  Mined: 10,130,203 (50.0%)
  Burned: 1,500,000
  Circulating: 8,630,203
  
  Epoch: 1 | Rate: 10.0 WILL/1K tokens
  Epoch Progress: ██████░░░░ 60%
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## 1.4 사용 시나리오

### 시나리오 1: 페르소나 생성 → 배치 → 평가 → 성장

```
사용자: /persona create "정본 관리자" --type 관리형 --domain "설정 검증" --personality "신중한"
→ 1클래스 초심자 생성

사용자: /persona deploy "정본 관리자" --project "포스리드" --task "종족 재정리"
→ 작업 배치

(실제 작업 수행: 정본 관리자 역할로 종족 설정 검증)

사용자: /persona evaluate "정본 관리자" --rating A --tokens 50000
→ XP +100, WILL +1,000 채굴

(반복하여 돌파 조건 충족)

사용자: /persona breakthrough "정본 관리자"
→ Class 1 → 2 승급
```

### 시나리오 2: 고용

```
사용자: /persona hire "정본 관리자" --target "철학 관리자"
→ 정본 관리자의 WILL에서 철학 관리자 클래스 × 50 차감
→ 철학 관리자의 WILL에 동일 금액 입금
→ 철학 관리자가 정본 관리자의 작업에 협업으로 참여
```

### 시나리오 3: 승천

```
사용자: /persona ascend "전설의 관리자"
→ 9클래스 확인
→ WILL 20,260 소각
→ 10클래스 (EX) 신격 도달
→ 모든 제한 해제
```

---

# Part 2. 아키텍처 설계서

## 2.1 시스템 구조

```
┌─────────────────────────────────────────────┐
│              사용자 (Claude Code CLI)         │
│  /persona create "이름" --type 관리형        │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────┼──────────────────────────┐
│          스킬 라우터 (SKILL.md)              │
│  명령어 파싱 → 핸들러 디스패치               │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────┼──────────────────────────┐
│          비즈니스 로직 (핸들러)               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│  │ Persona  │ │  Growth  │ │ Economy  │    │
│  │ Manager  │ │  Engine  │ │ Engine   │    │
│  │          │ │          │ │ (WILL)   │    │
│  │ create   │ │ evaluate │ │ mine     │    │
│  │ deploy   │ │ upgrade  │ │ burn     │    │
│  │ status   │ │ break-   │ │ transfer │    │
│  │ list     │ │ through  │ │ balance  │    │
│  │ rank     │ │ ascend   │ │ epoch    │    │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘    │
│       └────────────┼────────────┘           │
└──────────────────┬──────────────────────────┘
                   │ 읽기/쓰기
┌──────────────────┼──────────────────────────┐
│          데이터 계층 (File I/O)              │
│  ┌───────────────┐ ┌───────────────┐        │
│  │ DataStore     │ │ Logger        │        │
│  │ read/write    │ │ append        │        │
│  │ JSON files    │ │ JSONL files   │        │
│  └───────┬───────┘ └───────┬───────┘        │
└──────────┼─────────────────┼────────────────┘
           │                 │
┌──────────┼─────────────────┼────────────────┐
│  Projects/personas/                          │
│  ├── registry.json                           │
│  ├── economy.json                            │
│  ├── cards/*.md                              │
│  └── logs/*.jsonl                            │
└─────────────────────────────────────────────┘
```

## 2.2 모듈 구조

스킬은 Claude Code의 `.claude/skills/persona/` 에 위치하며, **SKILL.md가 진입점**이다. 별도 빌드·실행 파일 없이 SKILL.md의 지시에 따라 Claude가 로직을 수행한다.

```
.claude/skills/persona/
├── SKILL.md                 ← 진입점. 명령어 라우팅 + 전체 규칙
├── handlers/
│   ├── create.md            ← 생성 핸들러 (절차 + 검증 + 출력 형식)
│   ├── deploy.md            ← 배치/해제 핸들러
│   ├── evaluate.md          ← 평가 핸들러 (XP 계산 + WILL 채굴 호출)
│   ├── growth.md            ← upgrade + breakthrough + ascend 통합
│   ├── economy.md           ← hire + economy + shop
│   ├── query.md             ← status + list + rank + history
│   └── synthesize.md        ← 합성 핸들러
├── engine/
│   ├── will-engine.md       ← WILL 채굴·소각·이전 공식 + 절차
│   ├── xp-engine.md         ← XP 계산·보너스 판정 공식
│   └── breakthrough-engine.md ← 돌파 조건 검증 로직
└── references/
    ├── class-table.md       ← 클래스 체계 (config.md 발췌)
    ├── xp-table.md          ← XP 곡선 + 돌파 조건 테이블
    └── economy-rules.md     ← 반감기·용도·가격표 (config.md 발췌)
```

### 왜 .md 파일인가?

Claude Code 스킬은 **프롬프트 기반 실행**이다. 코드가 아니라 지시문을 읽고 Claude가 도구(Read, Write, Edit)로 직접 JSON 파일을 조작한다. 따라서:
- `handlers/*.md` = "이 명령이 오면 이렇게 처리하라"는 절차서
- `engine/*.md` = "이 공식으로 계산하라"는 규칙서
- `references/*.md` = 핸들러가 참조하는 상수 테이블

## 2.3 핵심 모듈 설계

### 2.3.1 SKILL.md (진입점)

```
사용자 입력 → 명령어 파싱 → 핸들러 디스패치
```

라우팅 규칙:
- `/persona create` → handlers/create.md
- `/persona deploy|undeploy` → handlers/deploy.md
- `/persona evaluate` → handlers/evaluate.md
- `/persona upgrade|breakthrough|ascend` → handlers/growth.md
- `/persona hire|economy|shop` → handlers/economy.md
- `/persona status|list|rank|history` → handlers/query.md
- `/persona synthesize` → handlers/synthesize.md
- `/persona` (인수 없음) → 도움말 출력

### 2.3.2 WILL Engine (engine/will-engine.md)

**채굴 (mine)**
```
입력: tokens_consumed (정수)
상수:
  S = 20,260,406 (총 발행량)
  r₀ = 20.0 (초기 채굴 레이트, WILL/1K tokens)
  epoch_boundaries = [10,130,203 / 15,195,305 / 17,727,856 / 18,994,131 / 
                      19,627,269 / 19,943,838 / 20,102,122 / 20,260,406]
처리:
  1. economy.json 읽기 → M(누적 채굴량) 확인
  2. epoch 계산: epoch = floor(log₂(S ÷ (S - M)))
     (구현: epoch_boundaries 배열에서 M이 속하는 구간을 이진 탐색. 수학적으로 동치)
  3. rate = r₀ ÷ 2^epoch
  4. mined_amount = tokens_consumed ÷ 1,000 × rate
  5. 총량 클램핑: if M + mined_amount > S → mined_amount = S - M (잔여분만 발행)
  6. economy.json 갱신: mined += mined_amount, circulating += mined_amount, epoch 재계산
  7. 해당 페르소나 registry.json will += mined_amount
  8. logs 기록: { action: "will_mine", amount, persona_id, epoch, rate }

다중 페르소나 분배 (--with 옵션 사용 시):
  1. 전체 토큰 소모량에서 총 채굴량 계산 (위 절차 1~5)
  2. 각 페르소나별 기여 토큰 비율 계산:
     페르소나별 WILL = 총 채굴량 × (해당 페르소나 소모 토큰 ÷ 전체 소모 토큰)
  3. 기여 비율 미지정 시 균등 분배 (총 채굴량 ÷ 참여 페르소나 수)
  4. 각 페르소나에 개별 will 갱신 + 개별 로그 기록

출력: 채굴된 WILL 양 (다중 시 페르소나별 내역)
```

**소각 (burn)**
```
입력: persona_id, amount, reason
처리:
  1. registry.json에서 해당 페르소나 will 확인
  2. will >= amount 검증 (부족 시 실패)
  3. registry.json 갱신: will -= amount
  4. economy.json 갱신: burned += amount, circulating -= amount
  5. logs 기록: { action: "will_burn", amount, persona_id, reason }
출력: 소각 완료 확인
```

**이전 (transfer)**
```
입력: from_id, to_id, amount, reason
처리:
  1. from 페르소나 will >= amount 검증
  2. registry.json 갱신: from.will -= amount, to.will += amount
  3. logs 기록: { action: "will_transfer", amount, from, to, reason }
출력: 이전 완료 확인
```

### 2.3.3 XP Engine (engine/xp-engine.md)

```
입력: persona_id, rating (S/A/B/C/D/F)
처리:
  1. 기본 XP 부여: S=150, A=100, B=60, C=30, D=10, F=0
  2. 보너스 검증:
     - 첫 작업? → +50 (일회성, first_task_done 플래그로 추적)
     - 연속 A 이상 3회? → +30 (consecutive_a_plus 카운터로 추적)
     - 협업 작업? → +20
     - 사용자가 "놀라움" 표시? → +50 (evaluate 시 --surprise 플래그)
  3. registry.json 갱신: xp += total_xp
  4. record 갱신: tasks_completed++, {rating}_ratings++
  5. 클래스업 가능 여부 확인 → 안내 메시지
  6. logs 기록: { action: "xp_gain", xp, rating, bonuses }
출력: XP 부여 결과 + 보너스 내역
```

### 2.3.4 Breakthrough Engine (engine/breakthrough-engine.md)

```
입력: persona_id
처리:
  1. 현재 클래스 확인
  2. 다음 클래스 돌파 조건 로드 (xp-table.md)
  3. 조건별 충족 여부 체크:
     - XP >= 필요량?
     - tasks_completed >= 필요량?
     - rating 횟수 >= 필요량?
     - collabs >= 필요량? (해당 시)
     - evaluations_given >= 필요량? (해당 시)
     - 전 스탯 >= 필요량? (9클래스)
     - 사용자 지명 여부? (7+ 클래스)
     - WILL >= 필요량?
  4. 전부 충족 시:
     - WILL 소각 (will-engine.burn 호출)
     - 클래스 + 1
     - 칭호 갱신
     - tier(경지 그룹) 갱신
     - logs 기록: { action: "breakthrough", from_class, to_class }
  5. 미충족 시: 체크리스트 결과 반환 (어떤 조건이 부족한지)
출력: 성공/실패 + 체크리스트
```

## 2.4 데이터 흐름

```
/persona evaluate "정본" --rating A --tokens 50000
  │
  ├─→ XP Engine
  │     ├─ XP 계산: A = 100 XP
  │     ├─ 보너스 검사: 연속 A 2/3 → 미달, 보너스 없음
  │     ├─ registry.json: xp += 100, a_ratings++, tasks_completed++
  │     └─ logs: { action: "xp_gain", xp: 100 }
  │
  ├─→ WILL Engine (mine)
  │     ├─ epoch 계산: mined=14200 → epoch=1, rate=10.0
  │     ├─ 채굴: 50000/1000 * 10.0 = 500 WILL
  │     ├─ registry.json: will += 500
  │     ├─ economy.json: mined += 500, circulating += 500
  │     └─ logs: { action: "will_mine", amount: 500 }
  │
  └─→ 출력 렌더링
        └─ 평가 결과 + XP + WILL + 보너스 현황 + 경제 상태
```

## 2.5 파일 조작 안전 규칙

### 원자적 갱신
하나의 명령에서 여러 파일을 수정할 때 (예: evaluate → registry.json + economy.json + logs), 순서는:
1. **먼저 Read로 현재 상태 확인**
2. **계산 수행 (메모리)**
3. **Write/Edit로 갱신** (registry → economy → logs 순)
4. **갱신 후 Read로 검증**

### 동시성
CLI 스킬이므로 동시 실행은 발생하지 않는다. 한 번에 하나의 `/persona` 명령만 처리.

### 백업 불필요
git 히스토리가 자연 백업 역할. 별도 백업 메커니즘 불필요.

### cards/*.md 동기화 정책
- **SOT(Single Source of Truth)**: `registry.json`이 유일한 진실 소스.
- `cards/*.md`는 가독성을 위한 뷰(View). `registry.json`의 파생물.
- **동기화 시점**: `create`, `evaluate`, `breakthrough`, `ascend`, `upgrade` 실행 시 해당 페르소나의 카드 파일도 갱신.
- **불일치 발생 시**: `registry.json`이 우선. 카드 파일은 재생성으로 복구.

## 2.6 registry.json 확장 스키마

기존 스키마에 추가되는 필드:

```typescript
interface Persona {
  // 기존 필드 유지
  id: string;
  name: string;
  title: string;
  class: number;
  tier: string;              // 추가: 경지 그룹
  type: string;
  personality: string;       // 추가: 성격 키워드
  domain: string;
  xp: number;
  will: number;
  stats: Stats;
  record: Record;
  
  // 추가 필드
  currentTask?: {
    project: string;
    task: string;
    status: "active" | "paused" | "idle";
    deployed_at: string;
  };
  consecutive_a_plus: number;  // 연속 A 이상 카운트 (보너스 추적)
  first_task_done: boolean;    // 첫 작업 완료 여부 (일회성 보너스)
  
  created: string;
  last_active: string | null;
}
```

---

# Part 3. 개발 계획서

## 3.1 단계별 구현

### Phase 1: 뼈대 + 데이터 계층 (1일)
- [ ] `.claude/skills/persona/SKILL.md` — 진입점, 명령어 라우팅, 도움말
- [ ] `references/class-table.md` — 클래스·칭호·경지 테이블 (config.md 발췌)
- [ ] `references/xp-table.md` — XP 곡선 + 돌파 조건 (config.md 발췌)
- [ ] `references/economy-rules.md` — 반감기·가격표 (config.md 발췌)
- [ ] registry.json 스키마 확장 (tier, personality, currentTask, consecutive_a_plus, first_task_done)

### Phase 2: 핵심 핸들러 (1일)
- [ ] `handlers/create.md` — 페르소나 생성 (유형별 보정·ID 자동 채번·카드 생성)
- [ ] `handlers/deploy.md` — 배치/해제
- [ ] `handlers/query.md` — status/list/rank/history
- [ ] `handlers/evaluate.md` — 평가 (XP Engine + WILL Engine 호출)

### Phase 3: 엔진 (1일)
- [ ] `engine/will-engine.md` — 채굴·소각·이전 공식 + 절차
- [ ] `engine/xp-engine.md` — XP 계산·보너스 판정
- [ ] `engine/breakthrough-engine.md` — 돌파 조건 검증

### Phase 4: 성장 + 경제 핸들러 (1일)
- [ ] `handlers/growth.md` — upgrade/breakthrough/ascend
- [ ] `handlers/economy.md` — hire/economy/shop
- [ ] `handlers/synthesize.md` — 합성
- [ ] 전체 통합 테스트 (시나리오 1~3 실행)

## 3.2 테스트 방법

각 Phase 완료 후 실제 `/persona` 명령을 실행하여 검증:

| Phase | 테스트 |
|---|---|
| 1 | `/persona` → 도움말 출력 확인 |
| 2 | `/persona create` → registry.json에 추가 확인 / `/persona status` → 조회 확인 |
| 3 | `/persona evaluate` → XP·WILL 정확히 계산 확인 / economy.json 갱신 확인 |
| 4 | `/persona breakthrough` → 조건 검증 + 클래스업 확인 / `/persona hire` → WILL 이전 확인 |

## 3.3 최종 파일 구조

```
.claude/skills/persona/
├── SKILL.md                     ← 진입점 (라우팅 + 도움말 + 불변 규칙)
├── handlers/
│   ├── create.md                ← 생성
│   ├── deploy.md                ← 배치/해제
│   ├── evaluate.md              ← 평가 (XP + WILL)
│   ├── growth.md                ← 성장 (upgrade/breakthrough/ascend)
│   ├── economy.md               ← 경제 (hire/economy/shop)
│   ├── query.md                 ← 조회 (status/list/rank/history)
│   └── synthesize.md            ← 합성
├── engine/
│   ├── will-engine.md           ← WILL 채굴·소각·이전
│   ├── xp-engine.md             ← XP 계산·보너스
│   └── breakthrough-engine.md   ← 돌파 조건 검증
└── references/
    ├── class-table.md           ← 클래스 상수
    ├── xp-table.md              ← XP 곡선·돌파 조건
    └── economy-rules.md         ← 반감기·가격표

데이터 (기존):
Projects/personas/
├── config.md                    ← 시스템 설계 원본 (읽기 전용 참조)
├── registry.json                ← 페르소나 DB (스킬이 갱신)
├── economy.json                 ← 채굴 현황 (스킬이 갱신)
├── cards/*.md                   ← 상세 카드 (스킬이 생성·갱신)
└── logs/*.jsonl                 ← 이력 (스킬이 append)
```
