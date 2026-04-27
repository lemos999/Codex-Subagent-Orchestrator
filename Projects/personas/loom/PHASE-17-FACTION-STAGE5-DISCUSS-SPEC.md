# [discuss] Phase 17 Φ-2 Faction Stage 5 — Anti-Collapse 메커니즘 후보 결정 토론 spec

> 토론 유형: `/discuss` 다중 라운드 (최대 3라운드)
> 엔진 배치: 6엔진 (Claude opus ×1, Codex gpt-5.5 xhigh ×5)
> ※ 본래 슬롯 5/6은 Gemini 3.1 pro 였으나, OAuth 계정에서 해당 모델 미가용(404, lite-preview만 가용)으로 Codex 계승 — role(창발 철학자/대안 탐색가)은 보존
> 산출 목표: Stage 5 `/spec`에 즉시 넘길 수 있는 후보 결정 (1순위 + 보조)
> 선행 조건: addendum-v2 머지 후 probe 1/3 PASS 유지 시 발동
> 토론 결과 ≠ 즉시 구현. 결과는 별도 `/spec` 사이클의 입력.

---

## 토론 목적·역할 3계층

**궁극 목적 (loom 전체)**
페르소나가 살아가는 과정에서 국가가 자연 탄생한다. Top-down 금지. 삶 → 유대 → 갈등 → 주권 선언의 인과 사슬.

**Phase 17 Stage 5 목적**
Stage 1~3 메커니즘이 5000틱 다수 Faction 공존을 만들지 못한 원인을 분석하고, **Charter v2 무파괴 + Φ-3 인계 계약 동결 + Phase 11~16 무파괴**를 유지하면서 collapse를 해결할 차세대 메커니즘 후보를 결정한다.

**본 토론 spec의 고유 역할**
"6명의 독립 사고가 같은 데이터를 보고 다른 결론을 내는지" 확인. 합의는 **다른 추론 경로로 도달한 결론의 일치**일 때만 의미가 있다. 표면 합의(전원 D 추천)는 가치 없음.

---

## 토론 주제 (Top-level Question)

> **5000틱 환경에서 active_factions_end >= 2 (3/3 seed)를 안정적으로 만족하기 위한 Stage 5 메커니즘은 무엇인가?**
>
> 부수 질문:
> 1. Stage 1~3 collapse의 진짜 근본 원인은 무엇인가? (4신호 가중치? 흡수 동역학? respawn timing?)
> 2. D / E / F / 가중치 조정 / 그 외 후보 중 어느 것이 최소 부작용으로 효과를 내는가?
> 3. Charter v2 [확정] 항목·D10 7종 API 시그니처를 무파괴로 유지할 수 있는가?
> 4. Stage 4 acceptance 기준 외에 추가로 측정해야 할 secondary 지표는?

---

## 사전 컨텍스트 (모든 엔진에 1라운드 시작 시 주입)

### 1. probe 1/3 PASS 결과 (Closure Report §1)

```
| seed | active_end | drift_ratio | gini   | faction_change | min_p50 | respawn | last_500_active>=2 | verdict |
|:----:|:----------:|:-----------:|:------:|:--------------:|:-------:|:-------:|:------------------:|:-------:|
|  7   |     2      |   86.24%    | 0.8014 |      298       |    3    |    8    |       1.0000       |  PASS   |
|  13  |     1      |   81.78%    | 0.6742 |      225       |    4    |    7    |       0.8333       |  FAIL   |
|  42  |     1      |   78.61%    | 0.7300 |      187       |    4    |    6    |       0.6667       |  FAIL   |
```

**핵심 관찰**:
- drift는 활발 (78~86%) — 이탈 자체는 막히지 않음.
- respawn 6~8회 발동 — Stage 3 C는 정상 작동.
- 그러나 2/3 seed는 결국 단일 Faction으로 수렴.
- seed 13/42의 `last_500_active>=2`가 0.67~0.83 → 후반 500틱에서 소수 Faction이 사라짐 = **respawn된 신규 Faction이 다시 흡수당하는 패턴**.

### 2. 4신호 가중치 (`ontology/layers.py:197-213`)

```
W_TERRITORY_SAME = 0.3   # 같은 territory 거주
W_TERRITORY_DIFF = 0.1   # 다른 territory 거주
W_TRUST          = 0.8
W_GRIEVANCE      = 0.6
W_PROXIMITY      = 0.4
DECAY            = 0.92
DRIFT_MARGIN_MIN = 0.3
DRIFT_MARGIN_RATIO = 0.15
```

**관찰**: W_TRUST(0.8) >> W_TERRITORY_SAME(0.3). trust 누적이 영토보다 큼. 거대 Faction은 trust 네트워크 효과로 신규를 빨아들임.

### 3. Stage 2 + Stage 3 메커니즘 (`ontology/layers.py:215-231`)

```
FACTION_SIZE_TAX_START = 0.3      # 30% 점유 초과분부터 score tax
FACTION_SIZE_TAX_MIN   = 0.3      # tax 하한
HOMEOSTASIS_LOW_THRESHOLD = 2     # active <= 2 시 drift 완화
HOMEOSTASIS_DRIFT_MARGIN_SCALE = 0.5
MINORITY_PERSISTENCE_MAX_MEMBERS = 2
MINORITY_PERSISTENCE_BOOST = 0.15
FOUNDER_RESPAWN_EVERY = 480
FOUNDER_RESPAWN_TARGET_ACTIVE = 2
```

**관찰**: respawn 후 새 Faction의 초기 점유율 = 1명 = 약 1/200 = 0.5%. size tax 0.3 임계 + minority boost 0.15는 **신생 Faction을 거대 Faction의 추격으로부터 보호하지 못함**.

### 4. faction_change source 분포

```
| source        | seed 7 | seed 13 | seed 42 |
| birth_founder |   11   |   10    |    9    |
| affiliation   |   30   |   31    |   31    |
| drift         |  257   |  184    |  147    |
| conflict      |    0   |    0    |    0    |
```

**관찰**: drift가 압도적. drift 후 어디로 가는가? 거대 Faction. → **drift 자체가 흡수 경로**. drift는 막히지 않았지만, drift 결과가 다양화되지 않음.

### 5. 후보 카탈로그 (Closure Report §6)

- **D. Territory locking / retention pressure**: 영토 거주가 길어질수록 territory 가중치 증가 (이탈 비용 ↑).
- **E. Contact correction**: `factions_in_contact(radius)` 결과가 일정 임계 미만이면 합병 보너스 / 초과면 분리 압력.
- **F. Join/leave asymmetry**: 가입은 쉬움, 이탈은 비용. 신규 Faction의 멤버 손실 둔화.
- **G. Respawn timing vs affiliation drift dominance**: respawn 직후 N틱 grace period (drift 면역).
- **H. (열린 후보)**: charter affinity / generational drift / founder lineage / SNN-driven affinity 등 — 슬롯 6(대안 탐색가, Codex)이 발굴.

### 6. 무파괴 제약 (모든 후보가 준수해야 함)

1. **Charter v2 [확정] #1~#9 무수정** — `PHASE-17-FACTION-CHARTER.md`. 특히 #8 D10 7종 API 시그니처 동결.
2. **D10 read-only 5채널 결정성** — addendum-v2 [필수] F 정의 유지 (`_faction_members_cache` 제외).
3. **Phase 11~16 무파괴** — Hard 5지표 (gold, public_works, food_stockpile, total_wealth, deaths).
4. **Φ-1 23/23 PASS 유지** — Land Charter 결정 무손상.
5. **SNN `n_neurons=1000` freeze** — `readout_weights_v1.npy` 호환.
6. **`FactionChangeSource` 4종 고정** — `birth_founder | affiliation | drift | conflict`.
7. **`CHARTER_PRIMITIVE_COUNT = (3, 5)`** 동결.
8. **결정성 RNG 단일 경로** — `_derive_rng()` 외 호출 금지.

---

## 엔진 배치 (6엔진)

| 슬롯 | 엔진 | 모델 | 역할 | 핵심 질문 |
|:----:|:----:|:----:|------|-----------|
| 1 | **Claude** | opus | **호환성·SSoT 파수꾼** | "이 후보가 Charter v2 / 5채널 결정성 / Phase 11~16을 깨지 않는가?" |
| 2 | **Codex** | gpt-5.5 xhigh | **구현 효율 분석가** | "각 후보의 구현 비용·복잡도·LOC 추정·성능 영향(ms/tick) 비교" |
| 3 | **Codex** | gpt-5.5 xhigh | **수치 분석가** | "4신호 가중치 조정 vs 메커니즘 추가 — 어느 쪽이 최소 부작용?" |
| 4 | **Codex** | gpt-5.5 xhigh | **회귀 위험 분석가** | "각 후보가 Stage 1/2/3 메커니즘과 어떻게 충돌·중복하는가?" |
| 5 | **Codex** | gpt-5.5 xhigh | **창발 철학자** (Gemini 계승) | "왜 collapse가 발생하는가? 자연 탄생 원칙에서 본 근본 원인은?" |
| 6 | **Codex** | gpt-5.5 xhigh | **대안 탐색가** (Gemini 계승) | "D/E/F/G 외 새로운 차원의 후보를 발굴하라 (charter affinity, generational drift, SNN-driven, …)" |

### 역할 차이의 의도

- 슬롯 2와 3은 같은 엔진이지만 **다른 관점** (구현 vs 수치). 같은 엔진의 여러 슬롯은 **명시적 역할 분리** 시에만 허용.
- 슬롯 5는 "왜?"를 끝까지 추적 (Rule 17~20 근본 원인 우선). "표면 후보 D/E/F"가 아니라 "그 후보들이 왜 필요해진 근본"을 묻는다.
- 슬롯 6은 "다른 차원" 발굴. 차원 전환 (Rule 12) 의 토론 내 구현.

### 5 Codex 동일 모델의 shallow consensus 위험 — 명시 차원 분리

본 토론은 6슬롯 중 5슬롯이 동일 엔진(Codex gpt-5.5 xhigh). 본래 Gemini 2슬롯이 다른 사고 패러다임(거대 컨텍스트·창발 추론) 차원을 담당했으나 모델 미가용으로 Codex 계승. 차원 다양성 보강 책임은 **role 텍스트**에 일임:
- 슬롯 2: 코드 hot path / LOC / ms/tick (구현·기술)
- 슬롯 3: 가중치 고정점 분석 / 정량 부작용 (수학·수치)
- 슬롯 4: Stage 1~3 충돌·중복 (회귀 위험)
- 슬롯 5: 인과·창발·근본 원인 (코드 무관, "왜")
- 슬롯 6: D/G 채택을 전제하지 않는 근본 대안 발굴 (반례·차원 전환)

### 같은 결론·다른 경로 검증

Round 3 시점에 6 엔진 중 4 이상이 같은 후보를 1순위로 추천했더라도, **추천 근거 경로가 모두 다른지** 모더레이터가 검증. 같은 근거(예: "drift가 너무 강함")에 5명이 모이면 **shallow consensus** — 슬롯 6의 대안을 한 번 더 강제 검토. 5/6 슬롯이 Codex로 통합된 이번 구성에서는 모더레이터의 shallow consensus 차단이 특히 중요.

---

## 라운드 구조

### Round 1 — 독립 의견 (모더레이터 개입 없음)

각 엔진에 동일한 사전 컨텍스트(§1~§6) + 자기 역할 질문을 입력. 다른 엔진의 응답은 보지 않음.

산출:
1. **현 상태 진단** (1단락): probe 1/3 결과의 의미·해석.
2. **근본 원인 가설** (1~3개): "왜 collapse가 일어나는가?" — 표면적 원인 아닌 한 단계 더 들어간 원인.
3. **추천 후보** (1순위 + 보조 1~2): D/E/F/G/H 중 또는 신규 후보. 각 후보별 (a) 메커니즘 본문, (b) 무파괴 제약 충돌 분석, (c) 예상 구현 LOC·성능 영향.
4. **반대 주장에 대한 사전 방어**: "내 추천을 반대하는 사람은 X라고 말할 텐데, 내 답은 Y이다."
5. **수렴 라벨 표기**: `[AGREE/PARTIAL/DISAGREE]` (자기 신뢰도, 상대 응답 미참조 상태).

각 응답 길이: ~500~1500자.

### Round 2 — 쟁점 집중 + WKI 마이크로 컨텍스트

모더레이터 (Claude haiku) 가 Round 1 결과를 다음 형식으로 정리:

```
## Round 1 합의점
- ...

## Round 1 쟁점
1. <쟁점 명> — 슬롯 X vs 슬롯 Y
2. ...

## Round 2 집중 질문
- 슬롯 X에게: ... (당신의 근거 A에 대해, 슬롯 Y의 반박 B를 어떻게 보는가?)
- ...
```

각 엔진은 **자기 슬롯 번호와 집중 질문만** 받음 (전체 라운드 1 결과를 보지 않음, 컨텍스트 절감 + 결론 동조 방지).

WKI 마이크로 컨텍스트: 쟁점 관련 코드·문서를 모더레이터가 발췌해 함께 주입. 예: "쟁점 1이 `_compute_affiliation_tick`의 territory 가중치 계산이라면, 해당 함수 본문(line 1235~1280)을 함께 주입."

산출:
1. **자기 입장 재확인 또는 수정** (1단락).
2. **상대 반박에 대한 응답**.
3. **수렴 라벨 갱신**.

### Round 3 — 최종 결론 (또는 부분 합의)

모더레이터가 Round 2 종료 시점에 수렴 판정:

- **AGREE 4+**: Round 3 생략, 합의안 작성 단계로 이동.
- **PARTIAL**: Round 3 진행. 합의된 부분 lock, 미합의 부분만 쟁점화.
- **DISAGREE 다수**: Round 3 진행. **차원 전환**: 모더레이터가 "이 토론의 전제 자체를 의심하라"는 메타 질문을 추가.

Round 3 산출:
1. 최종 결론 (1순위 후보 + 메커니즘 본문 윤곽).
2. 보조 후보 (PARTIAL 시 또는 1순위 실패 시 fallback).
3. 미합의 항목 (있으면 [미결]로 명시).
4. **추천 다음 액션**: `/spec` 입력으로 즉시 사용 가능한 형태로 정리.

---

## 합의 도출 기준 (모더레이터 판정)

### AGREE 조건 (모두 충족)

1. 6 엔진 중 **4 이상**이 같은 후보를 1순위로 추천.
2. 추천 근거가 **2개 이상의 다른 추론 경로**로 도달 (구현 효율 + 회귀 안전 + 창발 원칙 등).
3. 무파괴 제약 8종 모두 충돌 없음 (슬롯 1이 명시적으로 PASS).
4. 슬롯 5(창발 철학자)가 "근본 원인을 해결한다"고 동의.

### PARTIAL 조건

- 1순위는 합의되었으나 보조 후보가 갈림 → 1순위만 lock.
- 메커니즘 본문은 합의되었으나 상수 값(예: respawn grace ticks)이 갈림 → 본문 lock, 상수는 [미결].
- 무파괴 제약 충돌 가능성이 슬롯 1에서 PARTIAL → 슬롯 1의 의견을 [필수 검증 항목]으로 spec에 반영.

### DISAGREE 조건

- 1순위 후보가 갈리고 (3-3 또는 2-2-2 분포), 추론 경로도 같은 차원에서만 다툼.
- → **메타 질문**: "이 토론의 전제 자체를 의심하라."
  - "Stage 1~3 메커니즘이 잘못된 추상화 수준에 있는가?"
  - "5000틱·3시드 acceptance가 옳은 게이트인가?"
  - "Φ-2 단계에서 collapse를 해결할 수 있는가, Φ-3에서 자연 해소되는가?"

### Shallow Consensus 차단

- 6 엔진 중 5+가 같은 후보 + 같은 근거 → 모더레이터는 **AGREE로 판정하지 않음**.
- 슬롯 6 대안 탐색가의 후보를 한 번 더 검토하라는 R3 추가 질문을 발행.

---

## 산출물 (토론 종료 후 생성)

### 1. 토론 운영 산출물 (자동)

위치: `subagent-runs/discuss/phase17-stage5-anticollapse-2026-04-XX/`

- `discussion-manifest.md` — 토론 메타 (참가자·라운드·시각).
- `discussion-summary.md` — 합의안 본문.
- `conclusion.md` — 최종 결론 (PASS/PARTIAL/DISAGREE 라벨).
- `round-1/`, `round-2/`, `round-3/` (라운드 진행 시) — 각 슬롯 응답 + 모더레이터 요약.
- `wki-context-snapshot.md` — 사전 컨텍스트(§1~§6) 고정 사본.

### 2. /spec 입력용 결정 사항 (수동 정리)

위치: `Projects/personas/loom/PHASE-17-FACTION-STAGE5-DECISIONS.md` (토론 후 작성)

내용:
- 1순위 후보 메커니즘 본문 ([확정]).
- 보조 후보 ([보류]).
- 무파괴 제약 충돌 분석 결과 ([확정]).
- 미합의 항목 ([미결]).
- Stage 5 spec 작성 시 [필수] / [선택] / [금지] 윤곽.

### 3. Stage 5 본격 spec (별도 사이클)

`Projects/personas/loom/PHASE-17-FACTION-STAGE5-SPEC.md` — Decisions 문서를 입력으로 `/spec` 사이클 진행.

---

## /discuss 실행 명령 (참고)

본 spec은 **토론 운영 가이드**. 실제 실행은 사용자가 다음 중 선택:

### 옵션 A: CLI 직접 실행 (권장 — JSON spec)

토론 spec JSON 생성 후 `discuss-cli`에 전달:

```bash
cd c:/Users/haj/projects/subagent-orchestrator
node packages/launcher/dist/discussion/discuss-cli.js --spec Projects/personas/loom/phase17-stage5-discuss.json
```

JSON spec 예시 (참고용 — 실제 작성은 토론 시작 시):

```json
{
  "topic": "Phase 17 Φ-2 Faction Stage 5 — Anti-Collapse 메커니즘 후보 결정",
  "max_rounds": 3,
  "context_files": [
    "Projects/personas/loom/PHASE-17-FACTION-STAGE4-CLOSURE-REPORT.md",
    "Projects/personas/loom/PHASE-17-FACTION-CHARTER.md",
    "Projects/personas/loom/PHASE-17-STAGE3-ANTI-COLLAPSE-SPEC.md",
    "Projects/personas/loom/PHASE-17-FACTION-STAGE5-DISCUSS-SPEC.md"
  ],
  "participants": [
    { "engine": "claude", "model": "opus",          "role": "호환성·SSoT 파수꾼" },
    { "engine": "codex",  "model": "gpt-5.5-xhigh", "role": "구현 효율 분석가" },
    { "engine": "codex",  "model": "gpt-5.5-xhigh", "role": "수치 분석가 (4신호 가중치)" },
    { "engine": "codex",  "model": "gpt-5.5-xhigh", "role": "회귀 위험 분석가" },
    { "engine": "codex", "model": "gpt-5.5", "role": "창발 철학자 (근본 원인) — Gemini 슬롯 5 계승" },
    { "engine": "codex", "model": "gpt-5.5", "role": "대안 탐색가 (차원 전환) — Gemini 슬롯 6 계승" }
  ],
  "moderator": { "engine": "claude", "model": "haiku" },
  "convergence": { "agree_threshold": 4, "shallow_check": true }
}
```

### 옵션 B: 인라인 호출 (간이)

```
/discuss Phase 17 Stage 5 anti-collapse 메커니즘 후보 (D/E/F/G/H) 결정 — Codex 5명 (gpt-5.5 xhigh, 슬롯 5/6은 Gemini 계승), Claude opus 1명
```

옵션 B는 본 spec의 사전 컨텍스트 §1~§6을 토론 시작 메시지에 그대로 붙여 넣을 것 (자동 주입 안 됨).

---

## 토론 운영 원칙

1. **Round 1은 진짜 독립**: 다른 엔진 응답을 보지 않은 상태에서 자기 판단. 동조 압박 없음.
2. **모더레이터는 판정만**: 슬롯 7 (Claude haiku) 은 토론 참여 금지. 라벨링·쟁점 정리만.
3. **WKI는 한 번 고정**: Round 1 시작 시 사전 컨텍스트 §1~§6 스냅샷. Round 2~3에서 컨텍스트 변경 금지 (단 모더레이터가 발췌하는 마이크로 컨텍스트는 예외).
4. **DISAGREE 환영**: 합의가 안 되는 것이 데이터. "AGREE 못 했으니 실패"가 아님. 미합의 자체를 산출물로 기록.
5. **부분 실행 우선** (Rule 15): 토론이 막히면 차원 전환·전제 반전 중 **하나라도 시도** 후 부분 결론을 낸다.
6. **외부 엔진 stdin pipe**: Codex/Gemini 호출 시 긴 프롬프트는 `cat | codex exec --full-auto` / `cat | npx @google/gemini-cli --yolo`. 인자 방식 금지.
7. **결과는 즉시 구현 아님**: 토론 결론은 **`/spec` 사이클의 입력**. 직접 코드 수정으로 가지 않음.

---

## 중지·재개

- 사용자가 라운드 사이에 **stop** 명령 시 토론 종료, 그 시점까지의 부분 결론으로 산출.
- **continue** 시 다음 라운드 진행.
- **guide "지시"** 시 다음 라운드 모더레이터 질문에 사용자 지시 추가.

---

## 본 spec의 검증 (작성자 자체)

- [x] 사전 컨텍스트 §1~§6에 probe 결과·4신호 가중치·Stage 1~3 상수·후보 카탈로그·무파괴 제약 모두 포함.
- [x] 6 엔진 역할 분리가 **명시적** (같은 엔진 여러 슬롯이지만 다른 질문).
- [x] 합의 기준이 **shallow consensus 차단** 포함.
- [x] DISAGREE 환영 + 차원 전환 메타 질문 명시.
- [x] 산출물이 **/spec 입력**으로 직결되는 형태.
- [x] 무파괴 제약 8종이 모든 후보의 필수 검증 대상으로 박힘.
- [x] 외부 엔진 stdin pipe 원칙 명시.
- [x] 토론 결과 ≠ 즉시 구현 명시.
